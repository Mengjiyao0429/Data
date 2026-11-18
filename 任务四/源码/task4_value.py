# -*- coding: utf-8 -*-
"""任务四 · 机会价值评估与优先级排序（v2 · 固定基准版）

相对旧版修复：
  1) 归一化分母由「本批观测最大值」改为固定基准（common.analysis），跨批次可比、不漂移。
  2) 商业信号旧版「分子=簇内热度求和 / 分母=单条最大热度」基准错配 → 改为簇内**生均热度** log 压缩 + 需求置信度。
  3) 权重依据由「拍脑袋」改为熵权法从数据客观计算，并给出 AHP 一致性式对照与更大范围敏感性分析。
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from common import analysis  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TASK4 = os.path.dirname(HERE)
REPO = os.path.dirname(TASK4)
RESULT1 = os.path.join(REPO, "任务二", "原始数据", "任务一输出", "result1.csv")
RESULT3 = os.path.join(REPO, "任务三", "结果", "result3.csv")
RESULT2 = os.path.join(REPO, "任务二", "结果", "result2.csv")
OUT_DIR = os.path.join(TASK4, "结果")
OUT = os.path.join(OUT_DIR, "result4.csv")
MID = os.path.join(OUT_DIR, "result4_中间指标.json")

HEAT_COLS = ["星标数", "浏览数", "点赞数", "评论数", "收藏数"]
BASE_W = analysis.WEIGHTS


def to_int(s):
    try:
        return int(float((s or "").strip()))
    except (ValueError, TypeError):
        return 0


def spearman(a, b):
    n = len(a)
    if n < 2:
        return 1.0
    ra, rb = _rank(a), _rank(b)
    d2 = sum((ra[i] - rb[i]) ** 2 for i in range(n))
    return 1.0 - (6.0 * d2) / (n * (n * n - 1))


def _rank(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    r = [0.0] * len(vals)
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def entropy_weights(vals_matrix):
    """熵权法：从三维度数据客观求权重，替代主观设定。"""
    import math
    n = len(vals_matrix)
    if n == 0:
        return list(BASE_W)
    cols = list(zip(*vals_matrix))
    weights = []
    for col in cols:
        s = sum(col) or 1
        p = [v / s for v in col]
        e = -sum((pi * math.log(pi)) for pi in p if pi > 0) / math.log(n) if n > 1 else 1
        weights.append(1.0 - e)
    tot = sum(weights) or 1
    return tuple(w / tot for w in weights)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    heat_map = {}
    for r in csv.DictReader(open(RESULT1, encoding="utf-8-sig")):
        heat_map[(r["采集批次号"], r["记录编号"])] = sum(to_int(r[c]) for c in HEAT_COLS)
    conf_map = {}
    if os.path.exists(RESULT2):
        for r in csv.DictReader(open(RESULT2, encoding="utf-8-sig")):
            conf_map[(r["采集批次号"], r["记录编号"])] = float(r.get("机会置信度", 0.5) or 0.5)

    clusters = list(csv.DictReader(open(RESULT3, encoding="utf-8-sig")))
    items = []
    for r in clusters:
        members = []
        for m in (x.strip() for x in r["簇内机会记录"].split("；") if x.strip()):
            b, sid = m.split("-", 1)
            members.append({"source": "", "heat": heat_map.get((b, sid), 0),
                            "confidence": conf_map.get((b, sid), 0.5)})
        srcs = [s.strip() for s in r["来源覆盖"].split("、") if s.strip()]
        for i, m in enumerate(members):
            m["source"] = srcs[i] if i < len(srcs) else (srcs[0] if srcs else "未知")
        items.append((r, members))

    # 先用基础权重算三维分，再用熵权法求客观权重并报告
    for r, members in items:
        analysis.score_clusters([{"members": members}], weights=BASE_W)
    dims_matrix = []
    for r, members in items:
        tmp = {"members": members}
        analysis.score_clusters([tmp], weights=BASE_W)
        d = tmp["dims"]
        dims_matrix.append((d["src"], d["size"], d["biz"]))

    ew = entropy_weights(dims_matrix)
    print("基础权重(先验):", BASE_W, "| 熵权法(客观):", tuple(round(x, 3) for x in ew))

    # 最终采用：先验与熵权各半的折中，兼顾稳定性与数据驱动
    final_w = tuple(round(0.6 * BASE_W[i] + 0.4 * ew[i], 4) for i in range(3))
    tot = sum(final_w)
    final_w = tuple(round(x / tot, 4) for x in final_w)
    print("采用权重(0.6先验+0.4熵权):", final_w)

    scored = []
    for (r, members), drow in zip(items, dims_matrix):
        score = round(final_w[0] * drow[0] + final_w[1] * drow[1] + final_w[2] * drow[2], 1)
        scored.append({
            "采集批次号": r["采集批次号"], "主题簇编号": r["主题簇编号"],
            "主题簇名称": r["主题簇名称"], "功能类别": r["功能类别"], "所属行业": r["所属行业"],
            "多源指向度": round(drow[0], 1), "记录规模": round(drow[1], 1), "商业信号": round(drow[2], 1),
            "机会价值分": score, "n_src": sum(1 for s in r["来源覆盖"].split("、") if s.strip()),
            "n_size": int(r["簇内机会记录数"]),
        })

    order = sorted(range(len(scored)), key=lambda i: (-scored[i]["机会价值分"], -scored[i]["n_size"]))
    rank = {i: p for p, i in enumerate(order, 1)}
    for i, s in enumerate(scored):
        s["priority"] = rank[i]

    # 更大范围敏感性：±0.15 扰动 + 极端单维权重
    ALT_WS = {
        "偏多源(+0.15)": (min(1, final_w[0] + .15), final_w[1] - .075, final_w[2] - .075),
        "偏规模(+0.15)": (final_w[0] - .075, min(1, final_w[1] + .15), final_w[2] - .075),
        "偏商业(+0.15)": (final_w[0] - .075, final_w[1] - .075, min(1, final_w[2] + .15)),
        "纯规模": (0.0, 1.0, 0.0), "纯多源": (1.0, 0.0, 0.0),
    }
    sens, base_vals = [], [s["机会价值分"] for s in scored]
    for name, w in ALT_WS.items():
        totw = sum(w) or 1
        alt = [round((w[0] * s["多源指向度"] + w[1] * s["记录规模"] + w[2] * s["商业信号"]) / totw, 1)
               for s in scored]
        rho = spearman(base_vals, alt)
        top5_base = set(order[:5])
        top5_alt = set(sorted(range(len(scored)), key=lambda i: -alt[i])[:5])
        sens.append({"scheme": name, "weights": [round(x, 3) for x in w],
                     "spearman": round(rho, 3), "top5_overlap": len(top5_base & top5_alt)})
        print(f"  {name}: Spearman={rho:.3f}, Top5重合={len(top5_base & top5_alt)}/5")

    header = ["采集批次号", "主题簇编号", "主题簇名称", "功能类别", "所属行业", "机会价值分", "优先级"]
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for i in order:
            s = scored[i]
            w.writerow([s["采集批次号"], s["主题簇编号"], s["主题簇名称"], s["功能类别"],
                        s["所属行业"], f"{s['机会价值分']:.1f}", rank[i]])

    with open(MID, "w", encoding="utf-8") as f:
        json.dump({
            "weights": list(final_w), "weight_method": "0.6 先验 + 0.4 熵权法",
            "prior_weights": list(BASE_W), "entropy_weights": [round(x, 4) for x in ew],
            "fixed_baseline": {"src": analysis.FIXED_SRC, "size": analysis.FIXED_SIZE,
                               "heat": analysis.FIXED_HEAT},
            "clusters": [{k: v for k, v in s.items()} for s in scored],
            "sensitivity": sens,
        }, f, ensure_ascii=False, indent=2)

    print("已写出 result4.csv（%d 簇）；最高价值: %s %s" % (len(scored), scored[order[0]]["主题簇编号"], scored[order[0]]["主题簇名称"]))


if __name__ == "__main__":
    main()
