# 任务三 主题聚合报告（语义级 v3）

- 输入机会记录：388 条（跨 B01–B05）
- 向量化：jieba 中文分词（AI 术语词典）+ 英文词 → TF-IDF（ngram 1-2，min_df=2，max_df=0.6）
- 语义投影：TruncatedSVD(LSA)，维度 96，累计方差 0.449
- 候选：KMeans、层次聚类(Ward)，k∈{12..20}
- 评估方案：轮廓系数(0.20)+DB(0.20)+CH(0.15)+NPMI 主题一致性(0.30)+簇规模均衡度(0.15)，归一化加权
- 最终选优：KMeans，在“最大簇占比≤16%”约束下最大化 NPMI 主题一致性 → k=14
- 稳定性(5 次随机种子两两 ARI 均值) = 0.408
- 主题簇数：14，覆盖机会记录：388

## 一、聚类评估结果（候选方案前 12）

| 方法 | k | 轮廓 | DB | CH | NPMI | 均衡 | 综合 |
|---|---|---|---|---|---|---|---|
| Agglomerative | 20 | 0.093 | 2.58 | 7.2 | 0.486 | 0.78 | 0.848 |
| Agglomerative | 19 | 0.089 | 2.60 | 7.3 | 0.490 | 0.78 | 0.848 |
| Agglomerative | 18 | 0.083 | 2.72 | 7.4 | 0.467 | 0.78 | 0.742 |
| Agglomerative | 17 | 0.080 | 2.81 | 7.5 | 0.461 | 0.78 | 0.698 |
| Agglomerative | 16 | 0.075 | 2.85 | 7.5 | 0.463 | 0.78 | 0.685 |
| Agglomerative | 12 | 0.064 | 2.74 | 7.9 | 0.486 | 0.65 | 0.670 |
| Agglomerative | 14 | 0.070 | 2.79 | 7.7 | 0.472 | 0.71 | 0.669 |
| Agglomerative | 13 | 0.065 | 2.78 | 7.8 | 0.478 | 0.69 | 0.666 |
| Agglomerative | 15 | 0.075 | 2.82 | 7.6 | 0.467 | 0.71 | 0.662 |
| KMeans | 20 | 0.076 | 3.00 | 6.9 | 0.459 | 0.84 | 0.610 |
| KMeans | 19 | 0.078 | 2.80 | 6.8 | 0.453 | 0.76 | 0.576 |
| KMeans | 17 | 0.070 | 2.96 | 7.3 | 0.432 | 0.83 | 0.562 |

## 二、主题簇一览

| 簇 | 主题簇名称 | 功能类别 | 所属行业 | 记录数 | 主导批次 | 来源覆盖 |
|---|---|---|---|---|---|---|
| C1 | 大模型 API 与行业应用开发 | 文本生成 | 其他 | 59 | B02 | GitHub、Stack Overflow、CSDN、腾讯新闻 |
| C2 | 大模型 API 调用与文本生成 | 文本生成 | 其他 | 58 | B04 | Stack Overflow、GitHub |
| C3 | 知识图谱与智能体应用开发 | 知识检索 | 其他 | 44 | B04 | Stack Overflow、GitHub |
| C4 | 行业智能体与视觉检测方案 | 智能体编排 | 其他 | 43 | B02 | GitHub |
| C5 | 大模型 API 调试与工程实践 | 文本生成 | 其他 | 31 | B04 | Stack Overflow |
| C6 | LangChain 与模型推理工程 | 知识检索 | 其他 | 26 | B04 | Stack Overflow |
| C7 | 文档 OCR 与法律文本分析 | 图像识别 | 法律 | 23 | B02 | GitHub、CSDN |
| C8 | AI 治理与法律行业应用 | 审核审查 | 法律 | 21 | B05 | CSDN、GitHub、36氪、阿里云开发者社区 |
| C9 | 健康与生活方式智能推荐 | 推荐系统 | 医疗 | 21 | B02 | GitHub |
| C10 | 知识图谱增强的检索问答 | 知识检索 | 其他 | 17 | B05 | CSDN、GitHub |
| C11 | 语音识别与面试辅助 | 语音处理 | 人力资源 | 14 | B04 | Stack Overflow、GitHub |
| C12 | 医疗影像诊断与辅助医疗 | 图像识别 | 医疗 | 14 | B05 | CSDN、GitHub |
| C13 | AI 赋能智慧教育 | 推荐系统 | 教育 | 9 | B05 | CSDN |
| C14 | 能源行业智能体设计应用方案 | 智能体编排 | 能源 | 8 | B05 | CSDN |

## 三、多源共同指向的热点主题

来源覆盖含 2 个及以上网站的簇，视为“多源共同指向”的热点：

| 簇 | 主题 | 记录数 | 来源数 | 来源覆盖 |
|---|---|---|---|---|
| C1 | 大模型 API 与行业应用开发 | 59 | 4 | GitHub、Stack Overflow、CSDN、腾讯新闻 |
| C2 | 大模型 API 调用与文本生成 | 58 | 2 | Stack Overflow、GitHub |
| C3 | 知识图谱与智能体应用开发 | 44 | 2 | Stack Overflow、GitHub |
| C7 | 文档 OCR 与法律文本分析 | 23 | 2 | GitHub、CSDN |
| C8 | AI 治理与法律行业应用 | 21 | 4 | CSDN、GitHub、36氪、阿里云开发者社区 |
| C10 | 知识图谱增强的检索问答 | 17 | 2 | CSDN、GitHub |
| C11 | 语音识别与面试辅助 | 14 | 2 | Stack Overflow、GitHub |
| C12 | 医疗影像诊断与辅助医疗 | 14 | 2 | CSDN、GitHub |

共 8/14 个主题簇被多源共同指向。

## 四、各簇代表记录

### C1 大模型 API 与行业应用开发（59 条）
- 中文关键词：
- 英文关键词：search
- B01-S00005（GitHub）thedotmack/claude-mem
- B01-S00044（GitHub）tanweai/pua
- B01-S00108（GitHub）julep-ai/julep

### C2 大模型 API 调用与文本生成（58 条）
- 中文关键词：教育、学习、教师、个性化、个性化 学习、教学
- B01-S01039（GitHub）Ashinshani/Movie-Recommendation-System
- B02-S00032（GitHub）humanlayer/12-factor-agents
- B02-S00037（GitHub）screenpipe/screenpipe

### C3 知识图谱与智能体应用开发（44 条）
- 中文关键词：
- 英文关键词：openai
- B01-S00477（GitHub）roboflow/model-leaderboard
- B02-S00371（GitHub）maxigo-web/maxigo-client
- B02-S00744（GitHub）nomi30701/yolo-object-detection-onnxruntime-web

### C4 行业智能体与视觉检测方案（43 条）
- 中文关键词：医疗、诊断、治疗、个性化、未来、个性化 治疗
- B01-S00135（GitHub）iflytek/astron-rpa
- B01-S00206（GitHub）souvikmajumder26/Multi-Agent-Medical-Assistant
- B01-S00336（GitHub）kangjul3854/hyufa

### C5 大模型 API 调试与工程实践（31 条）
- 中文关键词：
- 英文关键词：text、code、sentiment
- B04-S00144（Stack Overflow）Streaming response from ASP.NET Core Web API to Angular fron
- B04-S00148（Stack Overflow）CloudFlare 400 Error When Calling OpenAI Completions API on 
- B04-S00154（Stack Overflow）Faraday too many requests when using openai ruby gem?

### C6 LangChain 与模型推理工程（26 条）
- 中文关键词：语音识别
- 英文关键词：agent、chatbot、llm、agents、job
- B04-S00011（Stack Overflow）How to add millions of documents to ChromaDB efficently
- B04-S00060（Stack Overflow）Cannot import langchain.vectorstores.FAISS, only langchain_c
- B04-S00092（Stack Overflow）Presidio with Langchain Experimental does not detect Polish 

### C7 文档 OCR 与法律文本分析（23 条）
- 中文关键词：
- 英文关键词：audio、speech、voice、interview、asr、openai
- B01-S00659（GitHub）PSPDFKit/nutrient-dws-client-python
- B01-S01041（GitHub）chaomazo-OCR/OCRgenius
- B01-S01220（GitHub）deephabiswashi/Legal-Document-CaseLaw-Analyzer

### C8 AI 治理与法律行业应用（21 条）
- 中文关键词：
- 英文关键词：vector、question、database
- B01-S00077（GitHub）shaxiu/XianyuAutoAgent
- B01-S00098（GitHub）interviewstreet/hiring-agent
- B03-S00233（GitHub）tgoai/tgo

### C9 健康与生活方式智能推荐（21 条）
- 中文关键词：智能体、方案、智能体 设计、设计 方案、设计、架构
- B01-S00540（GitHub）hoangsonww/Moodify-Emotion-Music-App
- B01-S00578（GitHub）Hrishikesh332/Twelve-Labs-Fashion-chat-assistant
- B01-S01024（GitHub）Rhythmica02/Cognitive_Health_Monitoring_System_for_Spacecraf

### C10 知识图谱增强的检索问答（17 条）
- 中文关键词：识别
- 英文关键词：ocr、document、extraction、pdf
- B01-S00862（GitHub）SoupCola/Agent_Project
- B03-S00291（GitHub）liangdabiao/langgraph_multi-agent-rag-customer-support
- B05-S00075（CSDN）知识图谱增强的RAG(KG-RAG)详细解析

### C11 语音识别与面试辅助（14 条）
- 中文关键词：
- 英文关键词：assistant、customer、medical、rag
- B01-S01032（GitHub）fortunatoman/AI-Interview-Assistant
- B02-S00334（GitHub）HKAllThingsLink/streaming-asr
- B02-S00435（GitHub）innovatorved/realtime-interview-copilot

### C12 医疗影像诊断与辅助医疗（14 条）
- 中文关键词：
- 英文关键词：recommendation、job
- B03-S00254（GitHub）ZeroTang05/cyber-doctor
- B05-S00026（CSDN）多模态大模型——多模态大模型技术特点、多模态大模型应用场景、多模态大模型案例、多模态大模型面临挑战
- B05-S00032（CSDN）大模型报告 | 《2024年医疗人工智能研究报告-生成式AI爆发，医疗人工智能走到新的十字路口》（附PDF下载）

### C13 AI 赋能智慧教育（9 条）
- 中文关键词：自动化、法律、智能体、工作、本文、规则
- 英文关键词：agent
- B05-S00011（CSDN）AI赋能教育：AI人工智能在教育中的 8 个应用示例（老师必须收藏）
- B05-S00049（CSDN）分享AI赋能教育：人工智能在教育中的八大应用
- B05-S00207（CSDN）人工智能与智能教育：AI如何帮助实现个性化学习与在线教育的未来？

### C14 能源行业智能体设计应用方案（8 条）
- 中文关键词：知识图谱、构建、检索、检索增强、生成、增强
- 英文关键词：rag
- B05-S00180（CSDN）【人工智能+】AI税务智能体设计应用方案
- B05-S00206（CSDN）【人工智能+】AI物流智能体设计应用方案
- B05-S00227（CSDN）【人工智能+】AI石油智能体系统设计应用方案
