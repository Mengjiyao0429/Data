# -*- coding: utf-8 -*-
"""任务五：AI 应用场景机会评估系统（后端服务）

启动：python 任务五/app.py
访问：http://127.0.0.1:5000
"""
import io
import os

from flask import Flask, Response, jsonify, render_template, request, send_file

from core import datastore, db, llm, proposal

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


@app.errorhandler(Exception)
def on_error(e):  # noqa: ANN001
    return jsonify(error=str(e)), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
