# -*- coding: utf-8 -*-
"""任务二 · 模块1：AI 应用机会判别与置信度计算

对应题面四条判定规则：
    ① 真实需求   —— 面向明确终端用户/业务场景，存在可观察需求信号（求推荐、有没有工具、吐槽等）
    ② AI 是核心 —— AI 能力是解决问题的核心手段，而非"文本里出现了 AI 字样"
    ③ 技术可落地 —— 现有成熟 AI 能力（大模型/多模态/智能体/成熟算法）即可实现
    ④ 排除情形   —— 纯科普教程、广告、AI 营销噱头，命中直接判 0

判别顺序固定为 ④→①→②→③，每一步输出可解释证据（命中关键词/否决原因），
置信度由四维证据强度加权合成，再乘以记录可信度 Q，作为"判别置信度"。
注意：该数值是规则证据评分，不是经统计校准的后验概率（论文中已如实说明）。
"""
from __future__ import annotations

import hashlib
import math
import re

# --------------------------------------------------------------------------
# 参数（论文"判别阈值依据"一节引用本处取值）
# --------------------------------------------------------------------------
DECISION_TAU = 0.56      # 机会判定阈值：人工标注集上 F1 最优区间（0.54~0.56）内取中，略偏保守；见 evaluate.py
MANUAL_REVIEW_LO = 0.62  # 判 1 但置信度低于该值进入人工复核队列
REVIEW_BAND = 0.08       # 判 0 但置信度高于 0.50-REVIEW_BAND 的边界样本进入复核队列

W = {"need": 0.36, "ai_core": 0.26, "feasible": 0.22, "reliability": 0.16}
DELTA_EXCL = 0.35        # 排除证据对置信度的最大扣减系数
NEED_GATE = 0.30         # 规则①门槛：真实需求维度低于该值视为"无需求信号"，直接判 0
GATE_EXCL = 0.50         # 排除强度阈值：≥ 该值直接判 0

# --------------------------------------------------------------------------
# ① 真实需求词典（寻解、求助、吐槽、明确场景）
# --------------------------------------------------------------------------
NEED_PATTERNS = [
    (r"求推荐|有没有(什么|哪)?(好)?(的)?(工具|方案|软件|平台|库|模型|框架|服务|方法)|推荐一下",
     "求推荐/寻工具", 1.0),
    (r"\bhow (do|can|should) i\b|is there (a|any) (way|tool|library|service)|any (suggestions?|recommendations?|ideas?)|(any|which) (recommendations?|suggestions?)",
     "英文寻解提问", 0.65),
    (r"想要|希望(能|可以)|\bneed (a|an|some|help)\b|would like|\bi want\b", "表达诉求", 0.85),
    (r"有没有人(知道|用过)|求(个|一个|带|解决)|跪求|在线等|怎么办|该怎么|请问", "求助表述", 0.9),
    (r"麻烦|太慢|费时|耗时|痛点|难用|不方便|手工|手动|繁琐|效率低", "痛点/吐槽", 0.85),
    (r"困难|瓶颈|error|failed|issue|problem|not working|does not work|无法|不能|失败|报错|不支持",
     "问题描述", 0.5),
    (r"自动化|提效|降本|效率|节省时间|省力|automate|automat", "效率诉求", 0.6),
    (r"能否|是否可以|能不能|could you|support for|是否支持", "可行性询问", 0.6),
]

# 业务场景：把"问题"锚定到具体用户/业务语境（弱场景仅作辅助证据）
SCENE_PATTERNS = [
    (r"customer[- ]?(service|support)|help ?desk|ticketing|troubleshoot(ing)?|after[- ]?sales|"
     r"contact center|call center|self[- ]?service|faq", "客服/支持场景", 0.75),
    (r"contract|clause|compliance|case law", "合同/合规场景", 0.7),
    (r"medical record|health|symptom|diagnos|prescription|patient care", "健康/诊疗场景", 0.7),
    (r"resume|screening|onboarding|talent", "招聘/人才场景", 0.7),
    (r"sales|lead|quotation|inquiry", "销售场景", 0.6),
    (r"客服|售后|工单|售前|经销商|门店|订单|电商|淘宝|京东|拼多多|店铺", "商业运营场景", 0.8),
    (r"简历|招聘|面试|考勤|绩效|\bhr\b|人事|员工|团队管理", "人事场景", 0.8),
    (r"患者|病历|医疗|临床|医院|处方|诊断|问诊|健康", "医疗场景", 0.8),
    (r"法条|合同|法律|诉讼|律师|合规", "法务场景", 0.8),
    (r"学生|课堂|教学|教师|作业|考试|课程", "教学场景", 0.8),
    (r"报表|对账|财务|发票|审计|报销|风控|银行|贷款|保险", "财务风控场景", 0.8),
    (r"生产线|质检|设备|工厂|车间|供应链", "制造场景", 0.7),
    (r"logistics|物流|仓储|配送|运输", "物流场景", 0.7),
    (r"\bbusiness\b|enterprise|company|customer|\bclient\b|user feedback|运营|客户|企业|业务",
     "业务语境", 0.55),
    (r"会议|meeting|文档|资料|知识库|邮件|通知", "办公协作场景", 0.55),
    (r"medical|healthcare|legal|contract|customer|sales|finance|e-?commerce|logistic|manufactur|education|learning platform|"
     r"\bsupport\b|\bservice\b|\bclinic\b|\bpatient\b", "英文业务语境", 0.55),
]

# 中文需求信号（题面举例："求推荐""有没有工具"等寻解、吐槽表述；中文社区亦常见"求""跪求""怎么办"）
ZH_NEED_PATTERNS = [
    (r"求推荐|有没有(人)?(知道|用过|推荐)|用什么|怎么(才能|办|解决)|如何(实现|解决|做|选型|提升|自动化)|"
     r"有没有(工具|方案|软件|平台|库|模型|办法)", "中文寻解提问", 0.85),
    (r"想要|希望(能|可以)|需要(一个|一款|搭建|实现)|能否|是否可以|可不可以|求(个|一个|带|解决)|跪求|在线等",
     "中文表达诉求", 0.8),
    (r"痛点|难点|折腾|重复劳动|效率低|效率不高|人力成本|耗时长|太慢|繁琐|手工|手动|机器代替|降本增效|提效",
     "中文痛点/效率诉求", 0.85),
    (r"吐槽|吐槽一下|太麻烦了|受不了|很难用|不方便|难以|困境|瓶颈|负担|缺口|焦虑|挑战|问题",
     "中文问题描述", 0.5),
]

# 中文业务场景（把问题锚定到具体用户/业务）
ZH_SCENE_PATTERNS = [
    (r"customer[- ]?(service|support)|help ?desk|ticketing|troubleshoot(ing)?|after[- ]?sales|"
     r"contact center|call center|self[- ]?service|faq", "客服/支持场景", 0.75),
    (r"contract|clause|compliance|case law", "合同/合规场景", 0.7),
    (r"medical record|health|symptom|diagnos|prescription|patient care", "健康/诊疗场景", 0.7),
    (r"resume|screening|onboarding|talent", "招聘/人才场景", 0.7),
    (r"sales|lead|quotation|inquiry", "销售场景", 0.6),
    (r"客服|售后|工单|售前|店铺|电商|商家|订单|运营|私域|导购|门店|零售|连锁", "中文商业运营场景", 0.75),
    (r"招聘|简历|面试|考勤|绩效|人事|员工|团队管理|hr|猎头", "中文人事场景", 0.8),
    (r"患者|病历|诊疗|医院|医生|临床|问诊|药品|制药|医药|健康|医学", "中文医疗场景", 0.8),
    (r"合同|法务|律师|诉讼|条款|合规|法律", "中文法务场景", 0.8),
    (r"学生|教师|课堂|教学|课程|作业|考试|培训", "中文教学场景", 0.8),
    (r"财务|对账|发票|报销|风控|银行|贷款|保险|理财|投顾", "中文财务风控场景", 0.8),
    (r"工厂|车间|产线|生产线|质检|设备|制造|工业", "中文制造场景", 0.7),
    (r"物流|仓储|配送|运输|供应链", "中文物流场景", 0.7),
    (r"企业|公司|业务|客户|用户|团队|组织|部门|开发者|政企|政府|市民", "中文业务语境", 0.55),
    (r"会议|纪要|文档|报表|公文|知识库|资料|邮件|表格", "中文办公协作场景", 0.55),
]

# 业务功能词（不绑定特定行业，但明确指向"为谁解决什么问题"的场景锚定）
BUSINESS_SCENE_PATTERNS = [
    (r"customer service|customer support|help desk|ticketing|troubleshoot|copilot|co-pilot|"
     r"self-service|faq|after-sales", "客服/支持业务", 0.7),
    (r"contract review|clause extraction|legal research|compliance check|document review",
     "合同/合规业务", 0.7),
    (r"medical record|symptom analysis|prescription|appointment|clinical summary|patient",
     "诊疗业务", 0.7),
    (r"resume screening|hiring|onboarding|interview", "招聘业务", 0.7),
    (r"recommendation|personaliz|ranking", "推荐业务", 0.55),
    (r"发票|报销|对账|审批|工单|巡店|巡检|质检", "营运业务", 0.6),
    (r"智能客服|客服机器人|电销|外呼|坐席|话术", "客服业务", 0.7),
]

# 中文 AI 核心能力（大模型/智能体/RAG/语音/视觉/推荐/预测等成熟能力）
ZH_AI_PATTERNS = [
    (r"大模型|大语言模型|语言模型|通义千问|千问|文心|星火|豆包|kimi|智谱|chatglm|deepseek|qwen|百炼|魔搭|pai",
     "中文大模型能力", 0.95),
    (r"智能体|agent|多智能体|工作流编排|工具调用|mcp", "中文智能体编排", 0.9),
    (r"rag|检索增强|向量检索|知识库问答|知识图谱|语义检索|embedding", "中文RAG/知识检索", 0.9),
    (r"语音识别|语音合成|语音转写|语音交互|asr|tts|会议纪要|转写|字幕", "中文语音处理", 0.9),
    (r"图像识别|目标检测|人脸识别|ocr|视觉|图片识别|图像分割", "中文图像识别", 0.85),
    (r"自然语言处理|nlp|文本分类|情感分析|实体抽取|意图识别|文本摘要|语义分析", "中文语义分析", 0.8),
    (r"对话|问答|聊天机器人|客服机器人|助手", "中文对话问答", 0.8),
    (r"推荐|召回|个性化", "中文推荐系统", 0.8),
    (r"预测|风控|异常检测|预警|评估", "中文预测分析", 0.8),
    (r"翻译|多语言|多语种", "中文翻译转写", 0.75),
    (r"视频理解|视频分析|多模态|图文", "中文多模态/视频", 0.8),
    (r"提示词|微调|prompt|大模型应用|ai应用|智能化|自动生成|自动化", "中文大模型工程/自动化", 0.6),
]

# 中文商业推广（产品/解决方案发布、试用引导）
ZH_AD = [
    (r"限时|优惠|立减|立即购买|现在下单|扫码|添加.{0,4}(客服|助理)|咨询客服|"
     r"解决方案提供商|行业首选|官方旗舰|预约演示|领取.{0,4}(资料|名额)|首发价|官网价|促销", "中文商业推广", 1.0),
]

# 中文语域：教程/科普、资讯、社区讨论
ZH_TUTORIAL = [
    (r"教程|入门|从零开始|手把手|保姆级|零基础|学习路线|速成|一篇(搞懂|学会|看懂)|如何学习|浅谈|科普|概念|原理|"
     r"概述|发展趋势|前景|一文(读懂|了解)|全解析|导读|读书笔记", "中文教程/科普", 1.0),
]
ZH_TUTORIAL_TITLE = [
    (r"教程|入门|从零开始|手把手|零基础|一篇(搞懂|学会|看懂)|浅谈|科普|原理|概述|全解析|万字|盘点|汇总|合集|清单|避坑|踩坑",
     "中文教程标题", 1.0),
]
ZH_NEWS = [
    (r"报道|据悉|获悉|记者|宣布|官宣|发布会|分析师|融资|投资大会|接受(媒体)?采访|表示|笑称|"
     r"赛迪|证券时报|据.*消息|资本市场|估值|市值|营收|财报", "中文资讯体裁", 0.8),
]

# 开发者工具/组件供给侧：memory / gateway / registry / skill / toolkit / 组件 / 网关 …
# 面向工程师复用，不等于"面向终端用户的业务需求"
DEV_SUPPLY_PATTERNS = [
    (r"\bmemory (store|system|hub|layer)\b|\bgateway\b|\bregistry\b|\bskill(set|s)?\b|\btoolkit\b|"
     r"\bplugin\b|\bextension\b|\bboilerplate\b|\btemplate\b|\bwrapper\b|\bsdk\b|"
     r"记忆(存储|系统|中枢|层)|网关|注册表|技能包|插件|扩展|组件库|模板|脚手架|工具链", "开发者组件/供给侧", 1.0),
    (r"\bfor (developers|engineers)\b|\bdeveloper (tool|first)\b|面向(开发者|工程师)|\bdevtools?\b",
     "明确面向开发者", 0.85),
]

# 模型供给：模型仓库本身不是应用机会（题面③要求"无需自研模型"）
MODEL_SUPPLY_PATTERNS = [
    (r"\bmodels?\b.*(checkpoint|weights|inference|serving|repository)|\bpretrained model\b|"
     r"\bmodel (zoo|hub|card)\b|\bwe release\b|\bopen[- ]?sourc(e|ed) .{0,20}model\b|"
     r"模型仓库|模型权重|预训练模型发布|开源模型发布|\bfoundation model\b", "模型供给", 1.0),
    (r"\b(asr|tts|ocr|llm|vlm)\b.*\bmodel\b|\bmodel\b.*\b(asr|tts|ocr|vlm)\b", "模型仓库", 0.55),
]

# 中文科普/综述/技术方案介绍：介绍"某领域有哪些 AI 应用"不等于提出需求
ZH_SCIENCE_PATTERNS = [
    (r"综述|盘点|浅析|应用现状|发展现状|未来方向|研究进展|发展趋势|行业趋势|"
     r"在.{0,8}领域的关键应用|在.{0,8}中的应用|"
     r"技术介绍|技术原理|方案介绍|科普|入门|什么是|入门到|知识图谱构建方案|技术解析",
     "中文科普/综述", 0.9),
]

# 资讯转述（报道他人观点）不构成需求
ZH_NEWS_OPINION = [
    (r"表示|认为|指出|强调|提到|称|报道|获悉|据.{0,6}(消息|报道)|峰会|大会|论坛|发布会", "中文资讯转述", 0.7),
]

# 项目/DOC 体裁：仓库介绍、最佳实践、技术选型说明等，缺少可观察的终端用户需求
DOC_PATTERNS = [
    (r"best practice|最佳实践|实践指南|指南|白皮书|方案介绍|功能介绍|产品介绍|架构设计|技术选型|选购指南|评测对比|深度解析|解读|盘点|汇总|合集|清单|awesome|roadmap|changelog|release notes",
     "项目/文档体裁", 1.0),
    (r"free|open[- ]?source|开源|免费|内置|支持|提供|集成|适用于|面向|帮助用户|赋能|助力|打造|构建一个|一站式|开箱即用",
     "产品/项目介绍语", 0.55),
]

# 开发者侧资产/框架信号：面向工程师的工具、框架、SDK、技能包、基础模型等，
# 属"供给侧"要素而非终端业务需求（题面要求"面向明确的终端用户或业务场景"）
DEV_ASSET_PATTERNS = [
    (r"framework|框架|\bsdk\b|playground|meta-?harness|observability|平台框架|\bskills\b|技能|合集|awesome|模板|boilerplate|starter|examples?\b|\bdemo\b",
     "开发工具/资产框架", 1.0),
    (r"open[- ]?source|\boss\b|self[- ]?hosted|built and used in production|model family|模型系列|系列模型|foundation model|基础模型|开源大模型|开源模型|underlying model|底层模型",
     "开源资产/基础模型供给", 0.6),
]

# ② AI 核心能力（与现代成熟 AI 能力对应）
AI_CORE_PATTERNS = [
    (r"大模型|大语言模型|\bllm\b|\bgpt\b|gemini|claude|qwen|deepseek|chatgpt|通义|文心|kimi|豆包|chatglm|mistral|llama",
     "大模型能力", 1.0),
    (r"\brag\b|检索增强|向量检索|embedding|语义检索|知识库问答|知识图谱", "RAG/知识检索", 0.9),
    (r"智能体|\bagents?\b|multi-?agent|tool calling|function calling|\bmcp\b|autogen|crewai", "智能体编排", 0.9),
    (r"语音识别|语音转文字|speech[- ]?to[- ]?text|\basr\b|文字转语音|\btts\b|whisper|会议纪要",
     "语音/音频处理", 0.9),
    (r"\bocr\b|图像识别|目标检测|yolo|人脸识别|图片分类|图像分割|object detection|image recognition|computer vision",
     "图像识别", 0.85),
    (r"自然语言处理|\bnlp\b|文本分类|情感分析|sentiment|命名实体|\bner\b|意图识别|文本摘要|summariz",
     "语义分析", 0.8),
    (r"对话|chatbot|聊天机器人|\bqa\b|客服机器人|\bbot\b|助手|assistant", "对话问答", 0.8),
    (r"推荐|recommend|召回|个性化", "推荐系统", 0.8),
    (r"预测|forecast|风险评估|风控|异常检测|anomaly", "预测分析", 0.65),
    (r"工作流编排|流程编排|\bworkflow\b|\brpa\b|批处理", "自动化流程", 0.45),
    (r"机器翻译|machine translation|字幕|转写|transcri", "翻译转写", 0.75),
    (r"视频理解|视频分析|video understanding", "视频处理", 0.6),
    (r"多模态|multimodal|视觉语言|\bvlm\b", "多模态融合", 0.85),
    (r"prompt|提示词|fine[- ]?tun|微调|system prompt", "大模型工程能力", 0.5),
]

# ③ 可落地证据：是否由成熟零件组成（API/SDK、开源预训练模型、轻量适配、可部署）
FEASIBLE_PATTERNS = [
    (r"\bapi\b|openai|azure|aws|阿里云|腾讯云|百度智能云|huggingface|hugging face|ollama|vllm|langchain|llamaindex|\bsdk\b",
     "现有 API/SDK", 0.75),
    (r"开源|open[- ]?source|github|预训练|pretrained|现成的|已有模型|lower[- ]?cost|低成本", "开源/预训练模型", 0.7),
    (r"微调|fine[- ]?tune|提示词|prompt|few[- ]?shot|低代码|插件", "轻量适配", 0.55),
    (r"部署|docker|本地部署|私有化|on[- ]?prem", "可部署", 0.55),
]

# ④ 排除情形
EXCL_TUTORIAL = [
    (r"教程|入门|从零开始|手把手|保姆级|学习路线|零基础|速成|一篇(搞懂|学会)|如何学习|浅谈|科普|概念|原理|概述|发展趋势|前景|一文(读懂|了解)|详解|指南|SOP",
     "教程/科普", 1.0),
    (r"tutorial|getting started|step[- ]?by[- ]?step|guide to|explained|primer|best practice guide|how[- ]?to (use|write|learn|start|get started)",
     "教程/科普(英)", 0.9),
]
EXCL_AD = [
    (r"购买|下单|优惠|折扣|立减|限时|注册送|优惠券|促销|团购|招商|加盟|咨询客服|扫码|加微|官方旗舰|售价|抢购",
     "商业推广", 1.0),
    (r"buy now|sign up (now|today)|limited (time|offer)|discount|coupon|free trial", "商业推广(英)", 0.9),
]
EXCL_HYPE = [
    (r"震惊|颠覆|炸裂|吊打|封神|YYDS|全网首发|史上最强|遥遥领先|杀疯了|引爆|躺赚|月入|风口",
     "营销噱头", 1.0),
    (r"revolutionary|game[- ]?changer|unprecedented|will change everything", "营销噱头(英)", 0.85),
]

ASK_MARKERS = [r"\?", r"？", r"\bhow (to|do|can|should)\b", r"\bwhat is\b", r"\bwhy\b", r"\berror\b",
               r"\bfailed\b", r"\bnot working\b", r"\bissue\b", r"\bproblem\b"]


class _DomainNeg:
    """非 AI 应用领域识别：文本主体属于"技术/工程/资讯"而非"业务需求"，AI 只是被提及的词。"""

    patterns = [
        # 英文技术工程语域
        (r"gcc|clang|\bcompile[sd]?\b|copy constructor|segmentation fault|linker|cmake|makefile",
         "编译/构建问题", 1.0),
        (r"\bflutter\b|scrollbar|\bcss\b|\bhtml\b|xml file|serializefield|monobehaviour|\bunity\b|\bwebkit\b|\bselector\b|\bdiv\b|布局|样式表",
         "前端/游戏引擎实现细节", 0.85),
        (r"playwright|selenium|distutils|pip install|install fails|tailscale|docker error|\\bspotip(y|yexception)\\b|\\bhttp status (4\\d\\d|5\\d\\d)\\b",
         "工具链/运维配置", 0.85),
        (r"laravel|django admin|flask app with sqlite|sqlite database|invalidindexerror|\bdataframe\b|\bpandas\b",
         "通用框架/数据处理语法", 0.9),
        # 中文技术工程语域（对应 Stack Overflow / 开发者社区问答）
        (r"报错|异常|堆栈|编译|依赖|版本冲突|安装失败|环境配置|调参|显存|张量|维度不匹配|梯度|损失函数|反向传播",
         "中文技术工程问题", 0.85),
        (r"代码报错|异常栈|堆栈|编译错误|依赖冲突|版本不兼容|配置文件|日志报错|显存不足", "中文开发实现细节", 0.7),
    ]

    def saturate(self, haystack):
        hits = _hits(self.patterns, haystack)
        self._last = hits
        return saturate([h["strength"] for h in hits])


DOMAIN_PATTERNS_NEG = _DomainNeg()

# 资讯/报道体裁：描述"发生了什么"，而非"用户需要什么"
# 资讯体裁（行业报道/通稿）：只取新闻写作特征词，不含 problem/issue/report 等问答高频词
NEWS_MARKERS = [r"发布|上线|宣布|亮相|据悉|官宣|美媒|消息人士|内部人士|报道称|记者",
                r"\bannounc|press release|sources say|reported that|according to"]

SOURCE_CATEGORY = {
    "Stack Overflow": "问答与需求社区", "V2EX": "问答与需求社区", "阿里云开发者社区": "问答与需求社区",
    "GitHub": "开源项目与产品社区", "Product Hunt": "开源项目与产品社区",
    "CSDN": "技术内容与教程社区", "掘金": "技术内容与教程社区", "InfoQ中国": "技术内容与教程社区",
    "少数派": "技术内容与教程社区",
    "36氪": "科技与AI垂直资讯", "量子位": "科技与AI垂直资讯", "机器之心": "科技与AI垂直资讯",
    "IT之家": "科技与AI垂直资讯",
    "哔哩哔哩": "视频与内容社区",
    "Kaggle": "竞赛与数据集平台", "天池": "竞赛与数据集平台",
    "DataFountain": "竞赛与数据集平台", "数睿思": "竞赛与数据集平台",
    "腾讯新闻": "行业机构资讯", "中国医药创新促进会": "行业机构资讯",
}
SOURCE_RELIABILITY = {
    "问答与需求社区": 0.95, "开源项目与产品社区": 0.70, "技术内容与教程社区": 0.50,
    "科技与AI垂直资讯": 0.40, "视频与内容社区": 0.50, "学术论文与预印本": 0.45,
    "竞赛与数据集平台": 0.65, "行业机构资讯": 0.35, "其他": 0.50,
}


def saturate(strengths):
    """多证据饱和叠加：单一证据保底，避免词频堆砌主导结果。"""
    comp = 1.0
    for s in strengths:
        comp *= 1.0 - min(0.92, s)
    return 1.0 - comp


def _hits(patterns, haystack, ascii_only_words=False):
    out = []
    for pat, label, strength in patterns:
        m = re.search(pat, haystack, re.I)
        if m:
            out.append({"label": label, "strength": strength, "span": m.group(0)})
    return out


def _has(haystack, markers):
    return any(re.search(p, haystack, re.I) for p in markers)


def _clean_title(title):
    """标题清洗：只处理 HTML 实体与多余空白，不改变语义。"""
    import html as _html
    t = _html.unescape(title or "")
    return re.sub(r"\s+", " ", t).strip()


def _title_tutorial_guard(title: str, ask: bool) -> bool:
    """标题层面的教程词（"xxx 教程"、"xxx 指南"）不足以作为排除依据：
    解答类标题里的 "how-to" 等词不改变记录性质。"""
    return not re.search(r"教程|指南|科普|原理|详解|入门|overview|guide", title, re.I)


def classify_opportunity(title: str, body: str, source_name: str) -> dict:
    """对单条记录做四维判别，返回判别结果与完整证据链。"""
    title = _clean_title(title)
    body = re.sub(r"\s+", " ", body or "").strip()
    # 平台模板噪声（阅读/点赞/收藏/推荐/收录等计数与导航），只用于语域判定时剔除，
    # 不改变记录内容本身（证据链仍保留原文快照）
    body_for_genre = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>|\{[^}]{0,200}\}\s*;?", " ", body, flags=re.S | re.I)
    body_for_genre = re.sub(
        r"文章浏览阅读[\d.]+[k万]?次[，,][^。]{0,40}。?|点赞\d+[，,]?|收藏\d+[，,]?|评论\d+[，,]?|"
        r"阅读[\d.]+[k万]?|当前文章被[收录于以下][^。]{0,40}|收录于[^。]{0,20}|"
        r"\[?已赞\]?|分享.*?举报", " ", body)
    text = f"{title} {title} {body}"
    text_genre = f"{title} {title} {body_for_genre}"
    low = text.lower()
    cat = SOURCE_CATEGORY.get(source_name, "其他")
    ask = _has(low, ASK_MARKERS)
    news = _has(low, NEWS_MARKERS)
    is_qa_source = cat == "问答与需求社区"

    # 文本语种判定：中文字符占比（用于选择中文/英文词表与语域规则）
    zh_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    # 中英混排的中文记录（如"大模型 + LangChain"）同样适用中文词表：
    # 只要中文字符达到 20 个且占比 ≥ 5%，或中文字符 ≥ 60 个，即视为中文语境
    is_zh = (zh_chars >= 20 and zh_chars >= 0.05 * max(1, len(text.replace(" ", "")))) or zh_chars >= 60
    zh_tut = _hits(ZH_TUTORIAL, text_genre) if is_zh else []
    zh_news = _hits(ZH_NEWS, text_genre) if is_zh else []

    # 项目/产品型表述（面向终端用户的产品，而非单一技术工具）
    github_pre = "github.com" in re.sub(r"\s+", "", text)
    is_project = bool(re.search(r"software|crm|ticketing|helpdesk|assistant|platform|app|analy|"
                                r"customer[- ]?(service|support)|chatbot|co-?pilot", low))
    product_like = bool(re.search(r"assistant|chatbot|chat bot|co-?pilot|copilot|platform|software|"
                                  r"\bapp\b|\bservice\b|agent for|\btoolkit\b", low))
    # ---------------- ④ 排除情形 ----------------
    ex = []
    for block in (EXCL_TUTORIAL, EXCL_AD, EXCL_HYPE):
        ex += _hits(block, low)
    if is_zh:
        ex += _hits(ZH_AD, text)
        # 资讯/专访中的转述式夸张词（"颠覆""风口""炸裂"）不构成 AI 营销噱头；
        # 只有同时出现销售引导词时才算推广
        if zh_news or re.search(r"专访|采访|表示|报道|分析|观察|评论", text_genre):
            ex = [h for h in ex if not (h["label"] == "营销噱头" and h["strength"] <= 1.0)]
    ex += zh_tut
    if is_zh:
        zh_sci = _hits(ZH_SCIENCE_PATTERNS, text_genre)
        zh_opinion = _hits(ZH_NEWS_OPINION, text_genre)
        ex += zh_sci
        # 资讯转述只有在记录确为报道体裁时才算排除，避免误伤正常方案介绍
        if zh_news and zh_opinion:
            ex.append({"label": "中文资讯转述", "strength": 0.8, "span": "news"})
    excl = saturate([h["strength"] for h in ex])
    # 注意：下面的 github 折扣会重算 excl，因此"工具型/官网"等后置规则必须改 ex 列表，不能只改 excl
    # 教程词与"提问求解决"共现时，排除强度衰减（如"请问这个教程示例报错怎么修"）；
    # 开发者本人正在做项目、提出工程问题的提问，其 how-to / best practice 词属提问方式而非内容体裁
    title_low = title.lower()
    dev_ask = re.search(r"\b(i'm|i am|we are|my|i've|we've)\b|\bi was\b|\bi have\b|\bi want\b|\bi need\b|我正在|我在|我们正在|我的",
                        low)
    # 标题层面的教程词（"xxx 教程/指南/科普"）说明文章体裁就是教程；正文里的 how-to 多为提问方式
    repo_ctx = "github.com" in low
    if ex and not repo_ctx and re.search(r"教程|指南|科普|原理|详解|入门|overview|guide|tutorial", title_low):
        excl = 1.0
    elif ex and (ask or dev_ask):
        excl *= 0.30 if (ask and dev_ask) else 0.6
    elif ex and repo_ctx:
        excl *= 0.7
    # 中文教程/科普标题（含"最佳实践""详解""万字""盘点"等）说明文章体裁就是教程 → 直接判 0
    zh_need_pre = _hits(ZH_NEED_PATTERNS, text) if is_zh else []
    zh_need_sig = saturate([h["strength"] for h in zh_need_pre])
    zh_tech_ask = bool(re.search(r"如何|怎么|报错|异常|配置|部署|安装|报错", title))
    if zh_tut and not zh_tech_ask and zh_need_sig < 0.8 and re.search(r"教程|入门|科普|原理|详解|最佳实践|指南|万字|盘点|汇总|合集|全解析|干货|收藏",
                                                title):
        # 标题即教程/科普体裁：直接排除；但若正文明确描述真实痛点且给出可落地方案，降为 E=0.6（仍判 0，进复核队列）
        excl = 1.0 if zh_need_sig < 0.8 else 0.6
    # 商业产品/内容分发体裁（"免费技能包""平台""合集"）：属推广与内容分发，非需求表达
    if re.search(r"免费|\bfree\b|平台|合集|技能包|一键同步|引流|付费|\bbuy\b|优惠", low) and re.search(
            r"skills?\b|技能|合集|平台|pack|工具包", low):
        ex.append({"label": "内容分发/推广", "strength": 0.45, "span": "平台/合集"})
    # 商业闭源产品官网（Marketing/定价页特征）：属商业推广
    if (not github_pre) and re.search(r"官网|our product|pricing|contact sales|免费试用|立即体验|预约演示|咨询客服", low) and re.search(
            r"license|订阅|收费|方案的唯一|唯一方案|最佳选择|行业领先", low):
        ex.append({"label": "商业推广(产品官网)", "strength": 1.0, "span": "官网"})
    # 开发者组件/模型供给：属"工具/模型供给侧"，面向工程师复用，不是面向终端用户的应用机会
    dev_supply = _hits(DEV_SUPPLY_PATTERNS, low)
    model_supply = _hits(MODEL_SUPPLY_PATTERNS, low)
    supply_sig = saturate([h["strength"] for h in dev_supply])
    model_sig = saturate([h["strength"] for h in model_supply])
    # 只有当记录没有明确的业务场景锚定（客服/医疗/法律/电商…）时，才按供给侧排除
    has_biz_anchor = bool(re.search(
        r"customer|customer service|客服|patient|医疗|legal|法律|contract|合同|recruit|招聘|e-?commerce|电商|"
        r"education|教育|logistics|物流|finance|金融|insurance|保险|appointment|预约", low))
    if dev_supply and supply_sig >= 0.5 and not has_biz_anchor:
        ex.append({"label": "开发者组件/工具供给", "strength": 1.0, "span": "supply"})
    # 模型供给：只有原句就是"发布/开源某模型"这类仓库描述，且无业务场景时才算供给
    model_release = re.search(
        r"\b(model|models)\b.*\b(release|release\s*d|weights|checkpoint|repo|repository)\b|"
        r"\b(release|open[- ]?sourc)\w* .{0,25}\b(model|models)\b|模型(仓库|权重|发布)", low)
    if model_supply and model_sig >= 0.5 and (model_release or not has_biz_anchor):
        ex.append({"label": "模型供给", "strength": 1.0, "span": "model"})

    # 个人/单模块工具型记录：标题与全文只描述一个工具或一句话产品定位，缺少业务痛点与使用场景
    github = "github.com" in low
    # 开源项目记录：需求强度已由 R 侧统一打折，此处不再叠加排除（避免重复计权导致系统性漏判）
    excl = saturate([h["strength"] * (0.6 if github else 1.0) for h in ex])
    tool_like = bool(re.search(r"\b(tool|utility|helper|cli|command[- ]line|extension|plugin)\b|工具", low))
    if tool_like and not github and not is_project and not re.search(
            r"pain|痛点|耗时|takes (hours|days|weeks)|效率低|总不能|手动|手工|customer|客户|业务", low):
        ex.append({"label": "单工具型描述", "strength": 0.55, "span": "tool"})
        excl = saturate([h["strength"] * (0.6 if github else 1.0) for h in ex])
    gate_ok = excl < GATE_EXCL

    # ---------------- ① 真实需求 ----------------
    need = _hits(NEED_PATTERNS, low)
    # 开发者工程问题（报错/异常/部署失败/版本冲突等）→ 需求信号按"技术问题"处理，不作为业务需求
    tech_issue = re.search(
        r"\berror\b|\bexception\b|\btraceback\b|\bfailed\b|\bfails?\b|not working|doesn't work|"
        r"\bissue\b|\bbug\b|\bhow (do|can|should) i\b|\bwhy (does|is|do)\b|\bi'm trying to\b|"
        r"\bi am trying to\b|报错|异常|失败|无法|不生效|不工作|怎么(改|修|解决)|为什么", low)
    if tech_issue:
        need = [h for h in need if h["strength"] <= 0.5]
    scene = _hits(SCENE_PATTERNS, low)
    if is_zh:
        need += _hits(ZH_NEED_PATTERNS, text)
        scene += _hits(ZH_SCENE_PATTERNS, text)
    doc = _hits(DOC_PATTERNS, low)
    need_sig = saturate([h["strength"] for h in need])
    scene_sig = saturate([h["strength"] * 0.9 for h in scene])
    doc_sig = saturate([h["strength"] for h in doc])
    dev = _hits(DEV_ASSET_PATTERNS, low)
    dev_sig = saturate([h["strength"] for h in dev])
    # 开发者工具/框架/基础模型：供给侧资产，需求强度打折（真实业务需求仍可保留部分证据）
    dev_factor = 0.40 if re.search(r"framework|框架|\bsdk\b|harness|observability|\bskills\b|技能",
                                   low) else 0.70
    # 需求强度 = 需求信号 × 场景锚定；二者缺一都大幅衰减
    need_score = (0.55 * need_sig + 0.45 * scene_sig) * (1.0 - 0.55 * doc_sig)
    # 提问形态是需求信号的最强形态；陈述形态需同时具备需求信号与场景锚定，
    # 否则只保留"产品介绍"级的弱证据（避免把项目/产品介绍误判为真实需求）
    if ask and not news:
        need_score = min(1.0, need_score + 0.12) * (1.0 - 0.3 * doc_sig)
    else:
        need_score *= (0.40 + 0.60 * min(need_sig, scene_sig)) * (1.0 - 0.5 * doc_sig)
    if (news or zh_news) and not ask:
        need_score *= 0.7
    # 中文"如何实现/如何选型"属技术提问而非业务痛点：需求强度不享受提问加成
    if is_zh and re.search(r"如何(实现|选型|配置|部署|使用|训练|调用|解决报错)", text):
        need_score *= 0.85
    # 技术语域程度（编译/报错/接口等）：只降低"需求信号"权重，不用来判定"是否 AI 领域"
    ctx_tech = 1.0 - DOMAIN_PATTERNS_NEG.saturate(low)
    need_factor = (0.45 + 0.55 * ctx_tech) if not (news or zh_news) else 0.85
    need_score = max(0.0, min(1.0, need_score * need_factor))
    if dev_sig:
        need_score *= (1.0 - (1.0 - dev_factor) * dev_sig)
    if is_qa_source and ask:
        need_score = max(need_score, min(1.0, 0.45 + 0.35 * need_sig + 0.2 * scene_sig))
    if tech_issue:
        # 有明确业务场景（客服/医疗/电商…）的技术问题保留部分需求证据；纯技术报错压到很低
        need_score *= 0.62 if has_biz_anchor else 0.28
    # 业务场景与问题表述：需求信号必须锚定在具体问题或业务语境上，不能把"提到某能力"当成"提出需求"
    if need_sig < 0.6 and len(scene) < 2 and not (ask and scene):
        need_score *= 0.75
    # 业务语境（generic business context）不足以构成场景锚定：它同样会出现在"用 AI 的开发者技术问题"里
    concrete_scene = [h for h in scene if h["label"] not in ("业务语境", "英文业务语境", "中文业务语境",
                                                             "办公协作场景", "中文办公协作场景")]
    concrete_sig = saturate([h["strength"] * 0.9 for h in concrete_scene])
    biz = _hits(BUSINESS_SCENE_PATTERNS, low)
    if is_zh:
        biz += _hits(BUSINESS_SCENE_PATTERNS, text)
    biz_sig = saturate([h["strength"] for h in biz])
    # 用户侧信号（stars 数）：说明"有人真的在用"，属于需求侧证据（R），不抬高可落地性（F）
    user_sig = 0.0
    for m in re.finditer(r"星标\s*(\d+)|\b(\d[\d,]*)\s*stars?\b|stars?\s*[:：]?\s*(\d+)", low):
        num = next(g for g in m.groups() if g)
        n = int(num.replace(",", ""))
        user_sig = 1.0 if n >= 1000 else (0.75 if n >= 300 else 0.55 if n >= 100 else 0.40 if n >= 30 else 0.25)
        break
    prior_concrete = concrete_sig
    concrete_sig = max(concrete_sig, biz_sig)
    # 产品型描述：业务功能词 + 产品表述 = 面向明确用户的业务场景（题面①）
    # 但"文档/清单"体裁（best practice、示例、合集）本身不构成需求，不享受该下限
    if is_project and product_like and concrete_sig >= 0.4 and doc_sig < 0.4:
        need_score = max(need_score, 0.66 * concrete_sig)
    # 用户侧采纳信号参与需求强度（最高 +0.15），已声明业务场景的成熟项目因此得以进入机会集
    if user_sig:
        need_score = min(1.0, need_score + 0.15 * user_sig * (0.6 + 0.4 * max(concrete_sig, prior_concrete)))
    elif is_project and concrete_sig >= 0.4 and product_like and need_sig >= 0.3:
        need_score = max(need_score, 0.66 * concrete_sig)
    elif concrete_scene and not re.search(r"\b(i'm|i am|my project|i am trying)\b", low):
        need_score = max(need_score, 0.55 * concrete_sig)   # 项目/产品描述里出现具体业务场景

    # ---------------- ② AI 是否核心 ----------------
    # A 置信度 = P(AI 为解决方案核心 | 面向 AI 应用领域) × 记录是否面向 AI 应用领域
    ai = _hits(AI_CORE_PATTERNS, low)
    if is_zh:
        ai += _hits(ZH_AI_PATTERNS, text)
    ai_evidence = saturate([h["strength"] for h in ai])
    # 纯软件开发工具链（含"用 AI 做代码生成/代码审查"的编码代理）：服务于软件工程本身，
    # 而不是某个业务的 AI 应用。此类记录在 F（可落地）维度打折，避免被误判为行业机会。
    devtool_ctx = bool(re.search(r"\bcodegen\b|code review|code-review|\bide\b|vscode|developer workflow|"
                                 r"plan-first|pull request|refactor", low))
    if ai_evidence == 0 and re.search(r"\bai\b|人工智能|machine learning|机器学习|deep learning|深度学习", low):
        ai_evidence = 0.30  # 只提 AI 字样属弱证据，不足以单独支撑"AI 为核心"
    ai_score = ai_evidence  # 该记为 P(AI 为解决方案核心 | 记录在讲 AI 应用)

    # ---------------- ③ 技术可落地 ----------------
    feas = _hits(FEASIBLE_PATTERNS, low)
    feas_sig = saturate([h["strength"] for h in feas])
    # F 置信度 = 已由成熟零件构成 × AI 能力可对应 × 记录面向 AI 领域
    feas_score = 0.55 * feas_sig + 0.45 * min(1.0, ai_evidence + 0.2)
    if re.search(r"自研基础模型|海量标注|万亿参数|训练自己的大模型|从零训练", low):
        feas_score *= 0.5
    if devtool_ctx:
        feas_score *= 0.55
    if re.search(r"ai, chinese|模型系列|series of \w+ models|语言与视觉|多模态大模型|large \w+\s*-\s*vision assistant|underlying model",
                 low):
        feas_score *= 0.6  # 基础模型/模型系列研发，非成熟能力直接落地
    # 开发者技术谈（编译/报错/接口实现等）且没有业务场景锚定时，AI 不是解决"业务问题"的手段 → 判 0
    off_domain = (ctx_tech < 0.25) and scene_sig < 0.45 and not (news or zh_news)
    if off_domain and ai_evidence >= 0.8 and concrete_sig >= 0.4 and not re.search(
            r"scrollbar|\bcss\b|\bhtml\b|compile|gcc|c\+\+|pip install|install fail|"
            r"version|兼容|报错堆栈|依赖冲突", low):
        # 讲 AI 应用实现的技术问题（AI 能力强 + 有具体业务场景）仍属机会线索
        off_domain = False

    # 项目/产品级最小规模校验：可用成熟 AI 能力落地的应用至少需要一个模块级说明
    # （直接的软件项目除外：其需求强度已体现在 R 中）
    thin = len(re.sub(r"\s+", "", title + body)) < 50 and not (is_project and scene_sig >= 0.4)
    thin = thin or bool(re.search(r"[🚂🚋🚘🚒🚃🚁⛴🚟✈🛼🚀🛫🚎🚅🕍🕌🏰🏨]", low))
    # 基础模型/模型系列研发：属模型供给侧，不是可直接落地的应用机会
    if re.search(r"\bmodel series\b|foundation model|基础模型|模型系列|系列模型|大模型研发|\bllm\d?\b.*series", low):
        off_domain = True

    # ---------------- 记录可信度 Q ----------------
    src_rel = SOURCE_RELIABILITY.get(cat, 0.5)
    q = (0.7 * src_rel
         + 0.15 * (1.0 if len(title) >= 12 else 0.6)
         + 0.15 * (1.0 if len(body) >= 60 else (0.7 if body else 0.4)))

    # ---------------- 合成判别置信度 ----------------
    pos = (W["need"] * need_score + W["ai_core"] * ai_score
           + W["feasible"] * feas_score + W["reliability"] * q)
    conf = pos * (1.0 - DELTA_EXCL * excl)
    conf = min(1.0, max(0.0, conf))
    # 规则①前置门槛：真实需求维度必须成立（有需求信号或已锚定的业务场景），
    # 否则即便 AI 能力与可落地性很强，也不构成"AI 应用机会"
    need_ok = need_score >= NEED_GATE
    is_opp = 1 if (gate_ok and need_ok and not off_domain and not thin and conf >= DECISION_TAU) else 0
    if thin:
        conf = min(conf, DECISION_TAU - 0.05)
    # 输出置信度与判定保持单调：判 1 → ≥0.5 且随证据增强；判 0 → <0.5
    # 判 1：置信度 = 证据分（≥ 阈值）；判 0：按证据分占阈值比例映射到 [0.01, 0.49]，保证"数值越大越可能是机会"的单调性
    # 判 0 的置信度必须 < 判 1 的置信度下限（DECISION_TAU），避免"置信度很高却判 0"的自相矛盾：
    # 被门控（排除情形/技术细节/信息不足）否决时，证据分先压缩到阈值以下，再线性映射到 [0.01, τ-0.01]
    if is_opp:
        confidence = conf
    else:
        capped = min(conf, DECISION_TAU)
        confidence = 0.01 + (DECISION_TAU - 0.02) * (capped / DECISION_TAU)
        if not gate_ok:
            confidence = min(confidence, 0.01 + (DECISION_TAU - 0.02) * (1.0 - excl))
    confidence = round(min(0.99, max(0.01, confidence)), 4)

    # ---------------- 否决/通过理由 ----------------
    if not gate_ok:
        rule = "④排除情形"
        reason = "命中排除情形（" + "、".join(sorted({h["label"] for h in ex if h["label"]})) + "），按题面规则直接判 0"
    elif not need_ok:
        rule = "①缺真实需求"
        reason = "记录未出现可观察的需求信号，也未锚定到具体业务场景，AI 能力再强也不构成应用机会"
    elif off_domain:
        rule = "②③非AI领域问题"
        reason = "记录属技术实现/调试细节（编译构建、前端渲染、工具链、通用语法等），面向的是开发者而非终端业务用户，AI 不是解决业务问题的手段"
    elif thin:
        rule = "①信息不足"
        reason = "文本仅含标题或符号堆砌，缺少可观察的需求信号与业务场景，无法判定为真实需求"
    elif conf < DECISION_TAU:
        weak = []
        if need_score < 0.45:
            weak.append("缺少可观察的真实需求信号")
        if ai_score < 0.45:
            weak.append("AI 非核心手段")
        if feas_score < 0.50:
            weak.append("技术可落地性不足")
        rule = "①②③证据不足"
        reason = "；".join(weak) or "综合证据强度低于判定阈值"
    else:
        rule = "①②③④全部通过"
        reason = "存在明确业务场景与需求信号，AI 为解决问题核心手段，且可用成熟能力落地"

    return {
        "is_opportunity": is_opp,
        "confidence": confidence,
        "decision_rule": rule,
        "decision_reason": reason,
        "need_score": round(need_score, 4),
        "ai_score": round(ai_score, 4),
        "feasible_score": round(feas_score, 4),
        "exclusion_score": round(excl, 4),
        "doc_score": round(doc_sig, 4),
        "reliability": round(q, 4),
        "evidence": {
            "need": sorted({h["label"] for h in need} | {h["label"] for h in scene}),
            "ai": sorted({h["label"] for h in ai}),
            "feasible": sorted({h["label"] for h in feas}),
            "exclusion": sorted({h["label"] for h in ex}),
            "doc": sorted({h["label"] for h in doc}),
            "zh_tutorial": sorted({h["label"] for h in zh_tut}),
            "zh_news": sorted({h["label"] for h in zh_news}),
        },
    }


def review_flag(entry: dict) -> bool:
    """人工复核队列：高置信度分界带、排除边界、分类冲突样本。"""
    c = entry["confidence"]
    if entry["is_opportunity"] == 1 and c < MANUAL_REVIEW_LO:
        return True
    if entry["is_opportunity"] == 0 and c > DECISION_TAU - REVIEW_BAND:
        return True
    cat = entry.get("category") or {}
    if entry["is_opportunity"] == 1 and cat.get("category_confidence", 1.0) < 0.55:
        return True
    return False


def content_digest(title: str, body: str) -> str:
    """记录级指纹：用于重复运行一致性校验（不修改任何数据）。"""
    return hashlib.sha256(f"{title}\n{body}".encode("utf-8")).hexdigest()