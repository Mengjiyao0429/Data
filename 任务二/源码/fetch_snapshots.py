# -*- coding: utf-8 -*-
"""补齐任务一快照缺失：从来源链接回取公开页面正文，重建 text/<批次>_<编号>.md。

严格约束
--------
* 只做"取回公开页面正文 -> 清洗 -> 落快照"，不修改 result1.xlsx 任何字段。
* 失败的记录不编造内容，保持缺失，由 result2_exporter 走降级通道并留痕。
* 输出 snapshots/_fetch_log.jsonl 记录每条的取回状态（fetched/missing/error）。

用法：
    python fetch_snapshots.py            # 取回全部缺失快照
    python fetch_snapshots.py --limit 20 # 试运行
"""
from __future__ import annotations

import gzip
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from result2_exporter import load_result1  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
LOG = os.path.join(HERE, "_fetch_log.jsonl")


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return r.status, data.decode("utf-8", errors="ignore")


def strip_tags(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</h[1-6]>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\u00a0]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def clean_text(t):
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"[ \t\u00a0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


# ---------------- 各来源适配器 ----------------
def fetch_stackoverflow(url):
    m = re.search(r"/questions/(\d+)", url)
    if not m:
        return None
    qid = m.group(1)
    _, d = http_get(f"https://api.stackexchange.com/2.3/questions/{qid}"
                    f"?site=stackoverflow&filter=withbody")
    items = json.loads(d).get("items") or []
    if not items:
        return None
    it = items[0]
    return it["title"], strip_tags(it.get("body_html") or it.get("body") or "")


def fetch_generic_meta(url):
    """通用回退：抓 og:title / og:description / <title> / meta description。"""
    _, page = http_get(url)
    def meta(name):
        mm = re.search(rf'<meta[^>]+(?:property|name)=["\']{name}["\'][^>]+content=["\'](.*?)["\']',
                       page, re.S | re.I)
        if not mm:
            mm = re.search(rf'<meta[^>]+content=["\'](.*?)["\'][^>]+(?:property|name)=["\']{name}["\']',
                           page, re.S | re.I)
        return html.unescape(mm.group(1)).strip() if mm else ""
    title = meta("og:title")
    if not title:
        mm = re.search(r"<title>(.*?)</title>", page, re.S | re.I)
        title = html.unescape(mm.group(1)).strip() if mm else ""
    body = meta("og:description") or meta("description")
    # 正文补充：取 <article> 或主要段落
    paras = re.findall(r"<p[^>]*>(.*?)</p>", page, re.S | re.I)
    extra = " ".join(strip_tags(p) for p in paras[:40])
    extra = re.sub(r"\s+", " ", extra)[:3000]
    text = (body + "\n" + extra).strip() if body else extra
    if not title and not text:
        return None
    return title, clean_text(text)


def fetch_github_meta(url):
    m = re.match(r"https://github\.com/([^/]+)/([^/#?]+)", url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2).replace(".git", "")
    api = f"https://api.github.com/repos/{owner}/{repo}"
    _, d = http_get(api)
    j = json.loads(d)
    topics = ", ".join(j.get("topics") or [])
    text = " ".join(x for x in [j.get("description") or "", topics,
                                "topics: " + topics if topics else ""] if x)
    return f"{owner}/{repo}", clean_text(text)


ADAPTERS = {
    "Stack Overflow": fetch_stackoverflow,
    "GitHub": fetch_github_meta,
}


def build_snapshot(rec):
    url = rec["url"]
    host = "Stack Overflow" if "stackoverflow.com" in url else (
        "GitHub" if "github.com" in url else rec["source"])
    fn = ADAPTERS.get(host, fetch_generic_meta)
    res = None
    errs = []
    for attempt, fetcher in enumerate([fn, fetch_generic_meta]):
        try:
            res = fetcher(url)
            if res and (res[0] or res[1]):
                break
        except Exception as e:  # noqa: BLE001
            errs.append(f"{fetcher.__name__}:{e}")
        time.sleep(0.5)
    if not res:
        return None, "; ".join(errs)
    title, body = res
    title = title.strip()
    body = (body or "").strip()
    # 通用回退若正文过短，用标题+描述构成可用文本
    md = (f"# {title}\n\n{body}\n\n"
          f"> 来源：{rec['source']} | {rec['url']}\n"
          f"> 发布时间：{rec['publish_time']} | 热度：{rec['heat']}\n")
    return md, ""


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    _, records = load_result1()
    os.makedirs(os.path.join(ROOT, "text"), exist_ok=True)
    log = open(LOG, "w", encoding="utf-8")
    todo = [r for r in records
            if not os.path.exists(os.path.join(ROOT, r["content_ref"].replace("\\", os.sep)))]
    if limit:
        todo = todo[:limit]
    ok = fail = 0
    for i, rec in enumerate(todo, 1):
        md, err = build_snapshot(rec)
        path = os.path.join(ROOT, rec["content_ref"].replace("\\", os.sep))
        if md:
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)
            status = "fetched"
            ok += 1
        else:
            status = "missing"
            fail += 1
        log.write(json.dumps({"key": rec["key"], "url": rec["url"], "status": status,
                              "error": err, "chars": len(md) if md else 0},
                             ensure_ascii=False) + "\n")
        log.flush()
        print(i, rec["key"], status, len(md) if md else 0, err[:80], flush=True)
        time.sleep(0.4)  # 控制访问频率，避免对目标站点造成压力
    log.close()
    print(f"done: fetched={ok} missing={fail} total={len(todo)}")


if __name__ == "__main__":
    main()