# -*- coding: utf-8 -*-
"""任务二 · 质量评估：与人工标注集对照，输出 Accuracy/Precision/Recall/F1、混淆矩阵与错误分析。

用法：
    python evaluate.py [gold_labels.csv] [--report task2_质量评估报告.md]
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# 结果位于 任务二/结果/result2.csv；证据链位于 任务二/task2_evidence.jsonl
# （兼容脚本与结果同目录的旧布局）
_rm = [os.path.join(HERE, "结果", "result2.csv"), os.path.join(HERE, "result2.csv"),
       os.path.join(os.path.dirname(HERE), "结果", "task2_evidence.jsonl").replace("task2_evidence.jsonl", "result2.csv")]
RESULT2 = next((p for p in _rm if os.path.exists(p)), _rm[0])
_ev = [os.path.join(HERE, "task2_evidence.jsonl"), os.path.join(os.path.dirname(HERE), "task2_evidence.jsonl")]
EVIDENCE = next((p for p in _ev if os.path.exists(p)), _ev[0])


def load_result2():
    with open(RESULT2, encoding="utf-8-sig") as f:
        return {f"{r['采集批次号']}-{r['记录编号']}": r for r in csv.DictReader(f)}


def load_gold(path):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            lab = (r.get("人工是否机会(0/1)") or "").strip()
            if lab in ("0", "1"):
                rows.append(r)
    return rows


def metrics(pred, gold, tau):
    """在阈值 tau 下计算二分类指标。"""
    tp = sum(1 for p, g in zip(pred, gold) if p >= tau and g == 1)
    fp = sum(1 for p, g in zip(pred, gold) if p >= tau and g == 0)
    fn = sum(1 for p, g in zip(pred, gold) if p < tau and g == 1)
    tn = sum(1 for p, g in zip(pred, gold) if p < tau and g == 0)
    acc = (tp + tn) / max(1, len(gold))
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    f1 = 2 * prec * rec / max(1e-9, prec + rec)
    return dict(TP=tp, FP=fp, FN=fn, TN=tn, Accuracy=acc, Precision=prec, Recall=rec, F1=f1)


def main():
    gold_path = os.path.join(HERE, "gold_labels.csv")
    report = os.path.join(HERE, "task2_质量评估报告.md")
    args = [a for a in sys.argv[1:]]
    if "--report" in args:
        report = args[args.index("--report") + 1]
        args.remove(report)
        args.remove("--report")
    if args:
        gold_path = args[0]

    res = load_result2()
    ev = {}
    with open(EVIDENCE, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            ev[e["唯一标识"]] = e

    lines = ["# 任务二 质量评估报告\n"]

    if not os.path.exists(gold_path):
        lines.append("未找到人工标注集，暂无法计算监督指标。请先 `python make_gold_sheet.py` 生成清单并完成标注。")
        open(report, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        print("no gold file:", gold_path)
        return

    gold_rows = load_gold(gold_path)
    keys = [f"{r['采集批次号']}-{r['记录编号']}" for r in gold_rows]
    gold = [int(r["人工是否机会(0/1)"]) for r in gold_rows]
    pred = [float(res[k]["机会置信度"]) for k in keys]
    syspred = [int(res[k]["是否构成机会"]) for k in keys]

    # ---- 阈值选择：在标注集上扫描，F1 最大；与系统阈值 0.50 对照 ----
    best = None
    for t in [round(0.30 + 0.02 * i, 2) for i in range(26)]:
        m = metrics(pred, gold, t)
        if best is None or m["F1"] > best[1]["F1"] or (m["F1"] == best[1]["F1"] and t > best[0]):
            best = (t, m)
    from opportunity_classifier import DECISION_TAU
    m_sys = metrics(syspred, gold, 0.5)  # 直接使用系统输出的判定列（1/0）
    m50 = metrics(pred, gold, DECISION_TAU)

    lines.append(f"人工标注样本数：**{len(gold)}**（正样本 {sum(gold)}，负样本 {len(gold)-sum(gold)}）\n")
    lines.append("## 一、判别指标\n")
    lines.append("| 阈值 | Accuracy | Precision | Recall | F1 | TP | FP | FN | TN |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for tag, t, m in [(f"系统判定（阈值 {DECISION_TAU}）", DECISION_TAU, m_sys),
                      (f"标注集最优阈值 {best[0]}", best[0], best[1])]:
        lines.append(f"| {tag} | {m['Accuracy']:.3f} | {m['Precision']:.3f} | {m['Recall']:.3f} | "
                     f"{m['F1']:.3f} | {m['TP']} | {m['FP']} | {m['FN']} | {m['TN']} |")
    lines.append(f"\n混淆矩阵（系统阈值 {DECISION_TAU}，行=人工真值，列=系统判定）：\n")
    lines.append("| 人工\\系统 | 判 1 | 判 0 |")
    lines.append("|---|---|---|")
    lines.append(f"| 人工=1 | {m_sys['TP']} | {m_sys['FN']} |")
    lines.append(f"| 人工=0 | {m_sys['FP']} | {m_sys['TN']} |")

    # ---- 分类指标（仅机会样本，人工给出标签的） ----
    func_gold = [(k, r["人工功能类别"].strip()) for k, r in zip(keys, gold_rows)
                 if int(r["人工是否机会(0/1)"]) == 1 and (r.get("人工功能类别") or "").strip()]
    ind_gold = [(k, r["人工所属行业"].strip()) for k, r in zip(keys, gold_rows)
                if int(r["人工是否机会(0/1)"]) == 1 and (r.get("人工所属行业") or "").strip()]
    # 分类一致率在"全部人工判 1 的样本"上计算（含系统判 0 的漏报样本，按分类错误计）
    func_gold = [(k, (r.get("人工功能类别") or "").strip()) for k, r in zip(keys, gold_rows)
                 if int(r["人工是否机会(0/1)"]) == 1 and (r.get("人工功能类别") or "").strip()]
    ind_gold = [(k, (r.get("人工所属行业") or "").strip()) for k, r in zip(keys, gold_rows)
                if int(r["人工是否机会(0/1)"]) == 1 and (r.get("人工所属行业") or "").strip()]
    if func_gold:
        hit = sum(1 for k, g in func_gold if res[k]["功能类别"] == g)
        lines.append(f"\n功能类别一致率：**{hit}/{len(func_gold)} = {hit/len(func_gold):.1%}**")
    if ind_gold:
        hit = sum(1 for k, g in ind_gold if res[k]["所属行业"] == g)
        lines.append(f"\n所属行业一致率：**{hit}/{len(ind_gold)} = {hit/len(ind_gold):.1%}**")

    # ---- 错误分析 ----
    lines.append("\n## 二、错误案例分析\n")
    lines.append("### 误报（系统判 1、人工判 0）\n")
    fps = [(k, r) for k, r in zip(keys, gold_rows) if int(res[k]["是否构成机会"]) == 1 and int(r["人工是否机会(0/1)"]) == 0]
    lines.append("| 记录 | 置信度 | 系统理由 | 人工备注 |")
    lines.append("|---|---|---|---|")
    for k, r in fps[:10]:
        e = ev.get(k, {})
        lines.append(f"| {k} | {res[k]['机会置信度']} | {e.get('判定理由','')} | {r.get('判定依据备注','')} |")
    if len(fps) > 10:
        lines.append(f"\n（其余 {len(fps)-10} 条误报见 result2.csv 与 task2_evidence.jsonl）")
    lines.append("\n### 漏报（系统判 0、人工判 1）\n")
    fns = [(k, r) for k, r in zip(keys, gold_rows) if int(res[k]["是否构成机会"]) == 0 and int(r["人工是否机会(0/1)"]) == 1]
    lines.append("| 记录 | 置信度 | 系统理由 | 人工备注 |")
    lines.append("|---|---|---|---|")
    for k, r in fns[:10]:
        e = ev.get(k, {})
        lines.append(f"| {k} | {res[k]['机会置信度']} | {e.get('判定理由','')} | {r.get('判定依据备注','')} |")

    # ---- 置信度分桶校准表 ----
    lines.append("\n## 三、置信度分桶一致性（判别置信度 vs 人工判定）\n")
    lines.append("| 置信度区间 | 样本数 | 人工判 1 比例 |")
    lines.append("|---|---|---|")
    bins = [(0.0, 0.3), (0.3, 0.4), (0.4, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 1.01)]
    for lo, hi in bins:
        sel = [g for p, g in zip(pred, gold) if lo <= p < hi]
        if sel:
            lines.append(f"| [{lo:.2f}, {hi:.2f}) | {len(sel)} | {sum(sel)/len(sel):.1%} |")

    if len(fns) > 10:
        lines.append(f"\n（其余 {len(fns)-10} 条漏报见 result2.csv 与 task2_evidence.jsonl）")
    with open(report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("\nreport ->", report)


if __name__ == "__main__":
    main()