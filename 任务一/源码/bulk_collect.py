# -*- coding: utf-8 -*-
"""批量扩容采集：在原有采集器基础上提升每页上限并启用翻页。

数据源（均属附件2官方来源）：
- GitHub Search API      : 24 个方向 × 4 页 × 100 条/页
- Stack Exchange API     : 12 个方向 × 2 页 × 100 条/页（withbody 取真实正文）
- CSDN 搜索接口          : 12 个中文关键词 × 2 页（真实浏览/点赞/评论数）
- RSS（量子位/IT之家/少数派/InfoQ中国）
国内站点（36氪/阿里云/腾讯/医药/互联网协会）复用已抓取的真实数据。

输出：data/collected_bulk/<source>.json，字段与既有采集口径一致。
"""
import json, os, re, sys, time
import urllib.parse, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "data", "collected_bulk")
os.makedirs(OUT, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
RECENT = "2024-01-01"
RECENT_TS = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp())

# ---------------- HTTP ----------------

def http_get(url, timeout=30, headers=None, proxy=None):
    h = {"User-Agent": UA, "Accept": "application/json, text/xml, */*"}
    if headers:
        h.update(headers)
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers=h)
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return -1, str(e).encode()


def parse_date(v):
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v, tz=timezone.utc).strftime("%Y-%m-%d")
    t = str(v).strip()
    if not t:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", t):
        return t[:10]
    if re.match(r"^\d{4}-\d{2}-\d{2}", t):
        return t[:10]
    try:
        return parsedate_to_datetime(t).strftime("%Y-%m-%d")
    except Exception:
        return t[:10]


def strip_html(text):
    # 搜索高亮标签 <em> 直接删除，避免中文标题被空格切断
    text = re.sub(r"</?em>", "", text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    import html as _h
    text = _h.unescape(text)
    # 中文之间的多余空格压缩
    text = re.sub(r"(\u4e00-\u9fff)\s+(\u4e00-\u9fff)", r"\1\2", text)
    return " ".join(text.split())

# ---------------- GitHub ----------------

GITHUB_QUERIES = [
    "llm application", "ai agent", "rag retrieval augmented", "chatbot",
    "ocr document", "speech recognition", "text to speech", "image segmentation",
    "object detection", "recommendation system", "knowledge graph", "mcp server",
    "workflow automation", "video understanding", "machine translation",
    "content moderation", "medical ai", "legal ai", "financial ai",
    "education ai tutor", "ecommerce ai", "customer service ai", "ai copilot",
    "synthetic data",
]


def collect_github(pages=4, per_page=100, target=3800, sleep_s=6.3):
    seen, out = set(), []
    for qi, q in enumerate(GITHUB_QUERIES, 1):
        for page in range(1, pages + 1):
            if len(out) >= target:
                print(f"[github] 已达目标 {target}")
                return out
            url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({
                "q": f"{q} created:>{RECENT}", "sort": "stars", "order": "desc",
                "per_page": per_page, "page": page})
            st, body = http_get(url)
            if st in (403, 429):
                print(f"[github] 限流(status={st})，等待 65s 后重试")
                time.sleep(65)
                st, body = http_get(url)
                if st != 200:
                    print(f"[github] 重试仍失败 status={st}，跳过 {q} p{page}")
                    continue
            if st != 200:
                print(f"[github] {q} p{page} status={st}")
                continue
            d = json.loads(body.decode("utf-8", "ignore"))
            items = d.get("items", [])
            if not items:
                break
            for it in items:
                link = it.get("html_url", "")
                if not link or link in seen:
                    continue
                seen.add(link)
                stars = it.get("stargazers_count", 0)
                out.append({
                    "source_name": "GitHub", "source_url": link,
                    "title": it.get("full_name", ""),
                    "raw_content": (it.get("description") or "").strip(),
                    "published_at": parse_date(it.get("created_at")),
                    "stars": stars,
                    "comments": it.get("open_issues_count", 0),
                    "views": None,
                    "heat_text": f"星标{stars}",
                })
            print(f"[github] {qi}/{len(GITHUB_QUERIES)} {q} p{page} -> 累计 {len(out)}")
            time.sleep(sleep_s)
    return out

# ---------------- Stack Overflow ----------------

SO_QUERIES = [
    "large language model", "openai api", "langchain", "rag vector database",
    "chatbot development", "speech recognition python", "object detection yolov8",
    "image classification", "recommendation system", "sentiment analysis",
    "machine translation", "ai agent tool calling",
]


def collect_so(pages=2, pagesize=100, sleep_s=1.0):
    seen, out = set(), []
    for qi, q in enumerate(SO_QUERIES, 1):
        for page in range(1, pages + 1):
            url = "https://api.stackexchange.com/2.3/search/advanced?" + urllib.parse.urlencode({
                "order": "desc", "sort": "votes", "q": q, "site": "stackoverflow",
                "pagesize": pagesize, "fromdate": RECENT_TS, "page": page,
                "filter": "withbody"})
            st, body = http_get(url)
            if st != 200:
                print(f"[so] {q} p{page} status={st}")
                continue
            d = json.loads(body.decode("utf-8", "ignore"))
            if d.get("backoff"):
                time.sleep(d["backoff"])
            quota = d.get("quota_remaining", 999)
            for it in d.get("items", []):
                link = it.get("link", "")
                if not link or link in seen:
                    continue
                seen.add(link)
                score = it.get("score", 0)
                ans = it.get("answer_count", 0)
                out.append({
                    "source_name": "Stack Overflow", "source_url": link,
                    "title": strip_html(it.get("title", "")),
                    "raw_content": strip_html(it.get("body", ""))[:4000],
                    "published_at": parse_date(it.get("creation_date")),
                    "stars": score, "comments": ans,
                    "views": it.get("view_count"),
                    "heat_text": f"点赞{score}；回答{ans}",
                })
            print(f"[so] {qi}/{len(SO_QUERIES)} {q} p{page} -> 累计 {len(out)} quota={quota}")
            if quota < 15:
                print("[so] 配额不足，停止")
                return out
            time.sleep(sleep_s)
    return out

# ---------------- CSDN ----------------

CSDN_KEYWORDS = [
    "大模型应用", "AI智能体", "RAG检索增强", "语音识别", "图像识别 OCR",
    "推荐系统", "知识图谱", "多模态大模型", "AI自动化工作流", "AI医疗",
    "AI法律", "AI教育",
]


def collect_csdn(pages=2, sleep_s=1.0):
    seen, out = set(), []
    for ki, kw in enumerate(CSDN_KEYWORDS, 1):
        for p in range(1, pages + 1):
            url = ("https://so.csdn.net/api/v3/search?q=" + urllib.parse.quote(kw) +
                   f"&t=blog&p={p}&s=0&tm=0&lv=-1&ft=0&l=&u=&ct=-1&pnt=-1&ry=-1"
                   "&ss=-1&dct=-1&vco=-1&cc=-1&sc=-1&sk=&c=0")
            st, body = http_get(url, headers={"Referer": "https://so.csdn.net/so/search"})
            if st != 200:
                print(f"[csdn] {kw} p{p} status={st}")
                continue
            try:
                d = json.loads(body.decode("utf-8", "ignore"))
            except Exception:
                continue
            items = (d.get("data") or {}).get("items") or d.get("result_vos") or []
            for it in items:
                raw_url = it.get("url", "")
                if not raw_url:
                    continue
                # 去掉搜索跟踪参数，保留可点击的真实文章地址
                clean_url = raw_url.split("?")[0]
                if clean_url in seen:
                    continue
                seen.add(clean_url)
                title = strip_html(it.get("title", ""))
                desc = strip_html(it.get("description") or it.get("digest") or "")
                views = it.get("viewcount") or it.get("view")
                digg = it.get("diggcount") or it.get("digg")
                cmt = it.get("commentcount") or it.get("comment")
                out.append({
                    "source_name": "CSDN", "source_url": clean_url,
                    "title": title, "raw_content": desc,
                    "published_at": parse_date(it.get("create_time_str") or it.get("create_time")),
                    "stars": digg, "comments": cmt, "views": views,
                    "heat_text": f"浏览{views}、点赞{digg}、评论{cmt}",
                })
            print(f"[csdn] {ki}/{len(CSDN_KEYWORDS)} {kw} p{p} -> 累计 {len(out)}")
            time.sleep(sleep_s)
    return out

# ---------------- RSS ----------------

RSS_FEEDS = [
    ("量子位", "https://www.qbitai.com/feed"),
    ("IT之家", "https://www.ithome.com/rss/"),
    ("少数派", "https://sspai.com/feed"),
    ("InfoQ中国", "https://www.infoq.cn/feed"),
]
AI_HINTS = ["ai", "人工智能", "大模型", "智能", "机器学习", "深度学习", "chatgpt",
            "gpt", "llm", "agent", "智能体", "生成式", "神经网络", "算法",
            "自动驾驶", "机器人", "ocr", "语音识别", "图像识别", "多模态", "aigc"]


def collect_rss(limit=120):
    out = []
    for name, feed in RSS_FEEDS:
        st, body = http_get(feed)
        if st != 200:
            print(f"[rss] {name} status={st}")
            continue
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            continue
        n = 0
        for it in root.findall(".//item")[:limit]:
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            summary = strip_html(it.findtext("description") or "")
            if summary in ("点击查看原文", "点击查看全文", "查看原文") or len(summary) < 8:
                summary = title
            if not link or not any(h in (title + summary).lower() for h in AI_HINTS):
                continue
            out.append({
                "source_name": name, "source_url": link, "title": title,
                "raw_content": summary, "published_at": parse_date(it.findtext("pubDate")),
                "stars": None, "comments": None, "views": None, "heat_text": "",
            })
            n += 1
        print(f"[rss] {name} -> {n} 条")
    return out


def save(name, data):
    p = os.path.join(OUT, name + ".json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"[save] {name}: {len(data)} 条 -> {p}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "github"):
        data = collect_github(); save("github", data)
    if which in ("all", "so"):
        data = collect_so(); save("so", data)
    if which in ("all", "csdn"):
        data = collect_csdn(); save("csdn", data)
    if which in ("all", "rss"):
        data = collect_rss(); save("rss", data)
