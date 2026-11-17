# -*- coding: utf-8 -*-
import csv, json

# (主题簇名称, 功能类别, 所属行业)
names = [
    ("大模型 API 与行业应用开发", "文本生成", "其他"),
    ("大模型 API 调用与文本生成", "文本生成", "其他"),
    ("知识图谱与智能体应用开发", "知识检索", "其他"),
    ("行业智能体与视觉检测方案", "智能体编排", "其他"),
    ("大模型 API 调试与工程实践", "文本生成", "其他"),
    ("LangChain 与模型推理工程", "知识检索", "其他"),
    ("文档 OCR 与法律文本分析", "图像识别", "法律"),
    ("AI 治理与法律行业应用", "审核审查", "法律"),
    ("健康与生活方式智能推荐", "推荐系统", "医疗"),
    ("知识图谱增强的检索问答", "知识检索", "其他"),
    ("语音识别与面试辅助", "语音处理", "人力资源"),
    ("医疗影像诊断与辅助医疗", "图像识别", "医疗"),
    ("AI 赋能智慧教育", "推荐系统", "教育"),
    ("能源行业智能体设计应用方案", "智能体编排", "能源"),
]

rows = list(csv.DictReader(open(r'D:\Data\Data\任务三\结果\result3.csv', encoding='utf-8-sig')))
mapping = {}
for r, (nm, fn, ind) in zip(rows, names):
    ids = sorted(x.strip() for x in r['簇内机会记录'].split('；') if x.strip())
    mapping[','.join(ids)] = {"name": nm, "func": fn, "industry": ind}
json.dump(mapping, open(r'D:\Data\Data\任务三\源码\curated_names.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)
print('written', len(mapping))
for k, v in mapping.items():
    print(v['name'], '|', v['func'], '|', v['industry'])
