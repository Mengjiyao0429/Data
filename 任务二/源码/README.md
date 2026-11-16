# 任务二源码说明

## 一、文件职责

| 文件 | 职责 |
|---|---|
| `opportunity_classifier.py` | 机会判别与置信度（④排除 → ①真实需求 → ②AI 为核心 → ③技术可落地；四维证据加权） |
| `category_classifier.py` | 功能类别与所属行业（附件1 的 16 类 / 30 类，每条机会记录各一个标签） |
| `result2_exporter.py` | 读取任务一结果，输出 `../结果/result2.csv`、证据链、状态文件与验收报告 |
| `evaluate.py` | 与人工标注集对照：Accuracy / Precision / Recall / F1 / 混淆矩阵 / 错误案例 |
| `gold_labels.csv` | 191 条人工标注集（正 60 / 负 131），由队员逐条阅读正文后标注 |
| `gold_labels_data.py` | 标注集源数据（与 csv 同源） |
| `diff_report.py` | 修订前后逐条差异表（人工复核用） |
| `fetch_snapshots.py` | 任务一快照正文过短时，从公开页面回取正文到 `../text/` |
| `make_gold_sheet.py` / `labeling_sample.py` | 标注清单与分层抽样材料生成 |

## 二、运行

```bash
python result2_exporter.py   # 生成 ../结果/result2.csv 与 ../task2_验收报告.md
python evaluate.py           # 生成 ../task2_质量评估报告.md
```

依赖：Python 3.9+、openpyxl。无外部 API、无随机数，重复运行结果逐字节一致。

## 三、输入路径（自动识别）

`result2_exporter.py` 按以下顺序查找任务一结果，取第一个存在的：

1. 环境变量 `TASK1_SOURCE`
2. `../原始数据/任务一输出/result1.xlsx`
3. `../原始数据/任务一输出/result1.csv`
4. `../result1.xlsx`
5. `../../任务一/结果/result1.xlsx`、`../../任务一/结果/result1.csv`

快照查找顺序：`../正文快照/<编号>.md`（任务一）→ `../text/<编号>.md`（任务二补齐）。
若任务一快照的可见正文字符数 < 120 且存在补齐正文，则改用补齐正文，并在证据链标记 `snapshot_enriched`。

## 四、可调参数

| 参数 | 位置 | 默认 | 说明 |
|---|---|---|---|
| `DECISION_TAU` | `opportunity_classifier.py` | 0.56 | 机会判定阈值；人工标注集上 F1 最优区间为 0.54~0.58 |
| `W` | `opportunity_classifier.py` | R .36 / A .26 / F .22 / Q .16 | 四维权重 |
| `DELTA_EXCL` | `opportunity_classifier.py` | 0.35 | 排除证据的最大扣减系数 |
| `MANUAL_REVIEW_LO` | `opportunity_classifier.py` | 0.62 | 判 1 但低于该值进入人工复核队列 |
| `MIN_BODY_CHARS` | `result2_exporter.py` | 120 | 任务一快照正文不足时启用补齐正文的阈值 |