# -*- coding: utf-8 -*-
"""需求导向数据重构 · 下游链路干净重建编排器

在 collect_demand_oriented.py 生成新 result1.csv + 新 text/ 快照后运行本脚本：
  1) 清空并重建 任务二/正文快照/（避免新旧编号串味）
  2) 同步 result1 到 任务二/原始数据/任务一输出/（csv + xlsx）
  3) 清理任务二状态/证据/报告文件（强制全量重判）
  4) 依次重跑：任务二判别 → 任务三聚类 → 任务四价值评估

所有被覆盖的产物在 D:/Data/workbuddy/_baseline_backup_20261118/结果数据_重构前/ 已备份。
"""
import csv
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY = sys.executable

TASK1 = os.path.join(REPO, "任务一")
TASK2 = os.path.join(REPO, "任务二")
TASK3 = os.path.join(REPO, "任务三")
TASK4 = os.path.join(REPO, "任务四")

SRC_CSV = os.path.join(TASK1, "结果", "result1.csv")
SRC_TEXT = os.path.join(TASK1, "结果", "text")
DST_CSV = os.path.join(TASK2, "原始数据", "任务一输出", "result1.csv")
DST_XLSX = os.path.join(TASK2, "原始数据", "任务一输出", "result1.xlsx")
DST_SNAP = os.path.join(TASK2, "正文快照")


def run(cmd, cwd=None):
    print("\n>>>", " ".join(cmd), "(cwd=%s)" % (cwd or REPO))
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(cmd, cwd=cwd or REPO, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(r.stdout[-3000:])
    if r.returncode != 0:
        raise SystemExit("命令失败 code=%d" % r.returncode)


def main():
    rows = list(csv.DictReader(open(SRC_CSV, encoding="utf-8-sig")))
    print("新 result1 记录数:", len(rows))

    # 1) 重建归档 csv/xlsx
    os.makedirs(os.path.dirname(DST_CSV), exist_ok=True)
    shutil.copyfile(SRC_CSV, DST_CSV)
    from openpyxl import Workbook
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("result1")
    with open(SRC_CSV, encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            ws.append(row)
    wb.save(DST_XLSX)
    print("归档 result1.csv/.xlsx 已更新")

    # 2) 清空并重建任务二快照（关键：避免旧编号残留）
    if os.path.isdir(DST_SNAP):
        shutil.rmtree(DST_SNAP)
    os.makedirs(DST_SNAP, exist_ok=True)
    copied = 0
    for r in rows:
        name = os.path.basename(r["内容"])
        src = os.path.join(SRC_TEXT, name)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(DST_SNAP, name))
            copied += 1
        else:
            print("警告：缺快照", name)
    print("任务二快照重建:", copied, "个")

    # 3) 清理任务二状态/证据，强制全量重判
    for fn in ("task2_states.json", "task2_evidence.jsonl", "task2_验收报告.md"):
        p = os.path.join(TASK2, fn)
        if os.path.exists(p):
            os.remove(p)
    print("任务二状态文件已清理")

    # 4) 重跑任务二 → 三 → 四
    run([PY, os.path.join(TASK2, "源码", "result2_exporter.py")], cwd=os.path.join(TASK2, "源码"))
    run([PY, os.path.join(TASK3, "源码", "cluster_task3.py")], cwd=os.path.join(TASK3, "源码"))
    run([PY, os.path.join(TASK4, "源码", "task4_value.py")], cwd=os.path.join(TASK4, "源码"))
    print("\n=== 下游链路重建完成 ===")


if __name__ == "__main__":
    main()
