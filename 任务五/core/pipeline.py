# -*- coding: utf-8 -*-
"""任务五 · 需求驱动的批次流水线

一次"需求发起" = 一个批次。批次内独立完成：
    采集 → 清洗 → 去重 → 正文快照 → 机会判别 → 主题聚类 → 价值评估 → 批次报告

每个批次的结果落在 `任务五/批次/<批次号>/`，结构与任务一～四完全一致：
    result1.csv / result2.csv / result3.csv / result4.csv
    text/<批次号>_Sxxxxx.md      （正文快照，result1“内容”列指向这里）
    原始记录.json                 （采集原始返回，用于溯源复核）
    批次报告.md                   （本次需求的完整结论）

批次之间互不影响：聚类、归一化分母、价值排序全部只在本批次记录内计算。
"""
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime

from . import sources

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BATCH_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "批次")
TASK2_SRC = os.path.join(BASE, "任务二", "源码")

R1_HEADER = ["采集批次号", "记录编号", "来源网站名称", "来源链接", "内容", "发布时间",
             "星标数", "浏览数", "点赞数", "评论数", "收藏数"]
R2_HEADER = ["采集批次号", "记录编号", "是否构成机会", "机会置信度", "功能类别", "所属行业"]
R3_HEADER = ["采集批次号", "主题簇编号", "主题簇名称", "功能类别", "所属行业",
             "簇内机会记录数", "来源覆盖", "簇内机会记录"]
R4_HEADER = ["采集批次号", "主题簇编号", "主题簇名称", "功能类别", "所属行业", "机会价值分", "优先级"]

DECISION_TAU = 0.50
WEIGHTS = (0.35, 0.35, 0.30)      # 多源指向 / 记录规模 / 商业信号

_MODS = {}


def _load(name):
    """按文件路径加载任务二的判别与分类模块，保证与基线口径完全一致。"""
    if name in _MODS:
        return _MODS[name]
    path = os.path.join(TASK2_SRC, name + ".py")
    spec = importlib.util.spec_from_file_location("t5_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _MODS[name] = mod
    return mod


def cached(name):
    return _MODS.get(name)


def preload():
    _load("opportunity_classifier")
    _load("category_classifier")


# ---------------- 批次编号 ----------------
def next_batch_id():
    used = set()
    r1 = os.path.join(BASE, "任务一", "结果", "result1.csv")
    if os.path.exists(r1):
        with open(r1, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                used.add(row["采集批次号"])
    if os.path.isdir(BATCH_ROOT):
        for d in os.listdir(BATCH_ROOT):
            used.add(d)
    n = 1
    while "B%02d" % n in used:
        n += 1
    return "B%02d" % n


# ---------------- 清洗 ----------------
def norm_url(u):
    u = (u or "").strip()
    if not u:
        return ""
    u = u.split("#")[0]
    if "?" in u:
        head, q = u.split("?", 1)
        keep = [p for p in q.split("&") if p and not re.match(r"(utm_|spm|from=|ref=|share|track)", p)]
        u = head + ("?" + "&".join(keep) if keep else "")
    return u.rstrip("/").lower()


def clean_body(text):
    t = re.sub(r"https?://\S+", " ", text or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def dedupe(records):
    seen_url, seen_hash, out, dup = set(), set(), [], 0
    for r in records:
        u = norm_url(r["url"])
        h = hashlib.md5(clean_body(r["body"]).encode("utf-8")).hexdigest()
        if u and u in seen_url:
            dup += 1
            continue
        if h in seen_hash:
            dup += 1
            continue
        if u:
            seen_url.add(u)
        seen_hash.add(h)
        out.append(r)
    return out, dup


def keep_ai_relevant(query, records):
    """需求相关性过滤：关键词命中 或 命中 AI 主题词，两者至少满足一个。"""
    terms = [t.lower() for t in re.split(r"[\s,，、/]+", query) if len(t) >= 2]
    ai_terms = ["ai", "人工智能", "大模型", "llm", "gpt", "agent", "智能", "模型", "机器学习",
                "深度学习", "神经网络", "nlp", "rag", "langchain", "prompt", "aigc", "copilot"]
    out = []
    for r in records:
        hay = (r["title"] + " " + r["body"]).lower()
        hit_q = any(t in hay for t in terms) if terms else True
        hit_ai = any(t in hay for t in ai_terms)
        if hit_q or hit_ai:
            out.append(r)
    return out


# ---------------- 写盘 ----------------
def write_snapshot(path, r):
    with open(path, "w", encoding="utf-8") as f:
        f.write("# %s\n\n- 来源：%s\n- 链接：%s\n- 发布时间：%s\n- 热度：%s\n\n## 正文\n%s\n"
                % (r["title"] or "(无标题)", r["source"], r["url"], r["published"] or "未知",
                   r["heat_text"] or "-", r["body"] or "(无正文)"))


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([r.get(h, "") for h in header])


# ---------------- 分词与聚类 ----------------
STOP = set("the a an and or but if then else for with without from this that these those is are was were be been "
           "to of in on at by as it its you your we our they their i me my he she his her not no yes do does did "
           "how what why when where which who can could should would will just also more most very much many "
           "about into over under between during after before than so such only own same other some any".split())

CN_STOP = set("的 了 是 在 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 自己 这 "
              "怎么 什么 如何 为什么 可以 但是 因为 所以 如果 这个 那个 我们 他们 以及 还是 已经 进行 通过 "
              "问题 使用 时候 需要 目前 或者 支持 实现 方式 情况 相关 内容 介绍".split())


NAME_NOISE = set("have has had do does did will would can could should may might must shall "
                 "powered using used based built make makes made get gets got give gives "
                 "just like want wants need needs know think really actually people time way "
                 "thing things something anything work works going gone also more most very "
                 "being print page initial capable technical fine good better best lot bit still "
                 "even though up per within into than then them there where which while".split())


def tokenize(text):
    """英文按词切、中文用 jieba；避免把英文词切碎（gitma / mudevelops 这类碎片）。"""
    import jieba
    low = (text or "").lower()
    ascii_words = re.findall(r"[a-z0-9][a-z0-9_+#.-]{1,}", low)
    zh_text = re.sub(r"[a-z0-9_+#.\-]+", " ", low)
    out = []
    for w in ascii_words:
        if w in STOP or w in NAME_NOISE or len(w) < 2:
            continue
        if w.isdigit():
            continue
        out.append(w)
    for w in jieba.cut(zh_text):
        w = w.strip()
        if not w or w in CN_STOP or len(w) < 2:
            continue
        if re.fullmatch(r"[\u4e00-\u9fa5]{2,}", w):
            out.append(w)
    return out


def cluster_opportunities(items):
    """items: [{title, body, func, industry, ...}] → 簇列表（独立于其它批次）。"""
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import silhouette_score

    n = len(items)
    if n == 0:
        return [], {"k": 0, "silhouette": 0.0, "vectors": 0}
    texts = [(it["title"] + " " + it["body"][:1200]) for it in items]
    vec = TfidfVectorizer(tokenizer=tokenize, lowercase=True, min_df=1, max_df=0.6,
                          sublinear_tf=True, token_pattern=None)
    X = vec.fit_transform(texts)
    vocab = vec.get_feature_names_out()
    dim = int(min(40, max(2, X.shape[1] - 1), max(2, n - 1)))
    Z = TruncatedSVD(n_components=dim, random_state=42).fit_transform(X)

    best = None
    upper = int(min(12, max(3, n // 6)))
    for k in range(3, upper + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(Z)
        labels = km.labels_
        if len(set(labels)) < 2:
            continue
        try:
            sil = silhouette_score(Z, labels) if n > k else -1
        except Exception:  # noqa: BLE001
            sil = -1
        if best is None or sil > best[1]:
            best = (labels, sil, k, km)
    if best is None:
        labels = np.zeros(n, dtype=int)
        sil, k = 0.0, 1
    else:
        labels, sil, k = best[0], best[1], best[2]

    # 零散小簇（<3 条）并入最相近的大簇，避免出现「一条记录一个主题」的噪声簇
    labels = np.asarray(labels)
    if k > 2:
        for _ in range(2):
            sizes = Counter(labels.tolist())
            small = [c for c, cnt in sizes.items() if cnt < 3]
            big = [c for c, cnt in sizes.items() if cnt >= 3]
            if not small or not big:
                break
            cents = {c: Z[labels == c].mean(axis=0) for c in big}
            for s in small:
                for i in np.where(labels == s)[0]:
                    norm = np.linalg.norm(Z[i]) + 1e-9
                    sims = {c: float(np.dot(Z[i], cents[c]) / (norm * (np.linalg.norm(cents[c]) + 1e-9)))
                            for c in big}
                    labels[i] = max(sims, key=sims.get)

    # 簇内 top 词 → 名称（功能类别做前缀，避免纯英文碎片名称）
    clusters = []
    for cid in sorted(set(labels.tolist())):
        idx = [i for i in range(n) if labels[i] == cid]
        sub = X[idx]
        mean = np.asarray(sub.mean(axis=0)).ravel()
        top_ids = mean.argsort()[::-1][:16]
        terms = []
        for j in top_ids:
            t = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fa5+#-]+$", "", str(vocab[j]).strip("."))
            if len(t) < 2 or t in NAME_NOISE or t in STOP or t in CN_STOP:
                continue
            if t not in terms:
                terms.append(t)
            if len(terms) >= 5:
                break
        funcs = Counter(items[i]["func"] for i in idx if items[i]["func"])
        inds = Counter(items[i]["industry"] for i in idx if items[i]["industry"])
        func = funcs.most_common(1)[0][0] if funcs else ""
        key = "、".join(terms[:2]) if terms else "未命名主题"
        clusters.append({
            "cid": "C%d" % (len(clusters) + 1),
            "idx": idx,
            "terms": terms,
            "func": func,
            "industry": inds.most_common(1)[0][0] if inds else "其他",
            "name": (func + "·" + key) if func else key,
        })
    clusters.sort(key=lambda c: -len(c["idx"]))
    for i, c in enumerate(clusters, 1):
        c["cid"] = "C%d" % i
    return clusters, {"k": len(clusters), "silhouette": round(float(sil), 4), "vectors": int(X.shape[1])}


# ---------------- 价值评估 ----------------
def value_scores(clusters, batch_span_days):
    max_src = max([len({m["source"] for m in c["members"]}) for c in clusters] + [1])
    max_size = max([len(c["members"]) for c in clusters] + [1])
    max_heat = max([sum(m["heat"] for m in c["members"]) for c in clusters] + [1])
    for c in clusters:
        n_src = len({m["source"] for m in c["members"]})
        src = 100.0 * n_src / max_src
        size = 100.0 * len(c["members"]) / max_size
        heat = sum(m["heat"] for m in c["members"])
        heat_s = 100.0 * math.log1p(heat) / math.log1p(max_heat)
        days = sorted(m["day"] for m in c["members"] if m["day"])
        span = (days[-1] - days[0]).days if len(days) >= 2 else 0
        persist = 100.0 * min(1.0, span / max(30.0, batch_span_days))
        biz = 0.6 * heat_s + 0.4 * persist
        c["dims"] = {"src": round(src, 1), "size": round(size, 1), "biz": round(biz, 1)}
        c["heat_sum"] = heat
        c["n_src"] = n_src
        c["span_days"] = span
        c["score"] = round(WEIGHTS[0] * src + WEIGHTS[1] * size + WEIGHTS[2] * biz, 1)
    clusters.sort(key=lambda c: -c["score"])
    for i, c in enumerate(clusters, 1):
        c["priority"] = i


def to_day(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return None


# ---------------- 主流程 ----------------
def run_batch(bid, requirement, log=print, proxy=None, raw=None):
    """执行一个批次的完整流水线，返回批次摘要 dict。

    raw 不为 None 时跳过采集，直接用它重算（离线复现）。
    """
    t0 = time.time()
    query = requirement.get("query", "").strip()
    src_keys = requirement.get("sources") or ["stackoverflow", "hackernews"]
    target = int(requirement.get("target") or 500)
    per_source = max(60, min(300, int(math.ceil(target / max(1, len(src_keys))) * 1.4)))

    workdir = os.path.join(BATCH_ROOT, bid)
    os.makedirs(workdir, exist_ok=True)
    textdir = os.path.join(workdir, "text")
    os.makedirs(textdir, exist_ok=True)

    log("【%s】需求：%s；来源：%s；目标 %d 条" % (bid, query, ",".join(src_keys), target))

    # 1) 采集（或离线复用既有原始记录）
    if raw is None:
        raw, notes = sources.collect(query, src_keys, limit_per_source=per_source, proxy=proxy, log=log)
        with open(os.path.join(workdir, "原始记录.json"), "w", encoding="utf-8") as f:
            json.dump({"batch": bid, "requirement": requirement, "notes": notes, "records": raw},
                      f, ensure_ascii=False, indent=1)
        log("采集完成：%d 条原始记录" % len(raw))
    else:
        notes = ["离线重算：复用原始记录.json（未重新采集）"]
        log("离线重算：复用已有原始记录 %d 条，不重新采集" % len(raw))
    if not raw:
        raise RuntimeError("本批次未采集到任何记录，请检查关键词或网络（可在来源中勾选“本地语料回放”离线运行）")

    # 2) 清洗 / 去重 / 相关性过滤
    cleaned = []
    for r in raw:
        body = clean_body(r["body"])
        title = (r["title"] or "").strip()
        if len(body) < 20 and len(title) < 8:
            continue
        r["body"] = body
        cleaned.append(r)
    deduped, dupn = dedupe(cleaned)
    filtered = keep_ai_relevant(query, deduped)
    log("清洗 %d → 去重剔除 %d → 相关性保留 %d" % (len(cleaned), dupn, len(filtered)))

    # 3) 正文快照 + result1
    rows1, records = [], []
    for i, r in enumerate(filtered, 1):
        sid = "S%05d" % i
        fn = "%s_%s.md" % (bid, sid)
        write_snapshot(os.path.join(textdir, fn), r)
        day = to_day(r["published"])
        rows1.append({
            "采集批次号": bid, "记录编号": sid, "来源网站名称": r["source"], "来源链接": r["url"],
            "内容": "./text/" + fn, "发布时间": r["published"] or "",
            "星标数": r["stars"] if r["stars"] else "", "浏览数": r["views"] if r["views"] else "",
            "点赞数": r["likes"] if r["likes"] else "", "评论数": r["comments"] if r["comments"] else "",
            "收藏数": r["favorites"] if r["favorites"] else "",
        })
        records.append({**r, "sid": sid, "day": day, "snapshot": "./text/" + fn,
                        "heat": sum(int(x or 0) for x in (r["stars"], r["views"], r["likes"],
                                                          r["comments"], r["favorites"]))})
    write_csv(os.path.join(workdir, "result1.csv"), R1_HEADER, rows1)

    # 4) 机会判别（复用任务二的判别口径）
    oc = _load("opportunity_classifier")
    cc = _load("category_classifier")
    rows2, opps = [], []
    for r in records:
        d = oc.classify_opportunity(r["title"], r["body"], r["source"])
        is_opp = 1 if d["is_opportunity"] else 0
        cat = cc.classify_category(r["title"], r["body"]) if is_opp else {"function": "", "industry": ""}
        rows2.append({
            "采集批次号": bid, "记录编号": r["sid"], "是否构成机会": is_opp,
            "机会置信度": "%.4f" % d["confidence"],
            "功能类别": cat.get("function", ""), "所属行业": cat.get("industry", ""),
        })
        if is_opp:
            opps.append({**r, "confidence": d["confidence"], "rule": d["decision_rule"],
                         "reason": d["decision_reason"], "func": cat.get("function", ""),
                         "industry": cat.get("industry", "")})
    write_csv(os.path.join(workdir, "result2.csv"), R2_HEADER, rows2)
    log("机会判定完成：%d 条机会（%.1f%%）" % (len(opps), len(opps) / max(1, len(rows2)) * 100))

    # 5) 主题聚类（仅本批次内）
    clusters, cinfo = ([], {"k": 0, "silhouette": 0, "vectors": 0})
    rows3, rows4 = [], []
    if opps:
        clusters, cinfo = cluster_opportunities(opps)
        for c in clusters:
            c["members"] = [opps[i] for i in c["idx"]]
        days = [m["day"] for m in opps if m["day"]]
        span = (max(days) - min(days)).days if len(days) >= 2 else 0
        value_scores(clusters, span)
        for c in clusters:
            src_map = Counter(m["source"] for m in c["members"])
            rows3.append({
                "采集批次号": bid, "主题簇编号": c["cid"], "主题簇名称": c["name"],
                "功能类别": c["func"], "所属行业": c["industry"],
                "簇内机会记录数": len(c["members"]),
                "来源覆盖": "、".join(k for k, _ in src_map.most_common()),
                "簇内机会记录": "；".join("%s-%s" % (bid, m["sid"]) for m in c["members"]),
            })
            rows4.append({
                "采集批次号": bid, "主题簇编号": c["cid"], "主题簇名称": c["name"],
                "功能类别": c["func"], "所属行业": c["industry"],
                "机会价值分": c["score"], "优先级": c["priority"],
            })
        write_csv(os.path.join(workdir, "result3.csv"), R3_HEADER, rows3)
        write_csv(os.path.join(workdir, "result4.csv"), R4_HEADER, rows4)
        with open(os.path.join(workdir, "result4_中间指标.json"), "w", encoding="utf-8") as f:
            json.dump({
                "batch": bid,
                "weights": list(WEIGHTS),
                "memo": "归一化分母均取本批次观测最大值，批次间不可横向比较数值",
                "clusters": [{
                    "主题簇编号": c["cid"], "主题簇名称": c["name"],
                    "多源指向度": c["dims"]["src"], "记录规模": c["dims"]["size"],
                    "商业信号": c["dims"]["biz"], "机会价值分": c["score"],
                    "priority": c["priority"], "n_src": c["n_src"], "n_size": len(c["members"]),
                    "n_batch": 1, "heat_sum": c["heat_sum"], "span_days": c["span_days"],
                } for c in clusters]}, f, ensure_ascii=False, indent=1)

    src_stat = Counter(r["source"] for r in records)
    summary = {
        "bid": bid,
        "query": query,
        "sources": src_keys,
        "target": target,
        "notes": notes,
        "records": len(records),
        "opportunities": len(opps),
        "opp_rate": round(len(opps) / max(1, len(records)) * 100, 1),
        "clusters": len(clusters),
        "silhouette": cinfo.get("silhouette", 0),
        "k": cinfo.get("k", 0),
        "source_stat": dict(src_stat),
        "top": ({"cid": clusters[0]["cid"], "name": clusters[0]["name"], "score": clusters[0]["score"]}
                if clusters else None),
        "elapsed": round(time.time() - t0, 1),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "workdir": workdir,
    }

    write_report(workdir, bid, requirement, summary, clusters, records, rows2)
    return summary


def write_report(workdir, bid, requirement, summary, clusters, records, rows2):
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    L = []
    L.append("# 批次 %s · 需求分析报告\n" % bid)
    L.append("- 需求关键词：**%s**" % requirement.get("query", ""))
    L.append("- 发起时间：%s；耗时：%ss" % (date, summary["elapsed"]))
    L.append("- 采集来源：%s" % "、".join(sources.SOURCE_LABELS.get(k, k) for k in summary["sources"]))
    L.append("- 处理链路：采集 → 清洗 → 去重 → 相关性过滤 → 正文快照 → 机会判别（阈值 %.2f）→ 主题聚类 → 价值评估"
             % DECISION_TAU)
    L.append("")
    L.append("## 一、本批次漏斗\n")
    L.append("| 阶段 | 数量 |")
    L.append("|---|---|")
    L.append("| 采集清洗去重后记录 | %d |" % summary["records"])
    L.append("| 判为 AI 应用机会 | %d（%.1f%%） |" % (summary["opportunities"], summary["opp_rate"]))
    L.append("| 机会主题簇 | %d |" % summary["clusters"])
    L.append("")
    L.append("## 二、来源构成\n")
    L.append("| 来源 | 条数 |")
    L.append("|---|---|")
    for k, v in sorted(summary["source_stat"].items(), key=lambda t: -t[1]):
        L.append("| %s | %d |" % (k, v))
    L.append("")
    if summary["notes"]:
        L.append("> 采集提示：" + "；".join(summary["notes"]) + "\n")
    if clusters:
        L.append("## 三、机会主题簇（按价值分排序）\n")
        L.append("| 簇 | 主题 | 功能类别 | 行业 | 记录数 | 来源数 | 价值分 |")
        L.append("|---|---|---|---|---|---|---|")
        for c in clusters:
            L.append("| %s | %s | %s | %s | %d | %d | %.1f |"
                     % (c["cid"], c["name"], c["func"] or "-", c["industry"] or "-",
                        len(c["members"]), c["n_src"], c["score"]))
        L.append("")
        L.append("## 四、Top3 机会的原始证据（可逐条溯源）\n")
        for c in clusters[:3]:
            L.append("### %s %s（价值 %.1f，优先级 %d）\n" % (c["cid"], c["name"], c["score"], c["priority"]))
            L.append("- 三维度：多源指向 %.1f / 记录规模 %.1f / 商业信号 %.1f"
                     % (c["dims"]["src"], c["dims"]["size"], c["dims"]["biz"]))
            L.append("- 簇内记录 %d 条，覆盖来源：%s\n"
                     % (len(c["members"]), "、".join(sorted({m["source"] for m in c["members"]}))))
            for m in sorted(c["members"], key=lambda x: -x["heat"])[:5]:
                L.append("  - [%s] %s（%s，置信度 %.2f）<%s> 快照 `%s`"
                         % (m["source"], (m["title"] or "")[:70], m["published"] or "时间未知",
                            m["confidence"], m["url"], m["snapshot"]))
            L.append("")
    L.append("## 五、溯源与复核方式\n")
    L.append("- 每条机会在 `result2.csv` 中有 `批次号-记录编号`；`result1.csv` 的 `内容` 列指向 `text/` 正文快照。")
    L.append("- 采集原始返回保存在 `原始记录.json`，字段与接口返回一致，可与 `result1.csv` 逐条比对。")
    L.append("- 复现本批次：`python 任务五/core/replay_batch.py %s`（离线重算，不重新采集）。" % bid)
    L.append("")
    L.append("## 六、本批次独立性说明\n")
    L.append("- 判别阈值固定为 %.2f，与基线一致，不因批次变化。" % DECISION_TAU)
    L.append("- 聚类的 k、归一化分母（最大来源数 / 最大簇规模 / 最大热度）全部只在本批次内计算。")
    L.append("- 因此不同批次的簇编号与价值分**不可横向比较数值大小**，只在本批次内排序有意义。")
    with open(os.path.join(workdir, "批次报告.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    _ = (rows2, records)

def replay(bid, log=print):
    """离线复现：只用该批次已保存的原始记录重算全链，不访问网络。"""
    workdir = os.path.join(BATCH_ROOT, bid)
    p = os.path.join(workdir, "原始记录.json")
    if not os.path.exists(p):
        raise RuntimeError("批次 %s 没有原始记录.json，无法离线复现" % bid)
    with open(p, encoding="utf-8") as f:
        payload = json.load(f)
    return run_batch(bid, payload.get("requirement") or {}, log=log, raw=payload.get("records") or [])
