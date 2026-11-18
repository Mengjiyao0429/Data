# -*- coding: utf-8 -*-
"""任务五：构建仪表盘数据 + 生成立项策划案

输入（全部为仓库内真实结果文件）：
  - 任务一/结果/result1.csv
  - 任务二/结果/result2.csv
  - 任务三/结果/result3.csv
  - 任务四/结果/result4_中间指标.json
  - 任务一/结果/text/*.md（取标题与链接）

输出：
  - 仪表盘/data/dashboard_data.js   （window.DASHBOARD_DATA = {...}，可直接双击 index.html 打开）
  - 示例立项策划案/*.md              （14 个主题簇各一份，可直接作为决策产出附件）
"""
import csv
import json
import os
import re
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DASH = os.path.join(ROOT, "任务五", "仪表盘")
DATA_DIR = os.path.join(DASH, "data")
PROPOSAL_DIR = os.path.join(ROOT, "任务五", "示例立项策划案")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PROPOSAL_DIR, exist_ok=True)

# ---------------------------------------------------------------- 文案映射（按附件1 的 16 功能 / 30 行业）
USERS = {
    "电商": "电商平台运营团队、平台商家与客服团队",
    "零售": "连锁零售的门店运营与商品管理团队",
    "医疗": "医院信息科、临床科室与医技人员",
    "教育": "院校教务与教学管理部门、一线教师",
    "人力资源": "企业 HR、招聘与培训团队",
    "法律": "律所、企业法务与合规部门",
    "物流": "物流企业调度、仓储与配送运营团队",
    "金融": "银行/保险的运营、风控与客服团队",
    "保险": "保险公司的核保、理赔与客服团队",
    "制造": "制造企业生产、质检与设备运维团队",
    "能源": "能源企业生产运行与安全管理团队",
    "政务": "政务服务中心与业务科室",
    "科研": "高校与科研院所的科研团队",
    "娱乐": "内容平台的运营、审核与创作者服务团队",
    "媒体": "媒体机构的内容生产与审核团队",
    "建筑": "设计院、施工单位与物业运营团队",
    "房地产": "房企营销与物业运营团队",
    "交通": "出行平台与交通运营管理方",
    "汽车": "车企的研发、售后与车主服务团队",
    "通信": "运营商网络运维与客服团队",
    "农业": "农业合作社与种植/养殖管理方",
    "旅游": "文旅景区与旅行社的运营团队",
    "餐饮": "连锁餐饮的门店与供应链运营团队",
    "游戏": "游戏研发与运营团队",
    "安防": "安防运营与监控中心",
    "环保": "环保企业的监测与合规团队",
    "化工": "化工企业的生产与安全管理团队",
    "纺织": "纺织服装企业的设计与生产团队",
    "其他": "有明确业务场景的中小企业/机构业务团队",
}

PAINS = {
    "推荐系统": "内容或商品与用户匹配效率低，人工运营难以规模化；新用户冷启动与长尾需求覆盖不足。",
    "知识检索": "知识分散在文档、工单与代码中，检索依赖关键词、命中率低，经验难以复用。",
    "智能体编排": "多步骤业务流程需人工串联，跨系统操作重复、易出错，缺少统一的编排与审计。",
    "对话问答": "客服与咨询人力压力大，回答口径不一致，夜间与高峰时段响应不及时。",
    "图像识别": "图像质检与识别依赖人工目检，效率低、标准不统一，难以规模化。",
    "语音处理": "语音内容的转写与结构化依赖人工，成本高、时效差。",
    "语义分析": "海量文本靠人工阅读归类，舆情、合同与用户反馈处理慢。",
    "自动化流程": "重复性流程占用大量人力，跨系统流转缺乏统一编排与可观测性。",
    "数据挖掘": "业务数据已沉淀但缺乏洞察，异常与风险发现滞后。",
    "翻译转写": "多语种内容处理依赖人工，术语一致性与交付时效难保证。",
    "文本生成": "文案、报告与摘要等内容生产耗时，质量与风格不稳定。",
    "多模态融合": "图文、视频等多模态信息割裂，检索与理解成本高。",
    "审核审查": "合规审核依赖人工逐条比对，漏检与标准漂移风险高。",
    "预测分析": "需求、销量与风险预测依赖经验，缺乏模型化支撑与回测。",
    "视频理解": "视频内容的检索与审核依赖人工抽看，效率低、覆盖不全。",
    "搜索匹配": "站内搜索的召回与排序不准，长尾需求无法满足。",
}

TECH = {
    "推荐系统": ["召回层：内容向量（Embedding）+ 协同过滤双路召回", "排序层：LR/GBDT 或轻量 DNN 精排，规则兜底", "冷启动：基于内容标签与热度的补全策略"],
    "知识检索": ["文档解析与切片（PDF/网页/工单）", "向量化（bge/m3e 类模型）+ 向量库（FAISS/Milvus）", "混合检索（BM25 + 向量）+ 重排 + 引用溯源"],
    "智能体编排": ["工具注册与函数调用（Function Calling）", "任务规划（ReAct / Plan-Execute）+ 状态机", "重试、超时与人工确认节点、全链路审计"],
    "对话问答": ["意图识别 + RAG 检索增强", "大模型生成 + 话术与知识约束", "多轮上下文管理 + 人工兜底转接"],
    "图像识别": ["预训练视觉模型（YOLO/ViT 类）微调", "数据标注与增强、难例回流", "服务端/边缘推理 + 阈值复核"],
    "语音处理": ["ASR（Whisper/Paraformer 类）转写", "说话人分离与时间戳对齐", "结构化抽取 + 人工校对"],
    "语义分析": ["文本分类/信息抽取（BERT 或微调 LLM）", "规则校验与置信度过滤", "批量处理与结果看板"],
    "自动化流程": ["工作流引擎编排", "API / 浏览器自动化执行", "异常重试、幂等与审计日志"],
    "数据挖掘": ["特征工程与数据治理", "统计/机器学习模型（异常检测、聚类）", "可视化与告警联动"],
    "翻译转写": ["机器翻译 + 术语库约束", "格式与版式还原", "人工审校 + 质量抽检"],
    "文本生成": ["提示词模板 + RAG 事实约束", "大模型生成与风格控制", "事实校验 + 人工终审"],
    "多模态融合": ["图文/视频统一编码", "跨模态对齐（CLIP 类）", "联合检索与结果融合"],
    "审核审查": ["规则引擎 + 模型判别双通道", "风险分级与抽样复核", "闭环反馈与规则迭代"],
    "预测分析": ["时序/回归模型与特征构建", "外部变量引入与回测", "滚动预测与阈值告警"],
    "视频理解": ["抽帧/关键帧提取", "视觉 + 语音联合理解", "结构化索引与检索"],
    "搜索匹配": ["倒排索引 + 向量召回", "排序模型与 Query 改写", "离线评估指标与线上 A/B"],
}

WBS = [
    ("T1", "场景与数据确认", "明确目标用户、业务流程与数据边界，完成合规评估", "2 周"),
    ("T2", "基线能力接入", "选择成熟模型/API 与向量库，跑通端到端最小链路", "2 周"),
    ("T3", "核心功能开发", "实现核心功能与业务系统对接，补齐权限与审计", "4 周"),
    ("T4", "评测与调优", "建立评测集与指标，完成准确率、时延与成本调优", "2 周"),
    ("T5", "试点上线", "小范围试点，收集反馈并修复问题", "2 周"),
    ("T6", "推广与运维", "扩量推广，建立监控、告警与迭代机制", "2 周"),
]


def read_csv(name):
    return list(csv.DictReader(open(os.path.join(ROOT, name), encoding="utf-8-sig")))


def to_int(s):
    try:
        return int(float((s or "").strip()))
    except (ValueError, TypeError):
        return 0


def load_records():
    rows = read_csv(os.path.join("任务一", "结果", "result1.csv"))
    text_dir = os.path.join(ROOT, "任务一", "结果", "text")
    rec = {}
    for r in rows:
        fn = os.path.basename((r.get("内容") or "").replace("/", os.sep))
        title = ""
        p = os.path.join(text_dir, fn)
        if fn and os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                first = f.readline().strip()
            title = first.lstrip("# ").strip()
        rec[(r["采集批次号"], r["记录编号"])] = {
            "batch": r["采集批次号"], "id": r["记录编号"], "src": r["来源网站名称"],
            "link": r.get("来源链接", ""), "time": r.get("发布时间", "").strip(),
            "heat": sum(to_int(r[k]) for k in ["星标数", "浏览数", "点赞数", "评论数", "收藏数"]),
            "title": title or (r["采集批次号"] + "-" + r["记录编号"]),
        }
    return rec


def build_proposal(cluster, meta):
    cid = cluster["cid"]
    name = cluster["name"]
    func = cluster["func"]
    ind = cluster["industry"]
    size = int(cluster["size"])
    dims = cluster["dims"]
    score = cluster["score"]
    pri = cluster["priority"]
    nsrc = len(cluster["sources"])
    nbatch = cluster.get("n_batch", 0)
    users = USERS.get(ind, USERS["其他"])
    pain = PAINS.get(func, PAINS["文本生成"])
    tech = TECH.get(func, TECH["文本生成"])
    src_str = "、".join(f"{s['name']}（{s['count']}）" for s in cluster["sources"])
    top_members = sorted(cluster["members"], key=lambda x: -x["heat"])[:10]

    lines = []
    lines.append(f"# 立项策划案：{name}")
    lines.append("")
    lines.append(f"> 本方案由「AI 应用场景的智能挖掘与机会评估系统」基于主题簇 **{cid}** 的 **{size}** 条真实机会记录自动生成；"
                 f"机会价值分 **{score}**，优先级 **{pri}/{meta['clusters']}**。")
    lines.append("")
    lines.append("## 一、机会来源与依据")
    lines.append(f"- 主题簇：{cid} · {name}")
    lines.append(f"- 功能类别：{func}；所属行业：{ind}")
    lines.append(f"- 簇内机会记录：{size} 条；来源网站覆盖：{src_str or '—'}（共 {nsrc} 个来源、{nbatch} 个采集批次）")
    lines.append(f"- 全流程规模：采集清洗去重 {meta['total_records']} 条 → AI 应用机会 {meta['total_opportunities']} 条 → 主题簇 {meta['clusters']} 个")
    lines.append(f"- 价值评分：多源指向度 {dims['src']}/100、记录规模 {dims['size']}/100、商业信号 {dims['biz']}/100 → 加权机会价值分 {score}")
    lines.append("")
    lines.append("## 二、目标用户与核心痛点")
    lines.append(f"- 目标用户：{users}")
    lines.append(f"- 核心痛点：{pain}")
    lines.append("")
    lines.append("## 三、核心功能")
    lines.append(f"- 面向{ind}场景的{func}能力封装：标准化输入输出与可配置策略")
    lines.append("- 业务系统对接：与现有工单/内容/数据平台打通，支持单点登录与权限继承")
    lines.append("- 结果可解释与可追溯：保留检索依据、模型理由与人工复核记录")
    lines.append("- 运营与度量：调用量、准确率、时延与成本看板，支持灰度与回滚")
    lines.append("")
    lines.append("## 四、技术路线")
    for t in tech:
        lines.append(f"- {t}")
    lines.append("- 工程侧：服务化部署（容器化）、异步队列与限流、日志与审计、灰度发布")
    lines.append("")
    lines.append("## 五、实施周期与里程碑")
    lines.append("- 总周期：约 12 周（可按团队规模压缩或并行）")
    lines.append("- 第 1–2 周：场景与数据确认，完成合规与数据边界评估")
    lines.append("- 第 3–4 周：基线能力接入，跑通端到端最小链路")
    lines.append("- 第 5–8 周：核心功能开发与业务系统对接")
    lines.append("- 第 9–10 周：评测与调优，形成验收指标")
    lines.append("- 第 11–12 周：试点上线、反馈修复与推广准备")
    lines.append("")
    lines.append("## 六、子任务分解（WBS）")
    for tid, tname, tdesc, tdur in WBS:
        lines.append(f"- **{tid} {tname}**（{tdur}）：{tdesc}")
    lines.append("")
    lines.append("## 七、依据来源（簇内真实记录 Top 10，按热度排序）")
    for m in top_members:
        title = m["title"].replace("\n", " ")[:80]
        lines.append(f"- `{m['batch']}-{m['id']}` · {title} · {m['src']} · {m['link']}")
    lines.append("")
    lines.append("## 八、价值评分与优先级")
    lines.append(f"- 多源指向度：{dims['src']}/100（来源种类越多，说明多源共同指向，需求越可信）")
    lines.append(f"- 记录规模：{dims['size']}/100（簇内机会记录条数，反映需求密度）")
    lines.append(f"- 商业信号：{dims['biz']}/100（0.6×互动热度 + 0.4×跨批次持续性）")
    lines.append(f"- 加权机会价值分：{score}（权重 0.35 / 0.35 / 0.30）；优先级：{pri}")
    lines.append("")
    lines.append("## 九、成本与资源估算")
    lines.append("- 人力：3–5 人（产品/算法/后端/前端/测试），约 12 周")
    lines.append("- 算力：推理以成熟大模型 API 为主，按日调用量估算；如需微调，按需租用 GPU")
    lines.append("- 存储：文档原文与向量索引约 10–50 GB 量级（视业务数据规模）")
    lines.append("- 外部依赖：大模型 API、向量数据库、对象存储与监控告警服务")
    lines.append("")
    lines.append("## 十、风险与应对")
    lines.append("- 数据合规风险：仅使用公开或已授权数据，脱敏处理个人信息，保留审计日志")
    lines.append("- 模型幻觉风险：RAG 引用溯源 + 事实校验 + 人工终审")
    lines.append("- 效果不达预期：先做基线对照与小流量灰度，设定止损与回滚条件")
    lines.append("")
    lines.append("---")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}｜数据版本：result1–result4（本仓库）")
    return "\n".join(lines)


def main():
    rec = load_records()
    r2 = read_csv(os.path.join("任务二", "结果", "result2.csv"))
    r3 = read_csv(os.path.join("任务三", "结果", "result3.csv"))
    r4 = json.load(open(os.path.join(ROOT, "任务四", "结果", "result4_中间指标.json"), encoding="utf-8"))
    r4map = {c["主题簇编号"]: c for c in r4["clusters"]}

    total = len(rec)
    opp = sum(1 for x in r2 if x["是否构成机会"] == "1")
    batches = sorted({x["batch"] for x in rec.values()})
    src_count = {}
    batch_stats = {}
    for x in rec.values():
        src_count[x["src"]] = src_count.get(x["src"], 0) + 1
        b = batch_stats.setdefault(x["batch"], {"records": 0, "opps": 0})
        b["records"] += 1
    for x in r2:
        if x["是否构成机会"] == "1":
            batch_stats[x["采集批次号"]]["opps"] += 1
    batch_list = []
    for b in batches:
        bs = batch_stats[b]
        batch_list.append({"batch": b, "records": bs["records"], "opps": bs["opps"],
                           "rate": round(bs["opps"] / bs["records"] * 100, 1)})
    sources = [{"name": k, "count": v} for k, v in sorted(src_count.items(), key=lambda t: -t[1])]

    clusters = []
    for row in r3:
        cid = row["主题簇编号"]
        members = []
        src_map = {}
        for m in row["簇内机会记录"].split("；"):
            m = m.strip()
            if not m:
                continue
            b, sid = m.split("-", 1)
            r = rec.get((b, sid))
            if not r:
                continue
            members.append({"batch": b, "id": sid, "title": r["title"], "src": r["src"],
                            "link": r["link"], "time": r["time"], "heat": r["heat"]})
            src_map[r["src"]] = src_map.get(r["src"], 0) + 1
        s4 = r4map.get(cid, {})
        cl = {
            "cid": cid,
            "batch": row["采集批次号"],
            "name": row["主题簇名称"],
            "func": row["功能类别"],
            "industry": row["所属行业"],
            "size": int(row["簇内机会记录数"]),
            "score": float(s4.get("机会价值分", 0)),
            "priority": int(s4.get("priority", 0)),
            "dims": {"src": float(s4.get("多源指向度", 0)), "size": float(s4.get("记录规模", 0)),
                     "biz": float(s4.get("商业信号", 0))},
            "n_batch": int(s4.get("n_batch", 0)),
            "sources": [{"name": k, "count": v} for k, v in sorted(src_map.items(), key=lambda t: -t[1])],
            "members": members,
        }
        cl["proposal_md"] = build_proposal(cl, {"total_records": total, "total_opportunities": opp,
                                                 "clusters": len(r3)})
        clusters.append(cl)

    clusters.sort(key=lambda x: x["priority"])
    source_names = [s["name"] for s in sources]
    matrix = []
    for c in clusters:
        row = []
        for s in source_names:
            row.append(next((x["count"] for x in c["sources"] if x["name"] == s), 0))
        matrix.append(row)

    payload = {
        "meta": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total_records": total,
            "total_opportunities": opp,
            "opp_rate": round(opp / total * 100, 1),
            "clusters": len(clusters),
            "batches": batches,
            "sources": sources,
            "batch_stats": batch_list,
            "weights": r4.get("weights", [0.35, 0.35, 0.30]),
        },
        "clusters": clusters,
        "charts": {"source_names": source_names, "source_matrix": matrix},
    }
    js = "window.DASHBOARD_DATA = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";\n"
    out = os.path.join(DATA_DIR, "dashboard_data.js")
    with open(out, "w", encoding="utf-8") as f:
        f.write(js)
    print("dashboard data ->", out, len(js), "bytes")

    for c in clusters:
        fn = f"{c['priority']:02d}_{c['cid']}_{c['name']}.md"
        fn = re.sub(r'[\\/:*?"<>|]', "_", fn)
        with open(os.path.join(PROPOSAL_DIR, fn), "w", encoding="utf-8") as f:
            f.write(c["proposal_md"])
    print("proposals ->", PROPOSAL_DIR, len(clusters), "files")


if __name__ == "__main__":
    main()
