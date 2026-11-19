# -*- coding: utf-8 -*-
"""任务一（1）多源数据采集。

对接附件2中经实测可用的真实数据源：
- GitHub Search API（开源项目，真实星标/创建日期/描述）
- Stack Exchange API（Stack Overflow 真实问答，投票/回答数/日期）
- RSS（少数派、IT之家、量子位、InfoQ中国 真实文章，日期/链接/摘要）

全部记录保留真实来源链接，字段统一对齐，供后续清洗与去重。
"""
import json
import re
import time
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from app import config

# 近期时间窗（对齐赛题“近期热门内容”）：2024-01-01 起
RECENT_SINCE = "2024-01-01"
_RECENT_FROMDATE = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp())

# ISO 8601 日期时间（如 2026-03-02T15:30:00Z），精确匹配避免误判 RFC2822 中的 GMT
ISO_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")

# GitHub 检索方向（围绕 AI 应用场景，覆盖多行业/功能）
GITHUB_QUERIES = [
    "ai customer service",
    "medical ai assistant",
    "legal ai contract",
    "ai agent framework",
    "speech recognition",
    "ocr document ai",
    "recommendation system",
    "ai workflow automation",
]

# Stack Overflow 检索方向
STACKOVERFLOW_QUERIES = [
    "AI chatbot",
    "LLM application",
    "speech recognition",
    "object detection",
    "recommendation system",
    "sentiment analysis",
    "machine translation",
    "process automation",
]

# RSS 仅保留与 AI 相关的文章（标题/摘要命中任一即保留）
AI_HINTS = [
    "ai", "人工智能", "大模型", "智能", "机器学习", "深度学习", "chatgpt", "gpt",
    "llm", "agent", "智能体", "生成式", "神经网络", "算法", "自动驾驶", "机器人",
    "ocr", "语音识别", "图像识别", "大语言模型", "多模态", "aigc",
]

# RSS 通用占位摘要（无实际正文），命中时以真实标题作为内容
_RSS_PLACEHOLDER = {
    "点击查看原文", "点击查看全文", "查看原文", "查看全文", "点击查看", "详情请点击",
}


def _http_get(url, timeout=None):
    """发起 GET，返回 (status, bytes)。"""
    req = urllib.request.Request(url, headers={
        "User-Agent": config.USER_AGENT,
        "Accept": "application/json, text/xml, application/rss+xml, */*",
    })
    timeout = timeout or config.REQUEST_TIMEOUT
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _parse_date(value):
    """ISO / RFC2822 / Unix 时间戳统一转 YYYY-MM-DD。"""
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d")
    text = str(value).strip()
    if not text:
        return ""
    # ISO 8601（正则精确匹配，避免 RFC2822 的 "GMT" 含字母 T 被误判）
    if ISO_DATETIME_RE.match(text):
        return text[:10]
    # RFC 2822
    try:
        return parsedate_to_datetime(text).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        pass
    # 常见格式回退，保证异常输入也能尽量解析
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text[:10]


def collect_github(verbose=False):
    """采集 GitHub 真实开源项目。"""
    records = []
    seen = set()
    for q in GITHUB_QUERIES:
        url = (
            "https://api.github.com/search/repositories?"
            + urllib.parse.urlencode({
                "q": f"{q} created:>{RECENT_SINCE}",
                "sort": "stars", "order": "desc",
                "per_page": config.GITHUB_PER_PAGE,
            })
        )
        status, body = _http_get(url)
        if status in (403, 429):
            if verbose:
                print(f"[github] 限流，停止后续查询（已得 {len(records)} 条）")
            break
        if status != 200:
            if verbose:
                print(f"[github] {q} 状态 {status}")
            continue
        data = json.loads(body.decode("utf-8"))
        for it in data.get("items", []):
            link = it.get("html_url", "")
            if not link or link in seen:
                continue
            seen.add(link)
            stars = it.get("stargazers_count", 0)
            records.append({
                "source_name": "GitHub",
                "source_url": link,
                "title": it.get("full_name", ""),
                "raw_content": (it.get("description") or "").strip(),
                "published_at": _parse_date(it.get("created_at")),
                "stars": stars,
                "comments": it.get("open_issues_count", 0),
                "views": None,
                "heat_text": f"星标{stars}",
            })
        time.sleep(1.0)  # 尊重未鉴权 10 req/min 限制
    return records


def collect_stackoverflow(verbose=False):
    """采集 Stack Overflow 真实问答。"""
    records = []
    seen = set()
    for q in STACKOVERFLOW_QUERIES:
        url = (
            "https://api.stackexchange.com/2.3/search/advanced?"
            + urllib.parse.urlencode({
                "order": "desc", "sort": "relevance", "q": q,
                "site": "stackoverflow", "pagesize": config.STACKOVERFLOW_PAGESIZE,
                "fromdate": _RECENT_FROMDATE,
            })
        )
        status, body = _http_get(url)
        if status != 200:
            if verbose:
                print(f"[stackoverflow] {q} 状态 {status}")
            continue
        data = json.loads(body.decode("utf-8"))
        if data.get("backoff"):
            time.sleep(data["backoff"])
        for it in data.get("items", []):
            link = it.get("link", "")
            if not link or link in seen:
                continue
            seen.add(link)
            score = it.get("score", 0)
            answers = it.get("answer_count", 0)
            records.append({
                "source_name": "Stack Overflow",
                "source_url": link,
                "title": it.get("title", ""),
                "raw_content": it.get("title", ""),
                "published_at": _parse_date(it.get("creation_date")),
                "stars": score,
                "comments": answers,
                "views": it.get("view_count"),
                "heat_text": f"点赞{score}；回答{answers}",
            })
        time.sleep(0.4)
    return records


def _strip_html(text):
    """粗略去除 HTML 标签与多余空白。"""
    out, in_tag = [], False
    for ch in text or "":
        if ch == "<":
            in_tag = True
            continue
        if ch == ">":
            in_tag = False
            continue
        if not in_tag:
            out.append(ch)
    text = "".join(out)
    for entity, repl in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                         ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        text = text.replace(entity, repl)
    return " ".join(text.split())


def _is_ai_related(title, summary):
    blob = f"{title} {summary}".lower()
    return any(h.lower() in blob for h in AI_HINTS)


def collect_rss(source_name, feed_url, verbose=False):
    """采集单个 RSS 源的真实文章，仅保留 AI 相关项。"""
    status, body = _http_get(feed_url)
    if status != 200:
        if verbose:
            print(f"[rss] {source_name} 状态 {status}")
        return []
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        if verbose:
            print(f"[rss] {source_name} 解析失败 {e}")
        return []
    records = []
    for it in root.findall(".//item")[: config.RSS_LIMIT]:
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        summary = _strip_html(it.findtext("description") or "")
        # 占位/过短摘要：以真实标题作为内容，避免多条正文相同被误去重
        if summary in _RSS_PLACEHOLDER or len(summary) < 8:
            summary = title
        if not link or not _is_ai_related(title, summary):
            continue
        pub = _parse_date(it.findtext("pubDate"))
        records.append({
            "source_name": source_name,
            "source_url": link,
            "title": title,
            "raw_content": summary,
            "published_at": pub,
            "stars": None,
            "comments": None,
            "views": None,
            "heat_text": "",
        })
    return records


def collect_all(verbose=True):
    """采集全部可用源，返回原始记录列表。"""
    all_records = []

    gh = collect_github(verbose=verbose)
    if verbose:
        print(f"GitHub 采集 {len(gh)} 条")
    all_records.extend(gh)

    so = collect_stackoverflow(verbose=verbose)
    if verbose:
        print(f"Stack Overflow 采集 {len(so)} 条")
    all_records.extend(so)

    # 延迟导入避免循环依赖
    from app import sources
    for name, cfg_ in sources.COLLECTIBLE.items():
        if cfg_["method"] != "rss":
            continue
        rss = collect_rss(name, cfg_["feed"], verbose=verbose)
        if verbose:
            print(f"{name} 采集 {len(rss)} 条（AI 相关）")
        all_records.extend(rss)

    return all_records
