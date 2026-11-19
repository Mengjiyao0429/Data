"""全局配置：路径、采集、去重与评估参数。"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# 采集
REQUEST_TIMEOUT = 25
USER_AGENT = "Mozilla/5.0 (compatible; AI-Opportunity-Miner/1.0; +research)"
GITHUB_PER_PAGE = 30
STACKOVERFLOW_PAGESIZE = 30
RSS_LIMIT = 40

# 去重
JACCARD_THRESHOLD = 0.85
SHINGLE_K = 3

# 任务二：机会判别
OPPORTUNITY_THRESHOLD = 0.55

# 任务四：价值评估权重（多源指向度 / 记录规模 / 互动热度）
WEIGHT_MULTI_SOURCE = 0.40
WEIGHT_SCALE = 0.30
WEIGHT_HEAT = 0.30

# 任务三：聚类 K 范围
CLUSTER_MIN_K = 2
CLUSTER_MAX_K = 8
MIN_CLUSTER_SIZE = 3
