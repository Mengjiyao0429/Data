# -*- coding: utf-8 -*-
"""任务一数据集 v2：二次清洗去重 + 5 批次分配 + 图片样式 result1.csv。

表头（对齐赛题 PDF 表1 样式）：
采集批次号, 记录编号, 来源网站名称, 来源链接, 内容, 发布时间, 星标数, 浏览数, 点赞数, 评论数, 收藏数
内容列 = ./text/{批次}_{编号}.md（正斜杠，text 子目录）。
批次划分：GitHub 三等分(B01/B02/B03) + Stack Overflow(B04) + 中文内容(B05)。
"""
import csv, hashlib, json, os, re, sys
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from app.pipeline.cleaner import clean_text

RAW = os.path.join(BASE, "data", "collected_bulk")
DOM = os.path.join(BASE, "data", "collected")
RESULT = r"D:\Data\Data\任务一\结果"
TEXT = os.path.join(RESULT, "text")
os.makedirs(TEXT, exist_ok=True)

RECENT = "2024-01-01"
HEADER = ["采集批次号", "记录编号", "来源网站名称", "来源链接", "内容", "发布时间",
          "星标数", "浏览数", "点赞数", "评论数", "收藏数"]
M_LABEL = [("星标数", "星标"), ("浏览数", "浏览"), ("点赞数", "点赞"),
           ("评论数", "评论"), ("收藏数", "收藏")]


def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def s(v):
    return "" if v in (None, "", 0, "0") else str(v).strip()


def metrics_for(r, source):
    m = {"星标数": "", "浏览数": "", "点赞数": "", "评论数": "", "收藏数": ""}
    h = r.get("heat")
    hd = h if isinstance(h, dict) else {}

    def g(*keys):
        for k in keys:
            if k in hd:
                return s(hd[k])
        return ""

    if source == "GitHub":
        m["星标数"] = s(r.get("stars"))
    elif source == "Stack Overflow":
        m["点赞数"] = s(r.get("stars"))
        m["评论数"] = s(r.get("comments"))
        m["浏览数"] = s(r.get("views"))
    elif source == "CSDN":
        m["浏览数"] = s(r.get("views"))
        m["点赞数"] = s(r.get("stars"))
        m["评论数"] = s(r.get("comments"))
    elif source == "36氪":
        m["点赞数"] = g("like")
        m["评论数"] = g("comment")
        m["收藏数"] = g("fav")
    elif source == "腾讯新闻":
        m["点赞数"] = g("点赞")
        m["评论数"] = g("评论")
        m["收藏数"] = g("收藏")
    elif source in ("阿里云开发者社区", "中国医药创新促进会"):
        m["浏览数"] = g("浏览量") or s(r.get("views"))
    elif source == "新浪科技":
        pass
    return m


def heat_text(m):
    parts = [f"{label}{m[key]}" for key, label in M_LABEL if m[key]]
    return "、".join(parts) if parts else "—"


def norm_rec(r, source):
    url = r.get("url") or r.get("source_url") or ""
    title = (r.get("title") or "").strip()
    raw = (r.get("raw_text") or r.get("raw_content") or "").strip()
    pub = (r.get("date") or r.get("published_at") or "").strip()[:10]
    return {
        "source_name": source,
        "source_url": url,
        "title": title,
        "raw_content": raw,
        "published_at": pub,
        "metrics": metrics_for(r, source),
    }


def norm_url(u):
    u = (u or "").strip().split("#")[0]
    m = re.match(r"https?://([^/]+)(.*)", u)
    if not m:
        return u
    return f"https://{m.group(1).lower().replace('www.', '')}{m.group(2).rstrip('/')}"


def simhash(text, bits=64):
    toks = [text[i:i + 4] for i in range(max(0, len(text) - 3))] or [text]
    v = [0] * bits
    for t in toks:
        h = int.from_bytes(hashlib.md5(t.encode()).digest()[:8], "big")
        for i in range(bits):
            v[i] += 1 if (h >> i) & 1 else -1
    return sum(1 << i for i in range(bits) if v[i] > 0)


def bands_of(sh, bbits=16, nb=4):
    mask = (1 << bbits) - 1
    return [(i, (sh >> (i * bbits)) & mask) for i in range(nb)]


def dedup(records):
    kept, seen_url, seen_md5 = [], set(), set()
    buckets = defaultdict(list)
    stat = Counter()
    for rec in records:
        nu = norm_url(rec["source_url"])
        if not nu:
            stat["无链接"] += 1
            continue
        if nu in seen_url:
            stat["链接重复"] += 1
            continue
        c = rec["clean_content"]
        md5 = hashlib.md5(c.encode()).hexdigest()
        if md5 in seen_md5:
            stat["正文完全相同"] += 1
            continue
        sh = simhash(c)
        L = len("".join(c.split()))
        dup = False
        for bi, bv in bands_of(sh):
            for kidx in buckets[(bi, bv)]:
                o = kept[kidx]
                Lo = len("".join(o["clean_content"].split()))
                if not L or not Lo or min(L, Lo) / max(L, Lo) < 0.7:
                    continue
                if bin(sh ^ o["_sh"]).count("1") <= 4:
                    dup = True
                    break
            if dup:
                break
        if dup:
            stat["近似重复"] += 1
            continue
        rec["_sh"] = sh
        seen_url.add(nu)
        seen_md5.add(md5)
        for bi, bv in bands_of(sh):
            buckets[(bi, bv)].append(len(kept))
        kept.append(rec)
    return kept, stat


def main():
    all_recs = []
    for name, src in (("github.json", "GitHub"), ("so.json", "Stack Overflow")):
        p = os.path.join(RAW, name)
        if os.path.exists(p):
            for r in load_json(p):
                all_recs.append(norm_rec(r, src))
    for r in (load_json(os.path.join(RAW, "csdn.json")) if os.path.exists(os.path.join(RAW, "csdn.json")) else []):
        all_recs.append(norm_rec(r, "CSDN"))
    for r in (load_json(os.path.join(RAW, "rss.json")) if os.path.exists(os.path.join(RAW, "rss.json")) else []):
        all_recs.append(norm_rec(r, r.get("source_name", "RSS")))
    dom = []
    for fn, src in (("browser_36kr.json", "36氪"), ("browser_aliyun.json", "阿里云开发者社区"),
                    ("browser_phirda.json", "中国医药创新促进会"), ("browser_isc.json", "中国互联网协会")):
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

    cleaned, dropped = [], Counter()
    for rec in all_recs:
        if not rec["source_url"].startswith("http"):
            dropped["无有效链接"] += 1
            continue
        if rec["published_at"] and rec["published_at"] < RECENT:
            dropped["早于2024-01-01"] += 1
            continue
        c = clean_text(rec["raw_content"]) or clean_text(rec["title"])
        if len(c) < 20:
            dropped["正文过短(<20字)"] += 1
            continue
        rec["clean_title"] = clean_text(rec["title"])
        rec["clean_content"] = c[:6000]
        cleaned.append(rec)

    kept, dstat = dedup(cleaned)

    # 批次划分
    gh = [r for r in kept if r["source_name"] == "GitHub"]
    so = [r for r in kept if r["source_name"] == "Stack Overflow"]
    zh = [r for r in kept if r["source_name"] not in ("GitHub", "Stack Overflow")]

    gh.sort(key=lambda r: -float(r["metrics"]["星标数"] or 0))
    g1, g2, g3 = gh[0::3], gh[1::3], gh[2::3]
    for b in (g1, g2, g3):
        b.sort(key=lambda r: -float(r["metrics"]["星标数"] or 0))
    so.sort(key=lambda r: -float(r["metrics"]["点赞数"] or 0))

    def sort_zh(r):
        for k in ("浏览数", "点赞数", "评论数", "收藏数"):
            if r["metrics"][k]:
                return -float(r["metrics"][k])
        return 0
    zh.sort(key=lambda r: (r["source_name"], sort_zh(r)))

    batches = {"B01": g1, "B02": g2, "B03": g3, "B04": so, "B05": zh}

    # 清空旧 text 目录（仅本任务生成的快照）
    for f in os.listdir(TEXT):
        if f.endswith(".md"):
            os.remove(os.path.join(TEXT, f))

    rows = []
    for b in sorted(batches):
        for i, rec in enumerate(batches[b], 1):
            sid = f"S{i:05d}"
            fn = f"{b}_{sid}.md"
            body = (f"# {rec['clean_title']}\n\n"
                    f"- 来源：{rec['source_name']}\n"
                    f"- 链接：{rec['source_url']}\n"
                    f"- 发布时间：{rec['published_at']}\n"
                    f"- 热度：{heat_text(rec['metrics'])}\n\n"
                    f"## 正文\n{rec['clean_content']}\n")
            with open(os.path.join(TEXT, fn), "w", encoding="utf-8") as f:
                f.write(body)
            row = {"采集批次号": b, "记录编号": sid,
                   "来源网站名称": rec["source_name"], "来源链接": rec["source_url"],
                   "内容": f"./text/{fn}", "发布时间": rec["published_at"]}
            for k, _ in M_LABEL:
                row[k] = rec["metrics"][k]
            rows.append(row)

    with open(os.path.join(RESULT, "result1.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)

    print("原始合并:", len(all_recs), "| 清洗丢弃:", dict(dropped), "| 去重移除:", dict(dstat))
    print("最终:", len(rows))
    print("批次:", dict(Counter(r['采集批次号'] for r in rows)))
    print("来源:", dict(Counter(r['来源网站名称'] for r in rows)))


if __name__ == "__main__":
    main()
