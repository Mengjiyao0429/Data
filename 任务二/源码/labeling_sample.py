# -*- coding: utf-8 -*-
"""打印分层抽样待标注记录（供人工独立标注），输出 _labeling_sample.md。

抽取策略（覆盖题面要求的各类样本）：
  * 各来源分层（问答社区/开源项目/教程博客/资讯）
  * 规则判别正负样本分层 + 置信度边界带（0.40~0.60）全量
  * 已知"边界类型"记录（教程科普、广告、仅提 AI、有需求但 AI 非核心、非 AI 领域问题）
"""
from __future__ import annotations

import json
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "_labeling_sample.md")
N = 70

ev = {}
with open(os.path.join(HERE, "task2_evidence.jsonl"), encoding="utf-8") as f:
    for line in f:
        e = json.loads(line)
        ev[e["唯一标识"]] = e


def body_of(e):
    """取判别正文（快照 -> 前 260 字；降级通道的标题即可）。"""
    ref = os.path.join(ROOT, e["原快照"].replace("\\", os.sep)) if e.get("原快照") else ""
    if ref and os.path.exists(ref):
        s = open(ref, encoding="utf-8", errors="ignore").read()
        s = re.sub(r"\n*>\s*来源.*$", "", s, flags=re.S)
        s = re.sub(r"\s+", " ", s).strip()
        return s[:260]
    return e.get("判别文本", "")


items = list(ev.items())
random.seed(20261116)
picked = {}
by_src = {}
for k, e in items:
    by_src.setdefault(e["来源网站"], []).append(k)
quota = {"Stack Overflow": 18, "GitHub": 18, "CSDN": 10, "36氪": 8, "阿里云开发者社区": 8,
         "腾讯新闻": 6, "中国医药创新促进会": 5}
for src, q in quota.items():
    ks = by_src.get(src, [])
    picked.update({k: "来源分层" for k in random.sample(ks, min(q, len(ks)))})
# 边界带全量
for k, e in items:
    if 0.40 <= e["机会置信度"] <= 0.60:
        picked.setdefault(k, "置信度边界带")
# 负样本（含排除情形）补充
for k, e in items:
    if e["是否构成机会"] == 0 and e.get("判定规则", "").startswith("④"):
        picked.setdefault(k, "排除情形")

rows = sorted(picked.items(), key=lambda kv: kv[0])
lines = ["# 任务二人工标注抽样清单（待独立标注）\n",
         f"共 {len(rows)} 条。请逐条阅读正文，独立填写：人工是否机会(0/1)、人工功能类别、人工所属行业、备注。\n",
         "> 注意：不要参考右侧“规则初判”再照抄，规则初判仅用于事后对比。\n"]
for i, (k, why) in enumerate(rows, 1):
    e = ev[k]
    cat = e.get("分类依据", {})
    lines.append(f"### {i}. {k}（{e['来源网站']}，抽样理由：{why}）")
    lines.append(f"- 正文：{body_of(e)}")
    lines.append(f"- 规则初判：{e['是否构成机会']} / {e['机会置信度']}，{e['判定规则']}；"
                 f"分类：{cat.get('功能类别','')} / {cat.get('所属行业','')}")
    lines.append("")
open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("wrote", OUT, len(rows))