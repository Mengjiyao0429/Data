# -*- coding: utf-8 -*-
"""命令行发起一次需求（不经过界面，便于复现与压测）。

用法：
    python 任务五/core/run_batch.py --query "AI 编程助手 代码生成" ^
        --sources stackoverflow,hackernews,github --target 600 --note "赛题演示"
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db, pipeline  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--sources", default="stackoverflow,hackernews,github")
    ap.add_argument("--target", type=int, default=500)
    ap.add_argument("--note", default="")
    ap.add_argument("--batch", default="")
    a = ap.parse_args()

    db.init()
    bid = a.batch or pipeline.next_batch_id()
    srcs = [s.strip() for s in a.sources.split(",") if s.strip()]
    db.create_batch(bid, a.query, srcs, a.target, a.note)
    try:
        summary = pipeline.run_batch(bid, {"query": a.query, "sources": srcs,
                                           "target": a.target, "note": a.note})
        db.finish_batch(bid, summary)
        print(json.dumps({k: v for k, v in summary.items() if k != "notes"},
                         ensure_ascii=False, indent=2))
    except Exception as e:  # noqa: BLE001
        db.finish_batch(bid, {}, str(e))
        print("FAILED:", e)
        raise


if __name__ == "__main__":
    main()
