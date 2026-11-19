# -*- coding: utf-8 -*-
"""共享分析引擎 —— 任务三 / 任务四 / 任务五 统一使用。

相对旧版修复的三个结构性问题：
  1) 簇按规模重排后仍用「排序序号」去取原「标签序」的 top_ids，导致主题词、
     主题名、逐簇 NPMI 全部错配。本模块统一按 label -> terms 映射，不再错位。
  2) 归一化分母取「本批观测最大值」，每批必有簇=100 分、分数随数据规模漂移、
     跨批不可比。本模块改用固定基准（见 FIXED_SRC/FIXED_SIZE/FIXED_HEAT）。
  3) 聚类跨 B01–B08 全局混合，与「各批次相互独立」冲突。本模块一次调用只处理
     一个批次；需要跨批热点时由调用方显式另做汇总，不混入 result3/result4。

对外主函数：
  cluster_items(items, ...) -> (clusters, info)
  score_clusters(clusters, ...) -> None（就地写 dims/score/priority）
  calibrate(scores, gold_labels) -> 校准后的概率（Platt / isotonic）
"""
import math
import re
from collections import Counter, defaultdict

import numpy as np
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression

jieba.setLogLevel(60)

SEED = 42

# 固定评分基准（论文中需说明选取依据）：
#   FIXED_SRC  = 官方参考数据源清单的渠道量级 14，覆盖到 14 类来源即满分；
#   FIXED_SIZE = 单簇 100 条机会记录视为「充分成规模」（约为基线最大簇 141 的 0.7）；
#   FIXED_HEAT = 单簇累计热度 200000 视为满分（约为基线单条最大热度 488775 的 0.4，
#                log 压缩后分布稳定）。固定基准使跨批次、跨规模可比。
FIXED_SRC = 14.0
FIXED_SIZE = 100.0
FIXED_HEAT = 200000.0
WEIGHTS = (0.35, 0.35, 0.30)

AI_DICT = [
    "大模型", "智能体", "多模态", "知识库", "语音识别", "语音合成", "图像识别", "目标检测", "文本生成",
    "对话问答", "推荐系统", "知识图谱", "机器学习", "深度学习", "神经网络", "自然语言处理", "计算机视觉",
    "智能客服", "会议纪要", "客服机器人", "虚拟助手", "数字人", "自动驾驶", "智能家居", "智慧医疗",
    "智慧教育", "智慧金融", "智能办公", "智能写作", "智能翻译", "智能搜索", "智能推荐", "智能问答",
    "文档解析", "信息抽取", "情感分析", "语义理解", "意图识别", "语音交互", "人脸识别", "图像生成",
    "视频理解", "内容审核", "风险控制", "智能运维", "智能营销", "智能招聘", "智能法务", "智能投研",
    "智能物流", "智能仓储", "供应链", "在线教育", "远程医疗", "金融科技", "智能驾驶", "机器人流程",
    "自动化流程", "低代码", "检索增强", "向量数据库", "提示词", "模型部署", "边缘计算", "隐私计算",
    "智能座舱", "智能质检", "企业知识库", "智能分析", "预测分析", "聊天机器人", "代码生成", "智能体编排",
]
for _w in AI_DICT:
    jieba.add_word(_w, freq=1000)

NAME_WORDS = set("问答 对话 客服 推荐 翻译 识别 生成 检索 分析 预测 审核 写作 会议 纪要 办公 文档 语音 "
                 "图像 视频 图谱 诊断 助手 机器人 摘要 抽取 分类 代码 面试 简历 外呼 催收 理赔 问诊 导诊 "
                 "用药 随访 备课 阅卷 排班 巡检 安防 质检 智能体 编排 多模态".split())
EN2CN = {
    "rag": "检索增强", "llm": "大模型", "agent": "智能体", "agents": "智能体", "chatbot": "聊天机器人",
    "ocr": "OCR识别", "asr": "语音识别", "tts": "语音合成", "nlp": "自然语言处理", "cv": "计算机视觉",
    "embedding": "向量嵌入", "vector": "向量检索", "knowledge": "知识图谱", "graph": "知识图谱",
    "recommendation": "智能推荐", "recommender": "智能推荐", "sentiment": "情感分析",
    "translation": "机器翻译", "detection": "目标检测", "vision": "计算机视觉", "speech": "语音处理",
    "voice": "语音处理", "diffusion": "图像生成", "medical": "医疗", "healthcare": "医疗",
    "finance": "金融", "education": "教育", "interview": "面试辅助", "resume": "简历解析",
    "customer": "客户", "service": "服务", "autonomous": "自动驾驶", "driving": "驾驶",
    "robot": "机器人", "multimodal": "多模态", "generation": "文本生成", "video": "视频",
    "image": "图像", "text": "文本", "audio": "音频", "summary": "摘要生成", "summarization": "摘要生成",
    "extraction": "信息抽取", "classification": "分类", "forecast": "预测", "anomaly": "异常检测",
    "assistant": "智能助手", "workflow": "流程自动化", "automation": "自动化", "memory": "记忆",
    "document": "文档处理", "pdf": "PDF解析", "code": "代码生成", "coding": "代码生成", "copilot": "代码助手",
    "retrieval": "检索", "query": "查询", "answer": "问答", "question": "问答", "dialogue": "对话",
    "conversation": "对话", "transcribe": "语音转写", "meeting": "会议", "notes": "笔记",
    "openai": "大模型对话", "gpt": "生成式对话", "search": "智能搜索", "database": "数据库",
}
TECH_EN = set(EN2CN.keys())

CN_STOP = set("的 了 和 与 是 在 有 为 对 及 或 这 那 个 我 你 他 它 们 就 都 而 还 也 很 可以 一个 我们 "
              "通过 进行 实现 使用 以及 基于 相关 支持 提供 包括 问题 需要 如何 什么 介绍 关于 自己 这个 "
              "那个 现在 已经 没有 不是 就是 但是 因为 所以 如果 可能 一下 一些 一种 各种 不同 主要 其中 "
              "同时 并且 或者 另外 然后 这里 这些 那些 来说 对于 由于 根据 目前 方面 应用 场景 领域 技术 "
              "方法 系统 工具 数据 模型 内容 信息 用户 服务 功能 能力 解决 满足 提升 提高 降低 帮助 具有 "
              "采用 利用 结合 面对 针对 随着 越来越 起来 出来 进去 里面 下面 上面 人工智能 智能".split())
EN_STOP = set("the and for with that this from are was were will can not you your our its use using based into "
              "more than has have had new how what when which who why but all any each other some such only about "
              "also there their they them then these those to in on of at by as it we he she could would should "
              "may might must do does did get go make made work works via per vs etc used".split())
EN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\+\-\.]{1,}")
CN_RE = re.compile(r"[\u4e00-\u9fff]+")


def tokenize(text):
    out = []
    for w in EN_RE.findall(text or ""):
        wl = w.lower()
        if wl not in EN_STOP and len(wl) >= 2:
            out.append(wl)
    for seg in CN_RE.findall(text or ""):
        for w in jieba.cut(seg):
            w = w.strip()
            if w and len(w) >= 2 and w not in CN_STOP:
                out.append(w)
    return out


def _top_terms_by_label(labels, X, vocab, topn=16):
    """返回 dict: label -> [term_id]。按原标签号索引，杜绝排序错配。"""
    out = {}
    for c in range(int(np.max(labels)) + 1):
        idx = np.where(labels == c)[0]
        if len(idx) == 0:
            out[c] = []
            continue
        mean = np.asarray(X[idx].mean(axis=0)).ravel()
        out[c] = [int(i) for i in mean.argsort()[::-1][:topn]]
    return out


def _compose_name(industry, func, terms):
    concepts = []
    for t in terms:
        if re.search(r"[\u4e00-\u9fff]", t):
            if t in NAME_WORDS or t in AI_DICT:
                if t not in concepts:
                    concepts.append(t)
        else:
            c = EN2CN.get(t.lower())
            if c and c not in concepts:
                concepts.append(c)
    deduped = []
    for c in concepts:
        if any(c in d or d in c for d in deduped):
            continue
        deduped.append(c)
    if len(deduped) >= 2:
        core = deduped[0] + "与" + deduped[1]
    elif deduped:
        core = deduped[0] + "相关"
    else:
        core = func or "综合应用"
    if industry and industry != "其他" and industry not in core:
        return (industry + core)[:40]
    return core[:40]


def cluster_items(items, min_df=1, svd_dim=48, k_min=2, k_max=10, seed=SEED):
    """对单批次机会记录做语义聚类。

    items: [dict]，每个至少含 text/title/body/func/industry；可选 id/source/heat/day。
    返回 (clusters, info)：
      clusters[i] = {"cid","idx","terms","name","func","industry","members","label",...}
      info = {"k","silhouette","stability","vectors","n"}
    """
    n = len(items)
    if n == 0:
        return [], {"k": 0, "silhouette": 0.0, "stability": 0.0, "vectors": 0, "n": 0}
    if n < 10:
        # 记录太少不做聚类（避免一条记录一个簇的噪声）：整批作为一个主题簇
        funcs = Counter(it.get("func", "") for it in items if it.get("func"))
        inds = Counter(it.get("industry", "") for it in items if it.get("industry"))
        terms = [t for it in items for t in tokenize(it.get("title", ""))[:3]][:5]
        func = funcs.most_common(1)[0][0] if funcs else ""
        ind = inds.most_common(1)[0][0] if inds else "其他"
        c = {"cid": "C1", "idx": list(range(n)), "label": 0, "terms": terms,
             "func": func, "industry": ind, "name": _compose_name(ind, func, terms),
             "members": list(items)}
        return [c], {"k": 1, "silhouette": 0.0, "stability": 0.0, "vectors": 0, "n": n}
    texts = [(it.get("title", "") + "\n" + it.get("body", ""))[:2000].strip() for it in items]
    vec = TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False,
                          ngram_range=(1, 2), min_df=min_df, max_df=0.7, sublinear_tf=True)
    X = vec.fit_transform(texts)
    vocab = vec.get_feature_names_out()
    dim = int(min(svd_dim, max(2, X.shape[1] - 1), max(2, n - 1)))
    Z = TruncatedSVD(n_components=dim, random_state=seed).fit_transform(X) if X.shape[1] > 1 else np.zeros((n, 2))

    upper = int(min(k_max, max(k_min, n // 6)))
    best = None
    for k in range(k_min, upper + 1):
        if k >= n:
            break
        km = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(Z)
        labels = km.labels_
        if len(set(labels)) < 2:
            continue
        try:
            sil = float(silhouette_score(Z, labels))
        except Exception:
            sil = -1.0
        if best is None or sil > best[1]:
            best = (labels, sil, k)
    if best is None:
        labels = np.zeros(n, dtype=int)
        sil, k = 0.0, 1
    else:
        labels, sil, k = best

    # 稳定性：多种子两两 ARI（同算法稳定性，非对真值准确率）
    stability = 0.0
    if k > 1:
        runs = [KMeans(n_clusters=k, n_init=10, random_state=s).fit_predict(Z) for s in (7, 77, 777)]
        ari = [adjusted_rand_score(runs[a], runs[b]) for a in range(len(runs)) for b in range(a + 1, len(runs))]
        stability = float(np.mean(ari)) if ari else 0.0

    # 关键修复：top_terms 按 label 索引；下面遍历时也按 label 取，绝不用排序序号。
    terms_by_label = _top_terms_by_label(labels, X, vocab, 16)

    groups = defaultdict(list)
    for i, lb in enumerate(labels):
        groups[int(lb)].append(i)
    ordered = sorted(groups.items(), key=lambda kv: -len(kv[1]))  # [(label, members)]

    clusters = []
    for cid, (label, members) in enumerate(ordered, 1):
        term_ids = terms_by_label[label]  # 按标签取，不按 cid 取
        terms = []
        for tid in term_ids:
            t = str(vocab[tid]).strip()
            t = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fa5+#.-]+$", "", t)
            if len(t) < 2 or t in EN_STOP or t in CN_STOP:
                continue
            if t not in terms:
                terms.append(t)
            if len(terms) >= 5:
                break
        funcs = Counter(items[i].get("func", "") for i in members if items[i].get("func"))
        inds = Counter(items[i].get("industry", "") for i in members if items[i].get("industry"))
        func = funcs.most_common(1)[0][0] if funcs else ""
        ind = inds.most_common(1)[0][0] if inds else "其他"
        clusters.append({
            "cid": "C%d" % cid, "idx": members, "label": int(label),
            "terms": terms, "func": func, "industry": ind,
            "name": _compose_name(ind, func, terms),
            "members": [items[i] for i in members],
        })

    info = {"k": len(clusters), "silhouette": round(sil, 4), "stability": round(stability, 4),
            "vectors": int(X.shape[1]), "n": n}
    return clusters, info


def score_clusters(clusters, weights=WEIGHTS, fixed_src=FIXED_SRC, fixed_size=FIXED_SIZE, fixed_heat=FIXED_HEAT):
    """固定基准评分：跨批次/跨规模可比；修复分子求和/分母单条的基准错配。"""
    for c in clusters:
        members = c["members"]
        n_src = len({m.get("source", "") for m in members if m.get("source")})
        n_size = len(members)
        # 每条记录热度取均值再 log 压缩，避免「条数多=热度高」的规模混淆
        heats = [float(m.get("heat", 0) or 0) for m in members]
        mean_heat = sum(heats) / max(1, len(heats))
        heat_score = 100.0 * math.log1p(mean_heat) / math.log1p(fixed_heat)
        heat_score = min(100.0, heat_score)
        confs = [float(m.get("confidence", 0.5) or 0.5) for m in members]
        conf_score = 100.0 * (sum(confs) / max(1, len(confs)))
        # 商业信号 = 互动热度 0.7 + 需求置信度 0.3（均 0~100）
        biz = 0.7 * heat_score + 0.3 * conf_score

        src_score = min(100.0, 100.0 * n_src / fixed_src)
        size_score = min(100.0, 100.0 * n_size / fixed_size)
        c["dims"] = {"src": round(src_score, 1), "size": round(size_score, 1),
                     "biz": round(biz, 1), "heat": round(heat_score, 1), "conf": round(conf_score, 1)}
        c["n_src"] = n_src
        c["n_size"] = n_size
        c["score"] = round(weights[0] * src_score + weights[1] * size_score + weights[2] * biz, 1)
    clusters.sort(key=lambda c: -c["score"])
    for i, c in enumerate(clusters, 1):
        c["priority"] = i
    return clusters


def calibrate(scores, labels, method="isotonic"):
    """用金标把启发式分数校准为概率，修复「置信度非单调」。

    scores: 0~1 的原始分数序列；labels: 0/1 真值。返回校准函数 f(score)->prob。
    """
    s = np.asarray(scores, dtype=float).reshape(-1, 1)
    y = np.asarray(labels, dtype=int)
    if len(set(y.tolist())) < 2 or len(y) < 20:
        return lambda x: float(x)
    if method == "platt":
        m = LogisticRegression(C=1.0, max_iter=1000)
        m.fit(s, y)
        return lambda x: float(m.predict_proba([[float(x)]])[0][1])
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(s.ravel(), y)
    return lambda x: float(iso.predict([float(x)])[0])
