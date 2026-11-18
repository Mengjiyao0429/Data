# 任务五：结果呈现与决策支持系统

一个**可运行的完整系统**（后端服务 + 前端界面 + 数据存储 + 模型调用），不是静态页面。
基于任务一～四的真实结果，完成赛题要求的「机会选取 → 决策产出 → 结果呈现与交互」。

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

## 二、系统架构

```
浏览器（原生 JS + ECharts 本地化）
        │  fetch / JSON，请求头带 X-Role
        ▼
Flask 服务 app.py
   ├── core/datastore.py   读取 result1–4，装配 14 个主题簇与证据记录
   ├── core/db.py          SQLite：settings / selections / proposals / audit
   ├── core/llm.py         模型调用：template / openai 兼容 / ollama
   └── core/proposal.py    提示词 + 严格校验 + 离线模板兜底 + Word 导出
        ▼
任务一/结果、任务二/结果、任务三/结果、任务四/结果（只读真实数据）
```

## 三、数据来源（全部为仓库内真实结果）

- 任务一 `结果/result1.csv`：5,517 条采集记录、5 个批次、12 个来源
- 任务二 `结果/result2.csv`：388 条机会（7.0%）
- 任务三 `结果/result3.csv`：14 个主题簇
- 任务四 `结果/result4_中间指标.json`：三维度得分、价值分、优先级、权重

系统启动时一次性装配并缓存，不复制、不改写原始结果。

## 四、运行

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

## 五、模型服务（成本可控，可选）

在「系统设置」页切换，无需改代码：

| 模式 | 说明 | 成本 |
|---|---|---|
| `template`（默认） | 离线模板生成，零 API 调用 | 0 元 |
| `openai` | 任意 OpenAI 兼容接口：硅基流动、智谱 GLM、DeepSeek、通义、Moonshot 等 | 用各家免费额度即可 |
| `ollama` | 本地 `http://localhost:11434` 跑 7B 级模型 | 0 元（本地算力） |

填写 `base_url / model / api_key` 后点「测试连通性」，通过即可生成。
模型调用失败或输出不合规时，系统自动回退离线模板并在文首标注，保证「永远有可交付的策划案」。

## 六、角色与权限

| 角色 | 操作权限 | 数据可见范围 |
|---|---|---|
| 需求发起者 `requester` | 浏览、筛选、选取机会、生成/下载策划案 | 主题簇与证据记录 |
| 决策者 `decision` | 以上全部 + 修改模型配置 + 查看审计日志 | 全部数据与配置 |

前端顶部切换角色；后端以请求头 `X-Role` 校验，`POST /api/settings` 非决策者返回 403。

## 七、成本与资源

- **存储**：单文件 SQLite（约几百 KB），无独立数据库服务，零运维
- **算力**：默认不调用模型；接入免费额度时按调用量计费，单份策划案约 2–4k tokens
- **部署**：单机 Flask，1 核 1G 即可；静态资源（ECharts）已本地化，不依赖 CDN
- **数据**：全部读取仓库内 CSV/JSON，无外部采集开销

## 八、接口一览

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

## 九、目录结构

```
任务五/
├── app.py                  Flask 入口与全部 API
├── requirements.txt
├── core/
│   ├── datastore.py        任务一～四装配（只读）
│   ├── db.py               SQLite 持久化
│   ├── llm.py              模型调用适配
│   └── proposal.py         策划案生成 / 校验 / Word 导出
├── templates/index.html    前端界面
├── static/
│   ├── style.css
│   ├── app.js
│   └── echarts.min.js      本地化图表库
└── instance/app.db         运行后生成（不入库）
```

## 十、验收步骤

1. 启动后打开首页，概览 4 张图与 KPI 有数（5,517 / 388 / 14）。
2. 机会选取页筛选「≥3 个来源」，表格实时收敛；点行打开抽屉，证据记录可点开真实链接。
3. 点「生成立项策划案」，弹窗出现十章节 Markdown；点「下载 Markdown」「下载 Word」得到文件。
4. 刷新页面后「策划案库」仍有该记录（SQLite 持久化）。
5. 切到「需求发起者」保存配置 → 提示 403；切「决策者」可保存并能测试连通性。
