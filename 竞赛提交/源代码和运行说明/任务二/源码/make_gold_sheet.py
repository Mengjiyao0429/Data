# -*- coding: utf-8 -*-
"""任务二 · 人工标注集构建辅助

说明（论文"人工标注"一节对应工具）
--------------------------------
* 本工具只打印"待标注"记录的判别文本与规则初判，供队员独立标注后填写。
* 标注结果写入 gold_labels.csv（列：唯一标识, 人工是否机会(0/1), 人工功能类别, 人工所属行业, 标注人, 备注）。
* 严禁把规则输出直接当作人工真值；gold_labels.csv 中的人工列必须由队员独立填写。
"""
from __future__ import annotations

import csv
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from result2_exporter import load_result1  # noqa: E402
from category_classifier import FUNCTION_LABELS, INDUSTRY_LABELS  # noqa: E402

GOLD = os.path.join(HERE, "gold_labels.csv")


def main():
    _, records = load_result1()
    if os.path.exists(GOLD):
        with open(GOLD, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        print(f"已存在标注集 {len(rows)} 条：{GOLD}")
        for r in rows[:20]:
            print(r)
        return
    # 生成待标注清单（全部批次分层抽样：问答社区 / 开源项目 / 教程博客 / 资讯）
    strata = {}
    for r in records:
        strata.setdefault(r["source"], []).append(r)
    quota = {"Stack Overflow": 20, "GitHub": 20, "CSDN": 10, "36氪": 10,
             "阿里云开发者社区": 10, "腾讯新闻": 6, "中国医药创新促进会": 5}
    random.seed(20261116)
    picked = []
    for src, q in quota.items():
        xs = strata.get(src, [])
        picked += random.sample(xs, min(q, len(xs)))
    picked.sort(key=lambda r: (r["batch_id"], r["record_id"]))
    with open(GOLD, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["采集批次号", "记录编号", "唯一标识", "人工是否机会(0/1)",
                    "人工功能类别", "人工所属行业", "标注人", "判定依据备注"])
        for r in picked:
            w.writerow([r["batch_id"], r["record_id"], r["key"], "", "", "", "", ""])
    print("已生成待标注清单：", GOLD, len(picked), "条")
    print("合法功能类别：", "、".join(FUNCTION_LABELS))
    print("合法行业：", "、".join(INDUSTRY_LABELS))


if __name__ == "__main__":
    main()