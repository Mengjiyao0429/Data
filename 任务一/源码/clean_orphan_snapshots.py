# -*- coding: utf-8 -*-
"""删除 result1 未引用的孤儿快照（重编号后遗留），保证快照目录与结果一一对应。"""
import csv, os

REPO = r"D:\Data\Data"
R1 = os.path.join(REPO, "任务一", "结果", "result1.csv")
DIRS = [os.path.join(REPO, "任务一", "结果", "text"), os.path.join(REPO, "任务二", "正文快照")]

rows = list(csv.DictReader(open(R1, encoding="utf-8-sig")))
keep = {os.path.basename(r["内容"]) for r in rows}
print("result1:", len(rows), "引用快照:", len(keep))
for d in DIRS:
    removed = 0
    for fn in os.listdir(d):
        if fn.endswith(".md") and fn not in keep:
            os.remove(os.path.join(d, fn))
            removed += 1
    print(f"{d}: 删除孤儿 {removed}，剩余 {len(os.listdir(d))}")
