# -*- coding: utf-8 -*-
"""一键启动任务五系统：拉起 Flask 服务并自动打开浏览器。

用法：python start_app.py    或双击 启动服务.bat
环境变量：T5_PORT 改端口（默认 5000）；T5_NO_BROWSER=1 不自动开浏览器
"""
import os
import sys
import threading
import time
import urllib.request
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from app import app  # noqa: E402

PORT = int(os.environ.get("T5_PORT", "5000"))
URL = "http://127.0.0.1:%d" % PORT


def _open_browser():
    for _ in range(40):
        try:
            urllib.request.urlopen(URL + "/health", timeout=1).read()
            webbrowser.open(URL)
            return
        except Exception:
            time.sleep(0.5)


if os.environ.get("T5_NO_BROWSER") != "1":
    threading.Thread(target=_open_browser, daemon=True).start()

print("=" * 52)
print("  AI 应用场景机会评估系统")
print("  打开地址：%s" % URL)
print("  停止服务：按 Ctrl+C 或关闭本窗口")
print("=" * 52)
app.run(host="127.0.0.1", port=PORT, debug=False)
