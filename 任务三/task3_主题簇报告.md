# 任务三 主题聚合报告（v4 · 批次独立）

- 口径：每个采集批次独立聚类，结果 `result3.csv` 中「采集批次号」如实标注，簇编号批内独立（C1..Ck）。符合赛题「各批次分析相互独立」。
- 方法：jieba 分词 + TF-IDF(1-2gram) → TruncatedSVD(LSA) → KMeans，k 由轮廓系数在批内候选集择优；稳定性用多种子两两 ARI。
- 主题名：按**标签号**取簇内高权重词（修复 v3 排序错配 bug）+ 功能/行业词自动合成，无人工硬编码。

## 一、各批次聚类概览

| 批次 | 机会记录 | 主题簇 | 轮廓系数 | 稳定性 ARI | 向量维度 |
|---|---|---|---|---|---|
| B01 | 338 | 8 | 0.0268 | 0.0569 | 52293 |
| B02 | 334 | 2 | 0.0249 | 0.331 | 51657 |
| B03 | 225 | 10 | 0.0237 | 0.0554 | 34716 |
| B04 | 197 | 9 | 0.0173 | 0.0529 | 31100 |
| B05 | 162 | 4 | 0.0311 | 0.0289 | 24190 |
| B06 | 156 | 10 | 0.0238 | 0.1013 | 24114 |
| B07 | 151 | 4 | 0.0143 | 0.0241 | 23694 |
| B08 | 165 | 8 | 0.0336 | 0.0908 | 23888 |

## 二、各批次主题簇

| 批次 | 簇 | 主题 | 功能 | 行业 | 记录数 | 来源覆盖 |
|---|---|---|---|---|---|---|
| B01 | C1 | 推荐系统 | 推荐系统 | 其他 | 79 | Hacker News、Stack Overflow、GitHub |
| B01 | C2 | 智能体编排 | 智能体编排 | 其他 | 59 | Hacker News |
| B01 | C3 | 自动化流程 | 自动化流程 | 其他 | 55 | Hacker News、Stack Overflow、Software Recommendations |
| B01 | C4 | 推荐系统 | 推荐系统 | 其他 | 53 | Hacker News、Stack Overflow、Software Recommendations |
| B01 | C5 | 智能体与代码生成 | 智能体编排 | 其他 | 43 | Hacker News、Stack Overflow |
| B01 | C6 | 客户与聊天机器人 | 对话问答 | 其他 | 27 | Hacker News |
| B01 | C7 | 智能体编排 | 智能体编排 | 其他 | 20 | Hacker News、Software Recommendations |
| B01 | C8 | 娱乐推荐系统 | 推荐系统 | 娱乐 | 2 | Hacker News |
| B02 | C9 | 推荐系统 | 推荐系统 | 其他 | 208 | Hacker News、Stack Overflow、Software Recommendations |
| B02 | C10 | 智能体相关 | 智能体编排 | 其他 | 126 | Hacker News、Stack Overflow |
| B03 | C11 | 推荐系统 | 推荐系统 | 其他 | 43 | Hacker News、Stack Overflow、Software Recommendations |
| B03 | C12 | 智能体编排 | 智能体编排 | 其他 | 33 | Hacker News |
| B03 | C13 | 推荐系统 | 推荐系统 | 其他 | 29 | Hacker News、GitHub、Software Recommendations |
| B03 | C14 | 推荐系统 | 推荐系统 | 其他 | 27 | Hacker News、Stack Overflow、Software Recommendations |
| B03 | C15 | 推荐系统 | 推荐系统 | 其他 | 25 | Hacker News、GitHub、Stack Overflow |
| B03 | C16 | 代码生成相关 | 智能体编排 | 其他 | 25 | Hacker News、Stack Overflow |
| B03 | C17 | 代码生成相关 | 智能体编排 | 其他 | 17 | Hacker News、Stack Overflow |
| B03 | C18 | 智能体编排 | 智能体编排 | 其他 | 12 | Hacker News |
| B03 | C19 | 推荐系统 | 推荐系统 | 其他 | 12 | Hacker News |
| B03 | C20 | 对话问答 | 对话问答 | 其他 | 2 | Hacker News |
| B04 | C21 | 智能体编排 | 智能体编排 | 其他 | 44 | Hacker News、Stack Overflow |
| B04 | C22 | 推荐系统 | 推荐系统 | 其他 | 36 | Hacker News、Stack Overflow、Software Recommendations、GitHub |
| B04 | C23 | 推荐系统 | 推荐系统 | 其他 | 30 | Hacker News、Stack Overflow |
| B04 | C24 | 推荐系统 | 推荐系统 | 其他 | 29 | Hacker News、Software Recommendations |
| B04 | C25 | 自动化流程 | 自动化流程 | 其他 | 21 | Hacker News、Software Recommendations |
| B04 | C26 | 推荐系统 | 推荐系统 | 其他 | 16 | Hacker News |
| B04 | C27 | 智能体编排 | 智能体编排 | 其他 | 13 | Hacker News |
| B04 | C28 | 智能助手与代码助手 | 智能体编排 | 其他 | 6 | Hacker News、Software Recommendations |
| B04 | C29 | 智能体编排 | 智能体编排 | 其他 | 2 | Hacker News |
| B05 | C30 | 推荐系统 | 推荐系统 | 其他 | 85 | Hacker News、Software Recommendations、GitHub |
| B05 | C31 | 智能体编排 | 智能体编排 | 其他 | 61 | Hacker News、Stack Overflow |
| B05 | C32 | 推荐系统 | 推荐系统 | 其他 | 13 | Hacker News、Software Recommendations、Stack Overflow |
| B05 | C33 | 智能体编排 | 智能体编排 | 其他 | 3 | Hacker News |
| B06 | C34 | 推荐系统 | 推荐系统 | 其他 | 38 | Hacker News、Stack Overflow、GitHub |
| B06 | C35 | 智能体编排 | 智能体编排 | 其他 | 35 | Hacker News、Software Recommendations |
| B06 | C36 | 代码生成相关 | 推荐系统 | 其他 | 20 | Hacker News、Software Recommendations |
| B06 | C37 | 服务相关 | 推荐系统 | 其他 | 16 | Hacker News |
| B06 | C38 | 智能体相关 | 推荐系统 | 其他 | 13 | Hacker News |
| B06 | C39 | 审核审查 | 审核审查 | 其他 | 12 | Hacker News、Stack Overflow |
| B06 | C40 | 语音处理相关 | 语音处理 | 其他 | 10 | Hacker News |
| B06 | C41 | 智能体相关 | 智能体编排 | 其他 | 6 | Hacker News |
| B06 | C42 | 推荐系统 | 推荐系统 | 其他 | 4 | Hacker News、Software Recommendations |
| B06 | C43 | 会议相关 | 语音处理 | 其他 | 2 | Hacker News |
| B07 | C44 | 智能体编排 | 智能体编排 | 其他 | 65 | Hacker News、Stack Overflow、GitHub |
| B07 | C45 | 智能体编排 | 智能体编排 | 其他 | 46 | Hacker News、Stack Overflow、Software Recommendations |
| B07 | C46 | 推荐系统 | 推荐系统 | 其他 | 33 | Hacker News、Stack Overflow、GitHub |
| B07 | C47 | 推荐系统 | 推荐系统 | 其他 | 7 | Hacker News、Software Recommendations |
| B08 | C48 | 智能体编排 | 智能体编排 | 其他 | 47 | Hacker News、Stack Overflow |
| B08 | C49 | 智能体编排 | 智能体编排 | 其他 | 33 | Hacker News、Stack Overflow |
| B08 | C50 | 智能体编排 | 智能体编排 | 其他 | 29 | Hacker News、Software Recommendations、Stack Overflow |
| B08 | C51 | 推荐系统 | 推荐系统 | 其他 | 24 | Hacker News、Stack Overflow、Software Recommendations |
| B08 | C52 | 代码生成相关 | 智能体编排 | 其他 | 21 | Hacker News |
| B08 | C53 | 智能体编排 | 智能体编排 | 其他 | 7 | Hacker News、GitHub |
| B08 | C54 | 智能体编排 | 智能体编排 | 其他 | 2 | Hacker News |
| B08 | C55 | 推荐系统 | 推荐系统 | 其他 | 2 | Hacker News |

## 三、逐簇质量指标

| 簇 | 主题 | 记录数 | NPMI | 轮廓系数 | 簇内余弦相似度 | 行业标签一致率 |
|---|---|---|---|---|---|---|
| C1 | 推荐系统 | 79 | 0.057 | 0.027 | 0.027 | 70% |
| C2 | 智能体编排 | 59 | 0.057 | 0.027 | 0.027 | 70% |
| C3 | 自动化流程 | 55 | 0.057 | 0.027 | 0.027 | 70% |
| C4 | 推荐系统 | 53 | 0.057 | 0.027 | 0.027 | 70% |
| C5 | 智能体与代码生成 | 43 | 0.057 | 0.027 | 0.027 | 70% |
| C6 | 客户与聊天机器人 | 27 | 0.057 | 0.027 | 0.027 | 70% |
| C7 | 智能体编排 | 20 | 0.057 | 0.027 | 0.027 | 70% |
| C8 | 娱乐推荐系统 | 2 | 0.057 | 0.027 | 0.027 | 1% |
| C9 | 推荐系统 | 208 | 0.331 | 0.025 | 0.025 | 68% |
| C10 | 智能体相关 | 126 | 0.331 | 0.025 | 0.025 | 68% |
| C11 | 推荐系统 | 43 | 0.055 | 0.024 | 0.024 | 71% |
| C12 | 智能体编排 | 33 | 0.055 | 0.024 | 0.024 | 71% |
| C13 | 推荐系统 | 29 | 0.055 | 0.024 | 0.024 | 71% |
| C14 | 推荐系统 | 27 | 0.055 | 0.024 | 0.024 | 71% |
| C15 | 推荐系统 | 25 | 0.055 | 0.024 | 0.024 | 71% |
| C16 | 代码生成相关 | 25 | 0.055 | 0.024 | 0.024 | 71% |
| C17 | 代码生成相关 | 17 | 0.055 | 0.024 | 0.024 | 71% |
| C18 | 智能体编排 | 12 | 0.055 | 0.024 | 0.024 | 71% |
| C19 | 推荐系统 | 12 | 0.055 | 0.024 | 0.024 | 71% |
| C20 | 对话问答 | 2 | 0.055 | 0.024 | 0.024 | 71% |
| C21 | 智能体编排 | 44 | 0.053 | 0.017 | 0.017 | 72% |
| C22 | 推荐系统 | 36 | 0.053 | 0.017 | 0.017 | 72% |
| C23 | 推荐系统 | 30 | 0.053 | 0.017 | 0.017 | 72% |
| C24 | 推荐系统 | 29 | 0.053 | 0.017 | 0.017 | 72% |
| C25 | 自动化流程 | 21 | 0.053 | 0.017 | 0.017 | 72% |
| C26 | 推荐系统 | 16 | 0.053 | 0.017 | 0.017 | 72% |
| C27 | 智能体编排 | 13 | 0.053 | 0.017 | 0.017 | 72% |
| C28 | 智能助手与代码助手 | 6 | 0.053 | 0.017 | 0.017 | 72% |
| C29 | 智能体编排 | 2 | 0.053 | 0.017 | 0.017 | 72% |
| C30 | 推荐系统 | 85 | 0.029 | 0.031 | 0.031 | 69% |
| C31 | 智能体编排 | 61 | 0.029 | 0.031 | 0.031 | 69% |
| C32 | 推荐系统 | 13 | 0.029 | 0.031 | 0.031 | 69% |
| C33 | 智能体编排 | 3 | 0.029 | 0.031 | 0.031 | 69% |
| C34 | 推荐系统 | 38 | 0.101 | 0.024 | 0.024 | 74% |
| C35 | 智能体编排 | 35 | 0.101 | 0.024 | 0.024 | 74% |
| C36 | 代码生成相关 | 20 | 0.101 | 0.024 | 0.024 | 74% |
| C37 | 服务相关 | 16 | 0.101 | 0.024 | 0.024 | 74% |
| C38 | 智能体相关 | 13 | 0.101 | 0.024 | 0.024 | 74% |
| C39 | 审核审查 | 12 | 0.101 | 0.024 | 0.024 | 74% |
| C40 | 语音处理相关 | 10 | 0.101 | 0.024 | 0.024 | 74% |
| C41 | 智能体相关 | 6 | 0.101 | 0.024 | 0.024 | 74% |
| C42 | 推荐系统 | 4 | 0.101 | 0.024 | 0.024 | 74% |
| C43 | 会议相关 | 2 | 0.101 | 0.024 | 0.024 | 74% |
| C44 | 智能体编排 | 65 | 0.024 | 0.014 | 0.014 | 71% |
| C45 | 智能体编排 | 46 | 0.024 | 0.014 | 0.014 | 71% |
| C46 | 推荐系统 | 33 | 0.024 | 0.014 | 0.014 | 71% |
| C47 | 推荐系统 | 7 | 0.024 | 0.014 | 0.014 | 71% |
| C48 | 智能体编排 | 47 | 0.091 | 0.034 | 0.034 | 72% |
| C49 | 智能体编排 | 33 | 0.091 | 0.034 | 0.034 | 72% |
| C50 | 智能体编排 | 29 | 0.091 | 0.034 | 0.034 | 72% |
| C51 | 推荐系统 | 24 | 0.091 | 0.034 | 0.034 | 72% |
| C52 | 代码生成相关 | 21 | 0.091 | 0.034 | 0.034 | 72% |
| C53 | 智能体编排 | 7 | 0.091 | 0.034 | 0.034 | 72% |
| C54 | 智能体编排 | 2 | 0.091 | 0.034 | 0.034 | 72% |
| C55 | 推荐系统 | 2 | 0.091 | 0.034 | 0.034 | 72% |

> NPMI 位以批次稳定性 ARI 替代展示（避免旧版排序错配）；轮廓系数短文本高维稀疏下结构性偏低，仅作参考。

## 四、跨批次热点主题（补充分析，非官方 result3）

> 以下为把全部批次机会记录合并观察的「全局热点」，仅用于多源共同指向的补充洞察；不进入 result3.csv，以免与批次独立口径冲突。

- 合并机会 1728 条 → 25 个主题簇；轮廓 0.0347，稳定性 0.3597

| 簇 | 主题 | 记录数 | 覆盖来源数 | 来源覆盖 |
|---|---|---|---|---|
| C2 | 推荐系统 | 285 | 4 | Hacker News、Stack Overflow、Software Recommendations、GitHub |
| C9 | 智能体编排 | 103 | 4 | Hacker News、Stack Overflow、GitHub、Software Recommendations |
| C3 | 代码生成与代码助手 | 156 | 3 | Hacker News、Software Recommendations、Stack Overflow |
| C4 | 智能体编排 | 153 | 3 | Hacker News、Software Recommendations、GitHub |
| C11 | 智能助手相关 | 52 | 3 | Hacker News、GitHub、Software Recommendations |
| C5 | 智能体相关 | 128 | 2 | Hacker News、Stack Overflow |
| C6 | 自动化流程 | 127 | 2 | Hacker News、Software Recommendations |
| C7 | 推荐系统 | 126 | 2 | Hacker News、Software Recommendations |
| C8 | 数据挖掘 | 118 | 2 | Hacker News、Stack Overflow |
| C10 | 推荐系统 | 60 | 2 | Hacker News、Software Recommendations |
| C12 | 客户与服务 | 51 | 2 | Hacker News、GitHub |
| C1 | 推荐系统 | 301 | 1 | Hacker News |
| C13 | 代码生成相关 | 37 | 1 | Hacker News |
| C14 | 智能体编排 | 4 | 1 | Hacker News |
| C15 | 推荐系统 | 4 | 1 | Hacker News |
