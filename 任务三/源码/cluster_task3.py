# -*- coding: utf-8 -*-
"""任务三 · 赛道热点主题聚合（v4 · 批次独立版）

相对 v3 的关键修复：
  1) 主题词错配 bug：旧版把簇按规模重排后用「排序序号」去取原「标签序」top_ids，
     导致主题名/关键词/逐簇 NPMI 大面积错配。v4 统一用 common.analysis 按标签映射。
  2) 跨批次混合：旧版把 B01–B08 机会记录全局混聚，违背「各批次分析相互独立」。
     v4 按采集批次号分组，逐批次独立聚类；result3.csv 的「采集批次号」如实标注。
  3) 多源共同指向：批次内聚类后单独统计来源覆盖；另出一份「跨批次热点主题」
     补充报告（不进官方 result3.csv）， honest 地区分两种分析口径。
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from common import analysis  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TASK3 = os.path.dirname(HERE)
REPO = os.path.dirname(TASK3)
TASK2 = os.path.join(REPO, "任务二")

RESULT2 = os.path.join(TASK2, "结果", "result2.csv")
SNAP2 = os.path.join(TASK2, "正文快照")
R1_PATH = os.path.join(TASK2, "原始数据", "任务一输出", "result1.csv")
OUT_DIR = os.path.join(TASK3, "结果")
OUT_CSV = os.path.join(OUT_DIR, "result3.csv")
CROSS_CSV = os.path.join(OUT_DIR, "result3_跨批次热点补充.csv")
REPORT = os.path.join(TASK3, "task3_主题簇报告.md")
META_JSON = os.path.join(OUT_DIR, "result3_聚类元信息.json")

HEADER = ["采集批次号", "主题簇编号", "主题簇名称", "功能类别", "所属行业",
          "簇内机会记录数", "来源覆盖", "簇内机会记录"]


def _load_text(b, sid):
    p = os.path.join(SNAP2, f"{b}_{sid}.md")
    if not os.path.exists(p):
        return "", ""
    t = open(p, encoding="utf-8").read()
    m = next((ln[2:].strip() for ln in t.splitlines() if ln.startswith("# ")), "")
    body = t.split("## 正文", 1)[1] if "## 正文" in t else t
    return m, body


def _build_items(opp, src_map):
    items = []
    for r in opp:
        b, sid = r["采集批次号"], r["记录编号"]
        title, body = _load_text(b, sid)
        items.append({
            "id": f"{b}-{sid}", "batch": b, "sid": sid,
            "title": title, "body": body,
            "text": (title + "\n" + body).strip(),
            "func": r.get("功能类别", ""), "industry": r.get("所属行业", ""),
            "confidence": float(r.get("机会置信度", 0.5) or 0.5),
            "source": src_map.get((b, sid), "未知"),
        })
    return items


def _cluster_rows(batch, items):
    """单批次聚类 → (result3行, 富信息簇)。簇编号批内独立 C1..Ck。"""
    clusters, info = analysis.cluster_items(items, min_df=1, svd_dim=48, k_min=2, k_max=10)
    rows, rich = [], []
    for c in clusters:
        ids = sorted(m["id"] for m in c["members"])
        srcs = Counter(m["source"] for m in c["members"])
        rows.append({
            "采集批次号": batch, "主题簇编号": c["cid"], "主题簇名称": c["name"],
            "功能类别": c["func"], "所属行业": c["industry"],
            "簇内机会记录数": str(len(c["members"])),
            "来源覆盖": "、".join(s for s, _ in srcs.most_common()),
            "簇内机会记录": "；".join(ids),
        })
        rich.append({**c, "batch": batch, "info": info})
    return rows, rich, info


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows2 = list(csv.DictReader(open(RESULT2, encoding="utf-8-sig")))
    opp = [r for r in rows2 if r["是否构成机会"] == "1"]

    src_map = {}
    if os.path.exists(R1_PATH):
        for r in csv.DictReader(open(R1_PATH, encoding="utf-8-sig")):
            src_map[(r["采集批次号"], r["记录编号"])] = r["来源网站名称"]

    items = _build_items(opp, src_map)
    by_batch = defaultdict(list)
    for it in items:
        by_batch[it["batch"]].append(it)

    all_rows, meta = [], {}
    for batch in sorted(by_batch):
        rows, rich, info = _cluster_rows(batch, by_batch[batch])
        all_rows.extend(rows)
        meta[batch] = {"n": len(by_batch[batch]), "clusters": len(rows), **info}
        print(f"{batch}: 机会 {len(by_batch[batch]):>4} 条 → {len(rows):>2} 簇 "
              f"(轮廓 {info['silhouette']}, 稳定性 {info['stability']})")

    # 簇编号全局连续（C1..Cn）：聚类仍逐批次独立，仅编号在汇总文件中连续，避免跨批重名
    for seq, r in enumerate(all_rows, 1):
        r["主题簇编号"] = "C%d" % seq

    # 批内优先级：按记录规模预排序（任务四将按固定基准评分重排优先级）
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(all_rows)

    with open(META_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "mode": "per_batch_independent",
            "note": "每个采集批次独立聚类；簇编号批内独立（C1..Ck）；分数跨批不可直接比较",
            "batches": meta,
        }, f, ensure_ascii=False, indent=2)

    # 跨批次热点补充（明确标注非官方 result3，用于多源共同指向的全局观察）
    cross_clusters, cross_info = analysis.cluster_items(items, min_df=2, svd_dim=96, k_min=10, k_max=30)
    cross_rows = []
    for c in cross_clusters:
        ids = sorted(m["id"] for m in c["members"])
        srcs = Counter(m["source"] for m in c["members"])
        cross_rows.append({
            "主题簇编号": c["cid"], "主题簇名称": c["name"], "功能类别": c["func"],
            "所属行业": c["industry"], "簇内机会记录数": str(len(c["members"])),
            "来源覆盖": "、".join(s for s, _ in srcs.most_common()),
            "覆盖来源数": str(len(srcs)), "簇内机会记录": "；".join(ids),
        })
    with open(CROSS_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cross_rows[0].keys()) if cross_rows else ["主题簇编号"])
        w.writeheader()
        w.writerows(cross_rows)

    # 报告
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("# 任务三 主题聚合报告（v4 · 批次独立）\n\n")
        f.write("- 口径：每个采集批次独立聚类，结果 `result3.csv` 中「采集批次号」如实标注，"
                "簇编号批内独立（C1..Ck）。符合赛题「各批次分析相互独立」。\n")
        f.write("- 方法：jieba 分词 + TF-IDF(1-2gram) → TruncatedSVD(LSA) → KMeans，"
                "k 由轮廓系数在批内候选集择优；稳定性用多种子两两 ARI。\n")
        f.write("- 主题名：按**标签号**取簇内高权重词（修复 v3 排序错配 bug）+ 功能/行业词自动合成，无人工硬编码。\n\n")
        f.write("## 一、各批次聚类概览\n\n")
        f.write("| 批次 | 机会记录 | 主题簇 | 轮廓系数 | 稳定性 ARI | 向量维度 |\n|---|---|---|---|---|---|\n")
        for b in sorted(meta):
            m = meta[b]
            f.write(f"| {b} | {m['n']} | {m['clusters']} | {m['silhouette']} | {m['stability']} | {m['vectors']} |\n")
        f.write("\n## 二、各批次主题簇\n\n")
        f.write("| 批次 | 簇 | 主题 | 功能 | 行业 | 记录数 | 来源覆盖 |\n|---|---|---|---|---|---|---|\n")
        for r in all_rows:
            f.write(f"| {r['采集批次号']} | {r['主题簇编号']} | {r['主题簇名称']} | {r['功能类别']} | "
                    f"{r['所属行业']} | {r['簇内机会记录数']} | {r['来源覆盖']} |\n")
        f.write("\n## 三、簇内行业一致率（外部有效性参照）\n\n")
        f.write("> 轮廓系数与多种子 ARI 是**批次级**指标（见第一节），不随簇变化，故不再伪装成“逐簇 NPMI/余弦”逐行重复。"
                "本表仅报告可从记录标签直接复算的簇内行业众数占比；该指标受“其他”标签占比高影响，"
                "只能作为弱监督参照，不作为聚类质量判据。\n\n")
        f.write("| 簇 | 主题 | 批次 | 记录数 | 批次轮廓系数 | 批次稳定性 ARI | 簇内行业众数占比 |\n|---|---|---|---:|---:|---:|---:|\n")
        ind_of = {(it["batch"], it["id"]): it.get("industry", "") for it in items}
        for row in all_rows:
            b = row["采集批次号"]
            info_b = meta[b]
            ids = [x.strip() for x in row["簇内机会记录"].split("；") if x.strip()]
            inds = Counter(ind_of.get((b, x.split("-")[1]), "") for x in ids)
            n = len(ids)
            modal = max(inds.values()) / n if n else 0.0
            f.write(f"| {row['主题簇编号']} | {row['主题簇名称']} | {b} | {n} | "
                    f"{info_b['silhouette']:.4f} | {info_b['stability']:.4f} | {modal:.1%} |\n")
        f.write("\n> 内部指标（批次级轮廓系数、ARI）显示簇结构偏弱；行业众数占比仅说明簇对应可辨认的业务语义，"
                "两类指标共同支持将聚类结果定位为“粗粒度主题分区”。\n")

        f.write("\n## 四、跨批次热点主题（补充分析，非官方 result3）\n\n")
        f.write("> 以下为把全部批次机会记录合并观察的「全局热点」，仅用于多源共同指向的补充洞察；"
                "不进入 result3.csv，以免与批次独立口径冲突。\n\n")
        f.write(f"- 合并机会 {len(items)} 条 → {len(cross_rows)} 个主题簇；"
                f"轮廓 {cross_info['silhouette']}，稳定性 {cross_info['stability']}\n\n")
        f.write("| 簇 | 主题 | 记录数 | 覆盖来源数 | 来源覆盖 |\n|---|---|---|---|---|\n")
        for r in sorted(cross_rows, key=lambda x: -int(x["覆盖来源数"]))[:15]:
            f.write(f"| {r['主题簇编号']} | {r['主题簇名称']} | {r['簇内机会记录数']} | "
                    f"{r['覆盖来源数']} | {r['来源覆盖']} |\n")

    print(f"已写出 result3.csv（{len(all_rows)} 簇，批次独立），"
          f"跨批次补充 {len(cross_rows)} 簇")


if __name__ == "__main__":
    main()
