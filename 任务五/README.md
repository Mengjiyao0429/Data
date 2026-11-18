# 任务五：结果呈现与决策支持系统

一个**可运行的完整系统**（后端服务 + 前端界面 + 数据存储 + 模型调用），不是静态页面。
系统以**用户需求**为驱动：每发起一次需求就触发一次真实采集，形成一个独立批次，批次内完成
采集 → 清洗 → 去重 → 机会判别 → 主题聚类 → 价值评估 → 策划案生成的全链分析，
并以任务四的价值分/优先级为依据做机会选取与决策产出。

## 先看这里：怎么打开

**不要双击 `templates/index.html`**。它只是服务端模板，里面还有 `{{ }}` 占位符，直接打开一定是残缺页面。

正确打开方式（任选一种）：

1. **双击 `任务五/启动服务.bat`**，会自动拉起服务并打开浏览器；
2. 或在 `任务五` 目录执行 `python start_app.py`；
3. 或分两步：`pip install -r requirements.txt` → `python app.py`，再手动访问地址。

地址固定是 **http://127.0.0.1:5000**。关闭那个命令行窗口即停止服务。

## 一、赛题要求对应

| 赛题要求 | 本系统实现 |
|---|---|
| 机会选取：以任务四簇机会价值分与优先级为主要依据 | 机会选取页按价值分/优先级排序，支持按行业、功能类别、来源数筛选与勾选，抽屉内展示三维度评分与真实证据记录 |
| 决策产出：生成立项策划案并导出文档（Word/Markdown） | `POST /api/proposal` 运行时生成 Markdown，落库后可在线预览、下载 `.md` 与 `.docx` |
| 要素：目标用户与核心痛点、核心功能、技术路线、实施周期、子任务分解、依据来源、价值评分 | 策划案固定十个章节，逐项覆盖；依据来源为真实记录编号 + 链接 |
| 结果呈现与交互：仪表盘、可视化图表、交互式查询 | 概览看板 4 张图（漏斗 / 价值排序 / 三维度贡献 / 簇×来源热力图）+ 全量筛选与搜索 |
| 系统设计：角色与权限、成本与资源、可常规环境部署 | 需求发起者 / 决策者两级角色（服务端校验）、SQLite 单文件存储、离线模板零 API 成本、一条命令启动 |
| **需求驱动：用户多次发起需求，一次需求触发一次采集（一个批次）** | 「需求发起」页填关键词/来源/目标条数 → `POST /api/requirements` 创建批次 → 后台线程跑真实采集（SO/HN/GitHub/CSDN）与全链分析 → 批次列表实时显示 running/done |
| **各批次分析相互独立** | 每批次单独目录 `批次/<批次号>/`；聚类 k、归一化分母、价值排序只在本批次内计算；判别阈值固定 0.50 不随批次改动 |
| **各环节结果可溯源至原始采集记录** | `result3` 的 `Bxx-Sxxxxx` → `result2` 判定 → `result1` 链接/热度/`text/Bxx_Sxxxxx.md` 快照 → `原始记录.json` 接口原始返回，四层可逐条核对 |

## 二、需求驱动：一次需求 = 一个独立批次

这是系统的主链路，也是与"静态看板"的根本区别：**用户每发起一次需求，就触发一次真实采集，形成一个批次，并独立跑完全链分析。**

```
需求表单（关键词 / 来源 / 目标条数）
        │  POST /api/requirements
        ▼
批次流水线 core/pipeline.py
  1) 采集    core/sources.py：Stack Overflow / Hacker News / GitHub / CSDN / 本地语料回放
  2) 清洗    去 HTML、去 URL、空白归一、长度过滤
  3) 去重    链接归一化（保留有意义的 query）+ 正文 MD5
  4) 相关性  需求关键词或 AI 主题词命中
  5) 快照    每条记录写 text/<批次>_Sxxxxx.md（与任务一格式完全一致）
  6) 判别    复用任务二 opportunity_classifier（阈值 0.50）+ category_classifier（附件1 的 16 类/30 类）
  7) 聚类    TF-IDF + LSA + KMeans，k 在本批次内按轮廓系数选，<3 条的零星簇并入最近大簇
  8) 评估    多源指向 / 记录规模 / 商业信号（0.35/0.35/0.30），分母取**本批次观测最大值**
  9) 报告    批次报告.md（漏斗、来源、簇表、Top3 证据、溯源方式）
```

**批次独立性的具体做法**（不是口号，是代码约束）：

| 环节 | 独立性保证 |
|---|---|
| 采集 | 每个批次独立请求接口，独立 `原始记录.json`，不与其它批次混池 |
| 去重 | 只在**本批次内**去重，不删历史批次记录 |
| 判别 | 阈值固定 0.50，判据与基线一致，不随批次改动 |
| 聚类 | k 与聚类只在本批次机会集上计算，不同批次的 C1 不是同一主题 |
| 价值分 | 三个分母都是本批次观测最大值，所以**跨批次不可比数值**，只在本批次内排序 |
| 存储 | 一个批次一个目录 `任务五/批次/<批次号>/`，互不覆盖 |

**溯源链（任何结论都能回到原始采集记录）**：

```
批次报告 / 界面结论
   → result3.csv「簇内机会记录」= Bxx-Sxxxxx（批次号-记录编号）
   → result2.csv：该编号的 机会判定 / 置信度 / 功能类别 / 行业
   → result1.csv：来源链接、发布时间、热度、内容列 ./text/Bxx_Sxxxxx.md
   → text/Bxx_Sxxxxx.md：标题 + 来源 + 链接 + 发布时间 + 热度 + 正文
   → 原始记录.json：接口原始返回字段（可与 result1 逐条比对）
```

**已跑通的真实批次（本机实测，全部为真实接口返回）**

| 批次 | 需求 | 来源 | 记录 | 机会 | 簇 | 耗时 |
|---|---|---|---|---|---|---|
| B09 | AI coding assistant code generation | Stack Overflow + Hacker News + GitHub | 226 | 52（23.0%） | 5 | 16.8s |
| B10 | 医疗影像 辅助诊断 AI | CSDN + Stack Overflow + 本地回放 | 68 | 25（36.8%） | 3 | 7.1s |
| B11 | 教育 智能批改 AI | 本地回放 + CSDN（HTTP 端到端验证） | 116 | 45（38.8%） | 5 | 待复算 |

> 断网或接口限流时可勾选「本地语料回放」：从任务一 8038 条快照里按关键词重排，
> 记录来源会写成「本地语料回放（来源，批次）」，界面与报告都明确标注，不冒充实时采集。

**复现一个批次（不联网，验证结果可重算）**

```bash
python 任务五/core/replay_batch.py B09
```

该命令只读 `批次/B09/原始记录.json`，重跑清洗→判别→聚类→评估→报告，输出应与已存结果一致。

## 三、系统架构

```
浏览器（原生 JS + ECharts 本地化；app.js 基线看板 / batch.js 需求驱动批次）
        │  fetch / JSON，请求头带 X-Role
        ▼
Flask 服务 app.py
   ├── core/sources.py     采集适配器（SO / HN / GitHub / CSDN / 回放）
   ├── core/pipeline.py    批次流水线：清洗→去重→快照→判别→聚类→评估→报告
   ├── core/batchstore.py  读取单个批次的 result1–4，装配成看板结构
   ├── core/datastore.py   读取基线 result1–4，装配 30 个主题簇与证据记录
   ├── core/db.py          SQLite：settings / selections / proposals / batches / audit
   ├── core/llm.py         模型调用：template / openai 兼容 / ollama
   └── core/proposal.py    提示词 + 严格校验 + 离线模板兜底 + Word 导出
        ▼
任务一~四真实结果（基线）  +  任务五/批次/<批次号>/（每次需求的独立结果）
```

## 四、数据来源（全部为仓库内真实结果）

- 任务一 `结果/result1.csv`：8,038 条采集记录、8 个批次、14 个来源
- 任务二 `结果/result2.csv`：986 条机会（12.3%）
- 任务三 `结果/result3.csv`：30 个主题簇
- 任务四 `结果/result4_中间指标.json`：三维度得分、价值分、优先级、权重

系统启动时一次性装配并缓存，不复制、不改写原始结果。

## 五、运行

```bash
pip install -r requirements.txt
python 任务五/app.py
# 打开 http://127.0.0.1:5000
```

Windows 下在仓库根目录执行：

```powershell
python .\任务五\app.py
```

首次启动会在 `任务五/instance/app.db` 自动建库（已加入 `.gitignore`）。

## 六、模型服务（成本可控，可选）

在「系统设置」页切换，无需改代码：

| 模式 | 说明 | 成本 |
|---|---|---|
| `template`（默认） | 离线模板生成，零 API 调用 | 0 元 |
| `openai` | 任意 OpenAI 兼容接口：硅基流动、智谱 GLM、DeepSeek、通义、Moonshot 等 | 用各家免费额度即可 |
| `ollama` | 本地 `http://localhost:11434` 跑 7B 级模型 | 0 元（本地算力） |

填写 `base_url / model / api_key` 后点「测试连通性」，通过即可生成。
模型调用失败或输出不合规时，系统自动回退离线模板并在文首标注，保证「永远有可交付的策划案」。

## 七、角色与权限

| 角色 | 操作权限 | 数据可见范围 |
|---|---|---|
| 需求发起者 `requester` | 浏览、筛选、选取机会、生成/下载策划案 | 主题簇与证据记录 |
| 决策者 `decision` | 以上全部 + 修改模型配置 + 查看审计日志 | 全部数据与配置 |

前端顶部切换角色；后端以请求头 `X-Role` 校验，`POST /api/settings` 非决策者返回 403。

## 八、成本与资源

- **存储**：单文件 SQLite（约几百 KB），无独立数据库服务，零运维
- **算力**：默认不调用模型；接入免费额度时按调用量计费，单份策划案约 2–4k tokens
- **部署**：单机 Flask，1 核 1G 即可；静态资源（ECharts）已本地化，不依赖 CDN
- **数据**：全部读取仓库内 CSV/JSON，无外部采集开销

## 九、接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 前端界面 |
| GET | `/health` | 健康检查 |
| GET | `/api/bootstrap` | 元数据 + 主题簇摘要 + 设置 + 统计 |
| GET | `/api/clusters` | 筛选：`q / industry / func / min_src` |
| GET | `/api/clusters/<cid>` | 主题簇详情（含证据记录） |
| POST | `/api/select` | 选取机会（落库 + 审计） |
| GET | `/api/selections` | 已选取列表 |
| POST | `/api/proposal` | 运行时生成策划案 |
| GET | `/api/proposals` | 策划案列表 |
| GET | `/api/proposals/<id>` | 策划案正文 |
| GET | `/api/proposals/<id>/download` | `fmt=md` / `fmt=docx` |
| GET/POST | `/api/settings` | 读取 / 保存模型配置（写需决策者） |
| POST | `/api/test` | 模型连通性测试 |
| GET | `/api/audit` | 审计日志（最近 50 条） |
| GET | `/api/sources` | 采集来源清单 + 代理可用性 |
| POST | `/api/requirements` | **发起一次需求**（创建批次并触发异步采集） |
| GET | `/api/batches` | 批次列表（状态 / 记录 / 机会 / 簇 / 耗时） |
| GET | `/api/batches/<bid>` | 批次摘要 + 主题簇列表（采集中返回 running） |
| GET | `/api/batches/<bid>/clusters/<cid>` | 批次内某簇详情（证据记录） |
| GET | `/api/batches/<bid>/records` | 记录级检索：`q / only_opp / source / limit / offset` |
| POST | `/api/batches/<bid>/proposal` | 运行时生成**该批次**的策划案 |
| GET | `/api/batches/<bid>/report` | 下载批次报告 Markdown |
| GET | `/api/batches/<bid>/file` | 下载 `result1.csv` 等结果文件（白名单） |

## 十、目录结构

```
任务五/
├── app.py                  Flask 入口与全部 API
├── requirements.txt
├── core/
│   ├── sources.py          采集适配器（SO / HN / GitHub / CSDN / 回放）
│   ├── pipeline.py         批次流水线（清洗→去重→快照→判别→聚类→评估→报告）
│   ├── batchstore.py       批次结果装配（供看板读取）
│   ├── run_batch.py        命令行发起需求（便于复现）
│   ├── replay_batch.py     离线复现批次（不联网）
│   ├── datastore.py        任务一～四装配（只读）
│   ├── db.py               SQLite 持久化（含 batches 表）
│   ├── llm.py              模型调用适配
│   └── proposal.py         策划案生成 / 校验 / Word 导出
├── templates/index.html    前端界面
├── static/
│   ├── style.css
│   ├── app.js              基线看板（任务一~四结果）
│   ├── batch.js            需求驱动批次（需求发起 / 批次分析）
│   └── echarts.min.js      本地化图表库
├── 批次/                    每次需求一个目录（B09 / B10 / B11 …，入库）
│   └── B09/
│       ├── result1.csv ~ result4.csv
│       ├── result4_中间指标.json
│       ├── text/B09_Sxxxxx.md   正文快照（result1“内容”列指向）
│       ├── 原始记录.json         接口原始返回（溯源）
│       └── 批次报告.md            本批次结论
├── 成果截图/               01~08（07 需求发起、08 批次分析为新增）
└── instance/app.db         运行后生成（不入库）
```

## 十一、验收步骤

1. 启动后打开首页，概览 4 张图与 KPI 有数（8,038 / 986 / 30）。
2. 机会选取页筛选「≥3 个来源」，表格实时收敛；点行打开抽屉，证据记录可点开真实链接。
3. 点「生成立项策划案」，弹窗出现十章节 Markdown；点「下载 Markdown」「下载 Word」得到文件。
4. 刷新页面后「策划案库」仍有该记录（SQLite 持久化）。
5. 切到「需求发起者」保存配置 → 提示 403；切「决策者」可保存并能测试连通性。
6. **需求驱动**：在「需求发起」填关键词、勾来源、设目标条数 → 点「发起采集与分析」→ 批次列表出现 running → 自动跳转「批次分析」→ 20–90 秒后 KPI / 漏斗 / 簇表 / 记录检索全部有数。
7. **批次独立**：连续发起两个不同需求（如「医疗影像」与「教育批改」），两个批次的记录数、机会数、簇数与价值分各自独立；点「查看」可来回切换。
8. **溯源**：在「批次分析」的记录检索里任取一条，点「原文」回到采集页面；编号 `Bxx-Sxxxxx` 与 `批次/Bxx/text/Bxx_Sxxxxx.md`、`result2.csv` 行一一对应。
9. **离线复现**：`python 任务五/core/replay_batch.py B09` 输出与已存结果一致（记录 226 / 机会 52 / 簇 5）。
