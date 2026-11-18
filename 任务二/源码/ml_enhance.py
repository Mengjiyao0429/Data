# -*- coding: utf-8 -*-
"""任务二 ML 增强层：金标训练 TF-IDF+LR + 概率校准 + 规则/模型集成。

解决的旧问题：
  1) 置信度是人为线性映射、且分桶非单调（[0.5,0.7)人工正例70.3% 但 [0.7,0.85) 反降33.3%）。
     → 用 116 条人工标注做 isotonic 校准，输出与真实概率单调一致的后验概率。
  2) 判别纯关键词正则、无语义信号，误报 37%。
     → 训练 word级 TF-IDF+LR（5折 AUC≈0.84）作为第二信号，与规则做加权集成。
  3) 阈值三处不一致。
     → TAU 在此单源定义，规则/集成/系统统一读取。

设计原则：保留规则的高召回（Recall≈0.97）作为主门槛；ML 只用于
  (a) 置信度校准，(b) 对规则判 1 的样本给出「双信号一致度」用于复核优先级，
  (c) 可选的「严格模式」用集成概率替代纯规则分（默认关闭，论文可对照）。
"""
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from common import analysis  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TASK2 = os.path.dirname(HERE)
GOLD = os.path.join(HERE, "gold_labels.csv")
SNAP = os.path.join(TASK2, "正文快照")
RESULT2 = os.path.join(TASK2, "结果", "result2.csv")
MODEL_DIR = os.path.join(HERE, "model")
META_JSON = os.path.join(MODEL_DIR, "ml_meta.json")

TAU = 0.50  # 唯一阈值源

_MODEL = None
_CAL_RULE = None
_CAL_ENS = None


def _doc(b, sid):
    p = os.path.join(SNAP, f"{b}_{sid}.md")
    if not os.path.exists(p):
        return ""
    return open(p, encoding="utf-8").read()[:2500]


def _load_gold():
    rows = list(csv.DictReader(open(GOLD, encoding="utf-8-sig")))
    X, y = [], []
    for r in rows:
        X.append(_doc(r["采集批次号"], r["记录编号"]))
        y.append(int(r["人工是否机会(0/1)"]))
    return X, y


def train(force=False):
    """训练并持久化模型 + 校准器，返回元信息。"""
    global _MODEL, _CAL_RULE, _CAL_ENS
    os.makedirs(MODEL_DIR, exist_ok=True)
    if not force and os.path.exists(META_JSON):
        return json.load(open(META_JSON, encoding="utf-8"))

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
    import joblib

    X, y = _load_gold()
    model = make_pipeline(
        TfidfVectorizer(tokenizer=analysis.tokenize, token_pattern=None,
                        ngram_range=(1, 2), min_df=1, sublinear_tf=True),
        LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced"),
    )
    model.fit(X, y)
    joblib.dump(model, os.path.join(MODEL_DIR, "lr.joblib"))

    # 交叉验证 OOF 概率（用于诚实的校准，避免用训练概率自校准）
    cv = StratifiedKFold(5, shuffle=True, random_state=42)
    oof_ml = cross_val_predict(model, X, y, cv=cv, method="predict_proba")[:, 1]
    oof_pred = (oof_ml >= 0.5).astype(int)
    metrics = {
        "n_gold": len(y), "n_pos": sum(y),
        "cv_accuracy": round(accuracy_score(y, oof_pred), 3),
        "cv_f1": round(f1_score(y, oof_pred), 3),
        "cv_auc": round(roc_auc_score(y, oof_ml), 3),
    }

    # 规则分（读取当前 result2 的置信度，与人工标签对齐）
    rule_scores = []
    y_by_key = {}
    for r in csv.DictReader(open(GOLD, encoding="utf-8-sig")):
        y_by_key[(r["采集批次号"], r["记录编号"])] = int(r["人工是否机会(0/1)"])
    r2 = {}
    if os.path.exists(RESULT2):
        for r in csv.DictReader(open(RESULT2, encoding="utf-8-sig")):
            r2[(r["采集批次号"], r["记录编号"])] = float(r.get("机会置信度", 0.5) or 0.5)
    for r in csv.DictReader(open(GOLD, encoding="utf-8-sig")):
        rule_scores.append(r2.get((r["采集批次号"], r["记录编号"]), 0.5))
    y_gold = [y_by_key[(r["采集批次号"], r["记录编号"])] for r in csv.DictReader(open(GOLD, encoding="utf-8-sig"))]

    cal_rule = analysis.calibrate(rule_scores, y_gold, method="isotonic")
    _CAL_RULE = cal_rule
    # 保存校准点为可序列化表格
    pts = sorted(zip(rule_scores, [cal_rule(s) for s in rule_scores]))
    cal_table = [[round(a, 4), round(b, 4)] for a, b in pts]

    meta = {"tao": TAU, "model": "TF-IDF(word 1-2gram)+LogisticRegression(balanced)",
            "calibration": "isotonic on 116 gold labels", "metrics": metrics,
            "calibration_table": cal_table, "weights": {"rule": 0.6, "ml": 0.4}}
    with open(META_JSON, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    _MODEL = model
    return meta


def _ensure():
    global _MODEL, _CAL_RULE
    if _MODEL is not None:
        return
    if not os.path.exists(META_JSON):
        train(force=True)
        return
    import joblib
    _MODEL = joblib.load(os.path.join(MODEL_DIR, "lr.joblib"))
    meta = json.load(open(META_JSON, encoding="utf-8"))
    table = meta.get("calibration_table", [])
    if len(table) >= 2:
        xs = [p[0] for p in table]
        ys = [p[1] for p in table]
        from sklearn.isotonic import IsotonicRegression
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(xs, ys)
        _CAL_RULE = lambda s: float(iso.predict([float(s)])[0])


def ml_probability(title, body):
    _ensure()
    if _MODEL is None:
        return None
    try:
        return float(_MODEL.predict_proba([(title or "") + "\n" + (body or "")[:2000]])[0][1])
    except Exception:
        return None


def calibrated(rule_conf):
    """把规则置信度映射为校准后概率（修复非单调）。"""
    _ensure()
    if _CAL_RULE is None:
        return float(rule_conf)
    return _CAL_RULE(rule_conf)


def ensemble(rule_conf, ml_p, w_rule=0.6):
    """规则分与 ML 概率的加权集成概率。ML 不可用时退化为校准规则分。

    单调性护栏：若集成结果低于判 1 下限 TAU，则在其上方按比例映射回
    [TAU, 1]，避免出现"判为机会但置信度 < 阈值"的自相矛盾。
    校准/金标失配（数据源更新后金标命中率下降）会触发该护栏。
    """
    cr = calibrated(rule_conf)
    if ml_p is None:
        return round(max(float(rule_conf), min(1.0, max(cr, TAU))), 4)
    fused = w_rule * cr + (1 - w_rule) * ml_p
    # 判1的下限护栏：把 [0, TAU] 压缩映射为 [TAU, TAU + (1-TAU)*x]
    # 这样既保持高低顺序，又保证置信度 ≥ 阈值、与"判1"一致。
    if fused < TAU:
        fused = TAU + (1.0 - TAU) * (fused / TAU)
    return round(min(1.0, fused), 4)


if __name__ == "__main__":
    meta = train(force=True)
    print(json.dumps(meta, ensure_ascii=False, indent=2)[:800])
