# -*- coding: utf-8 -*-
"""官方附件2参考数据源清单（20 个平台）及本系统的采集配置。

DATA_SOURCES 完整对齐《附件2.xlsx》；COLLECTIBLE 仅登记当前网络环境下
经实测可用、具备公开 API/RSS 且合规的源（采集前已实测连通性）。
"""

# 完整数据源清单（来源类别, 来源网站名称, 官网链接），顺序对齐附件2
DATA_SOURCES = [
    ("视频与内容社区", "哔哩哔哩", "https://www.bilibili.com/"),
    ("开源项目与产品社区", "GitHub", "https://github.com/"),
    ("开源项目与产品社区", "Product Hunt", "https://www.producthunt.com/"),
    ("技术内容与教程社区", "掘金", "https://juejin.cn/"),
    ("技术内容与教程社区", "InfoQ中国", "https://www.infoq.cn/"),
    ("技术内容与教程社区", "少数派", "https://sspai.com/"),
    ("技术内容与教程社区", "CSDN", "https://www.csdn.net/"),
    ("科技与AI垂直资讯", "机器之心", "https://www.jiqizhixin.com/"),
    ("科技与AI垂直资讯", "量子位", "https://www.qbitai.com/"),
    ("科技与AI垂直资讯", "36氪", "https://36kr.com/"),
    ("科技与AI垂直资讯", "IT之家", "https://www.ithome.com/"),
    ("问答与需求社区", "V2EX", "https://www.v2ex.com/"),
    ("问答与需求社区", "Stack Overflow", "https://stackoverflow.com/"),
    ("问答与需求社区", "阿里云开发者社区", "https://developer.aliyun.com/"),
    ("学术论文与预印本", "Papers with Code", "https://paperswithcode.com/"),
    ("学术论文与预印本", "Semantic Scholar", "https://www.semanticscholar.org/"),
    ("竞赛与数据集平台", "Kaggle", "https://www.kaggle.com/"),
    ("竞赛与数据集平台", "天池", "https://tianchi.aliyun.com/"),
    ("竞赛与数据集平台", "DataFountain", "https://www.datafountain.cn/"),
    ("竞赛与数据集平台", "数睿思", "https://www.tipdm.org/"),
]

# 当前可程序化采集的源（均经实测）。method: github / stackexchange / rss
COLLECTIBLE = {
    "GitHub": {
        "category": "开源项目与产品社区",
        "method": "github",
        "site": "https://github.com/",
    },
    "Stack Overflow": {
        "category": "问答与需求社区",
        "method": "stackexchange",
        "site": "https://stackoverflow.com/",
    },
    "少数派": {
        "category": "技术内容与教程社区",
        "method": "rss",
        "feed": "https://sspai.com/feed",
        "site": "https://sspai.com/",
    },
    "IT之家": {
        "category": "科技与AI垂直资讯",
        "method": "rss",
        "feed": "https://www.ithome.com/rss/",
        "site": "https://www.ithome.com/",
    },
    "量子位": {
        "category": "科技与AI垂直资讯",
        "method": "rss",
        "feed": "https://www.qbitai.com/feed",
        "site": "https://www.qbitai.com/",
    },
    "InfoQ中国": {
        "category": "技术内容与教程社区",
        "method": "rss",
        "feed": "https://www.infoq.cn/feed",
        "site": "https://www.infoq.cn/",
    },
}

# 实测暂不可用/受限的源（在论文与运行说明中如实披露）
UNAVAILABLE = {
    "V2EX": "本地网络连接超时",
    "Papers with Code": "本地网络无响应",
    "Semantic Scholar": "无 API Key 时持续 429 限流",
    "36氪": "/feed 返回反爬验证页而非 RSS",
    "机器之心": "原 RSS 地址已下线，返回数据服务 HTML",
}
