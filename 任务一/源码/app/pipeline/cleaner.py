# -*- coding: utf-8 -*-
"""任务一（2）文本清洗。

去除 URL 与渠道噪声、规范化空白与标点、处理缺失值；仅删除 ASCII 控制字符，
保留全部 Unicode 汉字与符号（不做 emoji 区间删除，避免误伤汉字）。
"""
import html
import re

URL_RE = re.compile(r"https?://[^\s，。；）)]+|www\.[^\s，。；）)]+")
WHITESPACE_RE = re.compile(r"[ \t\u00a0\u3000]+")
MULTI_NEWLINE_RE = re.compile(r"\n{2,}")
# 渠道噪声：#话题#、@用户、常见转发/来源标记
TOPIC_RE = re.compile(r"#([^#\n]{1,30})#")
AT_RE = re.compile(r"@[0-9A-Za-z一-龥_\-]{1,30}")
FORWARD_RE = re.compile(r"(转发微博|转发|repost|via\s*[0-9A-Za-z一-龥_]+)", re.IGNORECASE)
# 常见推广尾巴
PROMO_RE = re.compile(r"(扫码关注|点击关注|长按识别|关注公众号|二维码)[^\n]{0,30}")


def clean_text(text):
    """清洗单段文本，返回规范化字符串。"""
    text = text or ""
    text = html.unescape(text)  # 解码 HTML 实体，如 &#39; -> '、&quot; -> "、&gt; -> >
    text = URL_RE.sub(" ", text)
    text = TOPIC_RE.sub(r"\1", text)
    text = AT_RE.sub(" ", text)
    text = FORWARD_RE.sub(" ", text)
    text = PROMO_RE.sub(" ", text)
    # 仅删除 ASCII 控制字符（保留换行/制表），保留汉字与 emoji
    text = "".join(ch for ch in text if ch in "\n\t" or ord(ch) >= 32)
    text = WHITESPACE_RE.sub(" ", text)
    text = MULTI_NEWLINE_RE.sub("\n", text)
    return text.strip()


def clean_records(records):
    """对整批记录执行清洗，缺失正文以标题兜底。"""
    cleaned = []
    for rec in records:
        clean_title = clean_text(rec.get("title", ""))
        clean_content = clean_text(rec.get("raw_content", ""))
        if not clean_content:
            # 缺失值处理：正文为空时用标题兜底
            clean_content = clean_title
        item = dict(rec)
        item["clean_title"] = clean_title
        item["clean_content"] = clean_content
        cleaned.append(item)
    return cleaned
