# -*- coding: utf-8 -*-
"""任务一合并入口：把浏览器采集的国内真实记录并入现有 raw，再统一清洗/去重/编号/快照/result1。

用法：
    python merge_task1.py B01
产出（覆盖该批次）：
    data/collected/raw_<batch>.json
    data/<batch>/text/*.md
    data/<batch>/results/result1.csv
"""
import csv
import json
import re
import sys
from pathlib import Path

from app import config
from app.pipeline import cleaner, dedup

RESULT1_HEADER = [
    "采集批次号", "记录编号", "来源网站名称", "来源链接", "内容",
    "发布时间", "热度指标（如浏览数、点赞数、讨论数等）",
]

COLLECTED = config.DATA_DIR / "collected"
DATE_RE = re.compile(r"20\d{2}(?:年|-|/)\d{1,2}(?:月|-|/)\d{1,2}日?")
# 正文头部残留的元数据/功能行
NOISE_LINE_RE = re.compile(
    r"^(发布于|版权|举报|关注|简介[:：]?|文丨|编辑[:：]?|图源[:：]?|图片由|问AI|作者[:：]?|"
    r"来源[:：]?|缩小字体|放大字体|收藏|微博|微信|分享|新浪财经APP|返回搜狐|责任编辑|"
    r"\d{1,7}$|登录|注册|首页|更多|相关阅读|推荐阅读)"
)


def extract_body(raw_text, title):
    """从整页文本中剥离导航与头部元数据，返回纯正文。"""
    pos = -1
    for key in (title, title[:15], title[:10]):
        if key and key in raw_text:
            pos = raw_text.find(key)
            break
    seg = raw_text[pos:] if pos >= 0 else raw_text
    m = DATE_RE.search(seg)
    if m:
        tail = seg[m.end():]
        nl = tail.find("\n")
        seg = tail[nl + 1:] if nl >= 0 else tail
    # 逐行跳过开头的噪音行
    lines = seg.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line and not NOISE_LINE_RE.match(line):
            break
        i += 1
    return "\n".join(lines[i:]).strip()


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def load_browser_records():
    """读取 6 个浏览器 JSON，转换为统一 raw 字段。"""
    out = []

    def add(source_name, rec, body, heat_text, stars=None, comments=None, views=None):
        out.append({
            "source_name": source_name,
            "source_url": rec["url"],
            "title": rec["title"],
            "raw_content": body,
            "published_at": rec.get("date", ""),
            "stars": stars,
            "comments": comments,
            "views": views,
            "heat_text": heat_text,
        })

    # 36氪：点赞/收藏/评论
    for rec in json.load(open(COLLECTED / "browser_36kr.json", encoding="utf-8")):
        h = rec.get("heat", {})
        heat_text = f"点赞{h.get('like','0')}、收藏{h.get('fav','0')}、评论{h.get('comment','0')}"
        add("36氪", rec, extract_body(rec["raw_text"], rec["title"]), heat_text,
            stars=_to_int(h.get("like")), comments=_to_int(h.get("comment")))

    # 阿里云 PAI：浏览量
    for rec in json.load(open(COLLECTED / "browser_aliyun.json", encoding="utf-8")):
        v = _to_int(rec.get("views"))
        add("阿里云开发者社区", rec, extract_body(rec["raw_text"], rec["title"]),
            f"浏览{rec.get('views') or 0}", views=v)

    # 腾讯新闻 / 新浪科技
    news = json.load(open(COLLECTED / "browser_news.json", encoding="utf-8"))
    for rec in news.get("腾讯新闻", []):
        h = rec.get("heat", {})
        heat_text = (f"点赞{h.get('点赞','0')}、评论{h.get('评论','0')}、"
                     f"收藏{h.get('收藏','0')}")
        add("腾讯新闻", rec, extract_body(rec["raw_text"], rec["title"]), heat_text,
            stars=_to_int(h.get("点赞")), comments=_to_int(h.get("评论")))
    for rec in news.get("新浪科技", []):
        add("新浪科技", rec, extract_body(rec["raw_text"], rec["title"]), "未公开")

    # 中国互联网协会
    for rec in json.load(open(COLLECTED / "browser_isc.json", encoding="utf-8")):
        add("中国互联网协会", rec, extract_body(rec["raw_text"], rec["title"]), "未公开")

    # 中国医药创新促进会：浏览量
    for rec in json.load(open(COLLECTED / "browser_phirda.json", encoding="utf-8")):
        v = _to_int(rec.get("views"))
        add("中国医药创新促进会", rec, extract_body(rec["raw_text"], rec["title"]),
            f"浏览{rec.get('views') or 0}", views=v)

    return out


def run(batch_id="B01"):
    batch_dir = config.DATA_DIR / batch_id
    text_dir = batch_dir / "text"
    result_dir = batch_dir / "results"
    text_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    # 1) 现有原始 + 浏览器国内记录
    existing = json.load(
        open(COLLECTED / f"raw_{batch_id}.json", encoding="utf-8"))
    browser = load_browser_records()
    raw = existing + browser
    (COLLECTED / f"raw_{batch_id}.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2) 清洗 -> 3) 去重
    cleaned = cleaner.clean_records(raw)
    kept, removed = dedup.dedup_records(cleaned)

    # 4) 编号 + 快照 + result1
    rows = []
    for idx, rec in enumerate(kept, start=1):
        rec_no = f"S{idx:05d}"
        snap_rel = f"text/{batch_id}_{rec_no}.md"
        (text_dir / f"{batch_id}_{rec_no}.md").write_text(
            _snapshot(batch_id, rec_no, rec), encoding="utf-8")
        rows.append({
            "采集批次号": batch_id,
            "记录编号": rec_no,
            "来源网站名称": rec.get("source_name", ""),
            "来源链接": rec.get("source_url", ""),
            "内容": snap_rel,
            "发布时间": rec.get("published_at", ""),
            "热度指标（如浏览数、点赞数、讨论数等）": rec.get("heat_text", ""),
        })

    with open(result_dir / "result1.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT1_HEADER)
        writer.writeheader()
        writer.writerows(rows)

    print("===== 合并完成 =====")
    print(f"批次: {batch_id} | 原始合并: {len(raw)}（原 {len(existing)} + 国内 {len(browser)}）")
    print(f"去重保留: {len(kept)} 条（移除 {removed}）")
    dist = {}
    for r in kept:
        dist[r["source_name"]] = dist.get(r["source_name"], 0) + 1
    print("来源分布: " + "，".join(f"{k} {v}" for k, v in sorted(
        dist.items(), key=lambda x: -x[1])))
    return kept


def _snapshot(batch_id, rec_no, rec):
    return "\n".join([
        f"# {rec.get('clean_title', '')}",
        f"- 采集批次号: {batch_id}",
        f"- 记录编号: {rec_no}",
        f"- 来源网站: {rec.get('source_name', '')}",
        f"- 来源链接: {rec.get('source_url', '')}",
        f"- 发布时间: {rec.get('published_at', '')}",
        f"- 热度: {rec.get('heat_text', '') or '无'}",
        "",
        "## 正文",
        rec.get("clean_content", ""),
        "",
    ])


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "B01")
