# -*- coding: utf-8 -*-
"""构建扩容后的任务一数据集：清洗 → 去重 → 批次编号 → result1.csv + 正文快照。

去重三级：
1) 链接精确去重（归一化 host/path）
2) 正文 MD5 精确去重
3) SimHash 近似去重（4 段 16bit 分桶，汉明距离 ≤ 4 且长度比 ≥ 0.7）
"""
import csv, hashlib, json, os, re, sys
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from app.pipeline.cleaner import clean_text

RAW = os.path.join(BASE, "data", "collected_bulk")
DOM = os.path.join(BASE, "data", "collected")
OUT = os.path.join(BASE, "data", "task1_expand")
SNAP = os.path.join(OUT, "正文快照")
os.makedirs(SNAP, exist_ok=True)

RECENT = "2024-01-01"

# ---------------- 读取与归一化 ----------------

def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def norm_url(u):
    u = (u or "").strip()
    u = u.split("#")[0]
    m = re.match(r"https?://([^/]+)(.*)", u)
    if not m:
        return u
    host = m.group(1).lower().replace("www.", "")
    path = m.group(2).rstrip("/")
    return f"https://{host}{path}"


def heat_to_text(h):
    if isinstance(h, dict):
        parts = []
        for k, v in h.items():
            if v in (None, "", "0"):
                continue
            label = {"like": "点赞", "fav": "收藏", "comment": "评论",
                     "点赞": "点赞", "评论": "评论", "收藏": "收藏"}.get(k, k)
            parts.append(f"{label}{v}")
        return "、".join(parts)
    if isinstance(h, list):
        return "、".join(str(x) for x in h if x)
    return str(h or "")


def norm_rec(r, source):
    return {
        "source_name": source,
        "source_url": r.get("url") or r.get("source_url") or "",
        "title": (r.get("title") or "").strip(),
        "raw_content": (r.get("raw_text") or r.get("raw_content") or "").strip(),
        "published_at": (r.get("date") or r.get("published_at") or "").strip()[:10],
        "stars": r.get("stars") or r.get("likes"),
        "comments": r.get("comments") or r.get("comment"),
        "views": r.get("views"),
        "heat_text": (heat_to_text(r.get("heat")) if r.get("heat") is not None
                      else (r.get("heat_text") or "")).strip() or "—",
    }

# ---------------- SimHash ----------------

def simhash(text, bits=64):
    toks = [text[i:i + 4] for i in range(max(0, len(text) - 3))] or [text]
    v = [0] * bits
    for t in toks:
        h = int.from_bytes(hashlib.md5(t.encode("utf-8")).digest()[:8], "big")
        for i in range(bits):
            v[i] += 1 if (h >> i) & 1 else -1
    return sum(1 << i for i in range(bits) if v[i] > 0)


def bands_of(sh, band_bits=16, nbands=4):
    mask = (1 << band_bits) - 1
    return [(i, (sh >> (i * band_bits)) & mask) for i in range(nbands)]


def hamming(a, b):
    return bin(a ^ b).count("1")


def dedup(records):
    """返回 (保留记录, 各阶段移除统计)。"""
    kept = []
    seen_url = set()
    seen_md5 = set()
    buckets = defaultdict(list)   # (band_idx, band_val) -> [kept_idx]
    stats = Counter()

    for rec in records:
        nu = norm_url(rec["source_url"])
        if not nu:
            stats["无链接"] += 1
            continue
        if nu in seen_url:
            stats["链接重复"] += 1
            continue
        content = rec["clean_content"]
        md5 = hashlib.md5(content.encode("utf-8")).hexdigest()
        if md5 in seen_md5:
            stats["正文完全相同"] += 1
            continue
        # 近似去重
        sh = simhash(content)
        L = len("".join(content.split()))
        dup = False
        for bidx, bval in bands_of(sh):
            for kidx in buckets[(bidx, bval)]:
                other = kept[kidx]
                Lo = len("".join(other["clean_content"].split()))
                if not L or not Lo:
                    continue
                if min(L, Lo) / max(L, Lo) < 0.7:
                    continue
                if hamming(sh, other["_sh"]) <= 4:
                    dup = True
                    break
            if dup:
                break
        if dup:
            stats["近似重复"] += 1
            continue
        rec["_sh"] = sh
        seen_url.add(nu)
        seen_md5.add(md5)
        for bidx, bval in bands_of(sh):
            buckets[(bidx, bval)].append(len(kept))
        kept.append(rec)
    return kept, stats

# ---------------- 主流程 ----------------

def main():
    all_recs = []

    # B01：Stack Overflow + GitHub（技术社区）
    for name, src in (("so.json", "Stack Overflow"), ("github.json", "GitHub")):
        p = os.path.join(RAW, name)
        if not os.path.exists(p):
            print(f"[warn] 缺少 {p}")
            continue
        for r in load_json(p):
            all_recs.append(norm_rec(r, src))

    # B02：国内站点（复用真实抓取结果）
    dom = []
    for fn, src in (("browser_36kr.json", "36氪"),
                    ("browser_aliyun.json", "阿里云开发者社区"),
                    ("browser_phirda.json", "中国医药创新促进会"),
                    ("browser_isc.json", "中国互联网协会")):
        p = os.path.join(DOM, fn)
        if os.path.exists(p):
            for r in load_json(p):
                dom.append(norm_rec(r, src))
    p = os.path.join(DOM, "browser_news.json")
    if os.path.exists(p):
        for src, items in load_json(p).items():
            for r in items:
                dom.append(norm_rec(r, src))
    all_recs.extend(dom)

    # B03：CSDN
    p = os.path.join(RAW, "csdn.json")
    for r in (load_json(p) if os.path.exists(p) else []):
        all_recs.append(norm_rec(r, "CSDN"))

    # B04：RSS 科技媒体
    p = os.path.join(RAW, "rss.json")
    for r in (load_json(p) if os.path.exists(p) else []):
        all_recs.append(norm_rec(r, r.get("source_name", "RSS")))

    print("原始合并条数:", len(all_recs))

    # 清洗 + 时间窗过滤
    cleaned, dropped = [], Counter()
    for rec in all_recs:
        ctitle = clean_text(rec["title"])
        ccontent = clean_text(rec["raw_content"]) or ctitle
        if not rec["source_url"].startswith("http"):
            dropped["无有效链接"] += 1
            continue
        if rec["published_at"] and rec["published_at"] < RECENT:
            dropped["早于2024-01-01"] += 1
            continue
        if len(ccontent) < 5:
            dropped["正文过短"] += 1
            continue
        if len(ccontent) > 6000:
            ccontent = ccontent[:6000]
        item = dict(rec)
        item["clean_title"] = ctitle
        item["clean_content"] = ccontent
        cleaned.append(item)
    print("清洗后:", len(cleaned), "| 丢弃:", dict(dropped))

    kept, dstat = dedup(cleaned)
    print("去重后:", len(kept), "| 移除:", dict(dstat))

    # 批次划分
    def batch_of(rec):
        s = rec["source_name"]
        if s in ("Stack Overflow", "GitHub"):
            return "B01"
        if s in ("CSDN",):
            return "B03"
        if s in ("量子位", "IT之家", "少数派", "InfoQ中国"):
            return "B04"
        return "B02"

    groups = defaultdict(list)
    for rec in kept:
        groups[batch_of(rec)].append(rec)

    # 排序：热度降序，保证批次内头部是热门内容
    def heat_key(r):
        for v in (r.get("stars"), r.get("views"), r.get("comments")):
            if isinstance(v, (int, float)):
                return -float(v)
        return 0
    for b in groups:
        groups[b].sort(key=lambda r: (r["source_name"], heat_key(r)))

    rows = []
    for b in sorted(groups):
        for i, rec in enumerate(groups[b], 1):
            sid = f"S{i:05d}"
            fn = f"{b}_{sid}.md"
            path = os.path.join(SNAP, fn)
            body = (
                f"# {rec['clean_title']}\n\n"
                f"- 来源：{rec['source_name']}\n"
                f"- 链接：{rec['source_url']}\n"
                f"- 发布时间：{rec['published_at']}\n"
                f"- 热度：{rec['heat_text']}\n\n"
                f"## 正文\n{rec['clean_content']}\n"
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
            rows.append({
                "采集批次号": b,
                "记录编号": sid,
                "来源网站名称": rec["source_name"],
                "来源链接": rec["source_url"],
                "内容": f"正文快照\\{fn}",
                "发布时间": rec["published_at"],
                "热度指标（如浏览数、点赞数、讨论数等）": rec["heat_text"],
            })

    csv_path = os.path.join(OUT, "result1.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["采集批次号", "记录编号", "来源网站名称",
                                          "来源链接", "内容", "发布时间",
                                          "热度指标（如浏览数、点赞数、讨论数等）"])
        w.writeheader()
        w.writerows(rows)

    # 统计
    src_cnt = Counter(r["来源网站名称"] for r in rows)
    batch_cnt = Counter(r["采集批次号"] for r in rows)
    stats = {
        "总条数": len(rows),
        "批次分布": dict(batch_cnt),
        "来源分布": dict(src_cnt),
        "去重移除": dict(dstat),
        "清洗丢弃": dict(dropped),
    }
    with open(os.path.join(OUT, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print("\n===== 最终统计 =====")
    print("总条数:", len(rows))
    for k, v in sorted(batch_cnt.items()):
        print(f"  {k}: {v}")
    for k, v in sorted(src_cnt.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print("result1 ->", csv_path)


if __name__ == "__main__":
    main()
