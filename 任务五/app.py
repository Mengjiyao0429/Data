# -*- coding: utf-8 -*-
"""任务五：AI 应用场景机会评估系统（后端服务）

启动：python 任务五/app.py
访问：http://127.0.0.1:5000
"""
import io
import os
import threading

from flask import Flask, Response, jsonify, render_template, request, send_file

from core import batchstore, datastore, db, llm, pipeline, proposal, sources

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            static_folder=os.path.join(BASE, "static"),
            template_folder=os.path.join(BASE, "templates"))
app.config["JSON_AS_ASCII"] = False

db.init()


def role():
    r = (request.headers.get("X-Role") or request.args.get("role") or "requester").strip().lower()
    return r if r in ("requester", "decision") else "requester"


def summary(c):
    return {
        "cid": c["cid"], "name": c["name"], "func": c["func"], "industry": c["industry"],
        "size": c["size"], "score": c["score"], "priority": c["priority"], "dims": c["dims"],
        "sources": c["sources"], "n_batch": c["n_batch"],
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify(ok=True, service="task5-opportunity-system", clusters=len(datastore.clusters()))


@app.get("/api/bootstrap")
def bootstrap():
    return jsonify(
        meta=datastore.meta(),
        clusters=[summary(c) for c in datastore.clusters()],
        filters=datastore.filters(),
        settings=db.public_settings(),
        stats=db.stats(),
    )


@app.get("/api/clusters")
def api_clusters():
    items = datastore.search(
        request.args.get("q", ""), request.args.get("industry", ""),
        request.args.get("func", ""), request.args.get("min_src", 0))
    return jsonify(items=[summary(c) for c in items])


@app.get("/api/clusters/<cid>")
def api_cluster(cid):
    c = datastore.get(cid)
    if not c:
        return jsonify(error="主题簇不存在"), 404
    return jsonify(c)


@app.post("/api/select")
def api_select():
    data = request.get_json(silent=True) or {}
    c = datastore.get(data.get("cid"))
    if not c:
        return jsonify(error="主题簇不存在"), 404
    sid = db.add_selection(c["cid"], c["name"], c["score"], c["priority"], role(), data.get("note", ""))
    db.audit(role(), "select_opportunity", c["cid"])
    return jsonify(ok=True, id=sid, cid=c["cid"])


@app.get("/api/selections")
def api_selections():
    return jsonify(items=db.list_selections())


@app.post("/api/proposal")
def api_proposal():
    data = request.get_json(silent=True) or {}
    c = datastore.get(data.get("cid"))
    if not c:
        return jsonify(error="主题簇不存在"), 404
    cfg = db.get_settings()
    res = proposal.generate(c, datastore.meta(), cfg)
    pid = db.add_proposal(c["cid"], c["name"], res["mode"], res["model"],
                          res["markdown"], res["tokens"], role())
    db.audit(role(), "generate_proposal", "%s/%s" % (c["cid"], res["mode"]))
    return jsonify(ok=True, id=pid, cid=c["cid"], mode=res["mode"], model=res["model"],
                   tokens=res["tokens"], chars=len(res["markdown"]), markdown=res["markdown"])


@app.get("/api/proposals")
def api_proposals():
    return jsonify(items=db.list_proposals())


@app.get("/api/proposals/<int:pid>")
def api_proposal_get(pid):
    p = db.get_proposal(pid)
    if not p:
        return jsonify(error="策划案不存在"), 404
    return jsonify(p)


@app.get("/api/proposals/<int:pid>/download")
def api_proposal_download(pid):
    p = db.get_proposal(pid)
    if not p:
        return jsonify(error="策划案不存在"), 404
    fmt = (request.args.get("fmt") or "md").lower()
    base = "立项策划案_%s_%s" % (p["cid"], p["cluster_name"])
    if fmt == "docx":
        try:
            buf = proposal.markdown_to_docx(p["markdown"])
        except Exception as e:  # noqa: BLE001
            return jsonify(error="Word 导出失败：%s" % e), 500
        return send_file(
            buf, as_attachment=True, download_name=base + ".docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    data = io.BytesIO(p["markdown"].encode("utf-8"))
    return send_file(data, as_attachment=True, download_name=base + ".md",
                     mimetype="text/markdown")


@app.get("/api/settings")
def api_settings_get():
    return jsonify(db.public_settings())


@app.post("/api/settings")
def api_settings_post():
    if role() != "decision":
        return jsonify(error="仅决策者可修改系统配置"), 403
    cfg = db.save_settings(request.get_json(silent=True) or {})
    db.audit(role(), "update_settings", cfg.get("provider"))
    return jsonify(ok=True, settings=db.public_settings())


@app.post("/api/test")
def api_test():
    cfg = db.get_settings()
    ok, msg, ms = llm.test(cfg)
    db.audit(role(), "test_llm", "%s %s" % (cfg.get("provider"), "ok" if ok else "fail"))
    return jsonify(ok=ok, message=msg, ms=ms)


@app.get("/api/audit")
def api_audit():
    with db._conn() as c:  # noqa: SLF001
        rows = [dict(r) for r in c.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 50")]
    return jsonify(items=rows)


# ==================== 需求驱动的批次 ====================

def _run_batch_async(bid, requirement):
    try:
        pipeline.preload()
        summary = pipeline.run_batch(bid, requirement, log=lambda *a: None)
        db.finish_batch(bid, summary)
    except Exception as e:  # noqa: BLE001
        db.finish_batch(bid, {}, str(e))
    finally:
        batchstore.invalidate(bid)


@app.get("/api/sources")
def api_sources():
    return jsonify(
        items=[{"key": k, "label": sources.SOURCE_LABELS.get(k, k)} for k in sources.ADAPTERS],
        proxy=sources.proxy_url(),
        default=["stackoverflow", "hackernews", "github"],
    )


@app.post("/api/requirements")
def api_requirements():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify(error="请填写需求关键词（例如“AI 编程助手 代码生成”）"), 400
    srcs = [s for s in (data.get("sources") or []) if s in sources.ADAPTERS]
    if not srcs:
        return jsonify(error="请至少勾选一个采集来源"), 400
    try:
        target = max(50, min(2000, int(data.get("target") or 500)))
    except (TypeError, ValueError):
        target = 500

    bid = pipeline.next_batch_id()
    db.create_batch(bid, query, srcs, target, data.get("note", ""))
    db.audit(role(), "create_requirement", "%s %s %s" % (bid, query, ",".join(srcs)))
    threading.Thread(target=_run_batch_async,
                     args=(bid, {"query": query, "sources": srcs, "target": target,
                                 "note": data.get("note", "")}), daemon=True).start()
    return jsonify(ok=True, bid=bid, status="running")


@app.get("/api/batches")
def api_batches():
    return jsonify(items=db.list_batches(), next_batch=pipeline.next_batch_id())


@app.get("/api/batches/<bid>")
def api_batch(bid):
    info = db.get_batch(bid)
    if not info:
        return jsonify(error="批次不存在"), 404
    data = batchstore.load_batch(bid) if info.get("status") == "done" else None
    body = {"info": info, "status": info.get("status")}
    if data:
        body["meta"] = data["meta"]
        body["clusters"] = [summary(c) for c in data["clusters"]]
    return jsonify(body)


@app.get("/api/batches/<bid>/clusters/<cid>")
def api_batch_cluster(bid, cid):
    data = batchstore.load_batch(bid)
    if not data:
        return jsonify(error="批次结果尚未生成"), 404
    c = data["by_id"].get(cid)
    if not c:
        return jsonify(error="主题簇不存在"), 404
    return jsonify(c)


@app.get("/api/batches/<bid>/records")
def api_batch_records(bid):
    workdir = os.path.join(pipeline.BATCH_ROOT, bid)
    r1 = os.path.join(workdir, "result1.csv")
    if not os.path.exists(r1):
        return jsonify(error="批次结果尚未生成"), 404
    import csv
    with open(r1, encoding="utf-8-sig") as f:
        rows1 = list(csv.DictReader(f))
    r2 = os.path.join(workdir, "result2.csv")
    judged = {}
    if os.path.exists(r2):
        with open(r2, encoding="utf-8-sig") as f:
            judged = {(r["采集批次号"], r["记录编号"]): r for r in csv.DictReader(f)}

    q = (request.args.get("q") or "").strip().lower()
    only_opp = request.args.get("only_opp") in ("1", "true")
    src = (request.args.get("source") or "").strip()
    limit = min(500, max(1, int(request.args.get("limit") or 50)))
    offset = max(0, int(request.args.get("offset") or 0))

    textdir = os.path.join(workdir, "text")
    items = []
    for r in rows1:
        j = judged.get((r["采集批次号"], r["记录编号"]), {})
        fn = os.path.basename((r.get("内容") or "").replace("/", os.sep))
        tp = os.path.join(textdir, fn)
        title, body = "", ""
        if os.path.exists(tp):
            raw = open(tp, encoding="utf-8", errors="ignore").read()
            title = raw.split("\n", 1)[0].lstrip("# ").strip()
            body = raw.split("## 正文", 1)[-1].strip()
        if only_opp and j.get("是否构成机会") != "1":
            continue
        if src and r["来源网站名称"] != src:
            continue
        if q and q not in (title + " " + body + " " + r["来源网站名称"]).lower():
            continue
        items.append({
            "batch": r["采集批次号"], "id": r["记录编号"], "source": r["来源网站名称"],
            "link": r["来源链接"], "time": r["发布时间"], "snapshot": r["内容"],
            "title": title, "snippet": body[:180],
            "is_opp": j.get("是否构成机会"), "conf": j.get("机会置信度"),
            "func": j.get("功能类别"), "industry": j.get("所属行业"),
        })
    total = len(items)
    return jsonify(total=total, items=items[offset:offset + limit], offset=offset, limit=limit)


@app.post("/api/batches/<bid>/proposal")
def api_batch_proposal(bid):
    data = request.get_json(silent=True) or {}
    cid = data.get("cid")
    blob = batchstore.load_batch(bid)
    if not blob:
        return jsonify(error="批次结果尚未生成"), 404
    c = blob["by_id"].get(cid)
    if not c:
        return jsonify(error="主题簇不存在"), 404
    cfg = db.get_settings()
    res = proposal.generate(c, blob["meta"], cfg)
    pid = db.add_proposal(c["cid"], c["name"], res["mode"], res["model"],
                          res["markdown"], res["tokens"], role(), bid=bid)
    db.audit(role(), "generate_proposal", "%s/%s/%s" % (bid, c["cid"], res["mode"]))
    return jsonify(ok=True, id=pid, cid=c["cid"], bid=bid, mode=res["mode"],
                   model=res["model"], tokens=res["tokens"], chars=len(res["markdown"]),
                   markdown=res["markdown"])


@app.get("/api/batches/<bid>/report")
def api_batch_report(bid):
    p = os.path.join(pipeline.BATCH_ROOT, bid, "批次报告.md")
    if not os.path.exists(p):
        return jsonify(error="批次报告尚未生成"), 404
    return send_file(p, as_attachment=True, download_name="批次报告_%s.md" % bid,
                     mimetype="text/markdown")


@app.get("/api/batches/<bid>/file")
def api_batch_file(bid):
    kind = (request.args.get("name") or "").strip()
    allowed = {"result1.csv", "result2.csv", "result3.csv", "result4.csv", "原始记录.json"}
    if kind not in allowed:
        return jsonify(error="不允许的文件"), 400
    p = os.path.join(pipeline.BATCH_ROOT, bid, kind)
    if not os.path.exists(p):
        return jsonify(error="文件不存在"), 404
    return send_file(p, as_attachment=True, download_name="%s_%s" % (bid, kind))



@app.errorhandler(Exception)
def on_error(e):  # noqa: ANN001
    return jsonify(error=str(e)), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
