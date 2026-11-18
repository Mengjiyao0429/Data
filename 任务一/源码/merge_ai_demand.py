# -*- coding: utf-8 -*-
"""任务一 · 需求侧补采入库（B06 / B07 / B08）

读取 collect_ai_demand.py 落盘的原始 JSON，做三件事：
  1) 与现有 result1 全量去重（链接归一化 + 来源内标题归一化）；
  2) 按 B06/B07/B08 分配批次号与 Sxxxxx 连续编号，生成 ./text/{批}_{编号}.md 快照（与既有格式完全一致）；
  3) 追加写入 任务一/结果/result1.csv，并输出批次/来源/去重统计。
"""
import csv
import json
import os
import re
from collections import Counter

TASK1 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(TASK1, "原始数据")
RESULT = os.path.join(TASK1, "结果")
CSV_PATH = os.path.join(RESULT, "result1.csv")
TEXT_DIR = os.path.join(RESULT, "text")

HEADER = ["采集批次号", "记录编号", "来源网站名称", "来源链接", "内容",
          "发布时间", "星标数", "浏览数", "点赞数", "评论数", "收藏数"]

BATCHES = [("B06", "B06_stackoverflow_raw.json"),
           ("B07", "B07_hackernews_raw.json"),
           ("B08", "B08_v2ex_raw.json")]

NORM_RE = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")
# HN 每月固定置顶串（招聘/求职/自由职业）与失效帖：不是 AI 应用需求，且会污染主题簇
HN_NOISE_RE = re.compile(
    r"who wants to be hired|who is hiring|freelancer\? seeking freelancer|who's hiring", re.I)
HN_DEAD_TITLES = {"[dead]", "[flagged]", "[dupe]", ""}


TRACK_RE = re.compile(r"(utm_[a-z]+|ref|source|from|spm|fbclid|gclid)=[^&]*&?", re.I)


def norm_url(u):
    """归一化链接用于去重：去掉协议/www/锚点与跟踪参数，但保留有检索意义的查询参数
    （Hacker News 的 item?id=xxx 依赖 query 区分记录，不能整段裁掉）。"""
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = u.split("#")[0].rstrip("/")
    if "?" in u:
        base, q = u.split("?", 1)
        q = TRACK_RE.sub("", q).strip("&")
        u = f"{base}?{q}" if q else base
    return u


def norm_title(t):
    return NORM_RE.sub("", (t or "").lower())[:80]


def heat_text(src, it):
    if src == "Stack Overflow":
        parts = []
        if it.get("views"):
            parts.append(f"浏览{it['views']}")
        if it.get("score"):
            parts.append(f"点赞{it['score']}")
        if it.get("answers"):
            parts.append(f"回答{it['answers']}")
        return " · ".join(parts) or "问答"
    if src == "Hacker News":
        parts = []
        if it.get("score"):
            parts.append(f"所在帖点赞{it['score']}")
        if it.get("answers"):
            parts.append(f"所在帖评论{it['answers']}")
        return " · ".join(parts) or "讨论"
    if it.get("answers"):
        return f"回复{it['answers']}"
    return "热帖"


def snapshot(src, it):
    return (f"# {it['title']}\n\n"
            f"- 来源：{src}\n"
            f"- 链接：{it['url']}\n"
            f"- 发布时间：{it['date']}\n"
            f"- 热度：{heat_text(src, it)}\n\n"
            f"## 正文\n{it['text']}\n")


def main():
    os.makedirs(TEXT_DIR, exist_ok=True)

    # 1) 现有数据索引
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8-sig")))
    url_seen = {norm_url(r["来源链接"]) for r in rows}
    title_seen = {(r["来源网站名称"], norm_title(_title_of(r))) for r in rows}
    print(f"现有记录 {len(rows)} 条；已有链接 {len(url_seen)} 个")

    # 2) 逐批去重 + 编号 + 快照
    added = []
    stats = {}
    for batch, fname in BATCHES:
        path = os.path.join(RAW, fname)
        if not os.path.exists(path):
            print(f"! 缺少 {fname}，跳过")
            continue
        payload = json.load(open(path, encoding="utf-8"))
        items = payload["items"]
        kept, dup_url, dup_title, short = 0, 0, 0, 0
        noise = 0
        sid = 0
        for it in items:
            u, t = norm_url(it["url"]), norm_title(it["title"])
            if it["source"] == "Hacker News" and (
                    HN_NOISE_RE.search(it["title"] or "") or (it["title"] or "").strip().lower() in HN_DEAD_TITLES):
                noise += 1
                continue
            if len(it["text"]) < 60:
                short += 1
                continue
            if u in url_seen:
                dup_url += 1
                continue
            # HN 评论天然共享同一条讨论帖标题，标题级去重只对问答/教程类来源生效
            if it["source"] != "Hacker News" and (it["source"], t) in title_seen:
                dup_title += 1
                continue
            url_seen.add(u)
            title_seen.add((it["source"], t))

            sid += 1
            rid = f"S{sid:05d}"
            it["_batch"], it["_rid"] = batch, rid
            with open(os.path.join(TEXT_DIR, f"{batch}_{rid}.md"), "w", encoding="utf-8") as f:
                f.write(snapshot(it["source"], it))
            added.append({
                "采集批次号": batch, "记录编号": rid, "来源网站名称": it["source"],
                "来源链接": it["url"], "内容": f"./text/{batch}_{rid}.md",
                "发布时间": it["date"],
                "星标数": "", "浏览数": it.get("views") or "",
                "点赞数": it.get("score") or "", "评论数": it.get("answers") or "",
                "收藏数": "",
            })
            kept += 1
        stats[batch] = {"候选": len(items), "入库": kept, "重复链接": dup_url,
                        "重复标题": dup_title, "过短": short}
        print(f"{batch} 候选 {len(items)} → 入库 {kept}（重复链接 {dup_url}、重复标题 {dup_title}、过短 {short}）")

    # 3) 追加写回 result1
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)
        w.writerows(added)
    print(f"result1 已更新：{len(rows)} + {len(added)} = {len(rows) + len(added)} 条")

    # 4) 统计
    allrows = rows + added
    print("\n批次分布：")
    for b, c in sorted(Counter(r["采集批次号"] for r in allrows).items()):
        print(f"  {b}: {c}")
    print("来源分布：")
    for s, c in Counter(r["来源网站名称"] for r in allrows).most_common():
        print(f"  {s}: {c}")

    with open(os.path.join(RAW, "B06_B08_merge_stats.json"), "w", encoding="utf-8") as f:
        json.dump({"before": len(rows), "added": len(added), "after": len(allrows),
                   "batches": stats,
                   "batch_dist": dict(Counter(r["采集批次号"] for r in allrows)),
                   "source_dist": dict(Counter(r["来源网站名称"] for r in allrows))},
                  f, ensure_ascii=False, indent=2)


def _title_of(row):
    """从快照首行读标题，用于标题级去重。"""
    p = os.path.join(RESULT, row["内容"].lstrip("./").replace("/", os.sep))
    if not os.path.exists(p):
        return ""
    try:
        with open(p, encoding="utf-8") as f:
            first = f.readline()
        return first.lstrip("# ").strip()
    except OSError:
        return ""


if __name__ == "__main__":
    main()
