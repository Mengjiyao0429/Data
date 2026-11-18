# -*- coding: utf-8 -*-
"""回滚 B06/B07/B08 的入库结果，恢复到 5517 条基线（仅用于本次重跑前的清理）。"""
import csv, os, re

TASK1 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULT = os.path.join(TASK1, "结果")
CSV_PATH = os.path.join(RESULT, "result1.csv")
TEXT = os.path.join(RESULT, "text")
NEW = {"B06", "B07", "B08"}

rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8-sig")))
keep = [r for r in rows if r["采集批次号"] not in NEW]
removed = len(rows) - len(keep)

with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(keep)

n = 0
for fn in os.listdir(TEXT):
    if re.match(r"B0[678]_S\d{5}\.md$", fn):
        os.remove(os.path.join(TEXT, fn))
        n += 1

print(f"回滚：删除记录 {removed} 条、快照 {n} 个，现 {len(keep)} 条")
