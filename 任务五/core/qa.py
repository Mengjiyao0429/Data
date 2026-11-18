# -*- coding: utf-8 -*-
"""任务五 问答咨询（RAG）：基于真实主题簇证据的检索增强问答。

不编造：先检索最相关的主题簇/证据记录，再用模板生成带溯源的回答；
如配置了 LLM，则把检索到的真实事实作为唯一依据交给模型作答（含提示词留痕）。
无 API Key 时完全离线可用——满足赛题"交互式查询或问答咨询"的形式要求。
"""
import json
import os
import re

from . import datastore, llm

STOP = set("的 了 和 与 是 在 有 为 对 及 或 这 那 个 我 你 他 怎么 什么 哪些 哪个 多少 请问 帮我 我想 查询 一下 关于 请 介绍 说明".split())


def _tokens(q):
    import jieba
    q = (q or "").lower()
    en = re.findall(r"[a-z][a-z0-9]{1,}", q)
    zh = [w.strip() for w in jieba.cut(q)
          if re.fullmatch(r"[\u4e00-\u9fff]{2,}", w.strip()) and w.strip() not in STOP]
    return list(dict.fromkeys(en + zh))


def _corpus():
    """从基线数据构建检索语料：主题簇 + 证据记录。"""
    items = []
    for c in datastore.clusters():
        items.append({"type": "cluster", "title": c["name"],
                      "text": f"{c['name']} {c['func']} {c['industry']} 价值分{c['score']} 优先级{c['priority']}",
                      "ref": f"{c['cid']} {c['name']}", "score": c["score"]})
        for m in c.get("evidence", [])[:6]:
            items.append({"type": "evidence", "title": m.get("title", ""),
                          "text": f"{m.get('title','')} {m.get('src','')} {' '.join(c['terms']) if 'terms' in c else c['name']}",
                          "ref": f"{m['batch']}-{m['id']} {m.get('src','')}", "score": c["score"]})
    return items


def retrieve(question, topk=5):
    terms = _tokens(question)
    # 意图识别：直接命中常见问法，避免停用词吃掉关键词
    q = (question or "").lower()
    intent = None
    if any(k in q for k in ("价值最高", "价值分最高", "优先级", "最高价值", "top", "排名", "推荐方向")):
        intent = "top"
    elif any(k in q for k in ("行业", "医疗", "教育", "金融", "电商", "法律", "能源", "零售")):
        intent = "industry"
    elif any(k in q for k in ("来源", "渠道", "github", "stack overflow", "hacker news", "csdn")):
        intent = "source"

    if intent == "top":
        top = sorted(datastore.clusters(), key=lambda c: -c["score"])[:topk]
        return [{"type": "cluster",
                 "title": c["name"],
                 "text": f"{c['cid']} {c['name']} 功能={c['func']} 行业={c['industry']} "
                         f"价值分={c['score']} 优先级={c['priority']} 来源数={len(c['sources'])}",
                 "ref": f"{c['cid']} {c['name']}", "score": c["score"]} for c in top]

    scored = []
    for it in _corpus():
        hay = it["text"].lower()
        hit = sum(1 for t in terms if t in hay)
        if hit:
            # 命中数为主，簇价值分为次（轻微加权）
            scored.append((hit + min(1.0, it["score"] / 100.0) * 0.1, it))
    scored.sort(key=lambda x: -x[0])
    return [it for _, it in scored[:topk]]


def answer(question, cfg=None, use_llm=True):
    q = (question or "").strip()
    if not q:
        return {"answer": "请输入咨询问题，例如：'哪些主题簇价值最高？' 或 '医疗相关的机会有哪些？'", "sources": []}
    hits = retrieve(q)
    if not hits:
        return {"answer": "未在本地分析结果中找到相关的主题簇或证据记录，请尝试功能类别、行业、来源或主题关键词。", "sources": []}

    facts = [{"依据": h["ref"], "摘要": h["text"][:180]} for h in hits]
    srcs = list(dict.fromkeys(h["ref"] for h in hits))

    llm_text = None
    if use_llm and cfg and (cfg.get("provider") or "template").lower() != "template":
        try:
            msgs = [
                {"role": "system", "content": "你是数据分析助手。只能依据用户提供的真实事实回答，不得编造编号、数字或来源；答不出就说本地数据未覆盖。"},
                {"role": "user", "content": f"问题：{q}\n\n真实事实（JSON）：\n{json.dumps(facts, ensure_ascii=False)}\n\n请给出简明回答，并标注依据编号。"},
            ]
            r = llm.chat(msgs, cfg, timeout=int(cfg.get("timeout") or 60))
            if r:
                llm_text = r["text"]
        except Exception:  # noqa: BLE001
            llm_text = None

    if llm_text:
        text = llm_text + "\n\n（以上回答由模型基于本地检索事实生成，依据：" + "、".join(srcs[:5]) + "）"
        mode = "llm"
    else:
        lines = [f"在本地分析结果中检索到 {len(hits)} 条相关依据：", ""]
        for i, h in enumerate(hits, 1):
            lines.append(f"{i}. 【{h['type'] == 'cluster' and '主题簇' or '证据'}】{h['ref']}")
            lines.append(f"   {h['text'][:160]}")
        lines.append("")
        lines.append("提示：可在「机会选取」中查看完整簇详情，或在「策划案库」生成立项策划案。")
        text = "\n".join(lines)
        mode = "retrieval"

    return {"answer": text, "sources": srcs, "mode": mode, "question": q}
