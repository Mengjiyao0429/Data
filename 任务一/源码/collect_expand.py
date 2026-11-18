# -*- coding: utf-8 -*-
"""任务一 · 需求导向采集扩充版（v4）

在 collect_demand_oriented.py（合规需求侧采集）基础上扩大规模：
  1) 8 个业务场景 query 保留，Ask HN 分页 2 -> 3，cap 提高
  2) 新增一组「AI + 需求信号」通用 query（高机会率），分散到各批次
  3) HN 评论需求信号 cap 提高、分页覆盖
  4) 恢复 GitHub Issues feature request 采集（未认证 10 次/分钟，限流内 8 次）
  5) StackExchange 扩大 tag 覆盖与 pagesize

所有来源均为公开 API，遵守平台条款；正式机会判别仍由任务二四规则完成，
不在采集阶段硬判、不虚标。产出覆盖 任务一/结果/result1.csv 与 text/ 快照。

运行：python collect_expand.py
"""
from __future__ import annotations

import os
import sys
import time
import urllib.parse
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import collect_demand_oriented as base  # noqa: E402

# AI + 需求信号通用 query：既是"真实需求表达"，又明确指向 AI 手段，机会纯度高
AI_DEMAND_EXTRA = [
    "is there an AI that can",
    "looking for an AI tool",
    "recommend an AI tool",
    "AI tool to automate",
    "need an AI solution for",
    "AI assistant for",
    "looking for AI software",
    "recommend AI software",
    "AI powered tool for",
    "want an AI that",
    "use AI to automate",
    "AI that can automate",
    "looking for an AI app",
    "AI tool for productivity",
    "is there software that uses AI",
    "need help automating with AI",
    "AI solution for small business",
    "recommend a tool using machine learning",
    "automate this with AI",
    "any AI tool for this",
]

# GitHub feature request 的 AI 主题 query（限流内，每批 1 条）
GH_QUERIES = [
    "AI assistant", "chatbot", "automation", "document summarization",
    "code review AI", "speech to text", "image recognition", "workflow automation",
]

SE_TAGS_EXTRA = base.SE_TAGS + ["generative-ai", "llm", "computer-vision", "speech-recognition",
                                "nlp", "robotic-process-automation", "data-automation"]


def collect_ask_hn_pages(query, cap=260, pages=3):
    """复用基础采集器思路，显式多页。"""
    out = []
    seen = set()
    for page in range(pages):
        qs = urllib.parse.urlencode({"tags": "ask_hn", "query": query,
                                     "hitsPerPage": 100, "page": page})
        d = base.http_json("https://hn.algolia.com/api/v1/search?" + qs, timeout=15)
        hits = d.get("hits", [])
        if not hits:
            break
        for h in hits:
            oid = str(h.get("objectID") or "")
            if oid in seen:
                continue
            seen.add(oid)
            title = base.strip_html(h.get("title") or "")
            body = base.strip_html(h.get("story_text") or "")
            if len(title) < 12 or len(body) < 50:
                continue
            out.append({"source": "Hacker News", "native_id": "HN" + oid, "title": title,
                        "url": f"https://news.ycombinator.com/item?id={oid}",
                        "body": body[:4000], "date": (h.get("created_at") or "")[:10],
                        "heat": {"点赞数": h.get("points") or 0, "评论数": h.get("num_comments") or 0},
                        "query": query})
            if len(out) >= cap:
                return out
    return out


def collect_all(verbose=True):
    by_batch = defaultdict(list)

    # 1) 原场景 query（分页加深）
    for bid, scene, queries in base.SCENARIOS:
        for q in queries:
            got = collect_ask_hn_pages(q, cap=260, pages=3)
            for it in got:
                it["scene"] = scene
                by_batch[bid].append(it)
            if verbose:
                print(f"  {bid} AskHN q={q[:34]:<34} +{len(got)}", flush=True)
            time.sleep(0.04)

    # 2) AI 需求通用 query（高机会率），分散到各批次
    extra = []
    for q in base.HN_EXTRA + AI_DEMAND_EXTRA:
        extra.extend(collect_ask_hn_pages(q, cap=220, pages=3))
        time.sleep(0.04)

    # 3) HN 评论需求信号
    for q in base.HN_EXTRA + AI_DEMAND_EXTRA[:12]:
        extra.extend(base.collect_hn_comments(q, cap=120))
        time.sleep(0.04)

    # 4) StackExchange 扩大覆盖
    extra.extend(base.collect_stackexchange("softwarerecs", SE_TAGS_EXTRA, cap=220))
    extra.extend(base.collect_stackexchange("stackoverflow", SE_TAGS_EXTRA, cap=220))

    # 5) GitHub Issues（限流：未认证 10 次/分钟，间隔 7s）
    for q in GH_QUERIES:
        try:
            got = base.collect_github_issues(q, cap=30)
        except Exception as e:  # noqa: BLE001
            print("  GitHub 采集跳过:", e, flush=True)
            got = []
        extra.extend(got)
        if verbose:
            print(f"  GitHub q={q[:28]:<28} +{len(got)}", flush=True)
        time.sleep(7)

    n = len(base.SCENARIOS)
    for idx, it in enumerate(extra):
        bid, scene, _ = base.SCENARIOS[idx % n]
        it["scene"] = scene
        by_batch[bid].append(it)
    return by_batch


def main():
    print("开始需求导向采集扩充（公开渠道，遵守平台条款）…", flush=True)
    by_batch = collect_all(verbose=True)
    # 写入独立缓存，保留原始 demand_oriented_raw.json 作为回退
    cache = os.path.join(base.TASK1, "原始数据", "demand_expand_raw.json")
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    import json
    json.dump(by_batch, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    by_batch = base.dedup_within(by_batch)
    rows = base.build(by_batch)
    print("\n=== 扩充采集完成 ===", flush=True)
    print("总记录:", len(rows), flush=True)
    for bid in sorted(by_batch):
        print(f"  {bid}: {len(by_batch[bid])} 条", flush=True)
    print("来源分布:", dict(Counter(r["来源网站名称"] for r in rows)), flush=True)
    print("result1:", base.OUT_CSV, flush=True)


if __name__ == "__main__":
    main()
