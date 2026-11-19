# -*- coding: utf-8 -*-
"""任务五 数据访问层：把任务一～四的结果装配成系统所需的数据结构。

数据来源（只读，全部为仓库内真实结果）：
  任务一/结果/result1.csv + 任务一/结果/text/*.md
  任务二/结果/result2.csv
  任务三/结果/result3.csv
  任务四/结果/result4_中间指标.json
"""
import csv
import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEXT_DIR = os.path.join(BASE, "任务一", "结果", "text")


def _read_csv(rel):
    with open(os.path.join(BASE, rel), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _to_int(s):
    try:
        return int(float((s or "").strip()))
    except (TypeError, ValueError):
        return 0


def _title_of(fn):
    p = os.path.join(TEXT_DIR, fn)
    if fn and os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            first = f.readline().strip()
        return first.lstrip("# ").strip()
    return ""


_CACHE = {}


def load():
    """首次调用时装配数据，之后复用。"""
    if _CACHE:
        return _CACHE

    rows = _read_csv(os.path.join("任务一", "结果", "result1.csv"))
    rec = {}
    for r in rows:
        fn = os.path.basename((r.get("内容") or "").replace("/", os.sep))
        rec[(r["采集批次号"], r["记录编号"])] = {
            "batch": r["采集批次号"],
            "id": r["记录编号"],
            "src": r["来源网站名称"],
            "link": r.get("来源链接", ""),
            "time": (r.get("发布时间") or "").strip(),
            "heat": sum(_to_int(r.get(k)) for k in ("星标数", "浏览数", "点赞数", "评论数", "收藏数")),
            "title": _title_of(fn) or (r["采集批次号"] + "-" + r["记录编号"]),
        }

    r2 = _read_csv(os.path.join("任务二", "结果", "result2.csv"))
    r3 = _read_csv(os.path.join("任务三", "结果", "result3.csv"))
    with open(os.path.join(BASE, "任务四", "结果", "result4_中间指标.json"), encoding="utf-8") as f:
        r4 = json.load(f)
    r4map = {c["主题簇编号"]: c for c in r4.get("clusters", [])}

    total = len(rec)
    opp = sum(1 for x in r2 if x["是否构成机会"] == "1")
    src_count, batch_stat = {}, {}
    for x in rec.values():
        src_count[x["src"]] = src_count.get(x["src"], 0) + 1
        batch_stat.setdefault(x["batch"], {"records": 0, "opps": 0})["records"] += 1
    for x in r2:
        if x["是否构成机会"] == "1":
            batch_stat.setdefault(x["采集批次号"], {"records": 0, "opps": 0})["opps"] += 1

    clusters = []
    for row in r3:
        members, src_map = [], {}
        for item in row["簇内机会记录"].split("；"):
            item = item.strip()
            if not item:
                continue
            batch, rid = item.split("-", 1)
            r = rec.get((batch, rid))
            if not r:
                continue
            members.append({
                "batch": batch, "id": rid, "title": r["title"], "src": r["src"],
                "link": r["link"], "time": r["time"], "heat": r["heat"],
            })
            src_map[r["src"]] = src_map.get(r["src"], 0) + 1
        s4 = r4map.get(row["主题簇编号"], {})
        clusters.append({
            "cid": row["主题簇编号"],
            "name": row["主题簇名称"],
            "func": row["功能类别"],
            "industry": row["所属行业"],
            "size": int(row["簇内机会记录数"]),
            "score": float(s4.get("机会价值分", 0)),
            "priority": int(s4.get("priority", 0)),
            "dims": {
                "src": float(s4.get("多源指向度", 0)),
                "size": float(s4.get("记录规模", 0)),
                "biz": float(s4.get("商业信号", 0)),
            },
            "n_batch": int(s4.get("n_batch", 0)),
            "sources": [{"name": k, "count": v} for k, v in sorted(src_map.items(), key=lambda t: -t[1])],
            "members": members,
            "evidence": sorted(members, key=lambda m: -m["heat"])[:10],
        })
    clusters.sort(key=lambda c: c["priority"])

    meta = {
        "total_records": total,
        "total_opportunities": opp,
        "opp_rate": round(opp / total * 100, 1) if total else 0,
        "clusters": len(clusters),
        "batches": sorted({x["batch"] for x in rec.values()}),
        "sources": [{"name": k, "count": v} for k, v in sorted(src_count.items(), key=lambda t: -t[1])],
        "batch_stats": [
            {"batch": b, "records": batch_stat[b]["records"], "opps": batch_stat[b]["opps"],
             "rate": round(batch_stat[b]["opps"] / batch_stat[b]["records"] * 100, 1)}
            for b in sorted(batch_stat)
        ],
        "weights": r4.get("weights", [0.35, 0.35, 0.30]),
        "max_heat": r4.get("max_heat"),
    }

    _CACHE.update({
        "meta": meta,
        "clusters": clusters,
        "by_id": {c["cid"]: c for c in clusters},
        "source_names": [s["name"] for s in meta["sources"]],
    })
    return _CACHE


def meta():
    return load()["meta"]


def clusters():
    return load()["clusters"]


def get(cid):
    return load()["by_id"].get(cid)


def search(q="", industry="", func="", min_src=0):
    q = (q or "").strip().lower()
    out = []
    for c in clusters():
        if industry and c["industry"] != industry:
            continue
        if func and c["func"] != func:
            continue
        if len(c["sources"]) < int(min_src or 0):
            continue
        if q:
            hay = (c["cid"] + " " + c["name"] + " " + c["func"] + " " + c["industry"]).lower()
            if q not in hay:
                continue
        out.append(c)
    return out


def filters():
    return {
        "industries": sorted({c["industry"] for c in clusters()}),
        "funcs": sorted({c["func"] for c in clusters()}),
    }
