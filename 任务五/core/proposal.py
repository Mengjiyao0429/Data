# -*- coding: utf-8 -*-
"""任务五 策划案生成：模型调用 + 严格校验 + 离线模板兜底 + Word 导出。"""
import io
import json

from . import llm

SECTIONS = [
    "一、机会来源与依据",
    "二、目标用户与核心痛点",
    "三、核心功能",
    "四、技术路线",
    "五、实施周期与里程碑",
    "六、子任务分解（WBS）",
    "七、依据来源",
    "八、价值评分与优先级",
    "九、成本与资源估算",
    "十、风险与应对",
]

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
    "智能体编排": "多步骤业务流程需人工串联，跨系统操作重复、易出错，缺少统一编排与审计。",
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


def _facts(cluster, meta):
    return {
        "主题簇编号": cluster["cid"],
        "主题簇名称": cluster["name"],
        "功能类别": cluster["func"],
        "所属行业": cluster["industry"],
        "簇内机会记录数": cluster["size"],
        "来源网站覆盖": [{"来源": s["name"], "记录数": s["count"]} for s in cluster["sources"]],
        "覆盖来源数": len(cluster["sources"]),
        "覆盖批次数": cluster["n_batch"],
        "机会价值分": cluster["score"],
        "优先级": cluster["priority"],
        "三维度得分": {"多源指向度": cluster["dims"]["src"], "记录规模": cluster["dims"]["size"],
                       "商业信号": cluster["dims"]["biz"]},
        "全流程规模": {"采集清洗去重": meta["total_records"], "AI应用机会": meta["total_opportunities"],
                       "主题簇": meta["clusters"]},
        "证据记录": [{"编号": m["batch"] + "-" + m["id"], "标题": m["title"][:90],
                      "来源": m["src"], "链接": m["link"]} for m in cluster["evidence"]],
    }


def build_messages(cluster, meta):
    facts = _facts(cluster, meta)
    system = ("你是企业数字化项目的立项策划专家。你只能依据用户提供的“主题簇事实”写作，"
              "严禁编造任何数字、记录编号、链接或平台数据。输出为纯 Markdown。")
    user = (
        "请基于下面的“主题簇事实”，撰写一份中文立项策划案。\n\n"
        "硬性要求：\n"
        "1. 只能使用给定事实中的数字、记录编号与链接，不得编造；\n"
        "2. 必须按顺序包含以下二级标题：\n   " + "；".join(SECTIONS) + "；\n"
        "3. 第七节“依据来源”逐条列出给定证据记录（编号、标题、来源、链接），最多 10 条；\n"
        "4. 篇幅 1200–2500 字，不要输出代码块围栏，不要输出与事实冲突的内容；\n"
        "5. 要给出可执行的实施周期、WBS 分解、成本与风险，语言专业、具体。\n\n"
        "主题簇事实（JSON）：\n" + json.dumps(facts, ensure_ascii=False, indent=1)
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def validate(md):
    if not md or len(md) < 800:
        return False, "篇幅不足"
    hit = sum(1 for s in SECTIONS if s in md)
    if hit < 6:
        return False, "缺少必备章节（命中 %d/10）" % hit
    if "```" in md:
        return False, "包含代码块围栏"
    return True, "ok"


def name_users(name):
    """行业为“其他”时，按主题簇名称推断目标用户，避免出现“其他行业用户”这类空话。"""
    rules = [
        ("API", "开发者、AI 应用开发团队与平台工程团队"),
        ("开发", "软件开发者与 AI 应用工程团队"),
        ("知识图谱", "知识管理与业务支持团队"),
        ("检索", "知识管理与一线业务支持团队"),
        ("智能体", "业务流程自动化与运营团队"),
        ("OCR", "文档处理、录入与合规审核团队"),
        ("文档", "文档处理与合规审核团队"),
        ("语音", "客服中心、招聘与会议记录团队"),
        ("医疗", "医疗机构信息科与临床科室"),
        ("教育", "院校教务与一线教师"),
        ("法律", "律所与企业法务合规团队"),
    ]
    for kw, users in rules:
        if kw in name:
            return users
    return "有明确业务场景的企业业务团队"


def template_proposal(cluster, meta, reason=None):
    cid = cluster["cid"]
    name = cluster["name"]
    func = cluster["func"]
    ind = cluster["industry"]
    size = cluster["size"]
    dims = cluster["dims"]
    users = USERS.get(ind) or USERS["其他"]
    if ind == "其他":
        users = name_users(name)
    scene = ind if ind != "其他" else "行业"
    pain = PAINS.get(func, PAINS["文本生成"])
    tech = TECH.get(func, TECH["文本生成"])
    src_str = "、".join("%s（%d）" % (s["name"], s["count"]) for s in cluster["sources"]) or "—"

    L = []
    L.append("# 立项策划案：%s" % name)
    L.append("")
    if reason:
        L.append("> 说明：%s。以下内容由系统离线模板生成，所有数字与记录均取自任务一～四的真实结果。" % reason)
        L.append("")
    L.append("> 本方案基于主题簇 **%s** 的 **%d** 条真实机会记录生成；机会价值分 **%.1f**，优先级 **%d/%d**。"
             % (cid, size, cluster["score"], cluster["priority"], meta["clusters"]))
    L.append("")
    L.append("## 一、机会来源与依据")
    L.append("- 主题簇：%s · %s" % (cid, name))
    L.append("- 功能类别：%s；所属行业：%s" % (func, ind))
    L.append("- 簇内机会记录：%d 条；来源网站覆盖：%s（共 %d 个来源、%d 个采集批次）"
             % (size, src_str, len(cluster["sources"]), cluster["n_batch"]))
    L.append("- 全流程规模：采集清洗去重 %d 条 → AI 应用机会 %d 条 → 主题簇 %d 个"
             % (meta["total_records"], meta["total_opportunities"], meta["clusters"]))
    L.append("- 价值评分：多源指向度 %.1f/100、记录规模 %.1f/100、商业信号 %.1f/100 → 加权机会价值分 %.1f"
             % (dims["src"], dims["size"], dims["biz"], cluster["score"]))
    L.append("")
    L.append("## 二、目标用户与核心痛点")
    L.append("- 目标用户：%s" % users)
    L.append("- 核心痛点：%s" % pain)
    L.append("")
    L.append("## 三、核心功能")
    L.append("- 面向%s场景的%s能力封装：标准化输入输出与可配置策略" % (scene, func))
    L.append("- 业务系统对接：与现有工单/内容/数据平台打通，支持单点登录与权限继承")
    L.append("- 结果可解释与可追溯：保留检索依据、模型理由与人工复核记录")
    L.append("- 运营与度量：调用量、准确率、时延与成本看板，支持灰度与回滚")
    L.append("")
    L.append("## 四、技术路线")
    for t in tech:
        L.append("- %s" % t)
    L.append("- 工程侧：容器化部署、异步队列与限流、日志与审计、灰度发布")
    L.append("")
    L.append("## 五、实施周期与里程碑")
    L.append("- 总周期：约 12 周（可按团队规模压缩或并行）")
    L.append("- 第 1–2 周：场景与数据确认，完成合规与数据边界评估")
    L.append("- 第 3–4 周：基线能力接入，跑通端到端最小链路")
    L.append("- 第 5–8 周：核心功能开发与业务系统对接")
    L.append("- 第 9–10 周：评测与调优，形成验收指标")
    L.append("- 第 11–12 周：试点上线、反馈修复与推广准备")
    L.append("")
    L.append("## 六、子任务分解（WBS）")
    for tid, tname, tdesc, tdur in WBS:
        L.append("- **%s %s**（%s）：%s" % (tid, tname, tdur, tdesc))
    L.append("")
    L.append("## 七、依据来源")
    for m in cluster["evidence"]:
        L.append("- `%s-%s` · %s · %s · %s"
                 % (m["batch"], m["id"], m["title"][:80].replace("\n", " "), m["src"], m["link"]))
    L.append("")
    L.append("## 八、价值评分与优先级")
    L.append("- 多源指向度：%.1f/100（来源种类越多，说明多源共同指向，需求越可信）" % dims["src"])
    L.append("- 记录规模：%.1f/100（簇内机会记录条数，反映需求密度）" % dims["size"])
    L.append("- 商业信号：%.1f/100（0.7×簇内生均互动热度 + 0.3×簇内平均机会置信度）" % dims["biz"])
    L.append("- 加权机会价值分：%.1f（权重 0.293 / 0.5065 / 0.2005，与任务四一致）；优先级：%d"
             % (cluster["score"], cluster["priority"]))
    L.append("")
    L.append("## 九、成本与资源估算")
    L.append("- 人力：3–5 人（产品/算法/后端/前端/测试），约 12 周")
    L.append("- 算力：推理以成熟大模型 API 为主，按日调用量估算；如需微调，按需租用 GPU")
    L.append("- 存储：文档原文与向量索引约 10–50 GB 量级（视业务数据规模）")
    L.append("- 外部依赖：大模型 API、向量数据库、对象存储与监控告警服务")
    L.append("")
    L.append("## 十、风险与应对")
    L.append("- 数据合规风险：仅使用公开或已授权数据，脱敏处理个人信息，保留审计日志")
    L.append("- 模型幻觉风险：RAG 引用溯源 + 事实校验 + 人工终审")
    L.append("- 效果不达预期：先做基线对照与小流量灰度，设定止损与回滚条件")
    L.append("")
    L.append("---")
    L.append("生成方式：离线模板（零 API 成本）｜数据版本：result1–result4")
    return "\n".join(L)


def generate(cluster, meta, cfg, allow_fallback=True):
    provider = (cfg.get("provider") or "template").lower()
    if provider in ("template", "", "none"):
        return {"markdown": template_proposal(cluster, meta), "mode": "template",
                "model": "离线模板", "tokens": 0}

    try:
        res = llm.chat(build_messages(cluster, meta), cfg, timeout=int(cfg.get("timeout") or 60))
        ok, why = validate(res["text"])
        if not ok:
            raise llm.LLMError("输出校验未通过：" + why)
        return {"markdown": res["text"], "mode": "llm", "model": res["model"],
                "tokens": res.get("tokens", 0)}
    except llm.LLMError as e:
        if not allow_fallback:
            raise
        return {"markdown": template_proposal(cluster, meta, reason="模型调用失败（%s），已回退离线模板" % e),
                "mode": "template-fallback", "model": "离线模板", "tokens": 0}


def markdown_to_docx(md, title="立项策划案"):
    """把 Markdown 转为 Word（标题/正文/列表），失败时抛异常由调用方处理。"""
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Microsoft YaHei"
    style.font.size = Pt(10.5)

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        elif line.startswith("> "):
            p = doc.add_paragraph(line[2:])
            p.paragraph_format.left_indent = Pt(18)
        elif line.startswith("- "):
            doc.add_paragraph(line[2:].replace("**", ""), style="List Bullet")
        else:
            doc.add_paragraph(line.replace("**", ""))

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
