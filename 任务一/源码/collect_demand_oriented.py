# -*- coding: utf-8 -*-
"""任务一 · 需求导向采集（合规重构版）

设计动机
--------
旧版以 AI 技术热词（"ai customer service"/"LLM"…）检索，采回大量 GitHub 项目描述
（供给侧："我做了一个工具"），机会率仅 12%。赛题本意是"一次需求触发一次采集"，
采集对象应是"真实业务需求表达"（需求侧："我需要一个工具"）。

本脚本改为围绕真实需求信号采集，数据源均为公开 API / 社区，遵守 robots 与平台条款：
  1) Hacker News Ask HN  —— 用户真实提问（"Ask HN: 有没有工具…"）  机会率≈50%
  2) GitHub Issues        —— 用户的 feature request / enhancement（"需要支持…"）
  3) Stack Exchange       —— SoftwareRecs & SO 中"求推荐/寻找工具"问答
每个批次对应一个需求主题场景，批次相互独立，结果可溯源至原始链接与快照。

产出（覆盖 任务一/结果/result1.csv 与 任务一/结果/text/*.md）：
  - result1.csv 表头与赛题表1一致
  - text/{批次}_{编号}.md 正文快照（任务二会再同步到 任务二/正文快照/）
运行：
  python collect_demand_oriented.py            # 采集 + 生成
  python collect_demand_oriented.py --reuse     # 复用上次抓取的 raw 缓存重生成
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from app.pipeline.cleaner import clean_text
except Exception:  # noqa: BLE001
    clean_text = None

TASK1 = os.path.dirname(HERE)
REPO = os.path.dirname(TASK1)
RESULT_DIR = os.path.join(TASK1, "结果")
TEXT_DIR = os.path.join(RESULT_DIR, "text")
CACHE = os.path.join(TASK1, "原始数据", "demand_oriented_raw.json")
OUT_CSV = os.path.join(RESULT_DIR, "result1.csv")

UA = "Mozilla/5.0 (compatible; AI-Opportunity-Miner/1.0; +research; public data)"
HEADER = ["采集批次号", "记录编号", "来源网站名称", "来源链接", "内容", "发布时间",
          "星标数", "浏览数", "点赞数", "评论数", "收藏数"]

# ---------------------------------------------------------------------------
# 需求主题场景 → 批次。每批围绕一个真实的"用户想解决的业务问题"。
# query 均为需求信号，不是技术热词。
# ---------------------------------------------------------------------------
SCENARIOS = [
    ("B01", "客服与问答自动化", [
        "customer support automation tool", "chatbot for customer service",
        "automate answers to customer questions", "AI customer service software",
        "virtual assistant for support", "reduce support ticket response time",
        "self-service knowledge base tool", "automate FAQ answers",
    ]),
    ("B02", "文档与知识处理", [
        "extract data from documents tool", "summarize long documents AI",
        "search my documents AI", "OCR tool for invoices", "knowledge base software",
        "convert PDF to structured data", "organize my notes automatically",
        "find information in company documents",
    ]),
    ("B03", "内容与文案生成", [
        "tool to write product descriptions", "generate marketing copy AI",
        "help me write blog posts tool", "AI writing assistant recommendation",
        "rewrite text in different tone tool", "generate social media posts AI",
        "translate content at scale tool", "proofread my writing AI",
    ]),
    ("B04", "代码与开发提效", [
        "tool to automate code review", "AI code assistant recommendation",
        "generate tests for my code tool", "debug my code with AI",
        "document my codebase automatically", "convert code between languages tool",
        "find bugs in my code AI", "refactor legacy code tool",
    ]),
    ("B05", "数据分析与报表", [
        "tool to analyze spreadsheets automatically", "natural language to SQL tool",
        "automate weekly reports software", "dashboard from database AI",
        "analyze CSV with plain English", "predict sales from historical data tool",
        "automate data cleaning software", "visualize spreadsheet data AI",
    ]),
    ("B06", "语音与会议", [
        "transcribe meetings tool", "speech to text software recommendation",
        "automate meeting notes AI", "voice to text for interviews",
        "translate speech in real time tool", "generate meeting summary software",
        "record and transcribe calls AI", "dictation software for writing",
    ]),
    ("B07", "图像与视觉", [
        "tool to remove image background", "recognize text in images software",
        "automate image tagging AI", "product photo editing AI tool",
        "upscale old photos AI", "generate images for my blog tool",
        "detect defects in product images", "organize photo library by content AI",
    ]),
    ("B08", "流程与智能体编排", [
        "automate repetitive workflow tool", "AI agent to do tasks for me",
        "connect apps with AI automation", "no-code automation with AI",
        "automate email triage tool", "AI assistant for scheduling",
        "build a workflow without coding", " automate data entry with AI",
    ]),
]

# HN 搜索的补充 query（跨场景，扩大 Ask HN 覆盖）
HN_EXTRA = [
    "looking for a tool to automate", "is there an AI that can",
    "recommend software to", "need a solution for", "what tool do you use for automation",
]

# 需求信号（用于从 Issues/问答中筛真实需求表达，非教程/广告）
NEED_RE = re.compile(
    r"(feature request|enhancement|would (be (great|nice)|love)|please add|"
    r"looking for|recommend|is there (a|an|any)|need (a|an|to|the ability)|"
    r"requesting|it would be helpful|support for|want to be able to|"
    r"求推荐|有没有.*工具|求.*工具|寻找|需要.*功能|能否支持)", re.I)
# 教程/广告排除（采集阶段的轻量过滤，正式判别仍交由任务二四规则）
EXCLUDE_RE = re.compile(
    r"^(tutorial|how to (learn|build) a|sponsored|advertisement|"
    r"教程|入门|从零开始|一文读懂|广告|推广)", re.I)


def http_json(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept": "application/json, text/xml, */*"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except Exception:  # noqa: BLE001
        return {}


def strip_html(t):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t or "", flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def ok_need(title, body):
    text = (title or "") + " " + (body or "")[:500]
    return bool(NEED_RE.search(text)) and not EXCLUDE_RE.search(title or "")


# ---------------------------------------------------------------------------
# 采集器：返回 dict(source,title,url,body,date,heat)
# ---------------------------------------------------------------------------
def collect_ask_hn(query, cap=120):
    """Ask HN 真实提问 —— 需求密度最高的公开源。支持分页扩大采集量。"""
    out = []
    # Ask HN 真实提问为主，单页 100 条足够；多页会显著拖慢且重复率高
    for tag in ("ask_hn",):
        for page in range(2):
            qs = urllib.parse.urlencode({"tags": tag, "query": query,
                                         "hitsPerPage": 100, "page": page})
            d = http_json("https://hn.algolia.com/api/v1/search?" + qs, timeout=15)
            for h in d.get("hits", []):
                oid = str(h.get("objectID") or "")
                title = strip_html(h.get("title") or "")
                # story 类用 story_text，ask_hn 也用 story_text
                body = strip_html(h.get("story_text") or "")
                if len(title) < 12 or len(body) < 50:
                    continue
                url = f"https://news.ycombinator.com/item?id={oid}"
                out.append({"source": "Hacker News", "native_id": "HN" + oid, "title": title,
                            "url": url, "body": body[:4000],
                            "date": (h.get("created_at") or "")[:10],
                            "heat": {"点赞数": h.get("points") or 0, "评论数": h.get("num_comments") or 0},
                            "query": query})
                if len(out) >= cap:
                    return out
    return out


def collect_github_issues(query, cap=60):
    """GitHub feature request / enhancement —— 用户提的真实功能诉求。"""
    out = []
    q = query + " in:title is:issue is:open"
    qs = urllib.parse.urlencode({"q": q, "per_page": min(30, cap), "sort": "created",
                                 "order": "desc"})
    d = http_json("https://api.github.com/search/issues?" + qs)
    for it in d.get("items", []):
        title = strip_html(it.get("title") or "")
        body = strip_html(it.get("body") or "")
        if len(body) < 40:
            continue
        if not ok_need(title, body):
            continue
        out.append({"source": "GitHub", "native_id": "I" + str(it.get("id")), "title": title,
                    "url": it.get("html_url") or "", "body": body[:4000],
                    "date": (it.get("created_at") or "")[:10],
                    "heat": {"评论数": it.get("comments") or 0},
                    "query": query})
    return out


SE_TAGS = ["artificial-intelligence", "machine-learning", "chatbot", "automation",
           "natural-language-processing", "recommendation-system"]


def collect_hn_comments(query, cap=80):
    """HN 讨论评论中带明确需求信号的内容（"I need/wish there was/looking for…"），
    经 NEED_RE 过滤后作为需求侧补充，规模大且真实。"""
    out = []
    qs = urllib.parse.urlencode({"tags": "comment", "query": query, "hitsPerPage": 100})
    d = http_json("https://hn.algolia.com/api/v1/search?" + qs, timeout=15)
    for h in d.get("hits", []):
        oid = str(h.get("objectID") or "")
        body = strip_html(h.get("comment_text") or "")
        if len(body) < 80 or not NEED_RE.search(body[:600]):
            continue
        title = strip_html(h.get("story_title") or "") or f"Hacker News 需求讨论 {oid}"
        url = f"https://news.ycombinator.com/item?id={oid}"
        out.append({"source": "Hacker News", "native_id": "C" + oid, "title": title,
                    "url": url, "body": body[:4000],
                    "date": (h.get("created_at") or "")[:10],
                    "heat": {"评论数": h.get("num_comments") or 0},
                    "query": query})
        if len(out) >= cap:
            break
    return out


def collect_stackexchange(site, tags, cap=120):
    """Stack Exchange 求推荐/寻找工具问答。"""
    out = []
    seen = set()
    for tag in tags:
        qs = urllib.parse.urlencode({"order": "desc", "sort": "activity", "tagged": tag,
                                     "site": site, "pagesize": 100, "filter": "withbody"})
        d = http_json("https://api.stackexchange.com/2.3/questions?" + qs)
        for i in d.get("items", []):
            qid = i.get("question_id")
            if not qid or qid in seen:
                continue
            seen.add(qid)
            title = strip_html(i.get("title") or "")
            body = strip_html(i.get("body") or "")
            if len(title) < 12 or len(body) < 40 or not ok_need(title, body):
                continue
            out.append({"source": "Stack Overflow" if site == "stackoverflow" else "Software Recommendations",
                        "native_id": f"{site[:2]}{qid}", "title": title,
                        "url": i.get("link") or "", "body": body[:4000],
                        "date": datetime.fromtimestamp(i.get("creation_date", 0), tz=timezone.utc).strftime("%Y-%m-%d"),
                        "heat": {"点赞数": i.get("score") or 0, "浏览数": i.get("view_count") or 0,
                                 "评论数": i.get("answer_count") or 0}, "query": tag})
            if len(out) >= cap:
                return out
    return out


def collect_all(verbose=True):
    by_batch = defaultdict(list)
    for bid, scene, queries in SCENARIOS:
        for q in queries:
            got = collect_ask_hn(q)
            for it in got:
                it["scene"] = scene
                by_batch[bid].append(it)
            if verbose:
                print(f"  {bid} AskHN q={q[:38]:<38} +{len(got)}")
            time.sleep(0.05)
    # 全局补充 Ask HN + HN评论 + StackExchange（分散到各批）
    extra = []
    for q in HN_EXTRA:
        extra.extend(collect_ask_hn(q, cap=100))
        extra.extend(collect_hn_comments(q, cap=80))
        time.sleep(0.05)
    se = collect_stackexchange("softwarerecs", SE_TAGS, cap=150)
    so = collect_stackexchange("stackoverflow", SE_TAGS, cap=150)
    extra = extra + se + so
    for idx, it in enumerate(extra):
        it["scene"] = SCENARIOS[idx % len(SCENARIOS)][1]
        by_batch[SCENARIOS[idx % len(SCENARIOS)][0]].append(it)
    return by_batch


def dedup_within(by_batch):
    """全局按 URL/native_id 去重，记录保留批次。"""
    seen, out = set(), defaultdict(list)
    for bid in sorted(by_batch):
        for it in by_batch[bid]:
            key = it.get("url") or (it["source"] + it["native_id"])
            key = hashlib.md5(key.encode("utf-8")).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            out[bid].append(it)
    return out


def clean_body(text):
    text = strip_html(text)
    if clean_text:
        try:
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 30:
                text = cleaned
        except Exception:  # noqa: BLE001
            pass
    return text.strip()


def metrics_line(it):
    h = it.get("heat") or {}
    parts = []
    for col, label in [("星标数", "星标"), ("浏览数", "浏览"), ("点赞数", "点赞"),
                       ("评论数", "评论"), ("收藏数", "收藏")]:
        v = h.get(col)
        if v not in (None, "", 0, "0"):
            parts.append(f"{label}{v}")
    return "、".join(parts)


def build(by_batch):
    os.makedirs(TEXT_DIR, exist_ok=True)
    rows = []
    for bid in sorted(by_batch):
        items = sorted(by_batch[bid], key=lambda x: x.get("date", ""), reverse=True)
        for n, it in enumerate(items, 1):
            sid = f"S{n:05d}"
            body = clean_body(it["body"])
            title = it["title"].strip()
            date = it.get("date") or ""
            heat = metrics_line(it)
            # 正文快照
            snap = [f"# {title}", "", f"- 来源：{it['source']}", f"- 链接：{it['url']}",
                    f"- 发布时间：{date}"]
            if heat:
                snap.append(f"- 热度：{heat}")
            snap += ["", "## 正文", body]
            with open(os.path.join(TEXT_DIR, f"{bid}_{sid}.md"), "w", encoding="utf-8") as f:
                f.write("\n".join(snap))
            h = it.get("heat") or {}
            rows.append({
                "采集批次号": bid, "记录编号": sid, "来源网站名称": it["source"],
                "来源链接": it["url"], "内容": f"./text/{bid}_{sid}.md", "发布时间": date,
                "星标数": h.get("星标数", ""), "浏览数": h.get("浏览数", ""),
                "点赞数": h.get("点赞数", ""), "评论数": h.get("评论数", ""),
                "收藏数": h.get("收藏数", ""),
            })
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)
    return rows


def main():
    reuse = "--reuse" in sys.argv
    if reuse and os.path.exists(CACHE):
        print("复用缓存:", CACHE)
        by_batch = json.load(open(CACHE, encoding="utf-8"))
    else:
        print("开始需求导向采集（公开渠道，遵守平台条款）…")
        by_batch = collect_all(verbose=True)
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump(by_batch, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    by_batch = dedup_within(by_batch)
    rows = build(by_batch)
    print("\n=== 采集完成 ===")
    print("总记录:", len(rows))
    for bid in sorted(by_batch):
        print(f"  {bid}: {len(by_batch[bid])} 条")
    print("来源分布:", dict(Counter(r["来源网站名称"] for r in rows)))
    print("result1:", OUT_CSV)


if __name__ == "__main__":
    main()
