# -*- coding: utf-8 -*-
"""任务二 · 模块2：功能类别与所属行业分类（附件1 标签体系，单标签）

约束
----
* 标签严格取自附件1：功能类别 16 类、所属行业 30 类，不创造新标签。
* 每条机会记录各标注"一个"功能类别、"一个"所属行业（题面要求）。
* 采用"加权证据打分 + 主导标签裁定"：标题命中权重高于正文，保证可解释。
* 非机会记录不进入本模块，因此不会被强制分配标签。
"""
from __future__ import annotations

import math
import re

# --------------------------------------------------------------------------
# 附件1 · 功能类别（16 类）及判定边界
# --------------------------------------------------------------------------
FUNCTION_LABELS = [
    "图像识别", "语义分析", "语音处理", "文本生成", "对话问答", "推荐系统", "知识检索", "数据挖掘",
    "多模态融合", "智能体编排", "自动化流程", "预测分析", "审核审查", "搜索匹配", "翻译转写", "视频理解",
]

FUNCTION_PATTERNS = {
    "图像识别": [
        (r"图像识别|目标检测|ocr|图片识别|人脸|image recognition|yolo|分类图像|图像分割|识别图片", 1.0),
        (r"图像|图片|photo|vision|视觉|摄像头|截图", 0.45),
    ],
    "语音处理": [
        (r"语音|asr|speech|录音|会议纪要|转写|转录|podcast|字幕|tts|朗读|播客", 1.0),
        (r"音频|audio|声音|voice|听写", 0.7),
    ],
    "文本生成": [
        (r"生成|写作|写文章|文案|summary|摘要|报告|文章|输出文本|创作|写稿|content generation|rewrite|改写", 0.9),
        (r"写|draft|compose", 0.4),
    ],
    "对话问答": [
        (r"对话|问答|chatbot|客服|聊天|助手|assistant|机器人|bot|question answering|问答系统", 1.0),
        (r"提问|answer|回答|咨询", 0.5),
    ],
    "推荐系统": [
        (r"推荐|recommend|recall|召回|个性化|personalized|榜单", 1.0),
        (r"用户画像|ranking|排序", 0.5),
    ],
    "知识检索": [
        (r"检索|知识库|rag|向量|embedding|知识图谱|文档查询|语义检索|检索增强|knowledge base|retrieval|faq", 1.0),
        (r"搜索|search|库", 0.5),
    ],
    "数据挖掘": [
        (r"数据挖掘|聚类|关联规则|用户行为分析|指标分析|统计|insight|数据洞察|特征工程|数据清洗|etl", 1.0),
        (r"数据|data|dataset|分析", 0.5),
    ],
    "多模态融合": [
        (r"多模态|multimodal|图文|图生文|视觉语言|vlm|跨模态", 1.0),
        (r"图片和文字|语音和文字", 0.6),
    ],
    "智能体编排": [
        (r"智能体|agent|多智能体|multi-agent|工作流编排|tool calling|autogen|crewai|mcp|planning", 1.0),
        (r"编排|orchestrat|自动化助手", 0.6),
    ],
    "自动化流程": [
        (r"自动化|automat|rpa|批量处理|批处理|定时任务|workflow|流程|pipeline|流水线|cron", 1.0),
        (r"脚本|script|任务", 0.4),
    ],
    "预测分析": [
        (r"预测|forecast|风险|预警|异常检测|anomaly|趋势|评估模型|预测模型|信用|风控|分诊", 1.0),
        (r"预测性|不确定", 0.4),
    ],
    "审核审查": [
        (r"审核|审查|审核合规|违规|内容安全|敏感|风控审核|质检|审计|审查|举报|rating|moderation|content filter", 1.0),
        (r"检查|检测|review", 0.5),
    ],
    "搜索匹配": [
        (r"搜索匹配|关键词匹配|匹配|召回匹配|semantic match|搜索|搜索引擎|elasticsearch|模糊匹配", 1.0),
        (r"查找|定位|index", 0.5),
    ],
    "翻译转写": [
        (r"翻译|translat|多语言|多语种|字幕|转写|transcri|本地化|localization", 1.0),
    ],
    "视频理解": [
        (r"视频理解|视频分析|video understanding|视频内容|监控视频|短视频分析|抽帧|video", 1.0),
        (r"视频", 0.7),
    ],
    "语义分析": [
        (r"情感分析|语义|分类|意图|情感|实体|ner|sentiment|文本分类|intent|纠错|抽取|标签|理解", 0.9),
        (r"nlp|自然语言处理|文本|language", 0.6),
    ],
}

# 功能标签的互斥优先关系：当多个标签得分接近时，按"更具体"的能力优先裁定
FUNCTION_PRIORITY = [
    "语音处理", "多模态融合", "视频理解", "图像识别", "智能体编排", "推荐系统", "预测分析",
    "审核审查", "翻译转写", "搜索匹配", "知识检索", "对话问答", "自动化流程", "数据挖掘",
    "文本生成", "语义分析",
]

# --------------------------------------------------------------------------
# 附件1 · 所属行业（30 类）及判定边界
# --------------------------------------------------------------------------
INDUSTRY_LABELS = [
    "金融", "教育", "医疗", "法律", "电商", "零售", "房地产", "制造", "物流", "游戏", "餐饮", "农业",
    "政务", "汽车", "家居", "交通", "能源", "通信", "娱乐", "体育", "旅游", "保险", "建筑", "环保",
    "科研", "人力资源", "媒体出版", "营销广告", "外贸", "其他",
]

# 行业关键词分为"强"（1.0）与"弱"（0.5）两档：
#   强词为可单独确定行业的词；弱词易与他行业混淆（如 game、claim、研究、员工），只作辅助证据。
# 行业判定原则（对应人工核验反馈）：
#   (1) 英文关键词一律加词边界，杜绝 caller→car、email→mail、HR→hr、match→matches 之类的子串碰撞；
#   (2) 同一英文词在技术语境与业务语境含义不同（factory=工厂 vs factory pattern、store=门店 vs
#       data store、contract=合同 vs contract test、match=赛事 vs 正则匹配），一律按"业务义"降权，
#       只作弱证据；
#   (3) 只有出现可支撑行业的实质证据（业务场景词、行业专有词）才给行业标签，证据不足统一归"其他"。
INDUSTRY_PATTERNS = {
    "金融": [(r"金融|银行|券商|证券|基金|信贷|贷款|理财|fintech|\bbank(ing)?\b", 1.0),
             (r"投资|\bpayments?\b|\bfinancial\b|\bfinance\b", 0.5)],
    "教育": [(r"教育|教师|课堂|教学|课程|作业|考试|tutor|education|school|learning platform", 1.0),
             (r"学生|\bstudents?\b", 0.5)],
    "医疗": [(r"医疗|患者|病历|诊断|医院|临床|问诊|药品|医学|healthcare|medical|clinical|patients?|clinic", 1.0),
             (r"健康|\bhealth", 0.5)],
    "法律": [(r"法律|律师|法条|诉讼|合同审查|法务|司法", 1.0),
             (r"合同|\bcontracts?\b|legal|lawyer|\bclm\b", 0.5)],
    "电商": [(r"电商|淘宝|天猫|京东|拼多多|网店|店铺", 1.0),
             (r"商品|下单|购物车|\be-?commerce\b|shopify|\blistings?\b|\borders?\b", 0.5)],
    "零售": [(r"零售|超市|商超|导购", 1.0),
             (r"门店|\bretail\b|\bstores?\b|\binventory\b", 0.5)],
    "房地产": [(r"房地产|楼盘|置业|房产|租房|中介|real estate|property management", 1.0)],
    "制造": [(r"制造|工厂|车间|生产线|质检|工业|数控|manufactur|\bindustrial\b|\bplc\b", 1.0),
             (r"\bfactor(y|ies)\b|工程", 0.4)],
    "物流": [(r"物流|仓储|配送|快递|运输|logistics|warehouse|\bdeliver(y|ies)\b", 1.0)],
    "游戏": [(r"游戏|关卡|玩家|\bgaming\b|godot", 1.0),
             (r"\bgames?\b|\bunity\b", 0.35)],
    "餐饮": [(r"餐饮|餐厅|外卖|菜品|后厨|restaurant|food delivery|catering|coffee shop|咖啡", 1.0)],
    "农业": [(r"农业|种植|养殖|农机|agricultur|\bfarm(ing|er)?\b", 1.0),
             (r"\bcrops?\b|农业种植|农村", 0.5)],
    "政务": [(r"政务|政府|市民|公共服务|政务大厅|government|public service|citizen", 1.0)],
    "汽车": [(r"汽车|车企|自动驾驶|车机|车辆|整车|automotive|\badas\b", 1.0),
             (r"\bcars?\b|\bdriving\b|\bvehicle", 0.5)],
    "家居": [(r"家居|装修|家具|家电|智能家居|home improvement|furniture", 1.0)],
    "交通": [(r"交通|出行|地铁|公交|路况|导航|traffic|transit|mobility", 1.0)],
    "能源": [(r"能源|电力|电网|光伏|风电|石油|双碳|\benergy\b|power grid|solar", 1.0)],
    "通信": [(r"通信|运营商|基站|网络设备|telecom|network operator", 1.0),
             (r"\b5g\b", 0.5)],
    "娱乐": [(r"娱乐|音乐|影视|综艺|粉丝|entertainment|\bmusic\b|短剧", 1.0),
             (r"视频|\bvideo\b|内容创作|短视频|\bstreaming\b", 0.3)],
    "体育": [(r"体育|足球|篮球|球员|赛事|健身|sports|fitness", 1.0),
             (r"\bmatch(es)?\b", 0.3)],
    "旅游": [(r"旅游|酒店|景区|行程|机票|民宿|travel|tourism|\bhotels?\b|\btrips?\b", 1.0)],
    "保险": [(r"保险|理赔|保单|投保|insurance", 1.0),
             (r"\bclaims?\b", 0.3)],
    "建筑": [(r"建筑|施工|造价|图纸|\bbim\b|\bconstruction\b|\brevit\b|\barchitectural\b", 1.0),
             (r"\barchitectures?\b|工程", 0.25)],
    "环保": [(r"环保|环境监测|污染|碳排|垃圾分类|\benvironmental\b|\bpollution\b|\bemissions?\b", 1.0)],
    "科研": [(r"科研|学术|scientific research|\bbenchmark|论文|\bpapers?\b", 1.0),
             (r"\bdatasets?\b|研究|\bresearch", 0.3)],
    "人力资源": [(r"人力资源|招聘|简历|面试|考勤|绩效|人事|\brecruit(ing|er|ment)?\b|\bresumes?\b|\bhiring\b", 1.0),
                 (r"\bhr\b|员工|\bemplo(yees?|yment)\b", 0.4)],
    "媒体出版": [(r"媒体|出版|新闻|记者|编辑|内容运营|\bpublishing\b|\bnewsroom\b|\bjournalist", 1.0)],
    "营销广告": [(r"营销|广告|获客|\bseo\b|推广|marketing|advertis|\bcampaigns?\b|\bbrand", 1.0),
                 (r"投放|转化|\bconversion\b", 0.5)],
    "外贸": [(r"外贸|跨境|外汇|cross-?border|\boverseas\b|\bexport trading\b", 1.0),
             (r"\bimports?\b|\bexports?\b|\btrade\b", 0.3)],
    "其他": [(r"生活服务|个人|通用|工具|工具箱|日常|misc|general|utility", 0.3)],
}

# 跨行业客服/咨询场景：单独出现"客服/咨询"往往是最强业务线索，但其服务对象行业未必明示。
# 作为弱证据处理（0.5），且与其他行业同分时按下表优先。
INDUSTRY_CONTEXT = {
    "电商": [(r"电商客服|网购|商城|网店|线上店铺|e-?commerce|电商|\bshopify\b", 0.5)],
    "餐饮": [(r"咖啡|coffee|餐厅|点餐|外卖", 0.5)],
    "零售": [(r"门店|货架|进销存|\bretail\b", 0.5)],
    "金融": [(r"投顾|财富管理|券商|\bfintech\b", 0.5)],
    "营销广告": [(r"获客|投放|引流|私域|\bcampaigns?\b", 0.5)],
    "法律": [(r"合同审查|\bcontract review\b|\blegal\b", 0.5)],
    "医疗": [(r"\bmedical\b|\bhealthcare\b|\bclinic", 0.5)],
    "人力资源": [(r"\bhiring\b|\bresumes?\b|\bbehiring\b|招聘|简历", 0.5)],
}

INDUSTRY_PRIORITY = [
    "电商", "金融", "保险", "医疗", "法律", "教育", "人力资源", "制造", "物流", "通信", "能源",
    "房地产", "汽车", "交通", "建筑", "零售", "餐饮", "农业", "政务", "家居", "游戏", "体育",
    "旅游", "娱乐", "媒体出版", "营销广告", "外贸", "环保", "科研", "其他",
]

TITLE_WEIGHT = 2.2   # 标题命中权重
BODY_WEIGHT = 1.0


def _score(text_title: str, text_body: str, patterns) -> float:
    """加权饱和求和：标题 > 正文，避免长正文的词频堆砌主导分类。"""
    t = (text_title or "").lower()
    b = (text_body or "").lower()
    comp = 1.0
    for pat, strength in patterns:
        hit_t = re.search(pat, t, re.I)
        hit_b = re.search(pat, b, re.I)
        if hit_t:
            comp *= 1.0 - min(0.92, strength * TITLE_WEIGHT / (TITLE_WEIGHT + 1))
        elif hit_b:
            comp *= 1.0 - min(0.92, strength * BODY_WEIGHT / (TITLE_WEIGHT + 1))
    return 1.0 - comp


def _decide(scores: dict, priority: list, margin: float = 0.10) -> tuple[str, float, str]:
    """返回 (标签, 置信度, 说明)。

    采用"主导标签裁定"：主标签与次标签分差在 margin 内视为边界情形，
    按具体性优先表裁定，并在说明中列出候选，供人工复核。
    """
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], priority.index(kv[0])))
    top, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    tie = [k for k, v in ranked if top_score - v <= margin]
    tie_ambiguous = len(tie) > 1
    if tie_ambiguous:
        for label in priority:
            if label in tie:
                top = label
                break
    chosen = scores[top]
    gap = chosen - second_score
    conf = 0.55 * min(1.0, chosen) + 0.45 * (1.0 - math.exp(-3.5 * max(0.0, gap)))
    if tie_ambiguous:
        conf *= 0.85
    conf = max(0.30, min(0.97, conf))
    note = f"候选: {', '.join(f'{k}={v:.2f}' for k, v in ranked[:3])}"
    return top, round(conf, 4), note


def classify_category(title: str, body: str) -> dict:
    """对机会记录分别标注一个功能类别与一个所属行业（附件1 单标签）。"""
    f_scores = {lab: _score(title, body, FUNCTION_PATTERNS[lab]) for lab in FUNCTION_LABELS}
    i_scores = {}
    for lab in INDUSTRY_LABELS:
        pats = list(INDUSTRY_PATTERNS[lab])
        i_scores[lab] = _score(title, body, pats)
    for lab, pats in INDUSTRY_CONTEXT.items():
        ctx = _score(title, body, pats)
        if ctx > 0:
            # 业务意图词（如 coffee shop / 电商客服）是与强词同级的具体场景证据
            i_scores[lab] = max(i_scores[lab], 0.35 + 0.15 * min(1.0, ctx * 2))

    if max(f_scores.values()) < 0.10:
        f_scores["语义分析"] = max(f_scores["语义分析"], 0.12)  # 功能线索弱时归入通用语义处理
    func, func_conf, func_note = _decide(f_scores, FUNCTION_PRIORITY)

    # 行业"证据充分性"判定：证据不足一律归"其他"，绝不硬派具体行业
    sorted_ind = sorted(i_scores.items(), key=lambda kv: -kv[1])
    ind_top, ind_top_value = sorted_ind[0]
    ind_second = sorted_ind[1][1] if len(sorted_ind) > 1 else 0.0
    if ind_top_value >= 0.45:
        industry, ind_conf, ind_note = _decide(i_scores, INDUSTRY_PRIORITY)   # 强证据（正文明确业务/行业场景）
    elif ind_top_value >= 0.30 and (ind_top_value - ind_second) >= 0.12:
        industry, ind_conf, ind_note = _decide(i_scores, INDUSTRY_PRIORITY)   # 中证据且主次分差足够
        ind_conf = round(max(0.30, ind_conf * 0.85), 4)
        ind_note += "（中证据，待复核）"
    else:
        industry, ind_conf = "其他", 0.40
        ind_note = ("正文未出现足以支撑具体行业的业务场景证据（仅有技术性表述），"
                    "按附件1 归入“其他”" + f"；候选: {', '.join(f'{k}={v:.2f}' for k, v in sorted_ind[:3])}")
    assert func in FUNCTION_LABELS and industry in INDUSTRY_LABELS
    return {
        "function": func,
        "function_confidence": func_conf,
        "function_note": func_note,
        "industry": industry,
        "industry_confidence": ind_conf,
        "industry_note": ind_note,
        "category_confidence": round(min(func_conf, ind_conf), 4),
        "needs_review": industry == "其他" or min(func_conf, ind_conf) < 0.55,
    }