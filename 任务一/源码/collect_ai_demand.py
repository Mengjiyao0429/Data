# -*- coding: utf-8 -*-
"""任务一 · 需求侧补采（B06 / B07 / B08）

目的：修正"供给型记录（GitHub 仓库）占 67%、需求侧仅 33%"的结构失衡。
统一口径：只采集 AI 应用场景主题的真实用户讨论（问题、求助、经验、吐槽），
来源为三个公开免鉴权接口，全部保留原始返回以便复核：

  B06  Stack Overflow  ·  /2.3/questions（AI 主题标签，filter=withbody）
  B07  Hacker News     ·  hn.algolia.com/api/v1/search（tags=comment，含讨论正文）
  B08  V2EX            ·  /api/topics/hot.json + /api/topics/show.json（节点热帖）

输出：
  任务一/原始数据/B06_stackoverflow_raw.json   （原始条目 + 请求 URL + 抓取时间）
  任务一/原始数据/B07_hackernews_raw.json
  任务一/原始数据/B08_v2ex_raw.json
本脚本只采集与落盘原始数据，不修改 result1；入库见 merge_ai_demand.py。
"""
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(REPO, "原始数据")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

VERY_STRONG = [
    "大模型", "语言模型", "智能体", "多模态", "检索增强", "向量数据库", "提示词", "微调",
    "生成式", "chatgpt", "openai", "gpt", "claude", "gemini", "langchain", "llamaindex",
    "rag", "stable diffusion", "hugging face", "huggingface", "ai agent", "aigc",
    "文生图", "文生视频", "llm应用", "大语言模型",
]
STRONG = [
    "知识库", "语音识别", "语音合成", "图像识别", "目标检测", "文本生成", "智能客服",
    "智能推荐", "智能问答", "数字人", "自动驾驶", "智能写作", "智能翻译", "文档解析",
    "情感分析", "语义检索", "ocr", "chatbot", "copilot", "embedding", "transformer",
    "diffusion", "whisper", "fine-tun", "llm", "nlp", "machine learning", "deep learning",
    "neural network", "computer vision", "artificial intelligence", "vector database",
    "semantic search", "prompt engineering", "context window", "token 消耗", "推理成本",
]


def _count(text, keys):
    low = (text or "").lower()
    hits = set()
    for k in keys:
        if re.search(r"[\u4e00-\u9fff]", k):
            if k in low:
                hits.add(k)
        else:
            if re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", low):
                hits.add(k)
    return len(hits)


def is_ai(text):
    """AI 主题判定：命中任一"强特征词"（大模型/智能体/ChatGPT/RAG…），
    或命中 2 个以上一般特征词（LLM 单独出现不算——法学 LLM 学位、命令行 prompt 都会误命中）。"""
    return _count(text, VERY_STRONG) >= 1 or _count(text, STRONG) >= 2

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"[ \t\r\f\v]+")


def clean(text, limit=4000):
    if not text:
        return ""
    text = html.unescape(str(text))
    text = re.sub(r"<?(p|br|li|div|pre|code|blockquote)[^>]*>", "\n", text, flags=re.I)
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = WS_RE.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return text.strip()[:limit]


def get_json(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    print("  ! 失败:", url[:110], "|", last)
    return None


# --------------------------------------------------------------------------
# B06 Stack Overflow：AI 主题标签下的真实提问（带正文）
# --------------------------------------------------------------------------
SO_TAGS = [
    "large-language-model", "langchain", "openai-api", "gpt-4", "chatgpt",
    "huggingface-transformers", "retrieval-augmented-generation", "prompt-engineering",
    "llama-index", "vector-database", "ai-agents", "fine-tuning", "embeddings",
    "semantic-search", "chatbot", "stable-diffusion", "whisper", "ocr",
    "azure-openai", "google-gemini",
]


def collect_stackoverflow(pages=4, pagesize=100, cap=1800):
    out, seen = [], set()
    quota = None
    for tag in SO_TAGS:
        for page in range(1, pages + 1):
            qs = urllib.parse.urlencode({
                "tagged": tag, "site": "stackoverflow", "filter": "withbody",
                "pagesize": pagesize, "page": page, "order": "desc", "sort": "votes",
                "fromdate": 1672531200,          # 2023-01-01 起，保证时效性
            })
            url = "https://api.stackexchange.com/2.3/questions?" + qs
            d = get_json(url)
            if not d:
                continue
            quota = d.get("quota_remaining", quota)
            for it in d.get("items", []):
                qid = str(it.get("question_id"))
                if qid in seen:
                    continue
                seen.add(qid)
                title = clean(it.get("title"), 300)
                body = clean(it.get("body"))
                if len(body) < 60 or not is_ai(title + " " + body):
                    continue
                ts = int(it.get("creation_date") or 0)
                out.append({
                    "source": "Stack Overflow",
                    "native_id": qid,
                    "title": title,
                    "url": it.get("link"),
                    "text": body,
                    "date": time.strftime("%Y-%m-%d", time.gmtime(ts)) if ts else "",
                    "views": it.get("view_count") or 0,
                    "score": it.get("score") or 0,
                    "answers": it.get("answer_count") or 0,
                    "tags": it.get("tags") or [],
                    "query": tag,
                })
                if len(out) >= cap:
                    print("  B06 达到上限", cap)
                    return out, quota
            if not d.get("has_more"):
                break
        print(f"  B06 tag={tag:<32} 累计 {len(out)}")
    return out, quota


# --------------------------------------------------------------------------
# B07 Hacker News：AI 话题下的真实讨论评论（正文即需求/经验）
# --------------------------------------------------------------------------
HN_QUERIES = [
    "LLM", "AI agent", "RAG", "chatbot", "fine-tune", "AI customer service",
    "AI coding assistant", "speech to text", "OCR", "knowledge base",
    "prompt engineering", "embedding", "local LLM", "AI workflow", "LLM cost",
    "ChatGPT", "OpenAI API", "vector database", "AI startup", "copilot",
]


def collect_hackernews(pages=3, per=100, cap=1000):
    out, seen = [], set()
    for q in HN_QUERIES:
        for page in range(pages):
            qs = urllib.parse.urlencode({
                "query": q, "tags": "comment", "hitsPerPage": per, "page": page,
                "numericFilters": "created_at_i>1704067200",   # 2024-01-01 起
            })
            url = "https://hn.algolia.com/api/v1/search?" + qs
            d = get_json(url)
            if not d:
                continue
            for h in d.get("hits", []):
                oid = str(h.get("objectID"))
                if oid in seen:
                    continue
                seen.add(oid)
                text = clean(h.get("comment_text"))
                title = clean(h.get("story_title") or "", 300)
                if len(text) < 60 or not is_ai(title + " " + text):
                    continue
                sid = h.get("story_id")
                out.append({
                    "source": "Hacker News",
                    "native_id": oid,
                    "title": title or f"Hacker News 讨论 {oid}",
                    "url": f"https://news.ycombinator.com/item?id={oid}",
                    "story_id": str(sid) if sid else "",
                    "story_url": h.get("story_url") or "",
                    "text": text,
                    "date": (h.get("created_at") or "")[:10],
                    "score": 0,
                    "answers": 0,
                    "views": 0,
                    "query": q,
                })
                if len(out) >= cap:
                    print("  B07 达到上限", cap)
                    return out
        print(f"  B07 query={q:<24} 累计 {len(out)}")
    return out


HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"


def enrich_hn_story_metrics(items):
    """补齐每条评论所属讨论帖的点赞数/评论数，作为热度口径（诚实标注为所在帖热度）。"""
    sids = sorted({it["story_id"] for it in items if it.get("story_id")})
    print(f"  B07 待补热度的讨论帖 {len(sids)} 个")
    metrics = {}

    def fetch(sid):
        d = get_json(HN_ITEM.format(sid), tries=2)
        if not d:
            return sid, (0, 0)
        return sid, (int(d.get("score") or 0), int(d.get("descendants") or 0))

    with ThreadPoolExecutor(max_workers=16) as ex:
        for sid, (score, comments) in ex.map(fetch, sids):
            metrics[sid] = (score, comments)
    for it in items:
        s = metrics.get(it.get("story_id"), (0, 0))
        it["score"], it["answers"] = s[0], s[1]
    return items


# --------------------------------------------------------------------------
# B08 V2EX：中文开发者社区热帖
# --------------------------------------------------------------------------
V2EX_NODES = ["openai", "programmer", "qna", "python", "share", "ideas"]


def collect_v2ex(cap=350):
    out, seen = [], set()
    urls = ["https://www.v2ex.com/api/topics/hot.json"]
    urls += [f"https://www.v2ex.com/api/topics/show.json?node_name={n}" for n in V2EX_NODES]
    for url in urls:
        d = get_json(url)
        if not isinstance(d, list):
            continue
        for t in d:
            tid = str(t.get("id"))
            if tid in seen:
                continue
            seen.add(tid)
            title = clean(t.get("title"), 300)
            body = clean(t.get("content"))
            if len(body) < 40 or not is_ai(title + " " + body):
                continue
            ts = int(t.get("created") or 0)
            out.append({
                "source": "V2EX",
                "native_id": tid,
                "title": title,
                "url": t.get("url") or f"https://www.v2ex.com/t/{tid}",
                "text": body,
                "date": time.strftime("%Y-%m-%d", time.gmtime(ts / 1000)) if ts > 1e11
                        else (time.strftime("%Y-%m-%d", time.gmtime(ts)) if ts else ""),
                "views": 0,
                "score": 0,
                "answers": int(t.get("replies") or 0),
                "tags": [t.get("node", {}).get("name") or ""],
                "query": url.split("node_name=")[-1] if "node_name=" in url else "hot",
            })
            if len(out) >= cap:
                print("  B08 达到上限", cap)
                return out
        print(f"  B08 {url.split('?')[-1][:40]:<40} 累计 {len(out)}")
    return out


def dump(name, items, extra):
    path = os.path.join(RAW_DIR, name)
    payload = {
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "record_count": len(items),
        "note": "公开接口原始返回清洗后的条目；text 为接口正文，未做改写；url 可逐条溯源",
        **extra,
        "items": items,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"  -> {path}  ({len(items)} 条)")
    return path


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    t0 = time.time()

    print("[B06] Stack Overflow")
    so, quota = collect_stackoverflow()
    dump("B06_stackoverflow_raw.json", so, {
        "source": "Stack Overflow", "api": "https://api.stackexchange.com/2.3/questions",
        "tags": SO_TAGS, "quota_remaining": quota,
    })

    print("[B07] Hacker News")
    hn = collect_hackernews()
    enrich_hn_story_metrics(hn)
    dump("B07_hackernews_raw.json", hn, {
        "source": "Hacker News", "api": "https://hn.algolia.com/api/v1/search",
        "queries": HN_QUERIES,
    })

    print("[B08] V2EX")
    v2 = collect_v2ex()
    dump("B08_v2ex_raw.json", v2, {
        "source": "V2EX", "api": "https://www.v2ex.com/api/topics/{hot,show}.json",
        "nodes": V2EX_NODES,
    })

    print(f"\n合计新增候选 {len(so) + len(hn) + len(v2)} 条，用时 {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
