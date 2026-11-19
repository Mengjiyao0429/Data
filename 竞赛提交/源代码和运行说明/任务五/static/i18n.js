/* 智掘 AI Discovery · 双语引擎
   约定：以中文原文为 key；英文模式返回译文，中文模式原样返回。
   静态文案用 data-i18n / data-i18n-ph / data-i18n-title / data-i18n-key。
   动态文案在 JS 中调用 T('中文')。 */
(function () {
  'use strict';

  var LANG_KEY = 't5_lang';
  var lang = 'zh';
  try { lang = localStorage.getItem(LANG_KEY) || 'zh'; } catch (e) { lang = 'zh'; }
  if (lang !== 'en') lang = 'zh';

  /* ---------------- 词条：中文 -> 英文 ---------------- */
  var DICT = {
    /* 品牌 / 导航 */
    '智掘 AI Discovery': 'AI Discovery',
    '分析工作台': 'ANALYTICS WORKBENCH', '决策支持': 'DECISION SUPPORT', '系统': 'SYSTEM',
    '概览看板': 'Overview', '数据分析': 'Data Analysis', '批次分析': 'Batch Analysis',
    '需求发起': 'New Requirement', '机会选取': 'Opportunity Selection',
    '策划案库': 'Proposal Library', '智能问答': 'AI Q&A', '系统设置': 'Settings',
    '需求驱动 · 一次需求一批次': 'Requirement-driven · one batch per requirement',
    '条': 'records', '簇': 'clusters', '结果呈现与决策支持': 'Results & Decision Support',
    '收起 / 展开侧栏': 'Collapse / expand sidebar', '当前登录身份': 'Signed-in identity',
    '退出': 'Sign out', '模式加载中': 'Loading mode…', '服务正常': 'Service OK',
    '服务异常': 'Service error', '连接失败': 'Connection failed', '未登录': 'Not signed in',
    '使用说明': 'How to use', '关闭': 'Close', '使用指南': 'Guide',
    /* 需求发起 */
    '以需求为驱动发起一次独立批次，自动完成采集、清洗、去重、机会判别、主题聚类与价值评估全链路。': 'Launch an independent batch from a requirement, running collection, cleaning, dedup, opportunity detection, clustering and value scoring end to end.',
    '发起一次需求': 'Launch a requirement',
    '一次需求 = 一个独立批次：采集 → 清洗 → 去重 → 机会判别 → 主题聚类 → 价值评估': 'One requirement = one batch: collect → clean → dedup → detect → cluster → score',
    '需求关键词': 'Requirement keywords',
    '例如：AI 编程助手 代码生成；或：医疗影像辅助诊断': 'e.g. AI coding assistant code generation; or medical imaging diagnosis',
    '采集来源': 'Data sources', '加载中…': 'Loading…', '目标条数': 'Target records',
    '备注（写入批次报告）': 'Note (written to batch report)', '选填': 'Optional',
    '发起采集与分析': 'Start collection & analysis',
    '批次': 'Batch', '需求': 'Requirement', '来源': 'Sources', '记录': 'Records',
    '机会': 'Opportunities', '状态': 'Status', '耗时': 'Elapsed', '操作': 'Actions',
    '簇': 'Clusters', '已完成': 'Done', '采集中': 'Running', '采集中…': 'Running…',
    '失败': 'Failed', '查看': 'View', '报告': 'Report',
    '批次列表': 'Batch list',
    '每个批次独立采集、独立聚类、独立评估，结果互不影响': 'Each batch is collected, clustered and scored independently',
    /* 批次分析 */
    '逐批次独立计数与聚类，查看簇价值排序、证据链与原始记录溯源。': 'Independent counting and clustering per batch; inspect cluster ranking, evidence chain and record traceability.',
    '选择批次': 'Select batch', '请选择批次': 'Select a batch',
    '刷新列表': 'Refresh', '正在加载批次…': 'Loading batches…',
    '本批次记录': 'Batch records', '采集清洗去重后': 'After cleaning & dedup',
    'AI 应用机会': 'AI opportunities', '本批次内判别': 'Detected in this batch',
    '机会主题簇': 'Opportunity clusters', '本批次内聚类': 'Clustered in this batch',
    '最高价值主题簇': 'Top-value cluster', '本批次内排序': 'Ranked in this batch',
    '本批次转化占比': 'Batch conversion', '本批次独立计数 · 环形视图': 'Independent counts · donut view',
    '主题簇价值排序': 'Cluster value ranking', '仅在本批次内可比': 'Comparable within this batch only',
    '点击行查看证据链并生成策划案': 'Click a row for evidence & proposal',
    '簇号': 'Cluster', '主题簇名称': 'Cluster name', '功能类别': 'Function',
    '行业': 'Industry', '记录数': 'Records', '来源数': 'Sources', '价值分': 'Value',
    '优先级': 'Priority',
    '原始记录检索（逐条溯源）': 'Record search (traceable)',
    '编号 → 正文快照 → 原始链接，可逐条核对': 'ID → text snapshot → source link',
    '按标题 / 正文 / 来源搜索': 'Search title / body / source',
    '全部记录': 'All records', '只看机会记录': 'Opportunities only', '检索': 'Search',
    '下载批次报告': 'Download batch report',
    '时间': 'Time', '是否机会': 'Opportunity', '置信度': 'Confidence', '溯源': 'Trace',
    /* 概览 */
    '任务一至任务四核心结果一览：数据规模、机会分布、主题簇价值与三维度贡献。': 'Core results from Tasks 1–4: data scale, opportunity distribution, cluster value and 3-dimension contributions.',
    '采集清洗去重': 'Collected & cleaned', '任务一 result1.csv': 'Task 1 · result1.csv',
    '任务二识别': 'Detected in Task 2', '任务三聚类': 'Clustered in Task 3',
    '任务四评分': 'Scored in Task 4',
    '窗口越大、来源越多，可行性越高': 'Larger bubbles & more sources imply higher feasibility',
    '价值分三维度贡献': '3-dimension value breakdown',
    '多源指向 / 记录规模 / 商业信号': 'Multi-source / record scale / business signal',
    '主题簇 × 来源覆盖': 'Clusters × source coverage',
    '多源共同指向 = 需求更可信': 'Multi-source agreement = more credible demand',
    /* 机会选取 */
    '依据簇机会价值分与优先级筛选高价值方向，可勾选并批量生成立项策划案。': 'Filter high-value directions by cluster value & priority; select and batch-generate proposals.',
    '筛选与勾选': 'Filter & select', '搜索主题簇编号 / 名称 / 功能类别 / 行业': 'Search cluster ID / name / function / industry',
    '全部行业': 'All industries', '全部功能': 'All functions', '来源数不限': 'Any source count',
    '≥ 2 个来源': '≥ 2 sources', '≥ 3 个来源': '≥ 3 sources', '≥ 4 个来源': '≥ 4 sources',
    '清空勾选': 'Clear selection', '已勾选 0 个方向': '0 directions selected',
    '批量生成立项策划案': 'Generate proposals in batch',
    /* 策划案库 */
    '已生成的立项策划案，可在线预览并导出为 Word / Markdown 文档。': 'Generated proposals; preview online and export to Word / Markdown.',
    '已生成策划案': 'Generated proposals', '生成方式': 'Mode', '模型': 'Model',
    '字数': 'Chars', '生成时间': 'Created', '预览': 'Preview',
    /* 数据分析 */
    '基于任务一至任务四真实结果的统计视图，彩色桑基流向与环形占比，所有数据可溯源。': 'Statistical views of real Task 1–4 results: colorful Sankey flow and donut shares, all traceable.',
    '全流程流向 · 彩色桑基图': 'End-to-end flow · Sankey',
    '采集 → 机会 / 非机会 → 各主题簇，流向宽度即规模，颜色区分主题': 'Collect → opportunity / non-opportunity → clusters; width = scale, color = theme',
    '转化进度 · 环形占比': 'Conversion · donut shares', '机会率 / 簇覆盖率': 'Opportunity rate / cluster coverage',
    '来源构成占比': 'Source composition', '各公开渠道记录数': 'Records per public channel',
    '功能类别占比': 'Function categories', '按机会记录数': 'By opportunity records',
    '所属行业占比': 'Industries', '经金标准 isotonic 校准': 'Isotonic-calibrated on gold set',
    '置信度分布': 'Confidence distribution', '各批次机会数': 'Opportunities by batch',
    'B01–B08 批次独立': 'B01–B08 batches are independent',
    'Top10 主题簇机会价值分': 'Top 10 cluster value scores',
    '固定基准 + 熵权法合成，优先级排序依据': 'Fixed baseline + entropy weighting; basis of priority',
    /* 智能问答 */
    '基于真实主题簇与证据的检索增强问答，回答带溯源，无 API Key 时离线可用。': 'Retrieval-augmented Q&A over real clusters and evidence; answers are traceable and work offline without an API key.',
    '智能问答咨询': 'AI Q&A consultation', '试试：': 'Try:',
    '哪些主题簇价值最高？': 'Which clusters have the highest value?',
    '医疗相关的机会有哪些？': 'What healthcare opportunities are there?',
    '智能体编排方向的证据': 'Evidence for agent orchestration',
    '输入你的问题，例如：教育行业有哪些高价值机会？': 'Ask a question, e.g. high-value opportunities in education?',
    '提问': 'Ask', '提问后将在此显示带溯源的回答。': 'Traceable answers appear here after asking.',
    /* 系统设置 */
    '配置模型服务模式与角色权限，兼顾成本与运行开销。': 'Configure model service and role permissions, balancing cost and runtime overhead.',
    '模型服务配置': 'Model service', '模型服务模式': 'Service mode',
    '离线模板（默认，零 API 成本，无需联网）': 'Offline template (default, zero API cost, no internet)',
    'OpenAI 兼容接口（硅基流动 / 智谱 / DeepSeek / 通义 / Moonshot）': 'OpenAI-compatible API (SiliconFlow / Zhipu / DeepSeek / Qwen / Moonshot)',
    '本地 Ollama（http://localhost:11434）': 'Local Ollama (http://localhost:11434)',
    '模型名称': 'Model name', '仅存本机': 'stored locally',
    '留空则保持原值': 'Leave blank to keep current', '温度 temperature': 'Temperature',
    '最大输出 max_tokens': 'Max tokens', '超时 timeout（秒）': 'Timeout (s)',
    '未测试': 'Not tested', '测试连通性': 'Test connection', '保存配置': 'Save settings',
    '角色与数据可见范围': 'Roles & data visibility', '角色': 'Role',
    '可用操作': 'Allowed actions', '数据可见范围': 'Data visibility',
    '需求发起者': 'Requester', '决策者': 'Decision maker',
    '浏览看板、筛选、选取机会、生成并下载策划案': 'View dashboards, filter, select opportunities, generate & download proposals',
    '主题簇与证据记录（脱敏后）': 'Clusters and evidence records (masked)',
    '以上全部 + 修改模型配置、查看审计日志': 'All above + edit model settings, view audit log',
    '全部数据与系统配置': 'All data and system settings',
    /* 抽屉 / 弹窗 */
    '选取该方向': 'Select direction', '生成立项策划案': 'Generate proposal',
    '立项策划案': 'Project proposal', '下载 Markdown': 'Download Markdown',
    '下载 Word': 'Download Word', '使用说明': 'How to use',
    '价值评分': 'Value scoring', '来源覆盖': 'Source coverage', '证据记录': 'Evidence records',
    '评分解释': 'Scoring notes', '编号': 'ID', '标题': 'Title', '热度': 'Heat',
    '多源指向度': 'Multi-source', '记录规模': 'Record scale', '商业信号': 'Business signal',
    /* 动态提示（JS） */
    '响应解析失败': 'Failed to parse response', '未登录或会话已过期': 'Not signed in or session expired',
    '概览看板': 'Overview', '加载失败：': 'Load failed: ', '加载详情失败：': 'Failed to load details: ',
    '共 0 个': '0 total', '共 {n} 个主题簇': '{n} clusters', '共 {n} 份': '{n} proposals',
    '已勾选 {n} 个方向': '{n} directions selected', '加载中…': 'Loading…',
    '正在生成立项策划案…': 'Generating proposal…', '离线模板': 'Offline template',
    '模型调用': 'Model call', '生成完成：': 'Done: ', '生成失败：': 'Generation failed: ',
    '批量完成：成功 {a}/{b} 份，已存入策划案库': 'Batch done: {a}/{b} succeeded, saved to library',
    '预览失败：': 'Preview failed: ', '暂无策划案，请到「机会选取」生成': 'No proposals yet — generate them in Opportunity Selection',
    '模型生成': 'Model', '模板兜底': 'Template fallback', '保存失败：': 'Save failed: ',
    '配置已保存（仅存于本机 SQLite）': 'Settings saved (stored locally in SQLite)',
    '测试中…': 'Testing…', '已配置：': 'Configured: ', '（留空保持）': ' (blank to keep)',
    '未配置': 'Not configured', '失败': 'Failed',
    '来源加载失败：': 'Failed to load sources: ', '网络代理可用：': 'Proxy available: ',
    '未检测到代理（GitHub/HN 可能失败，可勾选本地回放）': 'No proxy detected (GitHub/HN may fail; use local replay)',
    '请选择批次': 'Select a batch', '请至少勾选一个采集来源': 'Select at least one source',
    '请填写需求关键词': 'Enter requirement keywords', '已创建批次 {b}，正在采集…': 'Batch {b} created, collecting…',
    '发起失败：': 'Launch failed: ', '批次 {b} 正在采集与计算，页面会自动刷新（通常 20–90 秒）。': 'Batch {b} is collecting; this page refreshes automatically (usually 20–90 s).',
    '计算中…': 'Computing…', '批次状态读取失败：': 'Failed to read batch status: ',
    '执行失败：': 'failed: ', '未知错误': 'unknown error', '需求「': 'Requirement "',
    '」；来源 ': '"; sources ', '；发起 ': '; started ', '；耗时 ': '; elapsed ',
    '；聚类 k=': '; clusters k=', '；轮廓系数 ': '; silhouette ',
    '占本批次 {p}% · 阈值 0.50': '{p}% of batch · threshold 0.50',
    '分': ' pts', '本批次未形成机会簇': 'No opportunity clusters in this batch',
    '条机会记录 · 价值 ': ' opportunity records · value ', ' · 优先级 ': ' · priority ',
    '多源指向': 'Multi-source', '打开原文': 'Open source', '生成本批次立项策划案': 'Generate batch proposal',
    '生成中…': 'Generating…', '加载中…': 'Loading…', '命中 {n} 条（显示前 {m} 条）': '{n} hits (showing {m})',
    '没有符合条件的记录': 'No matching records', '机会': 'Opportunity', '否': 'No',
    '原文': 'Source', '快照': 'Snapshot', '读取失败：': 'Read failed: ',
    '还没有批次，先在上方发起一次需求': 'No batches yet — launch a requirement above',
    '列表加载失败：': 'Failed to load list: ', '还没有批次：请到「需求发起」页填写关键词并发起一次需求。': 'No batches: go to New Requirement and launch one.',
    '批次列表读取失败：': 'Failed to load batch list: ', '批次分析 · ': 'Batch Analysis · ',
    '详情读取失败：': 'Failed to load details: ', '已选取「': 'Selected "', '」进入备选': '" into shortlist',
    '选取失败：': 'Selection failed: ', '正在检索本地分析结果…': 'Searching local results…',
    '提问失败': 'Question failed', '（无回答）': '(no answer)', '错误：': 'Error: ',
    '加载失败': 'Load failed', '条': ' records', '簇': ' clusters',
    /* 补充：图表轴名与分数说明 */
    '簇内机会记录数': 'Opportunity records in cluster', '机会价值分': 'Opportunity value score',
    '得分': 'Score', '所属行业': 'Industries', '条机会记录': 'opportunity records',
    '个来源': 'sources', '机会率': 'Opportunity rate', '簇覆盖率': 'Cluster coverage',
    '机会占比': 'Opportunity share', '高价值方向': 'High-value share',
    'AI应用机会': 'AI Opportunities', '未构成机会': 'Non-opportunities', '其他机会': 'Other opportunities',
    '离线模板模式': 'Offline template mode', '本地 Ollama': 'Local Ollama',
    '没有符合条件的主题簇': 'No matching clusters',
    '占采集总量 {p}% · 阈值 {t}': '{p}% of collected · threshold {t}',
    '已选取「{c}」进入备选': 'Selected "{c}" into shortlist',
    '按热度取前 10 条': '(top 10 by heat)',
    '多源指向度 = 100 × min(1, 来源数/14)：覆盖来源种类越多，需求越可信；': 'Multi-source = 100 × min(1, sources/14): more sources mean more credible demand;',
    '记录规模 = 100 × min(1, 簇内记录数/100)：固定基准，跨批可比；': 'Record scale = 100 × min(1, cluster records/100): fixed baseline, comparable across batches;',
    '商业信号 = 0.6×生均互动热度 + 0.4×需求置信度。': 'Business signal = 0.6 × avg interaction heat + 0.4 × demand confidence.',
    '初始化失败：': 'Initialization failed: ', '加载策划案库失败：': 'Failed to load proposal library: ',
    '共 {n} 个批次，{d} 个已完成': '{n} batches, {d} done', '（采集中会自动刷新）': ' (auto-refresh while running)',
    '发起': 'Started', '聚类 k=': 'clusters k=', '轮廓系数': 'silhouette',
    '批次 <b>{b}</b> 正在采集与计算，页面会自动刷新（通常 20–90 秒）。': 'Batch <b>{b}</b> is collecting and computing; this page auto-refreshes (usually 20–90 s).',
    /* 概览 / 数据分析：论文级图表 */
    '点击放大': 'Click to zoom',
    '悬停查看数值': 'Hover for values',
    '占比': 'Share',
    '记录数': 'Records', '来源数': 'Sources', '优先级': 'Priority',
    '任务一至任务四核心结果一览：数据规模、机会分布、主题簇价值与信息多元性。悬停任意图可查看数值，点击图表可查看说明。': 'Core results from Tasks 1–4: data scale, opportunity distribution, cluster value and source diversity. Hover any chart for values.',
    '主题簇价值排序': 'Cluster value ranking',
    '悬停查看簇名、价值分与记录数': 'Hover for cluster name, value and record count',
    '价值分三维度贡献': '3-dimension value contribution',
    '悬停查看各维度得分': 'Hover for each dimension score',
    '信息来源多元构成': 'Diverse source composition',
    '悬停查看各来源记录数与占比': 'Hover for record count and share per source',
    '任务一至任务四结果的统计视图与论文级图表：彩色桑基流向、类别分布、语义空间、权重敏感性与价值排名，点击任意图可放大。': 'Statistics and publication-quality figures from Tasks 1–4: Sankey flow, category distribution, semantic space, weight sensitivity and value ranking. Click to enlarge.',
    '论文级图表 · 结果深度分析': 'Publication figures · in-depth analysis',
    '机会类别分布 · 棒棒糖图': 'Opportunity categories · lollipop',
    '智能体编排与推荐系统合计约四成': 'Agent orchestration + recommendation ≈ 40%',
    '功能类别与行业分布': 'Function & industry distribution',
    '16 类功能 / Top12 行业，全类别可辨': '16 functions / top-12 industries, all legible',
    '来源构成 · 批次 × 来源': 'Source composition · batch × source',
    '四大来源 × 八批次，信息多元可溯源': '4 sources × 8 batches, diverse & traceable',
    '价值排名 · 条形哑铃图': 'Value ranking · bar & dumbbell',
    '头部稳定，权重扰动下排名位移有限': 'Stable top ranks; limited shift under weight perturbation',
    '聚类分布 · t-SNE': 'Cluster distribution · t-SNE',
    '1728 条机会在语义空间连续分布': '1,728 opportunities form a continuous semantic space',
    '语义空间散点': 'Semantic space scatter',
    '按 55 个主题簇着色，颜色区分语义群': 'Colored by 55 clusters, distinguishing semantic groups',
    '三维度加权贡献': '3-dimension weighted contribution',
    '权重敏感性分析': 'Weight sensitivity analysis',
    '基准权重附近排序稳定，极端纯多源时下降': 'Stable near baseline; drops under extreme multi-source weights',
    '规则判别 · 混淆矩阵': 'Rule detection · confusion matrix',
    '金标准 120 条 · Precision 1.000 / Recall 0.880': 'Gold set 120 · Precision 1.000 / Recall 0.880',
    '簇规模与聚类质量': 'Cluster size & quality',
    '55 簇规模分布 · 各批次轮廓系数 / ARI': '55-cluster sizes · per-batch silhouette / ARI',
    '价值分类排序 · Top10 清爽版': 'Value ranking · Top 10 (clean)',
    '左侧仅簇号、名称见悬停，标签间距重新排布': 'Only cluster IDs on the left; names on hover; labels respaced'
  };

  /* ---------------- 富文本通知块（含链接 / 代码） ---------------- */
  var HTML = {
    'notice.requirement': {
      zh: '采集耗时约 20–90 秒（取决于来源与条数）；断网或接口限流时可勾选「本地语料回放」离线运行，记录会明确标注为回放，不冒充实时采集。',
      en: 'Collection takes ~20–90 s (depends on sources and volume). Offline? Tick "Local corpus replay"; such records are explicitly labeled as replay, never passed off as live.'
    },
    'notice.batchSelect': {
      zh: '选择上方批次即可查看该批次的独立分析结果。',
      en: 'Select a batch above to view its independent analysis results.'
    },
    'notice.roleRequester': {
      zh: '当前角色为「需求发起者」：可浏览、选取机会、生成策划案；系统配置仅决策者可修改。',
      en: 'Current role: Requester — can browse, select opportunities and generate proposals; only decision makers may edit system settings.'
    },
    'notice.roleDecision': {
      zh: '当前角色为「决策者」：可修改模型配置、查看审计日志，也可选取机会并生成策划案。',
      en: 'Current role: Decision maker — can edit model settings, view the audit log, select opportunities and generate proposals.'
    },
    'notice.cost': {
      zh: '成本与部署：存储使用单文件 SQLite（零运维）；模型服务可先用免费额度或本地 Ollama；默认离线模板模式不产生任何 API 费用。部署仅需 <code>pip install -r requirements.txt</code> 与 <code>python app.py</code>。',
      en: 'Cost & deployment: single-file SQLite (zero ops); use a free API tier or local Ollama; the default offline template incurs no API cost. Deploy with <code>pip install -r requirements.txt</code> and <code>python app.py</code>.'
    }
  };

  /* ---------------- 每张卡片的「使用说明」 ---------------- */
  var HELP = {
    'req-form': {
      zh: ['如何发起需求', '<p>这是系统的主链路：<b>一次需求 = 一个独立批次</b>。</p><ol><li>填写<b>需求关键词</b>，例如「AI 编程助手 代码生成」；关键词决定采集相关性。</li><li>勾选<b>采集来源</b>：Stack Overflow / Hacker News / GitHub / CSDN 为实时联网采集；<b>本地语料回放</b>从你本地 4322 条里按关键词抽取，断网时可用。</li><li>设置<b>目标条数</b>（50–2000）。</li><li>点「发起采集与分析」，系统自动完成清洗→去重→机会判别→聚类→价值评估，通常 20–90 秒。</li></ol><p>完成后会自动跳转到「批次分析」。每次发起都会生成独立批次，互不覆盖。</p>'],
      en: ['How to launch a requirement', '<p>This is the main flow: <b>one requirement = one independent batch</b>.</p><ol><li>Enter <b>keywords</b>, e.g. "AI coding assistant code generation"; keywords drive relevance.</li><li>Tick <b>sources</b>: Stack Overflow / Hacker News / GitHub / CSDN are live; <b>Local corpus replay</b> draws from your 4,322 local records for offline use.</li><li>Set the <b>target count</b> (50–2000).</li><li>Click "Start collection & analysis"; cleaning → dedup → detection → clustering → scoring run automatically (usually 20–90 s).</li></ol><p>You will be taken to Batch Analysis. Each launch creates a separate batch.</p>']
    },
    'batch-list': {
      zh: ['批次列表', '<p>列出所有已发起的需求批次及状态（采集中 / 已完成 / 失败）、记录数、机会数、簇数与耗时。</p><p>点「查看」进入该批次的完整分析；点「报告」下载该批次的 Markdown 报告。有批次运行中时列表每 3 秒自动刷新。</p>'],
      en: ['Batch list', '<p>Lists every launched batch with status (running / done / failed), record count, opportunities, clusters and elapsed time.</p><p>Click "View" for full analysis or "Report" to download the Markdown report. While any batch is running, the list refreshes every 3 seconds.</p>']
    },
    'b-funnel': {
      zh: ['本批次转化占比', '<p>只看<b>当前所选批次</b>：外环是机会率（判为 AI 机会的记录 / 本批次记录），内环是簇覆盖率。</p><p>数字为本批次独立计数，不能与基线 4322 条或其它批次直接相加比较。</p>'],
      en: ['Batch conversion', '<p>Shows the <b>selected batch only</b>: the outer ring is the opportunity rate, the inner ring the cluster coverage.</p><p>Figures are counted within this batch and are not directly comparable to the 4,322-record baseline or other batches.</p>']
    },
    'b-rank': {
      zh: ['主题簇价值排序', '<p>按机会价值分降序显示本批次的主题簇，第一名为红色。价值分由多源指向度、记录规模、商业信号三维加权得到，<b>只在本批次内可比</b>。</p><p>点击「机会主题簇」表格中的行可查看该簇的证据记录。</p>'],
      en: ['Cluster value ranking', '<p>Clusters of this batch sorted by value score (top one in red). The score combines multi-source, record scale and business signal; <b>comparable within this batch only</b>.</p><p>Click a row in the cluster table to view its evidence records.</p>']
    },
    'b-clusters': {
      zh: ['机会主题簇', '<p>本批次聚类得到的主题簇，含记录数、来源数、价值分与优先级。点任意一行展开详情：三维评分、来源覆盖、证据记录，并可<b>生成本批次立项策划案</b>。</p>'],
      en: ['Opportunity clusters', '<p>Clusters formed in this batch with record count, source count, value and priority. Click any row for details: 3-dimension scores, source coverage, evidence records, and <b>generate a batch proposal</b>.</p>']
    },
    'b-records': {
      zh: ['原始记录检索', '<p>逐条查看本批次的采集记录，可按标题 / 正文 / 来源搜索，或只看机会记录。每条都可通过「原文」回到采集页面，用编号与正文快照核对，实现逐条溯源。</p>'],
      en: ['Record search', '<p>Browse individual records of this batch; filter by title / body / source or opportunities only. "Source" opens the original page; IDs and text snapshots allow line-by-line verification.</p>']
    },
    'over-rank': {
      zh: ['主题簇价值排序', '<p>基线 55 个主题簇的散点图：横轴为簇内机会记录数，纵轴为价值分，气泡越大表示覆盖来源越多。红/蓝/灰分别对应高、中、低优先级，标签只显示前 6 名。</p>'],
      en: ['Cluster value ranking', '<p>Scatter of the 55 baseline clusters: x = opportunity records, y = value score, bubble size = source count. Red/blue/gray mark high/medium/low priority; only the top 6 are labeled.</p>']
    },
    'over-contrib': {
      zh: ['价值分三维度贡献', '<p>前 8 个簇的价值分堆叠拆解：多源指向度、记录规模、商业信号。可看出每个簇的高分主要来自哪个维度。</p>'],
      en: ['3-dimension value breakdown', '<p>Stacked value scores of the top 8 clusters: multi-source, record scale and business signal. See which dimension drives each cluster’s score.</p>']
    },
    'over-source': {
      zh: ['信息来源多元构成', '<p>南丁格尔玫瑰图（扇形半径随记录数变化）：每个扇形是一个公开采集来源，面积越大表示该来源贡献的记录越多。</p><p>四个来源并存、半径相近，说明信息来自多个独立渠道而非单一站点，多源交叉印证使机会判别更可信。鼠标悬停可看具体记录数与占比。</p>'],
      en: ['Diverse source composition', '<p>Nightingale rose chart (sector radius scales with record count): each sector is a public collection source; larger area means more records contributed.</p><p>Four comparable sources show information comes from multiple independent channels rather than a single site — cross-validation makes detection more credible. Hover for exact counts and shares.</p>']
    },
    'ins-sankey': {
      zh: ['彩色桑基流向图', '<p>从「采集清洗去重」出发，分成「AI 应用机会」与「未构成机会」，再流向各主题簇。<b>流向宽度 = 记录规模</b>，颜色区分主题。鼠标悬停可看具体数值。</p><p>这是替代传统漏斗的呈现方式，数据来自基线 4322 条。</p>'],
      en: ['Sankey flow', '<p>From "Collected & cleaned", flow splits into "AI opportunities" and "Non-opportunities", then into clusters. <b>Width = record scale</b>; colors distinguish themes. Hover for values.</p><p>This replaces a traditional funnel and uses the 4,322-record baseline.</p>']
    },
    'ins-rate': {
      zh: ['转化进度 · 环形占比', '<p>三层同心环：外环机会率、中环簇覆盖率、内环高价值方向占比，中心数字为机会率。用于快速判断全流程的收窄程度。</p>'],
      en: ['Conversion donut', '<p>Three concentric rings: opportunity rate, cluster coverage and high-value share; the center number is the opportunity rate. A quick read of funnel narrowing.</p>']
    },
    'ins-source': {
      zh: ['来源构成占比', '<p>各公开采集渠道的记录数占比，用于判断数据来源是否集中于单一渠道。来源越分散，多源指向的可信度越高。</p>'],
      en: ['Source composition', '<p>Share of records per public channel; shows whether data is concentrated in one source. More diverse sources mean more credible multi-source signals.</p>']
    },
    'ins-func': {
      zh: ['功能类别占比', '<p>按机会记录数统计的 16 类功能分布（附件 1 标签体系）。用于发现需求集中在哪些 AI 功能上。</p>'],
      en: ['Function categories', '<p>Distribution across the 16 function categories (Appendix 1) by opportunity records; reveals which AI functions concentrate demand.</p>']
    },
    'ins-ind': {
      zh: ['所属行业占比', '<p>按机会记录数统计的行业分布。标注为「其他」表示文本中没有明确行业锚定词，系统不做硬指派。</p>'],
      en: ['Industries', '<p>Industry distribution by opportunity records. "Other" means no explicit industry anchor was found, so no label was forced.</p>']
    },
    'ins-conf': {
      zh: ['置信度分布', '<p>机会记录的置信度分桶直方图。置信度经金标准 isotonic 校准，数值越高表示规则证据越充分。</p>'],
      en: ['Confidence distribution', '<p>Histogram of opportunity confidence buckets. Values are isotonic-calibrated on a gold set; higher means stronger rule evidence.</p>']
    },
    'ins-batch': {
      zh: ['各批次机会数', '<p>B01–B08 八个采集批次各自判出的机会数，用于检查批次间机会率是否稳定、有无异常批次。</p>'],
      en: ['Opportunities by batch', '<p>Opportunities detected in each of the eight B01–B08 batches; useful for checking cross-batch stability and outliers.</p>']
    },
    'ins-value': {
      zh: ['Top10 主题簇机会价值分', '<p>价值分最高的 10 个主题簇，采用固定基准归一化 + 熵权法合成，是「机会选取」优先级排序的依据。</p>'],
      en: ['Top 10 cluster value scores', '<p>The 10 highest-value clusters, scored with fixed-baseline normalization + entropy weighting; drives priority in Opportunity Selection.</p>']
    },
    'ins-value': {
      zh: ['价值排名 · 条形哑铃图', '<p>左图为 55 个主题簇按机会价值分降序的<b>条形排名</b>（Top1 B02 推荐系统 65.9 分）；右图为<b>哑铃图</b>，对比基准权重与扰动方案下每个簇的排名位移。</p><p>绝大多数簇排名位移有限，说明价值排序对权重设定稳健；这也是「机会选取」优先级排序的依据。</p>'],
      en: ['Value ranking · dumbbell', '<p>Left: <b>bar ranking</b> of 55 clusters by value score (top: B02 recommender, 65.9). Right: <b>dumbbell</b> comparing each cluster’s rank under baseline vs. perturbed weights.</p><p>Most clusters shift little, showing the ranking is robust to weight settings — the basis of Opportunity Selection priority.</p>']
    },
    'ins-tsne': {
      zh: ['聚类分布 · t-SNE', '<p>将 1,728 条机会记录的 TF-IDF 文本经 LSA 降维后用 t-SNE 投影到二维。每个点按所属主题簇着色，形状区分来源。</p><p>点在语义空间呈连续分布、簇间边界模糊，说明主题是渐变的连续谱，而非彼此割裂的类别；系统不强行制造清晰边界。</p>'],
      en: ['Cluster distribution · t-SNE', '<p>TF-IDF features of 1,728 opportunity records reduced by LSA then projected with t-SNE; each point is colored by its cluster and shaped by source.</p><p>Points form a continuous semantic space with fuzzy boundaries, indicating a spectrum of topics rather than sharply separated categories.</p>']
    },
    'ins-semantic': {
      zh: ['语义空间散点', '<p>与 t-SNE 图互补的另一种语义投影（TF-IDF → LSA → PCA），按 55 个主题簇着色。颜色相同的点属于同一语义群。</p><p>用于直观检查聚类结果在语义空间中是否形成可分辨的群组，是任务三聚类有效性的可视化证据。</p>'],
      en: ['Semantic space scatter', '<p>A complementary projection (TF-IDF → LSA → PCA) colored by 55 clusters; points of the same color belong to one semantic group.</p><p>It visually checks whether clusters form distinguishable groups in semantic space — evidence for Task 3 clustering validity.</p>']
    },
    'ins-contrib': {
      zh: ['三维度加权贡献', '<p>55 个主题簇的机会价值分按三维拆解：<b>多源指向度、记录规模、商业信号</b>，每根柱的高度为加权后的贡献，总和即价值分。</p><p>可看出高分簇主要由哪个维度驱动，避免只看总分而忽略构成，是评分可解释性的核心图表。</p>'],
      en: ['3-dimension weighted contribution', '<p>Value scores of 55 clusters decomposed into <b>multi-source, record scale and business signal</b>; each bar shows the weighted contribution, summing to the total.</p><p>It reveals which dimension drives high scores, making the scoring interpretable rather than a black-box total.</p>']
    },
    'ins-sens': {
      zh: ['权重敏感性分析', '<p>四个子图检验价值排序对权重的稳健性：<b>权重网格热力图</b>（不同多源/规模权重下的 Spearman 相关）、Top5 重合度、单参数变化曲线与维度相关性热力图。</p><p>基准权重（多源 0.293 / 规模 0.5065 / 商业 0.2005）附近排名 Spearman 常高于 0.99；只有在极端「纯多源」设置下稳定性才明显下降。</p>'],
      en: ['Weight sensitivity analysis', '<p>Four panels test ranking robustness: a <b>weight-grid heatmap</b> (Spearman across weights), Top-5 overlap, single-parameter curves and dimension correlations.</p><p>Near the baseline weights (0.293 / 0.5065 / 0.2005) Spearman is usually above 0.99; stability drops only under extreme "pure multi-source" settings.</p>']
    },
    'ins-confmat': {
      zh: ['规则判别 · 混淆矩阵', '<p>在 120 条人工金标准上评估任务二的 AI 机会判别规则：TP 22 / FP 0 / FN 3 / TN 95，Precision 1.000、Recall 0.880、F1 0.936。</p><p>零误报意味着判为机会的记录可信；这是「规则阈值 0.60 是否合理」的量化依据。</p>'],
      en: ['Rule detection · confusion matrix', '<p>Evaluation of the Task 2 detection rule on a 120-record gold set: TP 22 / FP 0 / FN 3 / TN 95; Precision 1.000, Recall 0.880, F1 0.936.</p><p>Zero false positives means flagged opportunities are credible — quantitative evidence for the 0.60 threshold.</p>']
    },
    'ins-quality': {
      zh: ['簇规模与聚类质量', '<p>左图是 55 个主题簇的簇内记录数分布（呈长尾）；右图是各批次的轮廓系数与多子样本 ARI。</p><p>轮廓系数偏低与 t-SNE 中的连续分布一致，说明文本主题本身边界模糊；ARI 反映不同子样本间聚类的一致性。</p>'],
      en: ['Cluster size & quality', '<p>Left: within-cluster sizes of 55 clusters (long-tailed). Right: per-batch silhouette and multi-subsample ARI.</p><p>Low silhouette matches the continuous t-SNE distribution — topic boundaries are inherently fuzzy; ARI measures clustering consistency across subsamples.</p>']
    },
    'ask-box': {
      zh: ['智能问答怎么问', '<p>直接输入问题，或点上方三个示例。系统先从真实主题簇与证据中检索，再生成<b>带溯源的回答</b>。</p><p>不配 API Key 时使用离线检索，回答会列出依据编号；配置模型后会基于这些真实依据生成更自然的中文回答，但不会编造数据。</p>'],
      en: ['How to ask', '<p>Type a question or click one of the three examples. The system retrieves from real clusters and evidence, then answers <b>with traceable sources</b>.</p><p>Without an API key it runs offline and lists source IDs; with a model configured it writes a more natural answer grounded strictly in those facts — never fabricated.</p>']
    },
    'sel-table': {
      zh: ['如何选取机会', '<p>用搜索框、行业 / 功能 / 来源数筛选高价值簇；勾选左侧复选框后，点「批量生成立项策划案」。</p><p>点任意一行打开详情抽屉，可查看三维评分、证据记录和评分解释，并单独选取或生成策划案。价值分与优先级来自任务四。</p>'],
      en: ['How to select opportunities', '<p>Filter high-value clusters by search, industry / function / source count; tick checkboxes then click "Generate proposals in batch".</p><p>Click a row for the detail drawer with 3-dimension scores, evidence and scoring notes; select or generate a single proposal. Values and priorities come from Task 4.</p>']
    },
    'lib-table': {
      zh: ['策划案库', '<p>所有已生成的立项策划案都保存在本机 SQLite，刷新页面不会丢失。可在线「预览」，或导出为 Markdown / Word。</p><p>生成方式标记为「离线模板」「模型生成」或「模板兜底」：模型调用失败时自动回退，保证永远有可交付的策划案。</p>'],
      en: ['Proposal library', '<p>All generated proposals are stored in local SQLite and survive refresh. Preview online or export to Markdown / Word.</p><p>Mode is shown as offline template, model, or template fallback: if a model call fails, the system falls back automatically so a deliverable always exists.</p>']
    },
    'set-form': {
      zh: ['如何配置 API', '<p>三种模式：<b>离线模板</b>（默认，零成本、无需联网）、<b>OpenAI 兼容接口</b>（硅基流动 / 智谱 / DeepSeek 等）、<b>本地 Ollama</b>。</p><p>要配 API：用「决策者」账号登录 → 模式选 OpenAI 兼容 → base_url 填 <code>https://api.siliconflow.cn/v1</code> → model 填 <code>Qwen/Qwen2.5-7B-Instruct</code>（免费）→ api_key 粘贴 sk- 开头的密钥 → 测试连通性 → 保存。只有决策者能保存配置。</p><p>不配 API 也能完整使用系统；难度仅在策划案文字由模板生成。密钥只存本机 SQLite，请勿提交到 GitHub。</p>'],
      en: ['How to configure an API', '<p>Three modes: <b>offline template</b> (default, zero cost, no internet), <b>OpenAI-compatible API</b> (SiliconFlow / Zhipu / DeepSeek, etc.), <b>local Ollama</b>.</p><p>To connect: sign in as decision maker → choose OpenAI-compatible → set base_url <code>https://api.siliconflow.cn/v1</code>, model <code>Qwen/Qwen2.5-7B-Instruct</code> (free), and paste your sk- key → test connection → save. Only decision makers can save.</p><p>The system works fully without an API key; only proposal wording differs. Keys are stored in local SQLite — never commit them to GitHub.</p>']
    },
    'set-roles': {
      zh: ['角色与权限', '<p><b>需求发起者</b>（analyst / analyst@123）：浏览、筛选、选取机会、生成并下载策划案。</p><p><b>决策者</b>（decision / decision@123）：以上全部 + 修改模型配置、查看审计日志。角色由服务端会话判定，前端无法伪造；用需求发起者账号给 403。</p>'],
      en: ['Roles & permissions', '<p><b>Requester</b> (analyst / analyst@123): browse, filter, select opportunities, generate and download proposals.</p><p><b>Decision maker</b> (decision / decision@123): all above plus editing model settings and viewing the audit log. Roles are enforced by the server session and cannot be forged; the requester receives 403.</p>']
    }
  };

  /* ---------------- 引擎 ---------------- */
  function T(zh) {
    if (lang === 'zh' || zh === undefined || zh === null) return zh;
    return Object.prototype.hasOwnProperty.call(DICT, zh) ? DICT[zh] : zh;
  }
  function TF(zh, vars) {
    var s = T(zh);
    if (vars) Object.keys(vars).forEach(function (k) {
      s = String(s).split('{' + k + '}').join(vars[k]);
    });
    return s;
  }
  function getLang() { return lang; }

  function applyStatic() {
    document.documentElement.lang = lang === 'en' ? 'en' : 'zh-CN';
    document.title = (lang === 'en' ? 'AI Discovery' : '智掘 AI Discovery');

    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      if (!el.dataset.zhSrc) el.dataset.zhSrc = el.textContent;
      el.textContent = T(el.dataset.zhSrc);
    });
    document.querySelectorAll('[data-i18n-ph]').forEach(function (el) {
      if (!el.dataset.zhPh) el.dataset.zhPh = el.getAttribute('placeholder') || '';
      el.setAttribute('placeholder', T(el.dataset.zhPh));
    });
    document.querySelectorAll('[data-i18n-title]').forEach(function (el) {
      if (!el.dataset.zhTitle) el.dataset.zhTitle = el.getAttribute('title') || '';
      el.setAttribute('title', T(el.dataset.zhTitle));
    });
    document.querySelectorAll('[data-i18n-key]').forEach(function (el) {
      var item = HTML[el.getAttribute('data-i18n-key')];
      if (item) el.innerHTML = lang === 'en' ? item.en : item.zh;
    });
    document.querySelectorAll('.lang-switch button').forEach(function (b) {
      b.classList.toggle('on', b.getAttribute('data-lang') === lang);
    });
  }

  function setLang(l) {
    l = (l === 'en') ? 'en' : 'zh';
    if (l === lang) { applyStatic(); return; }
    lang = l;
    try { localStorage.setItem(LANG_KEY, lang); } catch (e) {}
    applyStatic();
    window.dispatchEvent(new CustomEvent('i18n:change', { detail: { lang: lang } }));
  }

  function help(id) {
    var h = HELP[id];
    if (!h) return { title: T('使用说明'), body: '' };
    return lang === 'en' ? { title: h.en[0], body: h.en[1] } : { title: h.zh[0], body: h.zh[1] };
  }

  function bindUI() {
    document.querySelectorAll('.lang-switch button').forEach(function (b) {
      b.addEventListener('click', function () { setLang(b.getAttribute('data-lang')); });
    });
    var hm = document.getElementById('helpModal');
    document.querySelectorAll('[data-help]').forEach(function (b) {
      b.addEventListener('click', function () {
        var h = help(b.getAttribute('data-help'));
        document.getElementById('hHelpTitle').textContent = h.title;
        document.getElementById('hHelpBody').innerHTML = h.body;
        if (hm) hm.classList.add('open');
      });
    });
    var closeHelp = function () { if (hm) hm.classList.remove('open'); };
    var hc = document.getElementById('hHelpClose');
    if (hc) hc.addEventListener('click', closeHelp);
    if (hm) hm.addEventListener('click', function (e) { if (e.target === hm) closeHelp(); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && hm) hm.classList.remove('open');
    });
    var nt = document.getElementById('btnNavToggle');
    if (nt) nt.addEventListener('click', function () {
      if (window.innerWidth <= 820) document.body.classList.toggle('nav-open');
      else document.body.classList.toggle('nav-mini');
      setTimeout(function () { window.dispatchEvent(new Event('resize')); }, 230);
    });
  }

  window.T = T;
  window.TF = TF;
  window.I18N = { T: T, TF: TF, getLang: getLang, setLang: setLang, apply: applyStatic, help: help, HTML: HTML };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { applyStatic(); bindUI(); });
  else { applyStatic(); bindUI(); }
})();
