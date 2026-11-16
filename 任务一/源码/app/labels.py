# -*- coding: utf-8 -*-
"""官方附件1标签体系：16 个功能类别 + 30 个所属行业，及各自关键词（中英文）。

标签名严格对齐《附件1.xlsx》，不得改名；关键词用于任务二的功能/行业归类。
英文关键词在分类器中以整词边界匹配，避免短词误命中。
"""

# ============ 16 个功能类别（顺序对齐附件1） ============
FUNCTION_LABELS = [
    "图像识别", "语义分析", "语音处理", "文本生成", "对话问答", "推荐系统",
    "知识检索", "数据挖掘", "多模态融合", "智能体编排", "自动化流程", "预测分析",
    "审核审查", "搜索匹配", "翻译转写", "视频理解",
]

# 每个功能：中文关键词 + 英文关键词（小写）
FUNCTION_KEYWORDS = {
    "图像识别": {
        "zh": ["图像识别", "图像分类", "目标检测", "人脸识别", "图像分割", "缺陷检测",
               "视觉检测", "文字识别", "ocr", "车牌识别", "遥感识别"],
        "en": ["image recognition", "object detection", "face recognition",
               "image classification", "image segmentation", "defect detection",
               "computer vision", "ocr", "optical character recognition"],
    },
    "语义分析": {
        "zh": ["语义分析", "情感分析", "情感倾向", "文本分类", "实体识别", "命名实体",
               "关系抽取", "意图识别", "语义理解", "文本理解", "情感识别", "观点分析"],
        "en": ["sentiment analysis", "named entity recognition", "ner",
               "text classification", "semantic analysis", "intent recognition",
               "entity recognition", "natural language understanding"],
    },
    "语音处理": {
        "zh": ["语音识别", "语音转写", "语音合成", "语音", "转写", "声纹", "语音助手",
               "语音交互", "语音转文字"],
        "en": ["speech recognition", "speech-to-text", "speech to text", "asr",
               "tts", "voice recognition", "voice assistant", "transcription"],
    },
    "文本生成": {
        "zh": ["文本生成", "文案生成", "自动写作", "内容生成", "生成文章", "写作助手",
               "ai写作", "文案写作"],
        "en": ["text generation", "copywriting", "content generation",
               "ai writing", "generative text"],
    },
    "对话问答": {
        "zh": ["对话问答", "智能客服", "聊天机器人", "问答", "对话", "客服", "知识库问答",
               "自动应答", "自动回复", "问答机器人"],
        "en": ["chatbot", "question answering", "question-answering",
               "customer service", "conversational ai", "dialogue", "chat bot"],
    },
    "推荐系统": {
        "zh": ["推荐系统", "个性化推荐", "推荐算法", "协同过滤", "内容推荐", "智能推荐"],
        "en": ["recommendation system", "recommender system", "recommendation engine",
               "collaborative filtering", "personalized recommendation"],
    },
    "知识检索": {
        "zh": ["知识检索", "检索增强", "rag", "知识库", "向量检索", "信息检索",
               "检索增强生成", "知识管理"],
        "en": ["knowledge retrieval", "retrieval augmented generation", "rag",
               "vector retrieval", "information retrieval", "retrieval-augmented"],
    },
    "数据挖掘": {
        "zh": ["数据挖掘", "关联分析", "聚类分析", "用户画像", "特征工程", "数据建模",
               "数据分析"],
        "en": ["data mining", "association rule", "user profiling",
               "feature engineering", "data analytics"],
    },
    "多模态融合": {
        "zh": ["多模态", "多模态融合", "图文", "跨模态", "图文理解", "多模态理解"],
        "en": ["multimodal", "multi-modal", "cross-modal", "multimodal fusion"],
    },
    "智能体编排": {
        "zh": ["智能体", "智能体编排", "智能体", "agent", "自主智能体", "多智能体",
               "智能体工作流", "ai智能体"],
        "en": ["agent", "multi-agent", "autonomous agent", "ai agent",
               "agent orchestration", "llm agent"],
    },
    "自动化流程": {
        "zh": ["自动化流程", "流程自动化", "rpa", "自动办公", "流程机器人", "业务流程自动化",
               "自动化办公"],
        "en": ["rpa", "robotic process automation", "workflow automation",
               "process automation"],
    },
    "预测分析": {
        "zh": ["预测分析", "需求预测", "销量预测", "风险预测", "预测模型", "趋势预测",
               "预测", "预估"],
        "en": ["predictive analytics", "forecasting", "demand forecast",
               "sales prediction", "prediction model"],
    },
    "审核审查": {
        "zh": ["内容审核", "合规审查", "合同审查", "风险审核", "审核", "审查", "内容审查"],
        "en": ["content moderation", "compliance review", "contract review",
               "moderation", "review and audit"],
    },
    "搜索匹配": {
        "zh": ["搜索匹配", "搜索引擎", "匹配算法", "智能搜索", "语义搜索", "精准匹配"],
        "en": ["search matching", "search engine", "semantic search",
               "matching algorithm", "smart search"],
    },
    "翻译转写": {
        "zh": ["机器翻译", "翻译", "语言转换", "字幕", "实时翻译", "同传"],
        "en": ["machine translation", "translation", "translate", "subtitle"],
    },
    "视频理解": {
        "zh": ["视频理解", "视频分析", "视频内容", "动作识别", "视频检测", "视频识别"],
        "en": ["video understanding", "video analysis", "action recognition",
               "video recognition"],
    },
}

# ============ 30 个所属行业（顺序对齐附件1） ============
INDUSTRY_LABELS = [
    "金融", "教育", "医疗", "法律", "电商", "零售", "房地产", "制造", "物流", "游戏",
    "餐饮", "农业", "政务", "汽车", "家居", "交通", "能源", "通信", "娱乐", "体育",
    "旅游", "保险", "建筑", "环保", "科研", "人力资源", "媒体出版", "营销广告", "外贸", "其他",
]

INDUSTRY_KEYWORDS = {
    "金融": {
        "zh": ["金融", "银行", "信贷", "风控", "证券", "基金", "支付", "贷款", "票据"],
        "en": ["finance", "banking", "credit", "fintech", "payment", "loan", "financial"],
    },
    "教育": {
        "zh": ["教育", "教学", "学习", "课程", "考试", "学生", "学校", "培训", "题库"],
        "en": ["education", "learning", "course", "student", "exam", "teaching", "tutoring"],
    },
    "医疗": {
        "zh": ["医疗", "医院", "病历", "医学", "诊断", "健康", "医生", "病患", "临床"],
        "en": ["medical", "healthcare", "clinical", "hospital", "diagnosis", "patient", "health"],
    },
    "法律": {
        "zh": ["法律", "合同", "律师", "法务", "司法", "诉讼", "法条", "裁判"],
        "en": ["legal", "law", "contract", "lawyer", "judicial", "litigation"],
    },
    "电商": {
        "zh": ["电商", "网店", "店铺", "商品", "购物", "订单", "电子商务"],
        "en": ["e-commerce", "ecommerce", "online shop", "shopping", "online store"],
    },
    "零售": {
        "zh": ["零售", "门店", "商超", "连锁", "消费品", "便利店"],
        "en": ["retail", "chain store", "consumer goods", "convenience store"],
    },
    "房地产": {
        "zh": ["房地产", "房产", "楼盘", "物业", "租房", "买房", "地产"],
        "en": ["real estate", "property", "housing", "realty"],
    },
    "制造": {
        "zh": ["制造", "工厂", "质检", "生产线", "工业", "车间", "缺陷", "生产"],
        "en": ["manufacturing", "factory", "industrial", "quality inspection", "production line"],
    },
    "物流": {
        "zh": ["物流", "仓储", "快递", "配送", "供应链", "分拣", "货运"],
        "en": ["logistics", "warehouse", "delivery", "supply chain", "sorting"],
    },
    "游戏": {
        "zh": ["游戏", "玩家", "电竞", "游戏开发", "网游"],
        "en": ["game", "gaming", "esports", "video game"],
    },
    "餐饮": {
        "zh": ["餐饮", "餐厅", "外卖", "点餐", "饭店"],
        "en": ["restaurant", "catering", "food service", "takeout"],
    },
    "农业": {
        "zh": ["农业", "种植", "养殖", "农作物", "病虫害", "农田", "农产品"],
        "en": ["agriculture", "farming", "crop", "planting", "livestock"],
    },
    "政务": {
        "zh": ["政务", "政府", "办事", "政务服务", "公共服务", "行政", "政务大厅"],
        "en": ["government", "public service", "administration", "e-government"],
    },
    "汽车": {
        "zh": ["汽车", "车辆", "驾驶", "车载", "车企", "自动驾驶"],
        "en": ["automotive", "vehicle", "car", "driving", "autonomous driving"],
    },
    "家居": {
        "zh": ["家居", "家具", "家电", "家装", "智能家居"],
        "en": ["home", "furniture", "household", "appliance", "smart home"],
    },
    "交通": {
        "zh": ["交通", "道路", "出行", "运输", "交通管理", "车牌", "路况"],
        "en": ["transportation", "traffic", "road", "transport", "traffic management"],
    },
    "能源": {
        "zh": ["能源", "电力", "石油", "煤炭", "新能源", "电网", "发电"],
        "en": ["energy", "power", "electricity", "oil", "power grid", "energy sector"],
    },
    "通信": {
        "zh": ["通信", "电信", "运营商", "通信网络", "5g", "通讯"],
        "en": ["telecom", "telecommunication", "5g", "network operator"],
    },
    "娱乐": {
        "zh": ["娱乐", "影视", "综艺", "明星", "文娱"],
        "en": ["entertainment", "show business", "celebrity"],
    },
    "体育": {
        "zh": ["体育", "赛事", "运动", "健身"],
        "en": ["sports", "fitness", "athletic"],
    },
    "旅游": {
        "zh": ["旅游", "酒店", "景区", "旅行", "民宿"],
        "en": ["tourism", "travel", "hotel", "scenic spot"],
    },
    "保险": {
        "zh": ["保险", "理赔", "保单", "保险产品", "承保"],
        "en": ["insurance", "insurance claim", "insurance policy", "underwriting"],
    },
    "建筑": {
        "zh": ["建筑", "施工", "工程", "工地", "建筑设计"],
        "en": ["construction", "architecture", "building project", "engineering"],
    },
    "环保": {
        "zh": ["环保", "环境", "污染", "碳排放", "废弃物", "生态"],
        "en": ["environmental", "pollution", "carbon emission", "waste management"],
    },
    "科研": {
        "zh": ["科研", "学术", "论文", "研究", "实验", "科学"],
        "en": ["research", "academic", "scientific", "science", "experiment"],
    },
    "人力资源": {
        "zh": ["人力资源", "招聘", "简历", "面试", "人事", "员工", "绩效", "考勤"],
        "en": ["human resources", "recruitment", "resume", "interview", "hr", "employee"],
    },
    "媒体出版": {
        "zh": ["媒体", "出版", "新闻", "内容创作", "编辑", "传媒", "出版社"],
        "en": ["media", "publishing", "news", "editorial", "content creation"],
    },
    "营销广告": {
        "zh": ["营销", "广告", "品牌", "推广", "市场", "获客", "营销文案"],
        "en": ["marketing", "advertising", "brand", "promotion", "customer acquisition"],
    },
    "外贸": {
        "zh": ["外贸", "跨境", "出口", "国际贸易", "海关"],
        "en": ["foreign trade", "cross-border trade", "export", "international trade"],
    },
    "其他": {
        "zh": ["其他", "通用"],
        "en": ["general", "miscellaneous"],
    },
}
