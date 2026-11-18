# -*- coding: utf-8 -*-
"""任务五 持久化层：SQLite 存储设置、机会选取、策划案与审计日志。

成本考虑：单文件 SQLite，无独立数据库服务，零运维成本。
"""
import json
import os
import sqlite3
from datetime import datetime

INSTANCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "instance")
DB_PATH = os.path.join(INSTANCE, "app.db")

DEFAULT_SETTINGS = {
    "provider": "template",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "api_key": "",
    "temperature": "0.4",
    "max_tokens": "2000",
    "timeout": "60",
}


def _conn():
    os.makedirs(INSTANCE, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
        CREATE TABLE IF NOT EXISTS selections(
            id INTEGER PRIMARY KEY AUTOINCREMENT, cid TEXT, cluster_name TEXT,
            score REAL, priority INTEGER, role TEXT, note TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS proposals(
            id INTEGER PRIMARY KEY AUTOINCREMENT, cid TEXT, cluster_name TEXT,
            mode TEXT, model TEXT, markdown TEXT, chars INTEGER, tokens INTEGER,
            role TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, role TEXT, action TEXT, detail TEXT);
        CREATE TABLE IF NOT EXISTS batches(
            bid TEXT PRIMARY KEY, query TEXT, sources TEXT, target INTEGER, note TEXT,
            status TEXT, created_at TEXT, finished_at TEXT, records INTEGER, opportunities INTEGER,
            clusters INTEGER, top_cid TEXT, top_name TEXT, top_score REAL, elapsed REAL,
            silhouette REAL, error TEXT);
        """)
        # 兼容旧库：补 bid 列（失败说明已存在）
        for tbl in ("proposals", "selections"):
            try:
                c.execute("ALTER TABLE %s ADD COLUMN bid TEXT DEFAULT ''" % tbl)
            except sqlite3.OperationalError:
                pass
    for k, v in DEFAULT_SETTINGS.items():
        if get_setting(k) is None:
            set_setting(k, v)


# ---------- settings ----------
def get_setting(k, default=None):
    with _conn() as c:
        row = c.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
    return row["v"] if row else default


def set_setting(k, v):
    with _conn() as c:
        c.execute("INSERT INTO settings(k,v) VALUES(?,?) "
                  "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))


def get_settings():
    out = dict(DEFAULT_SETTINGS)
    with _conn() as c:
        for row in c.execute("SELECT k,v FROM settings"):
            out[row["k"]] = row["v"]
    return out


def save_settings(patch):
    allowed = set(DEFAULT_SETTINGS)
    for k, v in (patch or {}).items():
        if k in allowed and v is not None:
            set_setting(k, v)
    return get_settings()


def public_settings():
    s = get_settings()
    key = s.get("api_key", "")
    s["api_key_set"] = bool(key)
    s["api_key"] = (key[:4] + "****" + key[-4:]) if len(key) >= 10 else ("****" if key else "")
    return s


# ---------- selections ----------
def add_selection(cid, name, score, priority, role, note=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO selections(cid,cluster_name,score,priority,role,note,created_at) "
            "VALUES(?,?,?,?,?,?,?)", (cid, name, score, priority, role, note, ts))
        return cur.lastrowid


def list_selections():
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM selections ORDER BY id DESC").fetchall()]


# ---------- proposals ----------
def add_proposal(cid, name, mode, model, markdown, tokens, role, bid=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO proposals(cid,cluster_name,mode,model,markdown,chars,tokens,role,created_at,bid) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (cid, name, mode, model, markdown, len(markdown), int(tokens or 0), role, ts, bid))
        return cur.lastrowid


def list_proposals(bid=None):
    with _conn() as c:
        if bid:
            rows = c.execute(
                "SELECT id,cid,cluster_name,mode,model,chars,tokens,role,created_at,bid "
                "FROM proposals WHERE bid=? ORDER BY id DESC", (bid,)).fetchall()
        else:
            rows = c.execute(
                "SELECT id,cid,cluster_name,mode,model,chars,tokens,role,created_at,bid "
                "FROM proposals ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def get_proposal(pid):
    with _conn() as c:
        row = c.execute("SELECT * FROM proposals WHERE id=?", (pid,)).fetchone()
    return dict(row) if row else None


# ---------- batches ----------
def create_batch(bid, query, sources, target, note="", status="running"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            "INSERT INTO batches(bid,query,sources,target,note,status,created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (bid, query, json.dumps(sources, ensure_ascii=False), int(target), note, status, ts))
    return bid


def finish_batch(bid, summary, error=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    top = summary.get("top") or {}
    with _conn() as c:
        c.execute(
            "UPDATE batches SET status=?, finished_at=?, records=?, opportunities=?, clusters=?, "
            "top_cid=?, top_name=?, top_score=?, elapsed=?, silhouette=?, error=? WHERE bid=?",
            ("failed" if error else "done", ts, summary.get("records"), summary.get("opportunities"),
             summary.get("clusters"), top.get("cid"), top.get("name"), top.get("score"),
             summary.get("elapsed"), summary.get("silhouette"), error, bid))


def list_batches():
    with _conn() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM batches ORDER BY created_at DESC, bid DESC")]
    for r in rows:
        try:
            r["sources"] = json.loads(r.get("sources") or "[]")
        except ValueError:
            r["sources"] = []
    return rows


def get_batch(bid):
    with _conn() as c:
        row = c.execute("SELECT * FROM batches WHERE bid=?", (bid,)).fetchone()
    if not row:
        return None
    r = dict(row)
    try:
        r["sources"] = json.loads(r.get("sources") or "[]")
    except ValueError:
        r["sources"] = []
    return r


# ---------- audit ----------
def audit(role, action, detail=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute("INSERT INTO audit(ts,role,action,detail) VALUES(?,?,?,?)",
                  (ts, role, action, str(detail)[:500]))


def stats():
    with _conn() as c:
        s = c.execute("SELECT COUNT(*) n FROM selections").fetchone()["n"]
        p = c.execute("SELECT COUNT(*) n FROM proposals").fetchone()["n"]
        t = c.execute("SELECT COALESCE(SUM(tokens),0) n FROM proposals").fetchone()["n"]
    return {"selections": s, "proposals": p, "tokens": t}
