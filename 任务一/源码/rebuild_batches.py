"""按用户要求重建任务一结果：B01（SO top100 + GitHub）、B02（浏览器国内源）、B03（CSDN 50）。

数据来源：
- 当前 result1.csv（GBK，用户已删减）确定保留清单；
- raw_B01.json 提供正文/日期/热度；
- browser_csdn.json 提供 CSDN 50 条。
输出：data/B01/results/result1.csv（utf-8-sig），data/B01/text/ 正文快照。
"""
import csv
import json
import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
COLLECTED = os.path.join(BASE, "data", "collected")
BATCH_DIR = os.path.join(BASE, "data", "B01")
RESULT_DIR = os.path.join(BATCH_DIR, "results")
TEXT_DIR = os.path.join(BATCH_DIR, "text")

CURRENT_CSV = os.path.join(RESULT_DIR, "result1.csv")
BROWSER_SOURCES = {"36氪", "阿里云开发者社区", "腾讯新闻", "中国医药创新促进会"}


def load_current():
    """读取当前 result1（自动识别 utf-8-sig / gbk），返回保留行列表。"""
    raw = open(CURRENT_CSV, "rb").read()
    for enc in ("utf-8-sig", "gbk"):
        try:
            text = raw.decode(enc)
            import io
            return list(csv.DictReader(io.StringIO(text)))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("无法识别 result1.csv 编码")


def build_records():
    # 当前 result1 的 URL 集合用于尊重用户删减（仅过滤 raw_B01 中的源）
    keep_urls = {r["来源链接"].split("?")[0] for r in load_current()}
    raw = json.load(open(os.path.join(COLLECTED, "raw_B01.json"), encoding="utf-8"))

    b01_so, b01_gh, b02 = [], [], []
    for rr in raw:
        url = rr["source_url"].split("?")[0]
        if url not in keep_urls:
            continue
        rec = {
            "source_name": rr["source_name"],
            "url": rr["source_url"],
            "title": rr["title"],
            "body": rr.get("raw_content") or rr["title"],
            "date": rr["published_at"],
            "heat_text": rr.get("heat_text") or "",
        }
        name = rr["source_name"]
        if name == "Stack Overflow":
            b01_so.append((rr.get("stars", 0), rr.get("comments", 0), rec))
        elif name == "GitHub":
            b01_gh.append(rec)
        elif name in BROWSER_SOURCES:
            b02.append(rec)

    # SO 按点赞、回答数降序取 top100
    b01_so.sort(key=lambda x: (x[0], x[1]), reverse=True)
    so_recs = [x[2] for x in b01_so[:100]]

    # B03：CSDN（独立来源，不经过 raw_B01 过滤）
    csdn = json.load(open(os.path.join(COLLECTED, "browser_csdn.json"), encoding="utf-8"))
    b03 = []
    for r in csdn:
        heat = (f"浏览{r.get('views','0')}、点赞{r.get('like','0')}、"
                f"评论{r.get('comment','0')}、收藏{r.get('favs','0')}")
        b03.append({
            "source_name": "CSDN",
            "url": r["url"],
            "title": r["title"],
            "body": r["raw_text"],
            "date": r["date"],
            "heat_text": heat,
        })

    grouped = [("B01", so_recs + b01_gh), ("B02", b02), ("B03", b03)]
    return grouped


def write_outputs(grouped):
    # 重建正文快照目录
    if os.path.exists(TEXT_DIR):
        shutil.rmtree(TEXT_DIR)
    os.makedirs(TEXT_DIR, exist_ok=True)
    os.makedirs(RESULT_DIR, exist_ok=True)

    header = ["采集批次号", "记录编号", "来源网站名称", "来源链接", "内容",
              "发布时间", "热度指标（如浏览数、点赞数、讨论数等）"]
    out_path = os.path.join(RESULT_DIR, "result1.csv")
    total = 0
    counts = {}
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for batch, recs in grouped:
            counts[batch] = len(recs)
            for j, rec in enumerate(recs, start=1):
                total += 1
                rec_id = f"S{j:05d}"  # 每批次独立编号
                file_name = f"{batch}_{rec_id}.md"
                rel = os.path.join("text", file_name)
                snap = os.path.join(TEXT_DIR, file_name)
                with open(snap, "w", encoding="utf-8") as sf:
                    sf.write(f"# {rec['title']}\n\n"
                             f"- 来源：{rec['source_name']} {rec['url']}\n"
                             f"- 发布时间：{rec['date']}\n"
                             f"- 热度：{rec['heat_text']}\n\n## 正文\n\n{rec['body']}\n")
                writer.writerow([batch, rec_id, rec["source_name"], rec["url"],
                                 rel, rec["date"], rec["heat_text"]])
    return total, counts


def main():
    grouped = build_records()
    total, counts = write_outputs(grouped)
    print("===== 重建完成 =====")
    print("各批次条数:", counts)
    print("总计:", total)
    from collections import Counter
    dist = Counter()
    for _, recs in grouped:
        for r in recs:
            dist[r["source_name"]] += 1
    print("来源分布:", dict(dist))


if __name__ == "__main__":
    main()
