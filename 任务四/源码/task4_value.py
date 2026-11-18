# -*- coding: utf-8 -*-
"""任务四 · 机会价值评估与优先级排序（优化版）

方法：
  1) 三维度 0~100 评分：
     ① 多源指向度 = 来源种类数 / 观测最大值(4)
     ② 记录规模   = 簇内机会记录数 / 观测最大值(59)
     ③ 补充维度「商业信号」（复合指标，0~100）：
            0.6 × 互动热度分（真实互动热度，log1p 压缩归一化）
          + 0.4 × 跨批次持续性分（簇覆盖 B01–B05 的批次数 / 5）
  2) 机会价值分 = 0.35×多源 + 0.35×规模 + 0.30×商业信号（保留 1 位小数）
  3) 优先级：价值分降序（1 最高），同分按记录规模降序
  4) 敏感性分析：3 组替代权重下的排名 Spearman 相关与 Top-5 集合稳定性
"""
import csv
import json
import math
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
TASK4 = os.path.dirname(HERE)
REPO = os.path.dirname(TASK4)

RESULT1 = os.path.join(REPO, "任务二", "原始数据", "任务一输出", "result1.csv")
RESULT3 = os.path.join(REPO, "任务三", "结果", "result3.csv")
OUT_DIR = os.path.join(TASK4, "结果")
OUT = os.path.join(OUT_DIR, "result4.csv")

HEAT_COLS = ["星标数", "浏览数", "点赞数", "评论数", "收藏数"]

# 基础权重（多源指向度, 记录规模, 商业信号）
BASE_W = (0.35, 0.35, 0.30)
# 敏感性分析用的替代权重
ALT_WS = {
    "偏记录规模": (0.30, 0.40, 0.30),
    "偏多源指向": (0.40, 0.30, 0.30),
    "偏商业信号": (0.30, 0.30, 0.40),
}


def to_int(s):
    s = (s or "").strip()
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def spearman(a, b):
    """两列排名的 Spearman 相关（a,b 均为数值列表，返回 [-1,1]）。"""
    n = len(a)
    ra = _rank(a)
    rb = _rank(b)
    d2 = sum((ra[i] - rb[i]) ** 2 for i in range(n))
    return 1.0 - (6.0 * d2) / (n * (n * n - 1)) if n > 1 else 1.0


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


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # 1) 建索引：(批次, 记录编号) -> 来源, 热度
    src_map, heat_map = {}, {}
    for r in csv.DictReader(open(RESULT1, encoding="utf-8-sig")):
        key = (r["采集批次号"], r["记录编号"])
        src_map[key] = r["来源网站名称"]
        heat_map[key] = sum(to_int(r[c]) for c in HEAT_COLS)
    max_heat = max(heat_map.values()) if heat_map else 1

    # 2) 读任务三 14 簇
    clusters = list(csv.DictReader(open(RESULT3, encoding="utf-8-sig")))

    scored = []
    for r in clusters:
        members = [x.strip() for x in r["簇内机会记录"].split("；") if x.strip()]
        keys = []
        for m in members:
            b, sid = m.split("-", 1)
            keys.append((b, sid))

        n_src = len({src_map.get(k, "未知") for k in keys})
        n_size = len(keys)
        heat = sum(heat_map.get(k, 0) for k in keys)
        n_batch = len({k[0] for k in keys})

        # 三维度 0~100
        src_score = 100.0 * n_src / 4.0
        size_score = 100.0 * n_size / 59.0
        heat_score = 100.0 * math.log1p(heat) / math.log1p(max_heat)
        persist_score = 100.0 * n_batch / 5.0
        biz_score = 0.6 * heat_score + 0.4 * persist_score   # 商业信号复合

        value = BASE_W[0] * src_score + BASE_W[1] * size_score + BASE_W[2] * biz_score

        scored.append({
            "采集批次号": r["采集批次号"],
            "主题簇编号": r["主题簇编号"],
            "主题簇名称": r["主题簇名称"],
            "功能类别": r["功能类别"],
            "所属行业": r["所属行业"],
            "多源指向度": round(src_score, 1),
            "记录规模": round(size_score, 1),
            "商业信号": round(biz_score, 1),
            "机会价值分": round(value, 1),
            "_n_size": n_size, "_n_src": n_src, "_heat": heat, "_n_batch": n_batch,
        })

    # 3) 基础权重下的优先级
    order = sorted(range(len(scored)),
                   key=lambda i: (-scored[i]["机会价值分"], -scored[i]["_n_size"]))
    rank = {i: pos for pos, i in enumerate(order, 1)}

    # 4) 敏感性分析
    sens = []
    base_vals = [s["机会价值分"] for s in scored]
    for name, w in ALT_WS.items():
        alt = [round(w[0] * s["多源指向度"] + w[1] * s["记录规模"] + w[2] * s["商业信号"], 1)
               for s in scored]
        rho = spearman(base_vals, alt)
        alt_order = sorted(range(len(scored)), key=lambda i: (-alt[i], -scored[i]["_n_size"]))
        top5_base = set(order[:5])
        top5_alt = set(alt_order[:5])
        sens.append((name, w, rho, len(top5_base & top5_alt)))

    # 5) 写出 result4.csv（官方 7 列）
    header = ["采集批次号", "主题簇编号", "主题簇名称", "功能类别",
              "所属行业", "机会价值分", "优先级"]
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for i in order:
            s = scored[i]
            w.writerow([s["采集批次号"], s["主题簇编号"], s["主题簇名称"],
                        s["功能类别"], s["所属行业"], f"{s['机会价值分']:.1f}", rank[i]])

    # 6) 控制台输出
    print("优先级 | 簇 | 主题 | 多源 | 规模 | 商业信号 | 价值分")
    for i in order:
        s = scored[i]
        print(f"{rank[i]:>2} | {s['主题簇编号']:>3} | {s['主题簇名称']} | "
              f"{s['多源指向度']:>5.1f} | {s['记录规模']:>5.1f} | {s['商业信号']:>5.1f} | {s['机会价值分']:>5.1f}")
    print("\n敏感性分析（对比基础权重 0.35/0.35/0.30）：")
    for name, w, rho, overlap in sens:
        print(f"  {name} {w} : Spearman={rho:.3f}, Top5 重合={overlap}/5")
    print("已写出:", OUT)

    # 7) 额外导出中间指标（便于论文/核对，不作为官方交付）
    with open(os.path.join(OUT_DIR, "result4_中间指标.json"), "w", encoding="utf-8") as f:
        json.dump({"weights": BASE_W,
                   "max_heat": max_heat,
                   "clusters": [{k: v for k, v in s.items() if not k.startswith("_")} | {"n_batch": s["_n_batch"], "heat_sum": s["_heat"], "n_src": s["_n_src"], "priority": rank[i]}
                                for i, s in enumerate(scored)],
                   "sensitivity": [{"scheme": n, "weights": w, "spearman": round(rho, 3), "top5_overlap": ov}
                                   for n, w, rho, ov in sens]},
                  f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
