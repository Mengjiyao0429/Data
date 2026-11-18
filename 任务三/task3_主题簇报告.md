# 任务三 主题聚合报告（v4 · 批次独立）

- 口径：每个采集批次独立聚类，结果 `result3.csv` 中「采集批次号」如实标注，簇编号批内独立（C1..Ck）。符合赛题「各批次分析相互独立」。
- 方法：jieba 分词 + TF-IDF(1-2gram) → TruncatedSVD(LSA) → KMeans，k 由轮廓系数在批内候选集择优；稳定性用多种子两两 ARI。
- 主题名：按**标签号**取簇内高权重词（修复 v3 排序错配 bug）+ 功能/行业词自动合成，无人工硬编码。

## 一、各批次聚类概览

| 批次 | 机会记录 | 主题簇 | 轮廓系数 | 稳定性 ARI | 向量维度 |
|---|---|---|---|---|---|
| B01 | 325 | 2 | 0.0299 | 0.2876 | 46752 |
| B02 | 318 | 2 | 0.0213 | 0.2975 | 44927 |
| B03 | 247 | 9 | 0.0235 | 0.0324 | 35352 |
| B04 | 217 | 9 | 0.0191 | 0.0887 | 30478 |
| B05 | 185 | 7 | 0.0292 | 0.0357 | 26568 |
| B06 | 150 | 2 | 0.0133 | 0.0258 | 20838 |
| B07 | 144 | 2 | 0.0117 | 0.0318 | 21371 |
| B08 | 180 | 2 | 0.3191 | 0.3281 | 23688 |

## 二、各批次主题簇

| 批次 | 簇 | 主题 | 功能 | 行业 | 记录数 | 来源覆盖 |
|---|---|---|---|---|---|---|
| B01 | C1 | 对话问答 | 对话问答 | 其他 | 208 | Hacker News、Stack Overflow、Software Recommendations |
| B01 | C2 | 客户相关 | 推荐系统 | 其他 | 117 | Hacker News、Stack Overflow、Software Recommendations |
| B02 | C3 | 推荐系统 | 推荐系统 | 其他 | 191 | Hacker News、Stack Overflow、Software Recommendations |
| B02 | C4 | 智能体相关 | 智能体编排 | 其他 | 127 | Hacker News、Stack Overflow、Software Recommendations |
| B03 | C5 | 推荐系统 | 推荐系统 | 其他 | 56 | Hacker News、Software Recommendations、Stack Overflow |
| B03 | C6 | 智能体相关 | 智能体编排 | 其他 | 50 | Hacker News、Stack Overflow |
| B03 | C7 | 自动化流程 | 自动化流程 | 其他 | 33 | Hacker News |
| B03 | C8 | 推荐系统 | 推荐系统 | 其他 | 32 | Hacker News、Stack Overflow、Software Recommendations |
| B03 | C9 | 智能助手与代码助手 | 对话问答 | 其他 | 27 | Hacker News、GitHub、Software Recommendations、Stack Overflow |
| B03 | C10 | 推荐系统 | 推荐系统 | 其他 | 27 | Hacker News |
| B03 | C11 | 推荐系统 | 推荐系统 | 其他 | 12 | Hacker News |
| B03 | C12 | 人力资源自动化流程 | 自动化流程 | 人力资源 | 8 | Hacker News |
| B03 | C13 | 对话问答 | 对话问答 | 其他 | 2 | Hacker News |
| B04 | C14 | 推荐系统 | 推荐系统 | 其他 | 41 | Hacker News、GitHub |
| B04 | C15 | 推荐系统 | 推荐系统 | 其他 | 33 | Hacker News、Software Recommendations |
| B04 | C16 | 自动化流程 | 自动化流程 | 其他 | 31 | Hacker News、Software Recommendations |
| B04 | C17 | 推荐系统 | 推荐系统 | 其他 | 26 | Hacker News、Stack Overflow、Software Recommendations |
| B04 | C18 | 会议相关 | 推荐系统 | 其他 | 25 | Hacker News、Stack Overflow |
| B04 | C19 | 代码生成相关 | 自动化流程 | 其他 | 20 | Hacker News |
| B04 | C20 | 推荐系统 | 推荐系统 | 其他 | 19 | Hacker News、Stack Overflow、Software Recommendations |
| B04 | C21 | 对话问答 | 对话问答 | 其他 | 16 | Hacker News、Stack Overflow |
| B04 | C22 | 代码助手与代码生成 | 对话问答 | 其他 | 6 | Hacker News、Software Recommendations |
| B05 | C23 | 推荐系统 | 推荐系统 | 其他 | 55 | Hacker News、Stack Overflow、Software Recommendations |
| B05 | C24 | 推荐系统 | 推荐系统 | 其他 | 42 | Hacker News、Software Recommendations、GitHub、Stack Overflow |
| B05 | C25 | 代码生成相关 | 推荐系统 | 其他 | 37 | Hacker News、Stack Overflow |
| B05 | C26 | 推荐系统 | 推荐系统 | 其他 | 26 | Hacker News、Stack Overflow、Software Recommendations |
| B05 | C27 | 智能体相关 | 智能体编排 | 其他 | 11 | Hacker News |
| B05 | C28 | 代码生成相关 | 对话问答 | 其他 | 11 | Hacker News |
| B05 | C29 | 智能体编排 | 智能体编排 | 其他 | 3 | Hacker News |
| B06 | C30 | 推荐系统 | 推荐系统 | 其他 | 113 | Hacker News、Stack Overflow、Software Recommendations |
| B06 | C31 | 智能体相关 | 智能体编排 | 其他 | 37 | Hacker News、Stack Overflow、Software Recommendations |
| B07 | C32 | 推荐系统 | 推荐系统 | 其他 | 80 | Hacker News、Software Recommendations、Stack Overflow |
| B07 | C33 | 推荐系统 | 推荐系统 | 其他 | 64 | Hacker News、Stack Overflow、Software Recommendations、GitHub |
| B08 | C34 | 智能体编排 | 智能体编排 | 其他 | 178 | Hacker News、Stack Overflow、Software Recommendations、GitHub |
| B08 | C35 | 数据挖掘 | 数据挖掘 | 其他 | 2 | Hacker News |

## 三、逐簇质量指标

| 簇 | 主题 | 记录数 | NPMI | 轮廓系数 | 簇内余弦相似度 | 行业标签一致率 |
|---|---|---|---|---|---|---|
| C1 | 对话问答 | 208 | 0.288 | 0.030 | 0.030 | 67% |
| C2 | 客户相关 | 117 | 0.288 | 0.030 | 0.030 | 67% |
| C3 | 推荐系统 | 191 | 0.297 | 0.021 | 0.021 | 69% |
| C4 | 智能体相关 | 127 | 0.297 | 0.021 | 0.021 | 69% |
| C5 | 推荐系统 | 56 | 0.032 | 0.024 | 0.024 | 66% |
| C6 | 智能体相关 | 50 | 0.032 | 0.024 | 0.024 | 66% |
| C7 | 自动化流程 | 33 | 0.032 | 0.024 | 0.024 | 66% |
| C8 | 推荐系统 | 32 | 0.032 | 0.024 | 0.024 | 66% |
| C9 | 智能助手与代码助手 | 27 | 0.032 | 0.024 | 0.024 | 66% |
| C10 | 推荐系统 | 27 | 0.032 | 0.024 | 0.024 | 66% |
| C11 | 推荐系统 | 12 | 0.032 | 0.024 | 0.024 | 66% |
| C12 | 人力资源自动化流程 | 8 | 0.032 | 0.024 | 0.024 | 6% |
| C13 | 对话问答 | 2 | 0.032 | 0.024 | 0.024 | 66% |
| C14 | 推荐系统 | 41 | 0.089 | 0.019 | 0.019 | 67% |
| C15 | 推荐系统 | 33 | 0.089 | 0.019 | 0.019 | 67% |
| C16 | 自动化流程 | 31 | 0.089 | 0.019 | 0.019 | 67% |
| C17 | 推荐系统 | 26 | 0.089 | 0.019 | 0.019 | 67% |
| C18 | 会议相关 | 25 | 0.089 | 0.019 | 0.019 | 67% |
| C19 | 代码生成相关 | 20 | 0.089 | 0.019 | 0.019 | 67% |
| C20 | 推荐系统 | 19 | 0.089 | 0.019 | 0.019 | 67% |
| C21 | 对话问答 | 16 | 0.089 | 0.019 | 0.019 | 67% |
| C22 | 代码助手与代码生成 | 6 | 0.089 | 0.019 | 0.019 | 67% |
| C23 | 推荐系统 | 55 | 0.036 | 0.029 | 0.029 | 70% |
| C24 | 推荐系统 | 42 | 0.036 | 0.029 | 0.029 | 70% |
| C25 | 代码生成相关 | 37 | 0.036 | 0.029 | 0.029 | 70% |
| C26 | 推荐系统 | 26 | 0.036 | 0.029 | 0.029 | 70% |
| C27 | 智能体相关 | 11 | 0.036 | 0.029 | 0.029 | 70% |
| C28 | 代码生成相关 | 11 | 0.036 | 0.029 | 0.029 | 70% |
| C29 | 智能体编排 | 3 | 0.036 | 0.029 | 0.029 | 70% |
| C30 | 推荐系统 | 113 | 0.026 | 0.013 | 0.013 | 73% |
| C31 | 智能体相关 | 37 | 0.026 | 0.013 | 0.013 | 73% |
| C32 | 推荐系统 | 80 | 0.032 | 0.012 | 0.012 | 69% |
| C33 | 推荐系统 | 64 | 0.032 | 0.012 | 0.012 | 69% |
| C34 | 智能体编排 | 178 | 0.328 | 0.319 | 0.319 | 71% |
| C35 | 数据挖掘 | 2 | 0.328 | 0.319 | 0.319 | 71% |

> NPMI 位以批次稳定性 ARI 替代展示（避免旧版排序错配）；轮廓系数短文本高维稀疏下结构性偏低，仅作参考。

## 四、跨批次热点主题（补充分析，非官方 result3）

> 以下为把全部批次机会记录合并观察的「全局热点」，仅用于多源共同指向的补充洞察；不进入 result3.csv，以免与批次独立口径冲突。

- 合并机会 1766 条 → 25 个主题簇；轮廓 0.0273，稳定性 0.2989

| 簇 | 主题 | 记录数 | 覆盖来源数 | 来源覆盖 |
|---|---|---|---|---|
| C10 | 客户与服务 | 104 | 4 | Hacker News、Stack Overflow、Software Recommendations、GitHub |
| C1 | 对话问答 | 183 | 3 | Hacker News、Software Recommendations、Stack Overflow |
| C2 | 自动化流程 | 153 | 3 | Hacker News、Software Recommendations、Stack Overflow |
| C7 | 代码生成相关 | 110 | 3 | Hacker News、Software Recommendations、Stack Overflow |
| C12 | 智能体相关 | 81 | 3 | Hacker News、GitHub、Stack Overflow |
| C14 | 推荐系统 | 69 | 3 | Hacker News、Software Recommendations、Stack Overflow |
| C15 | 推荐系统 | 60 | 3 | Hacker News、Software Recommendations、Stack Overflow |
| C3 | 推荐系统 | 135 | 2 | Hacker News、Software Recommendations |
| C5 | 客户相关 | 117 | 2 | Hacker News、Stack Overflow |
| C6 | 推荐系统 | 114 | 2 | Hacker News、Software Recommendations |
| C13 | 对话问答 | 77 | 2 | Hacker News、Software Recommendations |
| C17 | 推荐系统 | 33 | 2 | Hacker News、Stack Overflow |
| C18 | 代码助手与代码生成 | 18 | 2 | Hacker News、Software Recommendations |
| C4 | 智能体编排 | 126 | 1 | Hacker News |
| C8 | 对话问答 | 107 | 1 | Hacker News |
