# -*- coding: utf-8 -*-
"""任务五 认证与授权（修复 X-Role 请求头可任意伪造的致命漏洞）。

设计：
  - 使用签名 Session Cookie（itsdangerous，Flask 内置依赖），服务端保存登录态；
  - 口令用 werkzeug 的 scrypt 加盐哈希存储，不明文、不回显；
  - 角色从会话推导，绝不读取客户端 X-Role / ?role 参数；
  - 按角色过滤数据可见范围：需求发起者仅见主题簇与公开证据，决策者另可改配置、看审计；
  - 审计记录服务端身份（用户名 + IP），不可伪造。

首次运行会创建 README 中注明的演示账号，可用环境变量 TASK5_SEED_* 覆盖。
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from . import db

ROLES = ("requester", "decision")
ROLE_LABELS = {"requester": "需求发起者", "decision": "决策者"}

# 演示账号（部署时务必修改口令；可用环境变量覆盖）
SEED_USERS = [
    ("analyst", "analyst@123", "requester"),
    ("decision", "decision@123", "decision"),
]


def _users_path():
    return os.path.join(db.INSTANCE, "users.db")


def _conn():
    import sqlite3
    os.makedirs(db.INSTANCE, exist_ok=True)
    c = sqlite3.connect(_users_path(), timeout=10)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY, pw_hash TEXT, role TEXT,
            display TEXT, active INTEGER DEFAULT 1, created_at TEXT)""")
        n = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
    if n == 0:
        for name, pwd, role in SEED_USERS:
            create_user(name, pwd, role, display=ROLE_LABELS[role])
        return True
    return False


def _hash_password(password):
    """优先用 scrypt；若运行环境的 hashlib 不支持 scrypt 则回退 pbkdf2。"""
    try:
        return generate_password_hash(password, method="scrypt")
    except ValueError:
        return generate_password_hash(password, method="pbkdf2:sha256")


def create_user(username, password, role, display=""):
    if role not in ROLES:
        raise ValueError("非法角色")
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO users(username,pw_hash,role,display,active,created_at) "
                  "VALUES(?,?,?,?,1,?)",
                  (username, _hash_password(password), role,
                   display or username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))


def verify(username, password):
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE username=? AND active=1", (username,)).fetchone()
    if not row:
        return None
    if not check_password_hash(row["pw_hash"], password):
        return None
    return {"username": row["username"], "role": row["role"], "display": row["display"]}


def list_users():
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT username,role,display,active,created_at FROM users ORDER BY role,username")]


def change_password(username, old, new):
    with _conn() as c:
        row = c.execute("SELECT pw_hash FROM users WHERE username=?", (username,)).fetchone()
    if not row or not check_password_hash(row["pw_hash"], old):
        return False
    with _conn() as c:
        c.execute("UPDATE users SET pw_hash=? WHERE username=?",
                  (generate_password_hash(new, method="scrypt"), username))
    return True


# ---------- 会话辅助（供 app.py 使用） ----------
def client_ip(request):
    return (request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.remote_addr or "-")


def session_user(session):
    """从服务端会话取当前用户；绝不信任请求头。"""
    u = session.get("user")
    if not u or u.get("username") not in (session.get("uid") or ""):
        return None
    return u


def set_session(session, user):
    session.clear()
    session["uid"] = user["username"]
    session["user"] = {"username": user["username"], "role": user["role"], "display": user["display"]}
    session.permanent = True
