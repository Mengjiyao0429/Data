# 任务三 主题簇报告

- 输入机会记录：388 条（跨全部批次）
- 聚类方法：字符/词 n-gram TF-IDF + 余弦 KMeans（k-means++）
- 选定簇数 k = 14（轮廓系数 0.0199）
- 主题簇数：14，覆盖机会记录合计：388

| 簇 | 名称 | 记录数 | 功能类别 | 所属行业 | 主导批次 | 来源覆盖 |
|---|---|---|---|---|---|---|
| T01 | 推荐系统｜vector、chatbot | 62 | 推荐系统 | 其他 | B04 | Stack Overflow(60)、GitHub(2) |
| T02 | 对话问答｜openai、api | 57 | 对话问答 | 其他 | B04 | Stack Overflow(55)、GitHub(2) |
| T03 | 智能体编排｜智能、人工 | 55 | 智能体编排 | 其他 | B05 | CSDN(49)、GitHub(3)、36氪(1)、腾讯新闻(1) 等5源 |
| T04 | 推荐系统｜agent、chatbot | 30 | 推荐系统 | 其他 | B02 | GitHub(24)、Stack Overflow(6) |
| T05 | 图像识别｜ocr、agents | 25 | 图像识别 | 其他 | B02 | GitHub(20)、Stack Overflow(5) |
| T06 | 推荐系统｜recommendation、medical | 25 | 推荐系统 | 电商 | B02 | GitHub(24)、Stack Overflow(1) |
| T07 | 语音处理｜speech、voice | 22 | 语音处理 | 人力资源 | B02 | GitHub(18)、Stack Overflow(4) |
| T08 | 知识检索｜知识、图谱 | 22 | 知识检索 | 医疗 | B05 | CSDN(19)、GitHub(3) |
| T09 | 推荐系统｜detection、llm | 21 | 推荐系统 | 其他 | B04 | Stack Overflow(15)、GitHub(6) |
| T10 | 语音处理｜speech、sentiment | 17 | 语音处理 | 其他 | B04 | Stack Overflow(16)、GitHub(1) |
| T11 | 图像识别｜llm、ocr | 14 | 图像识别 | 其他 | B03 | GitHub(10)、Stack Overflow(4) |
| T12 | 知识检索｜rag、ocr | 13 | 知识检索 | 医疗 | B03 | GitHub(12)、Stack Overflow(1) |
| T13 | 知识检索｜knowledge、graph | 13 | 知识检索 | 医疗 | B03 | GitHub(10)、Stack Overflow(3) |
| T14 | 推荐系统｜chatbot、finance | 12 | 推荐系统 | 其他 | B02 | GitHub(11)、Stack Overflow(1) |

## 各簇代表记录

### T01 推荐系统｜vector、chatbot（62 条）
- 关键词：vector、chatbot
- B03-S00182（GitHub）nyrahealth/CrisperWhisper
- B03-S00768（GitHub）brittonlaroche/Confluent-Kafka-Vector-Encoding
- B04-S00011（Stack Overflow）How to add millions of documents to ChromaDB effic

### T02 对话问答｜openai、api（57 条）
- 关键词：openai、api
- B01-S00005（GitHub）thedotmack/claude-mem
- B02-S00371（GitHub）maxigo-web/maxigo-client
- B04-S00016（Stack Overflow）Meta Cloud API is triggering every webhook for mul

### T03 智能体编排｜智能、人工（55 条）
- 关键词：智能、人工
- B01-S00077（GitHub）shaxiu/XianyuAutoAgent
- B02-S01020（GitHub）aicoting/Segmentation-Hub
- B03-S00280（GitHub）IceBearAI/LLM-And-More

### T04 推荐系统｜agent、chatbot（30 条）
- 关键词：agent、chatbot
- B01-S00098（GitHub）interviewstreet/hiring-agent
- B01-S00990（GitHub）shauryaverma03/old-Software-Recommendation-System
- B01-S00991（GitHub）HarrickChristoJP/Plant-Disease-Detection-Managemen

### T05 图像识别｜ocr、agents（25 条）
- 关键词：ocr、agents
- B01-S00108（GitHub）julep-ai/julep
- B01-S00659（GitHub）PSPDFKit/nutrient-dws-client-python
- B01-S01041（GitHub）chaomazo-OCR/OCRgenius

### T06 推荐系统｜recommendation、medical（25 条）
- 关键词：recommendation、medical
- B01-S00206（GitHub）souvikmajumder26/Multi-Agent-Medical-Assistant
- B01-S00540（GitHub）hoangsonww/Moodify-Emotion-Music-App
- B01-S00578（GitHub）Hrishikesh332/Twelve-Labs-Fashion-chat-assistant

### T07 语音处理｜speech、voice（22 条）
- 关键词：speech、voice
- B01-S00839（GitHub）Jason-chen-coder/Flutter-EasySpeechRecognition
- B01-S01016（GitHub）amar-chheda/InterviewWarmupLocal
- B01-S01032（GitHub）fortunatoman/AI-Interview-Assistant

### T08 知识检索｜知识、图谱（22 条）
- 关键词：知识、图谱
- B01-S00862（GitHub）SoupCola/Agent_Project
- B03-S00291（GitHub）liangdabiao/langgraph_multi-agent-rag-customer-sup
- B03-S00669（GitHub）feiyu1104/DUTMed

### T09 推荐系统｜detection、llm（21 条）
- 关键词：detection、llm
- B01-S00477（GitHub）roboflow/model-leaderboard
- B01-S00629（GitHub）tonlongthuat/Real-Time-Fall-Detection
- B01-S01123（GitHub）m-rishab/Diet-and-workout-Recommendation

### T10 语音处理｜speech、sentiment（17 条）
- 关键词：speech、sentiment
- B01-S00044（GitHub）tanweai/pua
- B04-S00213（Stack Overflow）Google speech v1 never return isFinal in French
- B04-S00218（Stack Overflow）How to calculate FPS in image classification?

### T11 图像识别｜llm、ocr（14 条）
- 关键词：llm、ocr
- B01-S00135（GitHub）iflytek/astron-rpa
- B01-S00464（GitHub）jgravelle/groqcrawl
- B01-S00943（GitHub）neeru24/Agri-Vision

### T12 知识检索｜rag、ocr（13 条）
- 关键词：rag、ocr
- B01-S00369（GitHub）DEV7Kadu/WhaticketPlus
- B01-S00968（GitHub）SrikarVeluvali/Astor-AI
- B01-S01220（GitHub）deephabiswashi/Legal-Document-CaseLaw-Analyzer

### T13 知识检索｜knowledge、graph（13 条）
- 关键词：knowledge、graph
- B01-S00536（GitHub）phoenix-zhou/logistics-industry-RAG
- B01-S01010（GitHub）The-Swarm-Corporation/radiology-swarm
- B01-S01024（GitHub）Rhythmica02/Cognitive_Health_Monitoring_System_for

### T14 推荐系统｜chatbot、finance（12 条）
- 关键词：chatbot、finance
- B01-S00336（GitHub）kangjul3854/hyufa
- B01-S01229（GitHub）AjayRastogi007/Legitify
- B01-S01231（GitHub）Logulokesh/KinAI-CareVault
