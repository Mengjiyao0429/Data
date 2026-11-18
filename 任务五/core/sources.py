# -*- coding: utf-8 -*-
"""任务五 · 需求驱动采集适配层

一个"需求"进来，按需求里的关键词与来源清单，去各公开渠道取回真实记录。
四个实时适配器（均可免鉴权调用）+ 一个本地回放适配器（离线兜底）：

  stackoverflow : api.stackexchange.com /2.3/search/advanced  (sort=votes, filter=withbody)
  hackernews    : hn.algolia.com /api/v1/search                (tags=comment)
  github        : api.github.com /search/repositories          (sort=stars, created 过滤)
  csdn          : so.csdn.net /api/v3/search                   (站内搜索接口)
  replay        : 任务一已采集语料（8038 条快照）按关键词重排 —— 仅用于断网演示，
                  记录里会明确标注"本地语料回放"，不会伪装成实时采集

统一记录字段：
  source, url, title, body, published, stars, views, likes, comments, favorites, heat_text, via
"""
import gzip
import html
import io
import json
import os
import re
import socket
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UA = {
    "User-Agent": "ai-opportunity-system/1.0 (dataset research; contact: local)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
}

PROXY_ENV = "T5_PROXY"


def proxy_url():
    """优先环境变量，其次探测本机 7890（Clash），都没有就走直连。"""
    p = (os.environ.get(PROXY_ENV) or "").strip()
    if p:
        return p
    try:
        s = socket.create_connection(("127.0.0.1", 7890), 0.6)
        s.close()
        return "http://127.0.0.1:7890"
    except OSError:
        return ""


def _opener(proxy):
    if proxy:
        return urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener()


def fetch(url, headers=None, timeout=25, proxy=None, retries=2):
    h = dict(UA)
    h.update(headers or {})
    last = None
    for attempt in range(retries + 1):
        try:
            resp = _opener(proxy).open(urllib.request.Request(url, headers=h), timeout=timeout)
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return resp.status, raw
        except Exception as e:  # noqa: BLE001  —— 网络异常统一降级为 None
            last = e
            time.sleep(1.2 * (attempt + 1))
    return 0, str(last).encode("utf-8", "ignore")


def strip_html(text):
    text = html.unescape(text or "")
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>|</p>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_ts(v):
    """把各接口的时间字段统一成 YYYY-MM-DD。"""
    if v in (None, ""):
        return ""
    if isinstance(v, (int, float)):
        return time.strftime("%Y-%m-%d", time.localtime(int(v)))
    s = str(v)
    if s.isdigit():
        return time.strftime("%Y-%m-%d", time.localtime(int(s)))
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return m.group(0)
    return ""


def rec(source, url, title, body, published, heat_text="", stars=None, views=None,
        likes=None, comments=None, favorites=None, via="live"):
    return {
        "source": source, "url": url, "title": strip_html(title), "body": strip_html(body),
        "published": parse_ts(published), "stars": stars, "views": views, "likes": likes,
        "comments": comments, "favorites": favorites,
        "heat_text": heat_text, "via": via,
    }


# ---------------- Stack Overflow ----------------
def collect_stackoverflow(query, limit=200, proxy=None, fromdate=1609459200):
    out, note = [], []
    pages = min(3, max(1, (limit + 99) // 100))
    for page in range(1, pages + 1):
        url = "https://api.stackexchange.com/2.3/search/advanced?" + urllib.parse.urlencode({
            "order": "desc", "sort": "votes", "q": query, "site": "stackoverflow",
            "pagesize": 100, "page": page, "fromdate": fromdate, "filter": "withbody"})
        st, raw = fetch(url, proxy=proxy)
        if st != 200:
            note.append("stackoverflow p%d 失败(status=%s)" % (page, st))
            break
        try:
            d = json.loads(raw.decode("utf-8", "ignore"))
        except ValueError:
            note.append("stackoverflow p%d 返回非 JSON" % page)
            break
        if d.get("backoff"):
            time.sleep(min(10, d["backoff"]))
        for it in d.get("items", []):
            if not it.get("link"):
                continue
            out.append(rec(
                "Stack Overflow", it["link"], it.get("title", ""), it.get("body", ""),
                it.get("creation_date"),
                "浏览%s、点赞%s、回答%s" % (it.get("view_count"), it.get("score"), it.get("answer_count")),
                views=it.get("view_count"), likes=it.get("score"),
                comments=it.get("answer_count"), favorites=it.get("favorite_count")))
        if not d.get("has_more") or len(out) >= limit:
            break
        time.sleep(1.2)
    return out[:limit], note


# ---------------- Hacker News ----------------
def collect_hackernews(query, limit=200, proxy=None):
    out, note = [], []
    for page in range(0, 2):
        url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode({
            "query": query, "tags": "comment", "hitsPerPage": 100, "page": page,
            "numericFilters": "created_at_i>1704067200"})
        st, raw = fetch(url, proxy=proxy)
        if st != 200:
            note.append("hackernews p%d 失败(status=%s)" % (page, st))
            break
        try:
            d = json.loads(raw.decode("utf-8", "ignore"))
        except ValueError:
            note.append("hackernews 返回非 JSON")
            break
        for h in d.get("hits", []):
            oid = h.get("objectID")
            if not oid:
                continue
            title = h.get("story_title") or h.get("title") or "Hacker News 讨论"
            body = h.get("comment_text") or h.get("story_text") or ""
            out.append(rec("Hacker News", "https://news.ycombinator.com/item?id=%s" % oid,
                           title, body, h.get("created_at"),
                           "HN 讨论（所在帖 %s 分）" % (h.get("points") or 0),
                           likes=h.get("points"), comments=h.get("num_comments")))
        if len(out) >= limit:
            break
        time.sleep(1.0)
    return out[:limit], note


# ---------------- GitHub ----------------
def collect_github(query, limit=100, proxy=None, created=">2024-01-01"):
    out, note = [], []
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({
        "q": "%s created:%s" % (query, created), "sort": "stars", "order": "desc",
        "per_page": min(100, limit), "page": 1})
    st, raw = fetch(url, headers={"Accept": "application/vnd.github+json"}, proxy=proxy)
    if st != 200:
        note.append("github 失败(status=%s)" % st)
        return out, note
    try:
        d = json.loads(raw.decode("utf-8", "ignore"))
    except ValueError:
        note.append("github 返回非 JSON")
        return out, note
    for it in d.get("items", []):
        if not it.get("html_url"):
            continue
        out.append(rec("GitHub", it["html_url"], it.get("full_name", ""), it.get("description") or "",
                       it.get("created_at"), "星标%s、议题%s" % (it.get("stargazers_count"), it.get("open_issues_count")),
                       stars=it.get("stargazers_count"), comments=it.get("open_issues_count")))
    return out[:limit], note


# ---------------- CSDN ----------------
def collect_csdn(query, limit=100, proxy=None):
    out, note = [], []
    for p in range(1, 3):
        url = ("https://so.csdn.net/api/v3/search?q=" + urllib.parse.quote(query) +
               "&t=blog&p=%d&s=0&tm=0&lv=-1&ft=0&l=&u=&ct=-1&pnt=-1&ry=-1&ss=-1&dct=-1"
               "&vco=-1&cc=-1&sc=-1&sk=&c=0" % p)
        st, raw = fetch(url, headers={"Referer": "https://so.csdn.net/so/search"}, proxy=proxy)
        if st != 200:
            note.append("csdn p%d 失败(status=%s)" % (p, st))
            break
        try:
            d = json.loads(raw.decode("utf-8", "ignore"))
        except ValueError:
            note.append("csdn 返回非 JSON")
            break
        items = (d.get("data") or {}).get("items") or d.get("result_vos") or []
        for it in items:
            u = (it.get("url") or "").split("?")[0]
            if not u:
                continue
            out.append(rec("CSDN", u, it.get("title", ""),
                           it.get("description") or it.get("digest") or "",
                           it.get("create_time_str") or it.get("create_time"),
                           "浏览%s、点赞%s、评论%s" % (it.get("viewcount"), it.get("diggcount"), it.get("commentcount")),
                           views=it.get("viewcount"), likes=it.get("diggcount"), comments=it.get("commentcount"),
                           favorites=it.get("collectcount")))
        if len(out) >= limit:
            break
        time.sleep(1.2)
    return out[:limit], note


# ---------------- 本地语料回放（离线兜底） ----------------
def collect_replay(query, limit=200, proxy=None):
    """从任务一已采集的 8038 条快照里，按需求关键词重排后取前 limit 条。

    用途：断网 / 接口限流时的可运行兜底。记录 via="replay"，界面与报告会明确标注，
    不冒充新采集。
    """
    import csv
    csv_path = os.path.join(BASE, "任务一", "结果", "result1.csv")
    text_dir = os.path.join(BASE, "任务一", "结果", "text")
    if not os.path.exists(csv_path):
        return [], ["本地语料不存在，回放不可用"]
    terms = [t.lower() for t in re.split(r"[\s,，、/]+", query) if len(t) >= 2]
    generic = {"ai", "aigc", "人工智能", "智能", "大模型", "模型", "llm", "gpt", "机器学习"}
    specific = [t for t in terms if t not in generic]
    terms = specific or terms
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
    scored = []
    for r in rows:
        fn = os.path.basename((r.get("内容") or "").replace("/", os.sep))
        p = os.path.join(text_dir, fn)
        if not os.path.exists(p):
            continue
        raw = open(p, encoding="utf-8", errors="ignore").read()
        title = raw.split("\n", 1)[0].lstrip("# ").strip()
        body = raw.split("## 正文", 1)[-1].strip()
        hay = (title + " " + body).lower()
        hit = sum(1 for t in terms if t in hay)
        if terms and hit == 0:
            continue
        scored.append((hit, r, title, body, fn))
    scored.sort(key=lambda x: -x[0])
    out = []
    for hit, r, title, body, fn in scored[:limit]:
        out.append(rec(
            "本地语料回放（%s，%s）" % (r["来源网站名称"], r["采集批次号"]),
            r.get("来源链接", ""), title, body, r.get("发布时间"),
            "星标%s 浏览%s 点赞%s" % (r.get("星标数"), r.get("浏览数"), r.get("点赞数")),
            stars=int(float(r.get("星标数") or 0)), views=int(float(r.get("浏览数") or 0)),
            likes=int(float(r.get("点赞数") or 0)), comments=int(float(r.get("评论数") or 0)),
            favorites=int(float(r.get("收藏数") or 0)), via="replay"))
    return out, ["回放命中 %d 条（共扫描 %d 条）" % (len(out), len(scored))]


ADAPTERS = {
    "stackoverflow": ("Stack Overflow", collect_stackoverflow),
    "hackernews": ("Hacker News", collect_hackernews),
    "github": ("GitHub", collect_github),
    "csdn": ("CSDN", collect_csdn),
    "replay": ("本地语料回放", collect_replay),
}

SOURCE_LABELS = {
    "stackoverflow": "Stack Overflow（技术问答·需求侧）",
    "hackernews": "Hacker News（英文讨论·需求侧）",
    "github": "GitHub（开源仓库·供给侧）",
    "csdn": "CSDN（中文技术社区）",
    "replay": "本地语料回放（断网兜底）",
}


def collect(query, sources, limit_per_source=200, proxy=None, log=None):
    """按来源清单采集，返回 (records, notes)。"""
    log = log or (lambda *a: None)
    records, notes = [], []
    proxy = proxy if proxy is not None else proxy_url()
    for key in sources:
        if key not in ADAPTERS:
            notes.append("未知来源 %s，已跳过" % key)
            continue
        label, fn = ADAPTERS[key]
        log("开始采集 %s（关键词：%s）" % (label, query))
        try:
            items, note = fn(query, limit=limit_per_source, proxy=proxy)
        except Exception as e:  # noqa: BLE001
            items, note = [], ["%s 适配器异常：%s" % (label, e)]
        for it in items:
            it["source_key"] = key
            it["query"] = query
        records.extend(items)
        notes.extend(note)
        log("%s 取回 %d 条%s" % (label, len(items), ("；" + "；".join(note)) if note else ""))
    return records, notes


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "ai coding assistant"
    srcs = (sys.argv[2].split(",") if len(sys.argv) > 2 else ["stackoverflow", "hackernews", "github", "csdn"])
    got, nt = collect(q, srcs, limit_per_source=50, log=print)
    print("total", len(got), "notes", nt)
