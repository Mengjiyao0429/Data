# -*- coding: utf-8 -*-
"""任务一～任务四 全流程可视化：信息量与分析过程图

所有图表均直接读取仓库内真实结果文件生成，可复现：
  - 任务一：任务一/结果/result1.csv（+ text/ 正文快照）
  - 任务二：任务二/结果/result2.csv、任务二/源码/gold_labels.csv
  - 任务三：任务三/结果/result3.csv、任务三/task3_主题簇报告.md
  - 任务四：任务四/结果/result4_中间指标.json、result4.csv

输出：可视化/图表/*.png（200 dpi）
运行：python 可视化/make_charts.py
"""
import csv
import json
import os
import re
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "可视化", "图表")
os.makedirs(OUT, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.dpi"] = 200
plt.rcParams["font.size"] = 10

C = {
    "blue": "#2E5C8A", "red": "#C0504D", "green": "#9BBB59", "cyan": "#4BACC6",
    "orange": "#F79646", "purple": "#8064A2", "steel": "#4F81BD", "gray": "#A5A5A5",
    "teal": "#31859B", "gold": "#D9A441",
}
BATCH_COLOR = {
    "B01": "#2E5C8A", "B02": "#4F81BD", "B03": "#4BACC6", "B04": "#C0504D",
    "B05": "#F79646", "B06": "#8064A2", "B07": "#31859B", "B08": "#9BBB59",
}


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", name)


def read_csv(path):
    return list(csv.DictReader(open(path, encoding="utf-8-sig")))


def to_int(s):
    s = (s or "").strip()
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------- 数据加载
def load_task1():
    rows = read_csv(os.path.join(ROOT, "任务一", "结果", "result1.csv"))
    text_dir = os.path.join(ROOT, "任务一", "结果", "text")
    snap_dir = os.path.join(ROOT, "任务二", "正文快照")
    out = []
    for r in rows:
        p = r.get("内容", "")
        fn = os.path.basename(p.replace("/", os.sep)) if p else ""
        cand = os.path.join(text_dir, fn)
        if not os.path.exists(cand):
            cand = os.path.join(snap_dir, fn)
        body = ""
        if fn and os.path.exists(cand):
            body = open(cand, encoding="utf-8").read()
            if "## 正文" in body:
                body = body.split("## 正文", 1)[1]
        cjk = len(re.findall(r"[\u4e00-\u9fff]", body))
        out.append({
            "batch": r["采集批次号"], "id": r["记录编号"], "src": r["来源网站名称"],
            "time": r.get("发布时间", "").strip(), "len": len(body.strip()),
            "cjk": cjk, "heat": sum(to_int(r[k]) for k in ["星标数", "浏览数", "点赞数", "评论数", "收藏数"]),
        })
    return out


def load_task2():
    return read_csv(os.path.join(ROOT, "任务二", "结果", "result2.csv"))


def load_task3():
    return read_csv(os.path.join(ROOT, "任务三", "结果", "result3.csv"))


def parse_task3_metrics():
    """解析 task3_主题簇报告.md 第三节逐簇质量指标表。"""
    p = os.path.join(ROOT, "任务三", "task3_主题簇报告.md")
    txt = open(p, encoding="utf-8").read()
    parts = txt.split("## 三、逐簇质量指标", 1)
    if len(parts) < 2:
        return []  # 报告已改为批次级指标，本函数仅兼容旧版报告
    sec = parts[1].split("## 四、", 1)[0]
    rows = []
    for line in sec.splitlines():
        m = re.match(r"^\|\s*(C\d+)\s*\|\s*(.+?)\s*\|\s*(\d+)\s*\|\s*([\-\d.]+)\s*\|\s*([\-\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)%", line)
        if m:
            rows.append({"cid": m.group(1), "name": m.group(2), "n": int(m.group(3)),
                         "npmI": float(m.group(4)), "sil": float(m.group(5)),
                         "cos": float(m.group(6)), "ind": float(m.group(7)) / 100.0})
    return rows


# ---------------------------------------------------------------- 图 1：全流程阶段收窄（阶梯瀑布）
def chart_funnel(t1, t2, t3, t4):
    n_rec = len(t1)
    n_opp = sum(1 for r in t2 if r["是否构成机会"] == "1")
    n_clu = len(t3)
    n_top = sum(1 for r in t4["clusters"] if int(r["priority"]) <= 5)
    stages = [
        ("采集清洗去重", n_rec, f"基准 100%"),
        ("AI 应用机会", n_opp, f"占采集 {n_opp / n_rec:.1%}"),
        ("主题簇", n_clu, f"占机会 {n_clu / max(n_opp, 1):.1%}"),
        ("高价值方向", n_top, f"优先级 1–5"),
    ]
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    colors = [C["blue"], C["green"], C["orange"], C["red"]]
    # 阶梯瀑布：每级宽度按规模线性递减，居中对齐，右侧标注数值与留存率
    for i, (name, cnt, note) in enumerate(stages):
        w = 0.68 * cnt / max(n_rec, 1) + 0.12
        y = len(stages) - i
        ax.add_patch(plt.Rectangle((0.5 - w / 2, y - 0.32), w, 0.64,
                                   color=colors[i], alpha=0.92))
        ax.text(0.5, y, f"{name}  {cnt:,}", ha="center", va="center",
                color="white", fontsize=11, fontweight="bold")
        ax.text(0.5, y - 0.46, note, ha="center", va="center", color="#555", fontsize=9)
        if i > 0:
            rate = cnt / max(stages[i - 1][1], 1) * 100
            ax.annotate("", xy=(0.5 + w / 2 + 0.02, y), xytext=(0.5 + w / 2 + 0.02, y + 1),
                        arrowprops=dict(arrowstyle="->", color="#9dbfdc", lw=1.4))
            ax.text(0.5 + w / 2 + 0.04, y + 0.5, f"{rate:.1f}%", va="center",
                    color="#2E5C8A", fontsize=9, fontweight="bold")
    ax.set_xlim(0, 1)
    ax.set_ylim(0.3, len(stages) + 0.7)
    ax.axis("off")
    ax.set_title("全流程阶段收窄（阶梯瀑布）：{} → {} → {} → {}".format(*[s[1] for s in stages]),
                 fontsize=13, fontweight="bold")
    save(fig, "01_全流程阶段收窄.png")


# ---------------------------------------------------------------- 图 2：批次×来源堆叠
def chart_batch_source(t1):
    batches = sorted({x["batch"] for x in t1})
    srcs = [s for s, _ in Counter(x["src"] for x in t1).most_common()]
    mat = defaultdict(lambda: defaultdict(int))
    for x in t1:
        mat[x["batch"]][x["src"]] += 1
    fig, ax = plt.subplots(figsize=(10, 5))
    bottom = np.zeros(len(batches))
    colors = plt.cm.tab20(np.linspace(0, 1, len(srcs)))
    for si, s in enumerate(srcs):
        vals = np.array([mat[b][s] for b in batches])
        ax.bar(batches, vals, bottom=bottom, label=s, color=colors[si], edgecolor="white", linewidth=0.4)
        bottom += vals
    for i, b in enumerate(batches):
        ax.text(i, bottom[i] + 15, str(int(bottom[i])), ha="center", fontsize=9, fontweight="bold")
    ax.set_ylabel("记录数")
    ax.set_title("任务一：各采集批次 × 来源网站 记录构成", fontsize=12, fontweight="bold")
    ax.legend(fontsize=7, ncol=2, loc="upper right", framealpha=0.9)
    save(fig, "02_批次来源构成.png")


# ---------------------------------------------------------------- 图 3：发布时间分布
def chart_time(t1):
    months = Counter()
    for x in t1:
        m = re.match(r"(\d{4})-(\d{2})", x["time"] or "")
        if m:
            months[f"{m.group(1)}-{m.group(2)}"] += 1
    keys = sorted(months)
    vals = [months[k] for k in keys]
    fig, ax = plt.subplots(figsize=(12, 4.2))
    ax.fill_between(range(len(keys)), vals, color=C["steel"], alpha=0.85)
    ax.plot(range(len(keys)), vals, color=C["blue"], linewidth=1.5)
    step = max(1, len(keys) // 12)
    ax.set_xticks(range(0, len(keys), step))
    ax.set_xticklabels([keys[i] for i in range(0, len(keys), step)], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("记录数")
    ax.set_title(f"任务一：发布时间月度分布（{keys[0]} ~ {keys[-1]}）", fontsize=12, fontweight="bold")
    ax.grid(axis="y", alpha=0.25)
    save(fig, "03_发布时间分布.png")


# ---------------------------------------------------------------- 图 4：正文长度 + 语种
def chart_length_lang(t1):
    lens = [x["len"] for x in t1 if x["len"] > 0]
    zh = sum(1 for x in t1 if x["cjk"] > 0)
    en = len(t1) - zh
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    ax.hist(lens, bins=50, color=C["cyan"], edgecolor="white")
    ax.set_yscale("log")
    ax.set_xlabel("清洗后正文长度（字符）")
    ax.set_ylabel("记录数（对数）")
    med = sorted(lens)[len(lens) // 2]
    ax.axvline(med, color=C["red"], linestyle="--", linewidth=1.4)
    ax.text(med, ax.get_ylim()[1] * 0.7, f" 中位数 {med}", color=C["red"], fontsize=9)
    ax.set_title("正文长度分布", fontsize=11, fontweight="bold")
    ax2 = axes[1]
    ax2.pie([zh, en], labels=[f"含中文 {zh}\n({zh / len(t1):.1%})", f"纯外文 {en}"],
            colors=[C["orange"], C["steel"]], autopct="%1.1f%%", startangle=90,
            wedgeprops={"edgecolor": "white"})
    ax2.set_title("记录语种构成", fontsize=11, fontweight="bold")
    save(fig, "04_正文长度与语种.png")


# ---------------------------------------------------------------- 图 5：各批次机会率
def chart_opp_rate(t2):
    tot = Counter(r["采集批次号"] for r in t2)
    opp = Counter(r["采集批次号"] for r in t2 if r["是否构成机会"] == "1")
    batches = sorted(tot)
    rates = [opp[b] / tot[b] * 100 for b in batches]
    global_rate = sum(opp.values()) / max(sum(tot.values()), 1) * 100
    fig, ax = plt.subplots(figsize=(9, 4.2))
    palette = plt.cm.tab10(np.linspace(0, 1, len(batches)))
    bars = ax.bar(batches, rates, color=[BATCH_COLOR.get(b, palette[i]) for i, b in enumerate(batches)], edgecolor="white")
    for i, b in enumerate(batches):
        ax.text(i, rates[i] + 0.3, f"{rates[i]:.1f}%\n{opp[b]}/{tot[b]}", ha="center", fontsize=9)
    ax.axhline(global_rate, color=C["gray"], linestyle="--", linewidth=1, label=f"全局 {global_rate:.1f}%")
    ax.set_ylabel("机会率 (%)")
    ax.set_ylim(0, max(rates) * 1.35)
    ax.set_title("任务二：各批次 AI 应用机会率", fontsize=12, fontweight="bold")
    ax.legend()
    save(fig, "05_各批次机会率.png")


# ---------------------------------------------------------------- 图 6：置信度分布
def chart_conf(t2):
    pos = [float(r["机会置信度"]) for r in t2 if r["是否构成机会"] == "1"]
    neg = [float(r["机会置信度"]) for r in t2 if r["是否构成机会"] == "0"]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    bins = np.linspace(0, 1, 41)
    ax.hist(neg, bins=bins, color=C["gray"], alpha=0.85, label=f"非机会 {len(neg)}", edgecolor="white")
    ax.hist(pos, bins=bins, color=C["red"], alpha=0.9, label=f"机会 {len(pos)}", edgecolor="white")
    ax.axvline(0.56, color=C["blue"], linestyle="--", linewidth=1.6)
    ax.text(0.57, ax.get_ylim()[1] * 0.8, "阈值 0.56", color=C["blue"], fontsize=9)
    ax.set_yscale("log")
    ax.set_xlabel("机会置信度")
    ax.set_ylabel("记录数（对数）")
    ax.set_title("任务二：机会置信度分布（判定与置信度一致）", fontsize=12, fontweight="bold")
    ax.legend()
    save(fig, "06_机会置信度分布.png")


# ---------------------------------------------------------------- 图 7：功能类别 + 行业
def chart_labels(t2):
    opp = [r for r in t2 if r["是否构成机会"] == "1"]
    fc = Counter(r["功能类别"] for r in opp if r["功能类别"])
    ind = Counter(r["所属行业"] for r in opp if r["所属行业"])
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    ax = axes[0]
    items = fc.most_common()
    ax.barh([k for k, _ in items][::-1], [v for _, v in items][::-1], color=C["steel"])
    for i, (k, v) in enumerate(items[::-1]):
        ax.text(v + 0.3, i, str(v), va="center", fontsize=8)
    ax.set_title(f"功能类别分布（{len(fc)} 类）", fontsize=11, fontweight="bold")
    ax.set_xlabel("机会记录数")
    ax2 = axes[1]
    items2 = ind.most_common(12)
    ax2.barh([k for k, _ in items2][::-1], [v for _, v in items2][::-1], color=C["orange"])
    for i, (k, v) in enumerate(items2[::-1]):
        ax2.text(v + 0.3, i, str(v), va="center", fontsize=8)
    ax2.set_title(f"所属行业分布（Top12 / 共 {len(ind)} 类）", fontsize=11, fontweight="bold")
    ax2.set_xlabel("机会记录数")
    save(fig, "07_功能类别与行业分布.png")


# ---------------------------------------------------------------- 图 8：混淆矩阵
def chart_confusion(t2):
    gold = read_csv(os.path.join(ROOT, "任务二", "源码", "gold_labels.csv"))
    pred = {(r["采集批次号"], r["记录编号"]): r["是否构成机会"] for r in t2}
    tp = fp = fn = tn = 0
    for g in gold:
        key = (g["采集批次号"], g["记录编号"])
        y = int(g["人工是否机会(0/1)"])
        p = int(pred.get(key, "0"))
        if y == 1 and p == 1: tp += 1
        elif y == 0 and p == 1: fp += 1
        elif y == 1 and p == 0: fn += 1
        else: tn += 1
    cm = np.array([[tp, fn], [fp, tn]])
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    im = ax.imshow(cm, cmap="Blues", alpha=0.9)
    labels = ["机会", "非机会"]
    ax.set_xticks([0, 1]); ax.set_xticklabels([f"预测 {l}" for l in labels])
    ax.set_yticks([0, 1]); ax.set_yticklabels([f"真实 {l}" for l in labels])
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=18,
                    color="white" if cm[i, j] > cm.max() * 0.5 else "#333", fontweight="bold")
    acc = (tp + tn) / max(1, len(gold))
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    f1 = 2 * prec * rec / max(1e-9, prec + rec)
    ax.set_title(f"人工标注集混淆矩阵（n={len(gold)}）\nAcc {acc:.3f} | P {prec:.3f} | R {rec:.3f} | F1 {f1:.3f}",
                 fontsize=10, fontweight="bold")
    save(fig, "08_混淆矩阵.png")


# ---------------------------------------------------------------- 图 9：簇规模 + 逐簇指标
def chart_cluster_quality(t3, meta):
    cids = [r["主题簇编号"] for r in t3]
    sizes = [int(r["簇内机会记录数"]) for r in t3]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    ax = axes[0]
    ax.bar(cids, sizes, color=[BATCH_COLOR.get(r["采集批次号"], C["steel"]) for r in t3])
    ax.set_title(f"{len(cids)} 个主题簇的记录规模（逐批次独立聚类）", fontsize=11, fontweight="bold")
    ax.set_ylabel("簇内机会记录数")
    ax.tick_params(axis="x", labelrotation=90, labelsize=7)
    # 右图：只展示批次级内部指标，避免把批次常量误画成“逐簇指标”
    ax2 = axes[1]
    batches = sorted(meta["batches"])
    sil = [meta["batches"][b]["silhouette"] for b in batches]
    ari = [meta["batches"][b]["stability"] for b in batches]
    x = np.arange(len(batches)); wgt = 0.38
    ax2.bar(x - wgt / 2, sil, wgt, label="轮廓系数（批次级）", color=C["blue"])
    ax2.bar(x + wgt / 2, ari, wgt, label="多种子平均 ARI（批次级）", color=C["green"])
    ax2.set_xticks(x); ax2.set_xticklabels(batches, fontsize=9)
    ax2.set_ylabel("指标值")
    ax2.set_title("批次级聚类质量指标（轮廓系数 / ARI）", fontsize=11, fontweight="bold")
    ax2.legend(fontsize=8)
    save(fig, "09_簇规模与质量指标.png")


# ---------------------------------------------------------------- 图 10：簇×来源热力图
def chart_cluster_source(t1, t3):
    src_of = {(x["batch"], x["id"]): x["src"] for x in t1}
    srcs = [s for s, _ in Counter(x["src"] for x in t1).most_common()]
    cids, mat = [], []
    for r in t3:
        cids.append(r["主题簇编号"])
        row = [0] * len(srcs)
        for m in r["簇内机会记录"].split("；"):
            m = m.strip()
            if not m:
                continue
            b, sid = m.split("-", 1)
            s = src_of.get((b, sid))
            if s in srcs:
                row[srcs.index(s)] += 1
        mat.append(row)
    M = np.array(mat)
    fig, ax = plt.subplots(figsize=(9.5, 6))
    im = ax.imshow(M, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(srcs)))
    ax.set_xticklabels(srcs, rotation=35, ha="right", fontsize=8)
    ax.set_yticks(range(len(cids)))
    ax.set_yticklabels(cids, fontsize=8)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if M[i, j]:
                ax.text(j, i, M[i, j], ha="center", va="center", fontsize=7,
                        color="white" if M[i, j] > M.max() * 0.5 else "#333")
    ax.set_title("任务三：主题簇 × 来源网站 机会记录热度矩阵", fontsize=12, fontweight="bold")
    fig.colorbar(im, ax=ax, shrink=0.8, label="机会记录数")
    save(fig, "10_簇来源热力图.png")


# ---------------------------------------------------------------- 图 11：语义空间散点
def chart_semantic_space(t3):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD, PCA
    except Exception as e:
        print("skip semantic scatter (sklearn unavailable):", e)
        return
    docs, labels = [], []
    snap = os.path.join(ROOT, "任务二", "正文快照")
    for ci, r in enumerate(t3):
        for m in r["簇内机会记录"].split("；"):
            m = m.strip()
            if not m:
                continue
            b, sid = m.split("-", 1)
            p = os.path.join(snap, f"{b}_{sid}.md")
            txt = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
            if "## 正文" in txt:
                txt = txt.split("## 正文", 1)[1]
            toks = re.findall(r"[\u4e00-\u9fff]{2,4}|[a-zA-Z]{2,}", txt.lower())
            docs.append(" ".join(toks))
            labels.append(ci)
    vec = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b", min_df=2, max_df=0.6, sublinear_tf=True)
    X = vec.fit_transform(docs)
    svd = TruncatedSVD(n_components=min(96, X.shape[1] - 1), random_state=42)
    Xl = svd.fit_transform(X)
    xy = PCA(n_components=2, random_state=42).fit_transform(Xl)
    fig, ax = plt.subplots(figsize=(9, 6.5))
    cmap = plt.cm.tab20(np.linspace(0, 1, len(t3)))
    for ci, r in enumerate(t3):
        idx = [i for i, l in enumerate(labels) if l == ci]
        ax.scatter(xy[idx, 0], xy[idx, 1], s=26, color=cmap[ci], alpha=0.85,
                   label=f"{r['主题簇编号']} {r['主题簇名称']}", edgecolor="white", linewidth=0.3)
    ax.set_xlabel("语义主成分 1")
    ax.set_ylabel("语义主成分 2")
    ax.set_title(f"任务三：语义空间散点（TF-IDF→LSA(96)→PCA，{len(docs)} 条机会记录）",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=6, ncol=2, loc="best", framealpha=0.9)
    save(fig, "11_语义空间散点.png")


# ---------------------------------------------------------------- 图 12：价值分排序
def chart_value_rank(t4):
    rows = sorted(t4["clusters"], key=lambda x: x["priority"])
    names = [f"{r['主题簇编号']} {r['主题簇名称']}" for r in rows]
    vals = [r["机会价值分"] for r in rows]
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    colors = [plt.cm.RdYlGn(1 - (v - min(vals)) / (max(vals) - min(vals)) * 0.85) for v in vals]
    bars = ax.barh(range(len(rows)), vals, color=colors)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"P{r['priority']}  {n}" for r, n in zip(rows, names)], fontsize=8)
    ax.invert_yaxis()
    for i, v in enumerate(vals):
        ax.text(v + 0.6, i, f"{v:.1f}", va="center", fontsize=8)
    ax.set_xlabel("机会价值分")
    ax.set_xlim(0, max(vals) * 1.12)
    ax.set_title(f"任务四：{len(t4['clusters'])} 个主题簇机会价值分与优先级", fontsize=12, fontweight="bold")
    save(fig, "12_价值分排序.png")


# ---------------------------------------------------------------- 图 13：三维度加权贡献
def chart_contrib(t4):
    rows = sorted(t4["clusters"], key=lambda x: x["priority"])
    src = [0.35 * r["多源指向度"] for r in rows]
    size = [0.35 * r["记录规模"] for r in rows]
    biz = [0.30 * r["商业信号"] for r in rows]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    x = np.arange(len(rows))
    ax.bar(x, src, label="多源指向度 ×0.35", color=C["blue"])
    ax.bar(x, size, bottom=src, label="记录规模 ×0.35", color=C["green"])
    ax.bar(x, biz, bottom=np.array(src) + np.array(size), label="商业信号 ×0.30", color=C["orange"])
    ax.set_xticks(x)
    ax.set_xticklabels([f"P{r['priority']}\n{r['主题簇编号']}" for r in rows], fontsize=7)
    ax.set_ylabel("机会价值分（加权贡献）")
    ax.set_title("任务四：机会价值分的三维度加权贡献分解", fontsize=12, fontweight="bold")
    ax.legend(fontsize=8)
    save(fig, "13_三维度加权贡献.png")


# ---------------------------------------------------------------- 图 14：敏感性分析
def chart_sensitivity(t4):
    sens = t4.get("sensitivity", [])
    if not sens:
        return
    names = ["基础权重\n0.35/0.35/0.30"] + [s["scheme"] + "\n" + "/".join(f"{w:.2f}" for w in s["weights"]) for s in sens]
    rhos = [1.0] + [s["spearman"] for s in sens]
    ov = [5] + [s["top5_overlap"] for s in sens]
    fig, ax = plt.subplots(figsize=(9, 4))
    bars = ax.bar(range(len(names)), rhos, color=[C["blue"]] + [C["orange"]] * len(sens))
    ax.set_ylim(0, 1.05)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, fontsize=8)
    for i, (rho, o) in enumerate(zip(rhos, ov)):
        ax.text(i, rho + 0.02, f"{rho:.3f}\nTop5 {o}/5", ha="center", fontsize=8)
    ax.set_ylabel("与基础权重排名的 Spearman 相关")
    ax.set_title("任务四：权重敏感性分析（排序稳健性）", fontsize=12, fontweight="bold")
    save(fig, "14_敏感性分析.png")


def main():
    print("loading...")
    t1 = load_task1()
    t2 = load_task2()
    t3 = load_task3()
    metrics = parse_task3_metrics()
    t3meta = json.load(open(os.path.join(ROOT, "任务三", "结果", "result3_聚类元信息.json"), encoding="utf-8"))
    t4 = json.load(open(os.path.join(ROOT, "任务四", "结果", "result4_中间指标.json"), encoding="utf-8"))
    print(f"t1={len(t1)} t2={len(t2)} t3={len(t3)} metrics={len(metrics)} t4clusters={len(t4['clusters'])}")

    chart_funnel(t1, t2, t3, t4)
    chart_batch_source(t1)
    chart_time(t1)
    chart_length_lang(t1)
    chart_opp_rate(t2)
    chart_conf(t2)
    chart_labels(t2)
    chart_confusion(t2)
    chart_cluster_quality(t3, t3meta)
    chart_cluster_source(t1, t3)
    chart_semantic_space(t3)
    chart_value_rank(t4)
    chart_contrib(t4)
    chart_sensitivity(t4)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
