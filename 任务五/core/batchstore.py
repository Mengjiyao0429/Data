# -*- coding: utf-8 -*-
"""任务五 · 批次结果读取层

把 `批次/<bid>/result1..4.csv` 装配成与基线看板相同的结构（meta / clusters / by_id），
这样前端只需要一套渲染逻辑，基线批次与新建批次都能显示。
"""
import csv
import json
import os

from . import db

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BATCH_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "批次")

_CACHE = {}


def _to_int(s):
    try:
        return int(float((s or "").strip()))
    except (TypeError, ValueError):
        return 0


def _read_csv(p):
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _title(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.readline().strip().lstrip("# ").strip()


def load_batch(bid):
    """读取一个批次的全部结果；文件缺失时返回 None。"""
    workdir = os.path.join(BATCH_ROOT, bid)
    r1p = os.path.join(workdir, "result1.csv")
    if not os.path.exists(r1p):
        return None
    stamp = os.path.getmtime(r1p)
    if bid in _CACHE and _CACHE[bid]["stamp"] == stamp:
        return _CACHE[bid]

    info = db.get_batch(bid) or {}
    rows1 = _read_csv(r1p)
    rows2 = _read_csv(os.path.join(workdir, "result2.csv"))
    rows3 = _read_csv(os.path.join(workdir, "result3.csv"))
    rows4 = _read_csv(os.path.join(workdir, "result4.csv"))

    rec = {}
    for r in rows1:
        fn = os.path.basename((r.get("内容") or "").replace("/", os.sep))
        rec[(r["采集批次号"], r["记录编号"])] = {
            "batch": r["采集批次号"], "id": r["记录编号"], "src": r["来源网站名称"],
            "link": r.get("来源链接", ""), "time": (r.get("发布时间") or "").strip(),
            "heat": sum(_to_int(r.get(k)) for k in ("星标数", "浏览数", "点赞数", "评论数", "收藏数")),
            "title": _title(os.path.join(workdir, "text", fn)) or (r["采集批次号"] + "-" + r["记录编号"]),
            "snapshot": r.get("内容", ""),
        }
    judged = {(r["采集批次号"], r["记录编号"]): r for r in rows2}
    v4 = {r["主题簇编号"]: r for r in rows4}
    mid = {}
    mp = os.path.join(workdir, "result4_中间指标.json")
    if os.path.exists(mp):
        with open(mp, encoding="utf-8") as f:
            mid = {c["主题簇编号"]: c for c in json.load(f).get("clusters", [])}

    clusters = []
    for row in rows3:
        members, src_map = [], {}
        for item in (row.get("簇内机会记录") or "").split("；"):
            item = item.strip()
            if not item or "-" not in item:
                continue
            b, rid = item.split("-", 1)
            r = rec.get((b, rid))
            if not r:
                continue
            j = judged.get((b, rid), {})
            members.append({**r, "conf": j.get("机会置信度", ""),
                            "func": j.get("功能类别", ""), "industry": j.get("所属行业", "")})
            src_map[r["src"]] = src_map.get(r["src"], 0) + 1
        s4 = v4.get(row["主题簇编号"], {})
        m4 = mid.get(row["主题簇编号"], {})
        clusters.append({
            "cid": row["主题簇编号"], "name": row["主题簇名称"],
            "func": row["功能类别"], "industry": row["所属行业"],
            "size": int(float(row["簇内机会记录数"] or 0)),
            "score": float(s4.get("机会价值分") or 0),
            "priority": int(float(s4.get("优先级") or 0)),
            "dims": {"src": float(m4.get("多源指向度") or 0),
                     "size": float(m4.get("记录规模") or 0),
                     "biz": float(m4.get("商业信号") or 0)}, "sources": [{"name": k, "count": v} for k, v in
                                      sorted(src_map.items(), key=lambda t: -t[1])],
            "members": members,
            "evidence": sorted(members, key=lambda m: -m["heat"])[:10],
            "n_batch": 1,
        })
    clusters.sort(key=lambda c: c["priority"])

    src_count = {}
    for r in rec.values():
        src_count[r["src"]] = src_count.get(r["src"], 0) + 1
    opp_n = sum(1 for r in rows2 if r["是否构成机会"] == "1")
    meta = {
        "total_records": len(rows1), "total_opportunities": opp_n,
        "opp_rate": round(opp_n / len(rows1) * 100, 1) if rows1 else 0,
        "clusters": len(clusters),
        "batches": [bid],
        "sources": [{"name": k, "count": v} for k, v in sorted(src_count.items(), key=lambda t: -t[1])],
        "batch_stats": [{"batch": bid, "records": len(rows1), "opps": opp_n,
                         "rate": round(opp_n / len(rows1) * 100, 1) if rows1 else 0}],
        "weights": [0.35, 0.35, 0.30],
        "max_heat": None,
        "batch": info,
    }
    data = {"stamp": stamp, "meta": meta, "clusters": clusters,
            "by_id": {c["cid"]: c for c in clusters}, "info": info}
    _CACHE[bid] = data
    return data


def invalidate(bid=None):
    if bid:
        _CACHE.pop(bid, None)
    else:
        _CACHE.clear()
