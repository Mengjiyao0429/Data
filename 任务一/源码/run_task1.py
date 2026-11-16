# -*- coding: utf-8 -*-
"""任务一运行入口：采集 -> 清洗 -> 去重 -> 编号 -> 正文快照 -> result1.csv。

用法：
    python run_task1.py                # 默认批次 B01
    python run_task1.py B02            # 指定批次号
产出：
    data/collected/raw_<batch>.json    # 原始采集记录（溯源）
    data/<batch>/text/<batch>_Sxxxxx.md  # 清洗后正文快照
    data/<batch>/results/result1.csv   # 官方表头结果（utf-8-sig，Excel 可直接打开）
"""
import csv
import json
import sys
from pathlib import Path

from app import config
from app.pipeline import collector, cleaner, dedup

RESULT1_HEADER = [
    "采集批次号", "记录编号", "来源网站名称", "来源链接", "内容",
    "发布时间", "热度指标（如浏览数、点赞数、讨论数等）",
]


def run(batch_id="B01"):
    batch_dir = config.DATA_DIR / batch_id
    text_dir = batch_dir / "text"
    result_dir = batch_dir / "results"
    text_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    # 1) 多源采集
    raw = collector.collect_all(verbose=True)
    raw_path = config.DATA_DIR / "collected" / f"raw_{batch_id}.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2) 文本清洗
    cleaned = cleaner.clean_records(raw)

    # 3) 去重
    kept, removed = dedup.dedup_records(cleaned)

    # 4) 编号 + 5) 正文快照 + 6) result1
    rows = []
    for idx, rec in enumerate(kept, start=1):
        rec_no = f"S{idx:05d}"
        snap_name = f"{batch_id}_{rec_no}.md"
        snap_rel = f"text/{snap_name}"
        snap_path = text_dir / snap_name
        snap_path.write_text(
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

    result1_path = result_dir / "result1.csv"
    with open(result1_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT1_HEADER)
        writer.writeheader()
        writer.writerows(rows)

    # 汇总
    print("\n===== 任务一完成 =====")
    print(f"批次: {batch_id}")
    print(f"原始采集: {len(raw)} 条")
    print(f"去重保留: {len(kept)} 条（移除 {removed} 条）")
    dist = {}
    for r in kept:
        dist[r["source_name"]] = dist.get(r["source_name"], 0) + 1
    print("来源分布: " + "，".join(f"{k} {v}" for k, v in sorted(
        dist.items(), key=lambda x: -x[1])))
    print(f"正文快照目录: {text_dir}")
    print(f"result1: {result1_path}")
    return kept


def _snapshot(batch_id, rec_no, rec):
    lines = [
        f"# {rec.get('clean_title','')}",
        f"- 采集批次号: {batch_id}",
        f"- 记录编号: {rec_no}",
        f"- 来源网站: {rec.get('source_name','')}",
        f"- 来源链接: {rec.get('source_url','')}",
        f"- 发布时间: {rec.get('published_at','')}",
        f"- 热度: {rec.get('heat_text','') or '无'}",
        "",
        "## 正文",
        rec.get("clean_content", ""),
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    bid = sys.argv[1] if len(sys.argv) > 1 else "B01"
    run(bid)
