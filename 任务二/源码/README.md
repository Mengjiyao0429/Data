# 任务二源码说明

> 当前版本适配**任务一更新后的 5517 条数据集**（B01–B05 五批次、12 个来源、新版表头与快照格式）。

## 一、文件职责

| 文件 | 职责 |
|---|---|
| `opportunity_classifier.py` | 机会判别与置信度（④排除 → ①真实需求 → ②AI 为核心 → ③技术可落地；四维证据加权） |
| `category_classifier.py` | 功能类别与所属行业（附件1 的 16 类 / 30 类，每条机会记录各一个标签） |
| `result2_exporter.py` | 读取任务一结果，输出 `../结果/result2.csv`、证据链、状态文件与验收报告 |
| `evaluate.py` | 与人工标注集对照：Accuracy / Precision / Recall / F1 / 混淆矩阵 / 错误案例 |
| `gold_labels.csv` | 116 条人工标注集（正 30 / 负 86，基于新数据集分层抽样） |
| `gold_labels_data.py` | 标注集源数据（与 csv 同源） |
| `diff_report.py` | 修订前后逐条差异表（人工复核用） |
| `fetch_snapshots.py` | 任务一快照正文过短/缺失时，从公开页面回取正文 |
| `make_gold_sheet.py` / `labeling_sample.py` | 标注清单与分层抽样材料生成 |

## 二、运行

```bash
python result2_exporter.py   # 生成 ../结果/result2.csv 与 ../task2_验收报告.md
python evaluate.py           # 生成 ../task2_质量评估报告.md
```

依赖：Python 3.9+、openpyxl。无外部 API、无随机数，重复运行结果逐字节一致。
5517 条规模完整运行约 1 分钟（快照读取带缓存）。

## 三、输入路径（自动识别）

`result2_exporter.py` 按以下顺序查找任务一结果，取第一个存在的：

1. 环境变量 `TASK1_SOURCE`
2. `../原始数据/任务一输出/result1.xlsx`
3. `../原始数据/任务一输出/result1.csv`
4. `../result1.xlsx`
5. `../../任务一/结果/result1.xlsx`、`../../任务一/结果/result1.csv`

快照查找：`../正文快照/<编号>.md`（任务一）→ `../text/<编号>.md`（任务二补齐）。

**新版表头兼容**：结果列按列名解析，支持 `星标数/浏览数/点赞数/评论数/收藏数` 分列，也兼容旧版单列“热度指标”。
**新版快照兼容**：`# 标题 - 来源：… - 链接：… - 发布时间：… - 热度：… ## 正文 …`，判别时剥离标题行元数据。

## 四、可调参数

| 参数 | 位置 | 默认 | 说明 |
|---|---|---|---|
| `DECISION_TAU` | `opportunity_classifier.py` | 0.56 | 机会判定阈值（人工标注集 F1 最优点） |
| `NEED_GATE` | `opportunity_classifier.py` | 0.30 | **规则①前置门槛**：真实需求低于该值直接判 0 |
| `W` | `opportunity_classifier.py` | R .36 / A .26 / F .22 / Q .16 | 四维权重 |
| `DELTA_EXCL` | `opportunity_classifier.py` | 0.35 | 排除证据的最大扣减系数 |
| `MANUAL_REVIEW_LO` | `opportunity_classifier.py` | 0.62 | 判 1 但低于该值进入人工复核队列 |
| `MIN_BODY_CHARS` | `result2_exporter.py` | 120 | 任务一快照正文不足时启用补齐正文的阈值 |

## 五、判别要点（相对上一版的新增）

1. **规则①前置门槛**：真实需求 R 低于 0.30 直接判 0——AI 能力再强，没有需求也不是“应用机会”。
2. **开发者工程问题降权**：含 error/exception/报错/怎么修 等表述的记录，需求信号按 0.28 折扣
   （若同时有明确业务场景则保留 0.62）。
3. **供给侧排除**：开发者组件/工具（memory 系统、gateway、registry、skill 包、SDK、插件…）
   与模型仓库（发布权重/模型系列）在无业务场景锚定时判 0。
4. **中文语域**：新增中文需求/场景/AI 能力词表，以及中文科普综述、资讯转述的排除规则。