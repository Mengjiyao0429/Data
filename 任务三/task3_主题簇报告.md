# 任务三 主题聚合报告（语义级 v3）

- 输入机会记录：986 条（跨 B01–B08，共 8 个批次）
- 向量化：jieba 中文分词（AI 术语词典）+ 英文词 → TF-IDF（ngram 1-2，min_df=2，max_df=0.6）
- 语义投影：TruncatedSVD(LSA)，维度 96，累计方差 0.266
- 候选：KMeans、层次聚类(Ward)，k∈{10..30}
- 评估方案：轮廓系数(0.20)+DB(0.20)+CH(0.15)+NPMI 主题一致性(0.30)+簇规模均衡度(0.15)，归一化加权
- 最终选优：KMeans，在“最大簇占比≤16%”约束下最大化 NPMI 主题一致性 → k=30
- 稳定性(5 次随机种子两两 ARI 均值) = 0.439
- 主题簇数：30，覆盖机会记录：986

## 一、聚类评估结果（候选方案前 12）

| 方法 | k | 轮廓 | DB | CH | NPMI | 均衡 | 综合 |
|---|---|---|---|---|---|---|---|
| Agglomerative | 12 | 0.081 | 2.31 | 21.3 | 0.563 | 0.57 | 0.739 |
| Agglomerative | 27 | 0.094 | 2.31 | 16.9 | 0.504 | 0.82 | 0.735 |
| Agglomerative | 11 | 0.078 | 2.41 | 21.8 | 0.572 | 0.57 | 0.733 |
| Agglomerative | 29 | 0.095 | 2.33 | 16.6 | 0.500 | 0.83 | 0.729 |
| KMeans | 21 | 0.079 | 2.35 | 18.0 | 0.541 | 0.78 | 0.726 |
| Agglomerative | 30 | 0.097 | 2.36 | 16.4 | 0.489 | 0.83 | 0.717 |
| Agglomerative | 23 | 0.088 | 2.41 | 17.6 | 0.512 | 0.81 | 0.715 |
| Agglomerative | 13 | 0.080 | 2.53 | 20.8 | 0.540 | 0.68 | 0.710 |
| Agglomerative | 28 | 0.092 | 2.38 | 16.7 | 0.497 | 0.83 | 0.710 |
| Agglomerative | 10 | 0.073 | 2.53 | 22.6 | 0.571 | 0.57 | 0.709 |
| Agglomerative | 15 | 0.083 | 2.43 | 20.0 | 0.528 | 0.68 | 0.708 |
| Agglomerative | 26 | 0.091 | 2.39 | 17.1 | 0.499 | 0.82 | 0.705 |

## 二、主题簇一览

| 簇 | 主题簇名称 | 功能类别 | 所属行业 | 记录数 | 主导批次 | 来源覆盖 |
|---|---|---|---|---|---|---|
| C1 | 代码生成与智能体 | 智能体编排 | 其他 | 141 | B07 | Hacker News、GitHub、V2EX、Stack Overflow |
| C2 | 聊天机器人与问答 | 对话问答 | 其他 | 84 | B04 | Stack Overflow |
| C3 | 知识检索 | 知识检索 | 其他 | 79 | B04 | Stack Overflow、Hacker News、GitHub |
| C4 | 教育大模型与智能体 | 对话问答 | 教育 | 72 | B06 | Stack Overflow |
| C5 | 医疗识别与文档处理 | 智能体编排 | 医疗 | 68 | B02 | GitHub、Hacker News、CSDN、Stack Overflow、V2EX、36氪、腾讯新闻、阿里云开发者社区 |
| C6 | 教育知识图谱与大模型 | 智能体编排 | 教育 | 55 | B07 | Hacker News、Stack Overflow、GitHub |
| C7 | 客户与智能助手 | 智能体编排 | 其他 | 48 | B06 | Stack Overflow、Hacker News、GitHub |
| C8 | 法律视频相关 | 智能体编排 | 法律 | 47 | B07 | Hacker News |
| C9 | 汽车推荐相关 | 语音处理 | 汽车 | 42 | B06 | Stack Overflow |
| C10 | 智能体相关 | 翻译转写 | 其他 | 37 | B06 | Stack Overflow |
| C11 | 查询与向量检索 | 知识检索 | 其他 | 32 | B03 | GitHub、Hacker News |
| C12 | 教育智能体与分析 | 智能体编排 | 教育 | 31 | B04 | Stack Overflow |
| C13 | 教育诊断相关 | 智能体编排 | 教育 | 28 | B07 | Hacker News、Stack Overflow |
| C14 | 法律智能推荐与医疗 | 图像识别 | 法律 | 26 | B02 | GitHub、CSDN、Hacker News、Stack Overflow |
| C15 | 能源智能体与生成 | 智能体编排 | 能源 | 22 | B07 | Hacker News、GitHub、Stack Overflow |
| C16 | 建筑代码生成相关 | 智能体编排 | 建筑 | 20 | B07 | Hacker News |
| C17 | 医疗语音识别与语音处理 | 推荐系统 | 医疗 | 18 | B02 | GitHub |
| C18 | 医疗生成式对话与视频 | 知识检索 | 医疗 | 17 | B05 | CSDN、GitHub |
| C19 | 代码生成相关 | 知识检索 | 其他 | 17 | B06 | Stack Overflow |
| C20 | 人力资源大模型对话相关 | 语音处理 | 人力资源 | 14 | B02 | GitHub、Stack Overflow |
| C21 | 教育智能体编排 | 智能体编排 | 教育 | 12 | B05 | CSDN、GitHub |
| C22 | 计算机视觉相关 | 智能体编排 | 其他 | 11 | B05 | CSDN、GitHub |
| C23 | 医疗智能体与客户 | 多模态融合 | 医疗 | 11 | B05 | CSDN |
| C24 | 医疗分析相关 | 知识检索 | 医疗 | 10 | B05 | CSDN |
| C25 | 法律向量检索与智能搜索 | 智能体编排 | 法律 | 9 | B05 | CSDN、GitHub |
| C26 | 汽车文本与图像 | 图像识别 | 汽车 | 9 | B07 | Hacker News |
| C27 | 能源行业智能体设计应用方案 | 智能体编排 | 能源 | 8 | B05 | CSDN |
| C28 | 大模型对话与问答 | 对话问答 | 其他 | 8 | B07 | Hacker News |
| C29 | 大模型与生成 | 智能体编排 | 其他 | 7 | B07 | Hacker News |
| C30 | 医疗与文本生成 | 智能体编排 | 其他 | 3 | B07 | Hacker News |

## 三、逐簇质量指标

| 簇 | 主题 | 记录数 | NPMI | 轮廓系数 | 簇内余弦相似度 | 行业标签一致率 |
|---|---|---|---|---|---|---|
| C1 | 代码生成与智能体 | 141 | 0.128 | -0.018 | 0.032 | 82.98% |
| C2 | 聊天机器人与问答 | 84 | 0.146 | 0.109 | 0.043 | 84.52% |
| C3 | 知识检索 | 79 | 0.240 | -0.020 | 0.053 | 78.48% |
| C4 | 教育大模型与智能体 | 72 | 0.092 | -0.027 | 0.038 | 0.00% |
| C5 | 医疗识别与文档处理 | 68 | 0.365 | 0.006 | 0.018 | 22.06% |
| C6 | 教育知识图谱与大模型 | 55 | 0.577 | -0.026 | 0.034 | 1.82% |
| C7 | 客户与智能助手 | 48 | 0.219 | 0.021 | 0.058 | 93.75% |
| C8 | 法律视频相关 | 47 | 0.958 | 0.268 | 0.228 | 4.26% |
| C9 | 汽车推荐相关 | 42 | 0.580 | 0.003 | 0.061 | 2.38% |
| C10 | 智能体相关 | 37 | 0.720 | 0.042 | 0.062 | 100.00% |
| C11 | 查询与向量检索 | 32 | 0.335 | 0.028 | 0.059 | 68.75% |
| C12 | 教育智能体与分析 | 31 | 0.594 | 0.080 | 0.077 | 0.00% |
| C13 | 教育诊断相关 | 28 | 0.593 | 0.047 | 0.107 | 0.00% |
| C14 | 法律智能推荐与医疗 | 26 | 0.412 | 0.155 | 0.069 | 11.54% |
| C15 | 能源智能体与生成 | 22 | 0.466 | 0.074 | 0.075 | 4.55% |
| C16 | 建筑代码生成相关 | 20 | 0.196 | 0.127 | 0.239 | 0.00% |
| C17 | 医疗语音识别与语音处理 | 18 | 0.387 | 0.185 | 0.146 | 27.78% |
| C18 | 医疗生成式对话与视频 | 17 | 0.322 | 0.007 | 0.117 | 29.41% |
| C19 | 代码生成相关 | 17 | 0.184 | 0.103 | 0.107 | 100.00% |
| C20 | 人力资源大模型对话相关 | 14 | 0.530 | 0.281 | 0.150 | 14.29% |
| C21 | 教育智能体编排 | 12 | 0.778 | 0.508 | 0.249 | 100.00% |
| C22 | 计算机视觉相关 | 11 | 0.692 | 0.493 | 0.182 | 63.64% |
| C23 | 医疗智能体与客户 | 11 | 0.407 | 0.657 | 0.286 | 100.00% |
| C24 | 医疗分析相关 | 10 | 0.527 | 0.421 | 0.204 | 40.00% |
| C25 | 法律向量检索与智能搜索 | 9 | 0.225 | 0.353 | 0.183 | 77.78% |
| C26 | 汽车文本与图像 | 9 | 0.330 | 0.438 | 0.251 | 0.00% |
| C27 | 能源行业智能体设计应用方案 | 8 | 0.143 | 0.753 | 0.431 | 25.00% |
| C28 | 大模型对话与问答 | 8 | 0.185 | 0.611 | 0.428 | 87.50% |
| C29 | 大模型与生成 | 7 | 0.455 | 0.622 | 0.389 | 14.29% |
| C30 | 医疗与文本生成 | 3 | 0.174 | 0.978 | 0.986 | 100.00% |

> NPMI 越高主题越连贯；簇内余弦相似度越高簇越紧凑；轮廓系数在短文本高维稀疏空间下结构性偏低，仅作参考；行业标签一致率用于检验与任务二既有标签体系的自洽性。

## 四、多源共同指向的热点主题

来源覆盖含 2 个及以上网站的簇，视为“多源共同指向”的热点：

| 簇 | 主题 | 记录数 | 来源数 | 来源覆盖 |
|---|---|---|---|---|
| C1 | 代码生成与智能体 | 141 | 4 | Hacker News、GitHub、V2EX、Stack Overflow |
| C3 | 知识检索 | 79 | 3 | Stack Overflow、Hacker News、GitHub |
| C5 | 医疗识别与文档处理 | 68 | 8 | GitHub、Hacker News、CSDN、Stack Overflow、V2EX、36氪、腾讯新闻、阿里云开发者社区 |
| C6 | 教育知识图谱与大模型 | 55 | 3 | Hacker News、Stack Overflow、GitHub |
| C7 | 客户与智能助手 | 48 | 3 | Stack Overflow、Hacker News、GitHub |
| C11 | 查询与向量检索 | 32 | 2 | GitHub、Hacker News |
| C13 | 教育诊断相关 | 28 | 2 | Hacker News、Stack Overflow |
| C14 | 法律智能推荐与医疗 | 26 | 4 | GitHub、CSDN、Hacker News、Stack Overflow |
| C15 | 能源智能体与生成 | 22 | 3 | Hacker News、GitHub、Stack Overflow |
| C18 | 医疗生成式对话与视频 | 17 | 2 | CSDN、GitHub |
| C20 | 人力资源大模型对话相关 | 14 | 2 | GitHub、Stack Overflow |
| C21 | 教育智能体编排 | 12 | 2 | CSDN、GitHub |
| C22 | 计算机视觉相关 | 11 | 2 | CSDN、GitHub |
| C25 | 法律向量检索与智能搜索 | 9 | 2 | CSDN、GitHub |

共 14/30 个主题簇被多源共同指向。

## 五、各簇代表记录

### C1 代码生成与智能体（141 条）
- 中文关键词：
- 英文关键词：code、agent、coding
- B01-S00005（GitHub）thedotmack/claude-mem
- B01-S00044（GitHub）tanweai/pua
- B01-S00369（GitHub）DEV7Kadu/WhaticketPlus

### C2 聊天机器人与问答（84 条）
- 中文关键词：
- 英文关键词：chatbot、answer、text
- B04-S00016（Stack Overflow）Meta Cloud API is triggering every webhook for multiple Apps
- B04-S00089（Stack Overflow）Spring AI's auto-configuration for multiple models of the sa
- B04-S00098（Stack Overflow）Llama3-8b-instruct returns value of "None" when using with_s

### C3 知识检索（79 条）
- 中文关键词：
- B03-S00768（GitHub）brittonlaroche/Confluent-Kafka-Vector-Encoding
- B04-S00011（Stack Overflow）How to add millions of documents to ChromaDB efficently
- B04-S00090（Stack Overflow）Can tiktoken be used instead of text-embedding-ada-002 for g

### C4 教育大模型与智能体（72 条）
- 中文关键词：
- 英文关键词：llm、agent、rag
- B04-S00060（Stack Overflow）Cannot import langchain.vectorstores.FAISS, only langchain_c
- B04-S00103（Stack Overflow）Difference b/w "from langchain_community.vectorstores import
- B04-S00304（Stack Overflow）How to make microphone suppress the audio that sounds from s

### C5 医疗识别与文档处理（68 条）
- 中文关键词：识别、图像识别
- 英文关键词：ocr、document、extraction、pdf
- B01-S00098（GitHub）interviewstreet/hiring-agent
- B01-S00108（GitHub）julep-ai/julep
- B01-S00206（GitHub）souvikmajumder26/Multi-Agent-Medical-Assistant

### C6 教育知识图谱与大模型（55 条）
- 中文关键词：知识图谱、构建、增强、语言、大模型、构建 知识图谱
- 英文关键词：rag
- B02-S00385（GitHub）Hungreeee/Resume-Screening-RAG-Pipeline
- B02-S00398（GitHub）mlx-chat/mlx-chat-app
- B02-S00448（GitHub）NVIDIA-AI-IOT/jetson-copilot

### C7 客户与智能助手（48 条）
- 中文关键词：
- 英文关键词：customer、assistant
- B01-S00990（GitHub）shauryaverma03/old-Software-Recommendation-System
- B01-S01165（GitHub）shauryaverma03/Software-Recommendation-System
- B04-S00005（Stack Overflow）Utilizing Gemini: Through Vertex AI or through Google/genera

### C8 法律视频相关（47 条）
- 中文关键词：
- 英文关键词：video
- B07-S00100（Hacker News）Ask HN: Who wants to be hired? (November 2026)
- B07-S00134（Hacker News）Ask HN: Who wants to be hired? (November 2026)
- B07-S00143（Hacker News）Ask HN: Who wants to be hired? (November 2026)

### C9 汽车推荐相关（42 条）
- 中文关键词：教育、学习、个性化、教学、个性化 学习、教师
- B04-S00018（Stack Overflow）OpenAI API: Can I access my custom ChatGPT ?
- B04-S00154（Stack Overflow）Faraday too many requests when using openai ruby gem?
- B04-S00159（Stack Overflow）How do I extract data from a document using the OpenAI API?

### C10 智能体相关（37 条）
- 中文关键词：
- 英文关键词：agent、agents
- B04-S00857（Stack Overflow）Large language model (TheBloke/Llama-2-7B-Chat-GPTQ)
- B06-S00005（Stack Overflow）Sentence embeddings from LLAMA 2 Huggingface opensource
- B06-S00025（Stack Overflow）How does `enforce_stop_tokens` work in LangChain with Huggin

### C11 查询与向量检索（32 条）
- 中文关键词：
- 英文关键词：query、vector
- B01-S00135（GitHub）iflytek/astron-rpa
- B01-S00464（GitHub）jgravelle/groqcrawl
- B01-S00943（GitHub）neeru24/Agri-Vision

### C12 教育智能体与分析（31 条）
- 中文关键词：智能体、方案、设计 方案、智能体 设计、设计、架构
- B04-S00092（Stack Overflow）Presidio with Langchain Experimental does not detect Polish 
- B04-S00117（Stack Overflow）How to correctly use solvePnP with fisheye cameras?
- B04-S00213（Stack Overflow）Google speech v1 never return isFinal in French

### C13 教育诊断相关（28 条）
- 中文关键词：医疗、诊断、治疗、个性化、未来、个性化 治疗
- B06-S00108（Stack Overflow）What is the max_tokens number I can put for OpenAI GPT gener
- B06-S00121（Stack Overflow）How to Match Claude.ai Response Quality Using the Anthropic 
- B06-S00374（Stack Overflow）How to upload files with the OpenAI API

### C14 法律智能推荐与医疗（26 条）
- 中文关键词：
- 英文关键词：recommendation、medical、job
- B01-S00659（GitHub）PSPDFKit/nutrient-dws-client-python
- B01-S01041（GitHub）chaomazo-OCR/OCRgenius
- B01-S01220（GitHub）deephabiswashi/Legal-Document-CaseLaw-Analyzer

### C15 能源智能体与生成（22 条）
- 中文关键词：自动化、工作、流程、自动化 工作、企业、平台
- B01-S01010（GitHub）The-Swarm-Corporation/radiology-swarm
- B02-S00018（GitHub）ashishpatel26/500-AI-Agents-Projects
- B02-S00037（GitHub）screenpipe/screenpipe

### C16 建筑代码生成相关（20 条）
- 中文关键词：
- 英文关键词：coding
- B07-S00118（Hacker News）Ask HN: Who wants to be hired? (November 2026)
- B07-S00207（Hacker News）Ask HN: Who wants to be hired? (November 2026)
- B07-S00209（Hacker News）Ask HN: Who wants to be hired? (November 2026)

### C17 医疗语音识别与语音处理（18 条）
- 中文关键词：实时、实时 语音识别、语音识别
- 英文关键词：speech、audio、voice、interview、asr、vision
- B01-S00540（GitHub）hoangsonww/Moodify-Emotion-Music-App
- B01-S00578（GitHub）Hrishikesh332/Twelve-Labs-Fashion-chat-assistant
- B01-S01123（GitHub）m-rishab/Diet-and-workout-Recommendation

### C18 医疗生成式对话与视频（17 条）
- 中文关键词：
- 英文关键词：gpt、video、driving
- B01-S00862（GitHub）SoupCola/Agent_Project
- B03-S00254（GitHub）ZeroTang05/cyber-doctor
- B03-S00291（GitHub）liangdabiao/langgraph_multi-agent-rag-customer-support

### C19 代码生成相关（17 条）
- 中文关键词：
- 英文关键词：code
- B04-S00105（Stack Overflow）Create a KnowledgeGraphIndex object from Neo4j database
- B04-S00927（Stack Overflow）Integrating llama index vectorstoreindex with Langchain agen
- B06-S00795（Stack Overflow）RAG with LlamaIndex SubDocument, how to persist embeddings

### C20 人力资源大模型对话相关（14 条）
- 中文关键词：
- 英文关键词：openai
- B01-S00839（GitHub）Jason-chen-coder/Flutter-EasySpeechRecognition
- B01-S01016（GitHub）amar-chheda/InterviewWarmupLocal
- B01-S01032（GitHub）fortunatoman/AI-Interview-Assistant

### C21 教育智能体编排（12 条）
- 中文关键词：
- B01-S00933（GitHub）VX18484646674/Springboot-Smart-Teaching-Recommendation-syste
- B05-S00011（CSDN）AI赋能教育：AI人工智能在教育中的 8 个应用示例（老师必须收藏）
- B05-S00049（CSDN）分享AI赋能教育：人工智能在教育中的八大应用

### C22 计算机视觉相关（11 条）
- 中文关键词：
- 英文关键词：cv
- B01-S00077（GitHub）shaxiu/XianyuAutoAgent
- B05-S00123（CSDN）Claude 与 n8n 协作：打造高效 AI 自动化工作流
- B05-S00130（CSDN）Golang实现智能体AI治理框架：基于新加坡《智能体人工智能治理示范框架》的企业级实战

### C23 医疗智能体与客户（11 条）
- 中文关键词：
- 英文关键词：agents、customer、agent、automation、service
- B05-S00121（CSDN）人工智能时代-AI医疗
- B05-S00125（CSDN）区块链、人工智能AI与未来医疗
- B05-S00184（CSDN）人工智能与医疗健康：AI 助力医疗的新格局

### C24 医疗分析相关（10 条）
- 中文关键词：法律、规则、探讨、挑战、本文、本文 探讨
- B05-S00075（CSDN）知识图谱增强的RAG(KG-RAG)详细解析
- B05-S00104（CSDN）KG-RAG: 知识图谱增强的检索增强生成技术
- B05-S00112（CSDN）【RAG探索第4讲】KG+RAG丨基于知识图谱优化大型语言模型方法

### C25 法律向量检索与智能搜索（9 条）
- 中文关键词：
- 英文关键词：vector、search、database、embedding、text、query
- B01-S00389（GitHub）AI-WorkDeck/aiworkdeck
- B05-S00059（CSDN）人工智能与法律：法律行业的变革
- B05-S00250（CSDN）【AI应用】AI+法律行业应用方案

### C26 汽车文本与图像（9 条）
- 中文关键词：
- 英文关键词：text、image、sentiment
- B07-S00006（Hacker News）GPT‑6.2 Astra and Sol
- B07-S00028（Hacker News）GPT‑6.2 Astra and Sol
- B07-S00037（Hacker News）GPT‑6.2 Astra and Sol

### C27 能源行业智能体设计应用方案（8 条）
- 中文关键词：
- 英文关键词：image
- B05-S00180（CSDN）【人工智能+】AI税务智能体设计应用方案
- B05-S00206（CSDN）【人工智能+】AI物流智能体设计应用方案
- B05-S00227（CSDN）【人工智能+】AI石油智能体系统设计应用方案

### C28 大模型对话与问答（8 条）
- 中文关键词：
- 英文关键词：openai、question
- B07-S00273（Hacker News）Ask HN: If the models are so good, why doesn't OpenAI just s
- B07-S00275（Hacker News）Ask HN: If the models are so good, why doesn't OpenAI just s
- B07-S00277（Hacker News）Ask HN: If the models are so good, why doesn't OpenAI just s

### C29 大模型与生成（7 条）
- 中文关键词：大模型、医疗、生成、检索增强、检索、检索增强 生成
- 英文关键词：rag
- B07-S00103（Hacker News）United Airlines bans AI agents from booking flights on behal
- B07-S00106（Hacker News）United Airlines bans AI agents from booking flights on behal
- B07-S00108（Hacker News）United Airlines bans AI agents from booking flights on behal

### C30 医疗与文本生成（3 条）
- 中文关键词：
- 英文关键词：medical、generation、rag、detection、agent、healthcare
- B07-S00778（Hacker News）Ask HN: Who wants to be hired? (October 2026)
- B07-S00789（Hacker News）Ask HN: Who wants to be hired? (September 2026)
- B07-S00799（Hacker News）Ask HN: Who wants to be hired? (August 2026)
