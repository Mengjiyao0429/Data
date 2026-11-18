# -*- coding: utf-8 -*-
"""任务三 · 赛道热点主题聚合（语义级 v3）

方法：
  1) jieba 中文分词（含 AI 术语词典）+ 英文词 → TF-IDF；
  2) TruncatedSVD(LSA) 投影到稠密语义空间；
  3) 候选聚类：KMeans 与层次聚类(Ward)，k∈[12,20]；
  4) 评估方案：轮廓系数、Davies-Bouldin、Calinski-Harabasz、NPMI 主题一致性、
     簇规模均衡度 五指标归一化加权；最终在“最大簇占比≤16%”约束下最大化 NPMI 选 k；
  5) 主题命名：c-TF-IDF 高权重词自动提取 + 人工核定一句话主题名（curated_names.json，按簇内记录编号确定性映射）。
"""
import csv, json, math, os, re, sys
from collections import Counter, defaultdict

import numpy as np
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score, silhouette_samples, davies_bouldin_score, calinski_harabasz_score, adjusted_rand_score

HERE = os.path.dirname(os.path.abspath(__file__))
TASK3 = os.path.dirname(HERE)
REPO = os.path.dirname(TASK3)
TASK2 = os.path.join(REPO, "任务二")
sys.path.insert(0, os.path.join(REPO, "任务一", "源码"))
from app.labels import INDUSTRY_KEYWORDS, FUNCTION_LABELS, FUNCTION_KEYWORDS, INDUSTRY_LABELS  # noqa: E402

RESULT2 = os.path.join(TASK2, "结果", "result2.csv")
SNAP2 = os.path.join(TASK2, "正文快照")
OUT_DIR = os.path.join(TASK3, "结果")
OUT_CSV = os.path.join(OUT_DIR, "result3.csv")
REPORT = os.path.join(TASK3, "task3_主题簇报告.md")
OPP_SNAP = os.path.join(TASK3, "机会快照")
HEADER = ["采集批次号", "主题簇编号", "主题簇名称", "功能类别", "所属行业",
          "簇内机会记录数", "来源覆盖", "簇内机会记录"]

SEED = 42
K_RANGE = list(range(10, 31))   # 机会记录扩至 1009 条后，候选 k 上限相应放宽至 30

CURATED = {}
_names_path = os.path.join(HERE, "curated_names.json")
if os.path.exists(_names_path):
    CURATED = json.load(open(_names_path, encoding="utf-8"))

AI_DICT = [
    "大模型", "智能体", "多模态", "知识库", "语音识别", "语音合成", "图像识别", "目标检测",
    "文本生成", "对话问答", "推荐系统", "知识图谱", "机器学习", "深度学习", "神经网络",
    "自然语言处理", "计算机视觉", "智能客服", "会议纪要", "客服机器人", "虚拟助手", "数字人",
    "自动驾驶", "智能家居", "智慧医疗", "智慧教育", "智慧金融", "智能办公", "智能写作",
    "智能翻译", "智能搜索", "智能推荐", "智能问答", "文档解析", "信息抽取", "情感分析",
    "语义理解", "意图识别", "语音交互", "人脸识别", "图像生成", "视频理解", "内容审核",
    "风险控制", "智能运维", "智能营销", "智能招聘", "智能法务", "智能投研", "智能物流",
    "智能仓储", "供应链", "在线教育", "远程医疗", "金融科技", "智能驾驶", "机器人流程",
    "自动化流程", "低代码", "检索增强", "向量数据库", "提示词", "模型部署", "边缘计算",
    "隐私计算", "智能座舱", "智能质检", "企业知识库", "智能分析", "预测分析", "聊天机器人",
]
for _w in AI_DICT:
    jieba.add_word(_w, freq=1000)
jieba.setLogLevel(60)

NAME_COMPOUND = set(AI_DICT)
NAME_WORDS = set("问答 对话 客服 推荐 翻译 识别 生成 检索 分析 预测 审核 写作 会议 纪要 办公 文档 语音 图像 视频 图谱 诊断 助手 机器人 摘要 抽取 分类 代码 面试 简历 外呼 催收 理赔 问诊 导诊 用药 随访 备课 阅卷 排班 巡检 安防 质检".split())
EN2CN = {
    "rag": "检索增强", "llm": "大模型", "agent": "智能体", "agents": "智能体", "chatbot": "聊天机器人",
    "ocr": "OCR识别", "asr": "语音识别", "tts": "语音合成", "nlp": "自然语言处理", "cv": "计算机视觉",
    "ml": "机器学习", "embedding": "向量嵌入", "vector": "向量检索", "knowledge": "知识图谱",
    "graph": "知识图谱", "recommendation": "智能推荐", "recommender": "智能推荐", "sentiment": "情感分析",
    "translation": "机器翻译", "detection": "目标检测", "vision": "计算机视觉", "speech": "语音处理",
    "voice": "语音处理", "diffusion": "图像生成", "medical": "医疗", "healthcare": "医疗",
    "finance": "金融", "education": "教育", "interview": "面试辅助", "resume": "简历解析",
    "job": "招聘", "customer": "客户", "service": "服务", "autonomous": "自动驾驶", "driving": "驾驶",
    "robot": "机器人", "multimodal": "多模态", "generation": "文本生成", "video": "视频",
    "image": "图像", "text": "文本", "audio": "音频", "summary": "摘要生成", "summarization": "摘要生成",
    "extraction": "信息抽取", "classification": "分类", "forecast": "预测", "anomaly": "异常检测",
    "assistant": "智能助手", "workflow": "流程自动化", "automation": "自动化", "pipeline": "流水线",
    "memory": "记忆", "document": "文档处理", "pdf": "PDF解析", "code": "代码生成", "coding": "代码生成",
    "retrieval": "检索", "query": "查询", "answer": "问答", "question": "问答", "dialogue": "对话",
    "conversation": "对话", "transcribe": "语音转写", "meeting": "会议", "notes": "笔记",
    "openai": "大模型对话", "gpt": "生成式对话", "search": "智能搜索", "database": "数据库",
}
TECH_EN = set(EN2CN.keys())

CN_STOP = set("的 了 和 与 是 在 有 为 对 及 或 这 那 个 我 你 他 它 们 就 都 而 还 也 很 可以 一个 我们 通过 进行 实现 使用 以及 基于 相关 支持 提供 包括 问题 需要 如何 什么 介绍 关于 自己 这个 那个 现在 已经 没有 不是 就是 但是 因为 所以 如果 可能 需要 一下 一些 一种 各种 不同 主要 其中 同时 并且 或者 另外 然后 这个 这里 这些 那些 其中 来说 对于 由于 根据 目前 方面 应用 场景 领域 技术 方法 系统 工具 数据 模型 内容 信息 用户 服务 功能 能力 解决 满足 提升 提高 降低 帮助 支持 具有 采用 利用 结合 面对 针对 随着 越来越 起来 出来 进去 里面 下面 上面 人工智能 智能".split())
EN_STOP = set("the and for with that this from are was were will can not you your our its use using based into more than has have had new how what when which who why but all any each other some such only about also there their they them then these those this to in on of with for is be a an at by as it we he she they can could would should may might must do does did get go make made work works base via per vs etc using used".split())
EN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\+\-\.]{1,}")
CN_RE = re.compile(r"[\u4e00-\u9fff]+")


def tokenize(text):
    out = []
    for w in EN_RE.findall(text):
        wl = w.lower()
        if wl not in EN_STOP and len(wl) >= 2:
            out.append(wl)
    for seg in CN_RE.findall(text):
        for w in jieba.cut(seg):
            w = w.strip()
            if w and len(w) >= 2 and w not in CN_STOP:
                out.append(w)
    return out


def load_text(b, sid):
    p = os.path.join(SNAP2, f"{b}_{sid}.md")
    if not os.path.exists(p):
        return "", ""
    t = open(p, encoding="utf-8").read()
    m = re.match(r"#\s*(.+)", t)
    title = m.group(1).strip() if m else ""
    body = t.split("## 正文", 1)[1] if "## 正文" in t else t
    return title, body


def npmi_coherence(X_bin, top_ids, n_docs):
    X = X_bin.tocsr()
    vals = []
    for terms in top_ids:
        terms = [t for t in terms if t is not None]
        if len(terms) < 2:
            continue
        s, cnt = 0.0, 0
        for a in range(len(terms)):
            for b in range(a + 1, len(terms)):
                ca = float(X[:, terms[a]].sum())
                cb = float(X[:, terms[b]].sum())
                cab = float(X[:, terms[a]].multiply(X[:, terms[b]]).sum())
                if cab <= 0:
                    continue
                p_i, p_j, p_ij = ca / n_docs, cb / n_docs, cab / n_docs
                s += math.log(p_ij / (p_i * p_j)) / (-math.log(p_ij))
                cnt += 1
        if cnt:
            vals.append(s / cnt)
    return float(np.mean(vals)) if vals else 0.0


def top_terms_per_cluster(labels, X, vocab, topn=20):
    res = []
    for c in range(int(labels.max()) + 1):
        idx = np.where(labels == c)[0]
        mean_w = np.asarray(X[idx].mean(axis=0)).ravel()
        res.append([int(i) for i in mean_w.argsort()[::-1][:topn]])
    return res


def score_labels(text, keyword_map):
    low = text.lower()
    scores = {}
    for lab, kw in keyword_map.items():
        s = 0
        for w in kw.get("zh", []):
            s += text.count(w)
        for w in kw.get("en", []):
            s += len(re.findall(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", low))
        scores[lab] = s
    return scores


def compose_name(ind, cat, cn_terms, en_terms):
    concepts = []
    for t in cn_terms:
        if t in NAME_COMPOUND or t in NAME_WORDS:
            if t not in concepts:
                concepts.append(t)
    for t in en_terms:
        if t in EN2CN:
            c = EN2CN[t]
            if c not in concepts:
                concepts.append(c)
    ded = []
    for c in concepts:
        if any(c in d or d in c for d in ded):
            continue
        ded.append(c)
    if len(ded) >= 2:
        core = ded[0] + "与" + ded[1]
    elif ded:
        core = ded[0] + "相关"
    else:
        core = cat or "综合应用"
    if ind and ind != "其他" and ind not in core:
        name = ind + core
    else:
        name = core
    return name[:40]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(OPP_SNAP, exist_ok=True)
    rows = list(csv.DictReader(open(RESULT2, encoding="utf-8-sig")))
    opp = [r for r in rows if r["是否构成机会"] == "1"]
    r1_path = os.path.join(TASK2, "原始数据", "任务一输出", "result1.csv")
    src_map = {}
    for r in csv.DictReader(open(r1_path, encoding="utf-8-sig")):
        src_map[(r["采集批次号"], r["记录编号"])] = r["来源网站名称"]

    docs, metas = [], []
    for r in opp:
        b, sid = r["采集批次号"], r["记录编号"]
        title, body = load_text(b, sid)
        docs.append((title + "\n" + body).strip())
        metas.append(r)
        src = os.path.join(SNAP2, f"{b}_{sid}.md")
        dst = os.path.join(OPP_SNAP, f"{b}_{sid}.md")
        if os.path.exists(src) and not os.path.exists(dst):
            open(dst, "w", encoding="utf-8").write(open(src, encoding="utf-8").read())

    n = len(docs)
    tfidf = TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False,
                            ngram_range=(1, 2), min_df=2, max_df=0.6, sublinear_tf=True)
    X = tfidf.fit_transform(docs)
    vocab = tfidf.get_feature_names_out()
    cvec = CountVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False,
                           ngram_range=(1, 2), min_df=2, max_df=0.6, binary=True)
    X_bin = cvec.fit_transform(docs)
    print("文档数:", n, "| 词表:", len(vocab))

    svd_dim = min(96, len(vocab) - 1, n - 1)
    svd = TruncatedSVD(n_components=svd_dim, random_state=SEED)
    X_lsa = svd.fit_transform(X)
    print("LSA 方差比: %.3f" % svd.explained_variance_ratio_.sum())

    eval_rows = []
    for method in ("KMeans", "Agglomerative"):
        for k in K_RANGE:
            m = KMeans(n_clusters=k, n_init=10, random_state=SEED) if method == "KMeans" \
                else AgglomerativeClustering(n_clusters=k, linkage="ward")
            labels = m.fit_predict(X_lsa)
            sil = silhouette_score(X_lsa, labels)
            db = davies_bouldin_score(X_lsa, labels)
            ch = calinski_harabasz_score(X_lsa, labels)
            top = top_terms_per_cluster(labels, X, vocab, 10)
            coh = npmi_coherence(X_bin, top, n)
            sizes = np.bincount(labels)
            balance = 1.0 - float(sizes.max()) / n
            eval_rows.append((method, k, sil, db, ch, coh, balance, int(sizes.min())))

    def norm(vals, lower=False):
        v = np.array(vals, dtype=float)
        if lower:
            v = -v
        lo, hi = v.min(), v.max()
        return (v - lo) / (hi - lo) if hi > lo else np.zeros_like(v)

    sil_a = norm([r[2] for r in eval_rows])
    db_a = norm([r[3] for r in eval_rows], True)
    ch_a = norm([r[4] for r in eval_rows])
    coh_a = norm([r[5] for r in eval_rows])
    bal_a = norm([r[6] for r in eval_rows])
    composite = 0.20 * sil_a + 0.20 * db_a + 0.15 * ch_a + 0.30 * coh_a + 0.15 * bal_a
    # 最终选优：仅 KMeans；在“最大簇占比 ≤16%”约束下最大化 NPMI 主题一致性，次选轮廓系数
    cand = [r for r in eval_rows if r[0] == "KMeans" and r[6] >= 0.84]
    best = max(cand, key=lambda r: (r[5], r[2]))
    best_method, best_k = best[0], best[1]
    print("最优:", best_method, "k=", best_k)

    labels = KMeans(n_clusters=best_k, n_init=10, random_state=SEED).fit_predict(X_lsa)

    seeds = [7, 77, 777, 7777, 77777]
    runs = [KMeans(n_clusters=best_k, n_init=10, random_state=s).fit_predict(X_lsa) for s in seeds]
    ari = []
    for a in range(len(seeds)):
        for b in range(a + 1, len(seeds)):
            ari.append(adjusted_rand_score(runs[a], runs[b]))
    stability = float(np.mean(ari))

    groups = defaultdict(list)
    for i, c in enumerate(labels):
        groups[c].append(i)
    clusters = sorted(groups.values(), key=lambda m: -len(m))
    top_ids = top_terms_per_cluster(labels, X, vocab, 20)

    out_rows, rep = [], []
    for ci, members in enumerate(clusters):
        cid = f"C{ci + 1}"
        text = "".join(docs[i] for i in members)
        f_scores = score_labels(text, FUNCTION_KEYWORDS)
        if f_scores and max(f_scores.values()) > 0:
            cat = max(f_scores, key=f_scores.get)
        else:
            cats = Counter(metas[i]["功能类别"] for i in members if metas[i]["功能类别"])
            cat = cats.most_common(1)[0][0] if cats else ""
        i_scores = score_labels(text, INDUSTRY_KEYWORDS)
        order = sorted(i_scores.items(), key=lambda kv: -kv[1])
        top_lbl, top_n = order[0]
        if top_n >= max(3, len(members) // 5) and (len(order) == 1 or top_n >= 1.3 * order[1][1]):
            ind = top_lbl
        else:
            ind = "其他"

        cn_terms, en_terms = [], []
        for tid in top_ids[ci]:
            w = vocab[tid]
            if re.search(r"[\u4e00-\u9fff]", w):
                if len(w) >= 2 and w not in cn_terms:
                    cn_terms.append(w)
            elif not any(ch.isdigit() for ch in w) and w in TECH_EN and w not in en_terms:
                en_terms.append(w)
        # 批号限定：跨 B01–B05 各批次编号独立，仅用 Sxxxxx 会跨批次歧义（如两个 S00005）
        ids = sorted(f"{metas[i]['采集批次号']}-{metas[i]['记录编号']}" for i in members)
        curated = CURATED.get(",".join(ids))
        if curated:
            name, cat, ind = curated["name"], curated["func"], curated["industry"]
        else:
            name = compose_name(ind, cat, cn_terms, en_terms)

        srcs = Counter(src_map.get((metas[i]["采集批次号"], metas[i]["记录编号"]), "未知") for i in members)
        src_txt = "、".join(s for s, _ in srcs.most_common())
        batches = Counter(metas[i]["采集批次号"] for i in members)
        batch = batches.most_common(1)[0][0]
        recs = "；".join(ids)
        out_rows.append({
            "采集批次号": batch, "主题簇编号": cid, "主题簇名称": name,
            "功能类别": cat, "所属行业": ind, "簇内机会记录数": str(len(members)),
            "来源覆盖": src_txt, "簇内机会记录": recs,
        })
        samples = []
        for i in members[:3]:
            t, _ = load_text(metas[i]["采集批次号"], metas[i]["记录编号"])
            samples.append(f"{metas[i]['采集批次号']}-{metas[i]['记录编号']}（{src_map.get((metas[i]['采集批次号'], metas[i]['记录编号']), '未知')}）{(t or '')[:60]}")
        rep.append(dict(cid=cid, name=name, n=len(members), cat=cat, ind=ind,
                        batch=batch, src=src_txt, cn=cn_terms, en=en_terms, samples=samples))

    # 逐簇质量指标：NPMI 主题一致性 / 轮廓系数 / 簇内平均余弦相似度 / 行业标签一致率
    sil_samples = silhouette_samples(X_lsa, labels)
    per_cluster = []
    for ci, members in enumerate(clusters):
        cl_npmi = npmi_coherence(X_bin, [top_ids[ci]], n)
        cl_sil = float(np.mean([sil_samples[i] for i in members]))
        Xc = X[members]
        sim = (Xc @ Xc.T).toarray()
        k = len(members)
        cl_cos = float((sim.sum() - k) / (k * (k - 1))) if k > 1 else 0.0
        ind_c = rep[ci]["ind"]
        lab_ind = sum(1 for i in members if metas[i]["所属行业"] == ind_c) / k
        per_cluster.append((f"C{ci + 1}", rep[ci]["name"], k,
                            cl_npmi, cl_sil, cl_cos, lab_ind))

    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(out_rows)

    with open(REPORT, "w", encoding="utf-8") as f:
        batch_list = sorted({m["采集批次号"] for m in metas})
        f.write("# 任务三 主题聚合报告（语义级 v3）\n\n")
        f.write(f"- 输入机会记录：{n} 条（跨 {batch_list[0]}–{batch_list[-1]}，共 {len(batch_list)} 个批次）\n")
        f.write("- 向量化：jieba 中文分词（AI 术语词典）+ 英文词 → TF-IDF（ngram 1-2，min_df=2，max_df=0.6）\n")
        f.write(f"- 语义投影：TruncatedSVD(LSA)，维度 {svd_dim}，累计方差 {svd.explained_variance_ratio_.sum():.3f}\n")
        f.write(f"- 候选：KMeans、层次聚类(Ward)，k∈{{{K_RANGE[0]}..{K_RANGE[-1]}}}\n")
        f.write("- 评估方案：轮廓系数(0.20)+DB(0.20)+CH(0.15)+NPMI 主题一致性(0.30)+簇规模均衡度(0.15)，归一化加权\n")
        f.write(f"- 最终选优：KMeans，在“最大簇占比≤16%”约束下最大化 NPMI 主题一致性 → k={best_k}\n")
        f.write(f"- 稳定性(5 次随机种子两两 ARI 均值) = {stability:.3f}\n")
        f.write(f"- 主题簇数：{len(out_rows)}，覆盖机会记录：{sum(int(r['簇内机会记录数']) for r in out_rows)}\n\n")
        f.write("## 一、聚类评估结果（候选方案前 12）\n\n")
        f.write("| 方法 | k | 轮廓 | DB | CH | NPMI | 均衡 | 综合 |\n|---|---|---|---|---|---|---|---|\n")
        order = sorted(range(len(eval_rows)), key=lambda i: -composite[i])
        for i in order[:12]:
            m, k, sil, db, ch, coh, bal, _min = eval_rows[i]
            f.write(f"| {m} | {k} | {sil:.3f} | {db:.2f} | {ch:.1f} | {coh:.3f} | {bal:.2f} | {composite[i]:.3f} |\n")
        f.write("\n## 二、主题簇一览\n\n")
        f.write("| 簇 | 主题簇名称 | 功能类别 | 所属行业 | 记录数 | 主导批次 | 来源覆盖 |\n|---|---|---|---|---|---|---|\n")
        for r in out_rows:
            f.write(f"| {r['主题簇编号']} | {r['主题簇名称']} | {r['功能类别']} | {r['所属行业']} | {r['簇内机会记录数']} | {r['采集批次号']} | {r['来源覆盖']} |\n")
        f.write("\n## 三、逐簇质量指标\n\n")
        f.write("| 簇 | 主题 | 记录数 | NPMI | 轮廓系数 | 簇内余弦相似度 | 行业标签一致率 |\n|---|---|---|---|---|---|---|\n")
        for cid, name, cnt, cn_, sil_, cs_, li in per_cluster:
            f.write(f"| {cid} | {name} | {cnt} | {cn_:.3f} | {sil_:.3f} | {cs_:.3f} | {li:.2%} |\n")
        f.write("\n> NPMI 越高主题越连贯；簇内余弦相似度越高簇越紧凑；轮廓系数在短文本高维稀疏空间下结构性偏低，仅作参考；行业标签一致率用于检验与任务二既有标签体系的自洽性。\n")

        f.write("\n## 四、多源共同指向的热点主题\n\n")
        f.write("来源覆盖含 2 个及以上网站的簇，视为“多源共同指向”的热点：\n\n")
        f.write("| 簇 | 主题 | 记录数 | 来源数 | 来源覆盖 |\n|---|---|---|---|---|\n")
        hot = 0
        for r in out_rows:
            srcs = [s for s in r['来源覆盖'].split('、') if s and s != '未知']
            if len(srcs) >= 2:
                hot += 1
                f.write(f"| {r['主题簇编号']} | {r['主题簇名称']} | {r['簇内机会记录数']} | {len(srcs)} | {r['来源覆盖']} |\n")
        f.write(f"\n共 {hot}/{len(out_rows)} 个主题簇被多源共同指向。\n")

        f.write("\n## 五、各簇代表记录\n")
        for r in rep:
            f.write(f"\n### {r['cid']} {r['name']}（{r['n']} 条）\n")
            f.write(f"- 中文关键词：{'、'.join(r['cn'][:6])}\n")
            if r['en']:
                f.write(f"- 英文关键词：{'、'.join(r['en'][:6])}\n")
            for s in r['samples']:
                f.write(f"- {s}\n")

    print("簇数:", len(out_rows), "| 覆盖:", sum(int(r['簇内机会记录数']) for r in out_rows))
    print("最优:", best_method, "k=", best_k, "| 稳定性 ARI:", round(stability, 3))


if __name__ == "__main__":
    main()
