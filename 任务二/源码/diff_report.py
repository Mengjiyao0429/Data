# -*- coding: utf-8 -*-
"""生成"修订前 → 修订后"逐条差异表，供人工复核。

用法（在修订前后各运行一次 result2_exporter.py，用 --snapshot 保存当时结果）：
    python diff_report.py --snapshot before   # 修订前
    python diff_report.py --snapshot after    # 修订后
    python diff_report.py                     # 生成 task2_修订差异表.csv
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R2 = os.path.join(HERE, "result2.csv")
EV = os.path.join(HERE, "task2_evidence.jsonl")
GOLD = os.path.join(HERE, "gold_labels.csv")
SNAP = os.path.join(HERE, "_snapshot_{}.json")
OUT = os.path.join(HERE, "task2_修订差异表.csv")


def load_current():
    ev = {}
    with open(EV, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            ev[e["唯一标识"]] = e
    rows = {}
    with open(R2, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            k = f"{r['采集批次号']}-{r['记录编号']}"
            e = ev.get(k, {})
            rows[k] = {
                "key": k,
                "src": e.get("来源网站", ""),
                "text": e.get("判别文本", "")[:70],
                "new": r["是否构成机会"],
                "conf": r["机会置信度"],
                "func": r["功能类别"],
                "ind": r["所属行业"],
                "rule": e.get("判定规则", ""),
            }
    return rows


def main():
    rows = load_current()
    if "--snapshot" in sys.argv:
        tag = sys.argv[sys.argv.index("--snapshot") + 1]
        json.dump(rows, open(SNAP.format(tag), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print("snapshot ->", SNAP.format(tag), len(rows))
        return
    before = json.load(open(SNAP.format("before"), encoding="utf-8"))
    after = json.load(open(SNAP.format("after"), encoding="utf-8"))
    gold = {}
    if os.path.exists(GOLD):
        with open(GOLD, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                gold[r["唯一标识"]] = r
    out = []
    for k, a in after.items():
        b = before.get(k, {})
        changed_flag = b.get("new") != a["new"]
        changed_lab = (b.get("func"), b.get("ind")) != (a["func"], a["ind"])
        if not (changed_flag or changed_lab):
            continue
        g = gold.get(k, {})
        out.append({
            "唯一标识": k,
            "来源": a["src"],
            "正文摘要": a["text"],
            "修订前": "1" if b.get("new") == "1" else "0",
            "修订后": "1" if a["new"] == "1" else "0",
            "修订后置信度": a["conf"],
            "修订前功能/行业": f"{b.get('func', '')}/{b.get('ind', '')}",
            "修订后功能/行业": f"{a['func']}/{a['ind']}",
            "修订后判定规则": a["rule"],
            "人工标注": g.get("人工是否机会(0/1)", ""),
            "人工备注": g.get("判定依据备注", ""),
        })
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()) if out else ["唯一标识"])
        w.writeheader()
        w.writerows(out)
    flipped = [o for o in out if o["修订前"] != o["修订后"]]
    print(f"差异 {len(out)} 条（其中判定翻转 {len(flipped)} 条）-> {OUT}")


if __name__ == "__main__":
    main()