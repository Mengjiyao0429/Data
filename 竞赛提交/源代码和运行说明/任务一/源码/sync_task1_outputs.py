# -*- coding: utf-8 -*-
"""把任务一的最新 result1 同步到任务二的两个下游依赖位置：

  1) 任务二/原始数据/任务一输出/result1.csv、result1.xlsx   —— 任务二导出器、任务三、任务四都优先读这里
  2) 任务二/正文快照/{批}_{编号}.md                          —— 任务三聚类的正文来源

只同步差异，不删除任何既有文件，避免破坏已有快照。
"""
import csv
import os
import shutil

TASK1 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(TASK1)
TASK2 = os.path.join(REPO, "任务二")
SRC_CSV = os.path.join(TASK1, "结果", "result1.csv")
SRC_TEXT = os.path.join(TASK1, "结果", "text")
DST_CSV = os.path.join(TASK2, "原始数据", "任务一输出", "result1.csv")
DST_XLSX = os.path.join(TASK2, "原始数据", "任务一输出", "result1.xlsx")
DST_TEXT = os.path.join(TASK2, "正文快照")


def main():
    rows = list(csv.DictReader(open(SRC_CSV, encoding="utf-8-sig")))
    print("任务一记录:", len(rows))

    shutil.copyfile(SRC_CSV, DST_CSV)
    print("已更新归档 CSV:", DST_CSV)

    from openpyxl import Workbook
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("result1")
    with open(SRC_CSV, encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            ws.append(row)
    wb.save(DST_XLSX)
    print("已重建归档 XLSX:", DST_XLSX, os.path.getsize(DST_XLSX), "bytes")

    os.makedirs(DST_TEXT, exist_ok=True)
    copied, existed = 0, 0
    for r in rows:
        name = os.path.basename(r["内容"])
        dst = os.path.join(DST_TEXT, name)
        if os.path.exists(dst):
            existed += 1
            continue
        shutil.copyfile(os.path.join(SRC_TEXT, name), dst)
        copied += 1
    print(f"快照同步：复制 {copied} 个，已存在 {existed} 个，目录共 {len(os.listdir(DST_TEXT))} 个")


if __name__ == "__main__":
    main()
