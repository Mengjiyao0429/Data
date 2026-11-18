# -*- coding: utf-8 -*-
"""任务五 模型调用层。

支持三种模式，均可用且成本可控：
  template  离线模板生成（不调用任何模型，零 API 成本，默认）
  openai    任意 OpenAI 兼容接口（硅基流动/智谱/DeepSeek/通义/Moonshot 等免费额度均可）
  ollama    本地模型（http://localhost:11434），零 API 费用

仅使用标准库 urllib，不引入额外 HTTP 依赖。
"""
import json
import time
import urllib.error
import urllib.request


class LLMError(Exception):
    pass


def _strip_code_fence(text):
    t = (text or "").strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def chat(messages, cfg, timeout=60):
    provider = (cfg.get("provider") or "template").strip().lower()
    if provider in ("template", "", "none"):
        return None
    if provider == "ollama":
        return _ollama(messages, cfg, timeout)
    return _openai(messages, cfg, timeout)


def _openai(messages, cfg, timeout):
    base = (cfg.get("base_url") or "").strip().rstrip("/")
    key = (cfg.get("api_key") or "").strip()
    if not base:
        raise LLMError("未填写 base_url")
    if not key:
        raise LLMError("未填写 api_key")
    url = base + "/chat/completions"
    payload = {
        "model": (cfg.get("model") or "gpt-4o-mini").strip(),
        "messages": messages,
        "temperature": float(cfg.get("temperature") or 0.4),
        "max_tokens": int(cfg.get("max_tokens") or 2000),
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:400]
        raise LLMError("HTTP %s：%s" % (e.code, body))
    except Exception as e:
        raise LLMError(str(e))
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise LLMError("返回结构异常：" + json.dumps(data, ensure_ascii=False)[:200])
    usage = data.get("usage") or {}
    return {"text": _strip_code_fence(text), "model": payload["model"], "provider": "openai",
            "tokens": usage.get("total_tokens", 0)}


def _ollama(messages, cfg, timeout):
    base = (cfg.get("base_url") or "http://localhost:11434").strip().rstrip("/")
    url = base + "/api/chat"
    payload = {
        "model": (cfg.get("model") or "qwen2.5:7b").strip(),
        "messages": messages,
        "stream": False,
        "options": {"temperature": float(cfg.get("temperature") or 0.4)},
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise LLMError("HTTP %s：%s" % (e.code, e.read().decode("utf-8", "ignore")[:300]))
    except Exception as e:
        raise LLMError(str(e))
    text = (data.get("message") or {}).get("content", "")
    if not text:
        raise LLMError("Ollama 返回为空")
    return {"text": _strip_code_fence(text), "model": payload["model"], "provider": "ollama",
            "tokens": data.get("eval_count", 0)}


def test(cfg, timeout=30):
    """连通性测试：返回 (ok, message, latency_ms)。"""
    started = time.time()
    try:
        res = chat(
            [{"role": "system", "content": "你是连通性测试助手。"},
             {"role": "user", "content": "只回复两个字：正常"}],
            cfg, timeout=timeout)
        ms = int((time.time() - started) * 1000)
        if res is None:
            return True, "当前为离线模板模式（不调用模型）", ms
        return True, "连通正常，模型 %s，返回：%s" % (res["model"], (res["text"] or "")[:40]), ms
    except LLMError as e:
        return False, str(e), int((time.time() - started) * 1000)
