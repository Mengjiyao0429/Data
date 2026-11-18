# -*- coding: utf-8 -*-
"""离线复现一个批次：只读 批次/<bid>/原始记录.json 重算全链，不联网。

用法：python 任务五/core/replay_batch.py B09
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db, pipeline  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("用法：python 任务五/core/replay_batch.py <批次号>")
        return 1
    bid = sys.argv[1].strip()
    db.init()
    pipeline.preload()
    summary = pipeline.replay(bid)
    db.finish_batch(bid, summary)
    print("复现完成：%s 记录 %d、机会 %d、簇 %d" %
          (bid, summary["records"], summary["opportunities"], summary["clusters"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
