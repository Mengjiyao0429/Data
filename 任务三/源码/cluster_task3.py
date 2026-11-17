# -*- coding: utf-8 -*-
"""任务三 · 赛道热点主题聚合

输入：任务二 result2.csv（388 条判为机会的记录）+ 任务二正文快照。
方法：字符/词 n-gram TF-IDF → 余弦相似度 → KMeans（k-means++ 初始化，余弦距离）聚类；
      k 由轮廓系数（余弦）在 [10,12,…,20] 内自动选取；主题名称由簇内高权重词提炼，
      功能类别/所属行业取簇内多数票。
输出：任务三/结果/result3.csv（官方 8 列表头）。
"""
import csv, math, os, random, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
TASK3 = os.path.dirname(HERE)
REPO = os.path.dirname(TASK3)
TASK2 = os.path.join(REPO, "任务二")
sys.path.insert(0, os.path.join(REPO, "任务一", "源码"))
try:
    from app.labels import INDUSTRY_KEYWORDS
except Exception:
    INDUSTRY_KEYWORDS = {}
RESULT2 = os.path.join(TASK2, "结果", "result2.csv")
SNAP2 = os.path.join(TASK2, "正文快照")
OUT_DIR = os.path.join(TASK3, "结果")
OUT_CSV = os.path.join(OUT_DIR, "result3.csv")
REPORT = os.path.join(TASK3, "task3_主题簇报告.md")
OPP_SNAP = os.path.join(TASK3, "机会快照")
HEADER = ["采集批次号", "主题簇编号", "主题簇名称", "功能类别", "所属行业",
          "簇内机会记录数", "来源覆盖", "簇内机会记录"]

SEED = 20261117
K_RANGE = [10, 12, 14, 16, 18, 20]

CN_STOP = set("的 了 和 与 是 在 有 为 对 及 或 这 那 个 我 你 他 它 们 就 都 而 还 也 很 可以 一个 我们 通过 进行 实现 使用 以及 基于 相关 支持 提供 包括 问题 需要 如何 什么 介绍 关于 一个 我们 自己 这个 那个 现在 已经 没有 不是 就是 但是 因为 所以 如果 可能 需要 一下 一些".split())
EN_STOP = set("the and for with that this from are was were will can not you your our its use using based into more than has have had new how what when which who why".split())


def load_text(b, sid):
    p = os.path.join(SNAP2, f"{b}_{sid}.md")
    if not os.path.exists(p):
        return "", ""
    t = open(p, encoding="utf-8").read()
    title = ""
    m = re.match(r"#\s*(.+)", t)
    if m:
        title = m.group(1).strip()
    body = t.split("## 正文", 1)[1] if "## 正文" in t else t
    return title, body


def tokens(text):
    low = text.lower()
    out = []
    for w in re.findall(r"[a-z][a-z0-9\+\-]{2,}", low):
        if w not in EN_STOP:
            out.append(w)
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(run) <= 4 and run not in CN_STOP:
            out.append(run)
        for i in range(len(run) - 1):
            bg = run[i:i + 2]
            if bg not in CN_STOP:
                out.append(bg)
        for i in range(len(run) - 2):
            tg = run[i:i + 3]
            if tg not in CN_STOP:
                out.append(tg)
    return out


def build_tfidf(docs):
    n = len(docs)
    tfs = [Counter(tokens(d)) for d in docs]
    df = Counter()
    for c in tfs:
        for w in c:
            df[w] += 1
    # df 过滤：去掉只出现 1 次的极罕见词与出现过半的泛词，降低噪声
    lo, hi = 2, int(0.45 * n)
    keep = {w for w, c in df.items() if lo <= c <= hi}
    idf = {w: math.log((n + 1) / (df[w] + 1)) + 1.0 for w in keep}
    vecs = []
    for c in tfs:
        v = {}
        for w, cnt in c.items():
            if w in keep:
                v[w] = (1 + math.log(cnt)) * idf[w]
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({w: x / norm for w, x in v.items()})
    return vecs, idf


def dot(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(w, 0.0) for w, x in a.items())


def kmeans(vecs, k, iters=40):
    n = len(vecs)
    rng = random.Random(SEED)
    cents = [vecs[rng.randrange(n)]]
    for _ in range(1, k):
        dist = []
        for v in vecs:
            dist.append(1.0 - max(dot(v, c) for c in cents))
        s = sum(dist) or 1.0
        r = rng.random() * s
        acc = 0.0
        idx = 0
        for i, d in enumerate(dist):
            acc += d
            if acc >= r:
                idx = i
                break
        cents.append(vecs[idx])
    assign = [-1] * n
    for _ in range(iters):
        changed = 0
        for i, v in enumerate(vecs):
            best, bs = 0, -2.0
            for j, c in enumerate(cents):
                s = dot(v, c)
                if s > bs:
                    bs, best = s, j
            if assign[i] != best:
                assign[i] = best
                changed += 1
        for j in range(k):
            acc = defaultdict(float)
            cnt = 0
            for i in range(n):
                if assign[i] == j:
                    cnt += 1
                    for w, x in vecs[i].items():
                        acc[w] += x
            if cnt:
                norm = math.sqrt(sum(x * x for x in acc.values())) or 1.0
                cents[j] = {w: x / norm for w, x in acc.items()}
        if not changed:
            break
    return assign


def silhouette(sim, assign, k):
    n = len(assign)
    clusters = defaultdict(list)
    for i, c in enumerate(assign):
        clusters[c].append(i)
    if len(clusters) < 2:
        return -1.0
    total = 0.0
    for i in range(n):
        own = clusters[assign[i]]
        if len(own) <= 1:
            continue
        a = sum(1.0 - sim[i][j] for j in own if j != i) / (len(own) - 1)
        b = 2.0
        for c, members in clusters.items():
            if c == assign[i]:
                continue
            b = min(b, sum(1.0 - sim[i][j] for j in members) / len(members))
        total += (b - a) / max(a, b) if max(a, b) > 0 else 0.0
    return total / n


TECH = set("llm ai agent agents api rag ocr asr tts nlp cv gpt openai langchain transformer embedding vision speech chatbot recommendation detection sentiment translation voice diffusion vector knowledge graph medical healthcare finance education".split())


def top_terms(members, vecs, idf, limit=2):
    acc = defaultdict(float)
    for i in members:
        for w, x in vecs[i].items():
            acc[w] += x
    ranked = sorted(acc.items(), key=lambda kv: -kv[1])
    chosen = []
    for w, _ in ranked:
        if not w or any(ch.isdigit() for ch in w):
            continue
        is_cn = bool(re.search(r"[\u4e00-\u9fff]", w))
        if is_cn:
            if len(w) < 2 or w in CN_STOP:
                continue
        else:
            if w not in TECH:  # 英文只保留技术白名单，滤掉用户名/泛词
                continue
        if any(w in c or c in w for c in chosen):
            continue
        chosen.append(w)
        if len(chosen) >= limit:
            break
    # 中文术语优先，其次技术英文
    chosen.sort(key=lambda w: 0 if re.search(r"[\u4e00-\u9fff]", w) else 1)
    return chosen


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(OPP_SNAP, exist_ok=True)
    rows = list(csv.DictReader(open(RESULT2, encoding="utf-8-sig")))
    opp = [r for r in rows if r["是否构成机会"] == "1"]
    print("机会记录:", len(opp))

    # 来源网站名称不在 result2 中，从任务一 result1 关联
    r1_path = os.path.join(TASK2, "原始数据", "任务一输出", "result1.csv")
    src_map = {}
    if os.path.exists(r1_path):
        for r in csv.DictReader(open(r1_path, encoding="utf-8-sig")):
            src_map[(r["采集批次号"], r["记录编号"])] = r["来源网站名称"]
    else:
        r1_path = os.path.join(REPO, "任务一", "结果", "result1.csv")
        for r in csv.DictReader(open(r1_path, encoding="utf-8-sig")):
            src_map[(r["采集批次号"], r["记录编号"])] = r["来源网站名称"]

    docs, metas = [], []
    for r in opp:
        b, sid = r["采集批次号"], r["记录编号"]
        title, body = load_text(b, sid)
        docs.append((title + "\n" + body).strip())
        metas.append(r)
        # 归档该机会记录快照，便于溯源
        src = os.path.join(SNAP2, f"{b}_{sid}.md")
        if os.path.exists(src):
            dst = os.path.join(OPP_SNAP, f"{b}_{sid}.md")
            if not os.path.exists(dst):
                open(dst, "w", encoding="utf-8").write(open(src, encoding="utf-8").read())

    empty = sum(1 for d in docs if not d.strip())
    print("空正文:", empty)

    vecs, idf = build_tfidf(docs)
    n = len(vecs)
    sim = [[0.0] * n for _ in range(n)]
    for i in range(n):
        sim[i][i] = 1.0
        for j in range(i + 1, n):
            s = dot(vecs[i], vecs[j])
            sim[i][j] = sim[j][i] = s

    best_k, best_s, best_assign = None, -9.0, None
    for k in K_RANGE:
        assign = kmeans(vecs, k, iters=20)
        s = silhouette(sim, assign, k)
        print(f"k={k} 轮廓系数={s:.4f}")
        if s > best_s:
            best_k, best_s, best_assign = k, s, assign
    assign = kmeans(vecs, best_k, iters=40)
    print("选定 k =", best_k, "轮廓系数 =", round(silhouette(sim, assign, best_k), 4))

    groups = defaultdict(list)
    for i, c in enumerate(assign):
        groups[c].append(i)
    clusters = sorted(groups.values(), key=lambda m: -len(m))

    out_rows = []
    report = []
    for idx, members in enumerate(clusters, 1):
        cid = f"T{idx:02d}"
        cats = Counter(metas[i]["功能类别"] for i in members if metas[i]["功能类别"])
        cat = cats.most_common(1)[0][0] if cats else ""
        ind_lbl = Counter(metas[i]["所属行业"] for i in members
                          if metas[i]["所属行业"] and metas[i]["所属行业"] != "其他")
        top_lbl, top_n = (ind_lbl.most_common(1)[0] if ind_lbl else ("", 0))
        if top_n >= max(2, len(members) // 4):
            ind = top_lbl
        else:
            text = " ".join(docs[i] for i in members)
            scores = {}
            for lab, kw in INDUSTRY_KEYWORDS.items():
                # 仅用中文关键词匹配，避免英文泛词（interview/learning 等）误配行业
                scores[lab] = sum(text.count(w) for w in kw.get("zh", []))
            ranked = sorted(scores.items(), key=lambda kv: -kv[1])
            if ranked and ranked[0][1] >= max(5, len(members) // 7) and \
                    (len(ranked) == 1 or ranked[0][1] >= 1.5 * ranked[1][1]):
                ind = ranked[0][0]
            else:
                ind = "其他"
        terms = top_terms(members, vecs, idf, 2)
        core = "、".join(terms) if terms else "综合"
        name = f"{cat}｜{core}" if cat else f"{core} 相关"
        srcs = Counter(src_map.get((metas[i]["采集批次号"], metas[i]["记录编号"]), "未知") for i in members)
        src_txt = "、".join(f"{s}({c})" for s, c in srcs.most_common(4))
        if len(srcs) > 4:
            src_txt += f" 等{len(srcs)}源"
        batches = Counter(metas[i]["采集批次号"] for i in members)
        batch = batches.most_common(1)[0][0]
        recs = ";".join(f"{metas[i]['采集批次号']}-{metas[i]['记录编号']}" for i in members)
        out_rows.append({
            "采集批次号": batch, "主题簇编号": cid, "主题簇名称": name[:40],
            "功能类别": cat, "所属行业": ind, "簇内机会记录数": str(len(members)),
            "来源覆盖": src_txt, "簇内机会记录": recs,
        })
        # 报告
        samples = []
        for i in members[:3]:
            t, _ = load_text(metas[i]["采集批次号"], metas[i]["记录编号"])
            samples.append(f"{metas[i]['采集批次号']}-{metas[i]['记录编号']}（{src_map.get((metas[i]['采集批次号'], metas[i]['记录编号']), '未知')}）{(t or '')[:50]}")
        report.append({
            "cid": cid, "name": name[:40], "n": len(members), "cat": cat, "ind": ind,
            "batch": batch, "src": src_txt, "terms": terms, "samples": samples,
        })

    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(out_rows)

    total = sum(int(r["簇内机会记录数"]) for r in out_rows)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("# 任务三 主题簇报告\n\n")
        f.write(f"- 输入机会记录：{len(opp)} 条（跨全部批次）\n")
        f.write(f"- 聚类方法：字符/词 n-gram TF-IDF + 余弦 KMeans（k-means++）\n")
        f.write(f"- 选定簇数 k = {best_k}（轮廓系数 {best_s:.4f}）\n")
        f.write(f"- 主题簇数：{len(out_rows)}，覆盖机会记录合计：{total}\n\n")
        f.write("| 簇 | 名称 | 记录数 | 功能类别 | 所属行业 | 主导批次 | 来源覆盖 |\n|---|---|---|---|---|---|---|\n")
        for r in report:
            f.write(f"| {r['cid']} | {r['name']} | {r['n']} | {r['cat']} | {r['ind']} | {r['batch']} | {r['src']} |\n")
        f.write("\n## 各簇代表记录\n")
        for r in report:
            f.write(f"\n### {r['cid']} {r['name']}（{r['n']} 条）\n")
            f.write(f"- 关键词：{'、'.join(r['terms'])}\n")
            for s in r["samples"]:
                f.write(f"- {s}\n")

    print("簇数:", len(out_rows), "| 覆盖记录:", total)
    print("已写:", OUT_CSV)


if __name__ == "__main__":
    main()
