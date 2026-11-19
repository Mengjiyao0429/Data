# 任务二源码说明

> 当前版本适配**任务一更新后的 4322 条数据集**（B01–B08 八批次、4 个来源、新版表头与快照格式）。

## 一、文件职责

| 文件 | 职责 |
|---|---|
| `opportunity_classifier.py` | 机会判别与置信度（体裁硬排除 → ①真实需求 → ②AI 为核心 → ③技术可落地；四维证据加权） |
| `category_classifier.py` | 功能类别与所属行业（附件1 的 16 类 / 30 类，每条机会记录各一个标签） |
| `result2_exporter.py` | 读取任务一结果，输出 `../结果/result2.csv`、证据链与状态文件 |
| `evaluate.py` | 与人工标注集对照：Accuracy / Precision / Recall / F1 / 混淆矩阵 / 错误案例 |
| `gold_labels.csv` | 120 条人工标注集（正 25 / 负 95，固定种子简单随机抽样，独立金标准） |
| `gold_labels_data.py` | 标注集源数据（与 csv 同源） |
| `diff_report.py` | 修订前后逐条差异表（人工复核用） |
| `fetch_snapshots.py` | 任务一快照正文过短/缺失时，从公开页面回取正文 |
| `make_gold_sheet.py` / `labeling_sample.py` | 标注清单与抽样材料生成 |
| `ml_enhance.py` | 增强/辅助脚本 |

## 二、运行

```bash
python result2_exporter.py   # 生成 ../结果/result2.csv
python evaluate.py           # 生成 task2_质量评估报告.md
```

依赖：Python 3.9+、openpyxl。无外部 API；导出顺序固定，重复运行结果逐字节一致。
4322 条规模完整运行约 2 分钟（快照读取带缓存）。

## 三、输入路径（自动识别）

`result2_exporter.py` 按以下顺序查找任务一结果，取第一个存在的：

1. 环境变量 `TASK1_SOURCE`
2. `../原始数据/任务一输出/result1.xlsx`
3. `../原始数据/任务一输出/result1.csv`
4. `../result1.xlsx`
5. `../../任务一/结果/result1.xlsx`、`../../任务一/结果/result1.csv`

快照查找：`../正文快照/<编号>.md`（任务一）→ `../text/<编号>.md`（任务二补齐）。

**表头兼容**：结果列按列名解析，支持 `星标数/浏览数/点赞数/评论数/收藏数` 分列，也兼容旧版单列“热度指标”。
**快照兼容**：`# 标题 - 来源：… - 链接：… - 发布时间：… - 热度：… ## 正文 …`，判别时剥离标题行元数据。

## 四、可调参数

| 参数 | 位置 | 默认 | 说明 |
|---|---|---|---|
| `DECISION_TAU` | `opportunity_classifier.py` | 0.60 | 机会判定阈值（按 120 条标注集敏感性分析校准，全量机会率约 40%） |
| `NEED_GATE` | `opportunity_classifier.py` | 0.30 | **规则①前置门槛**：真实需求低于该值直接判 0 |
| `GATE_EXCL` | `opportunity_classifier.py` | 0.50 | 排除门槛 |
| `W` | `opportunity_classifier.py` | R .36 / A .26 / F .22 / Q .16 | 四维权重 |
| `DELTA_EXCL` | `opportunity_classifier.py` | 0.35 | 排除证据的最大扣减系数 |
| `MANUAL_REVIEW_LO` | `opportunity_classifier.py` | 0.68 | 判 1 但低于该值进入人工复核队列 |
| `REVIEW_BAND` | `opportunity_classifier.py` | 0.08 | 复核带宽度 |

## 五、判别要点

1. **意图体裁硬排除层**：在评分最前面，标题命中学习/资源/职业类、观点泛讨论、开发者编码工具讨论、
   招聘门户、找人新闻等强模式即直接判 0；另设非 AI 工具词（data warehouse、pandas、antivirus 等，
   且标题不含 AI 强词）排除。
2. **规则①前置门槛**：真实需求 R 低于 0.30 直接判 0——AI 能力再强，没有需求也不是“应用机会”。
3. **业务场景锚定扩展**：业务语境词覆盖 customer/patient/product/saas/platform/retail/用户/客户/
   平台/零售/医疗/教育 等，避免终端产品仅因提到 extension/SDK 被误杀。
4. **开发者工程问题分层**：跨来源强技术问题与仅 Stack Overflow 触发的弱技术问题分别处理，
   报错求助的需求信号按规则折扣。
5. **供给侧排除**：开发者组件/工具与模型仓库在无业务场景锚定时判 0。
6. **功能分类去子串碰撞**：`ner` 加词边界（不再误匹配 vul-ner-abilities）、`automat` 收紧
   （不再误匹配 Automatic）、审核审查加入 vulnerabilit/漏洞、形态词 assistant/bot 降权。
7. **中文语域**：完整的中文需求/场景/AI 能力词表，以及中文科普综述、资讯转述的排除规则。
