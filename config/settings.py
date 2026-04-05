# -*- coding: utf-8 -*-
"""
Digital Human AI - 配置文件
"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# LLM 配置
LLM_CONFIG = {
    "provider": "openai",  # openai / anthropic / local
    "model": "gpt-4o-mini",
    "api_key": os.getenv("OPENAI_API_KEY", ""),
    "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    "temperature": 0.7,
    "max_tokens": 2000,
}

# 向量数据库配置
VECTOR_DB_CONFIG = {
    "provider": "faiss",  # faiss / milvus / pinecone
    "dimension": 768,
    "index_type": "Flat",
    "storage_path": PROJECT_ROOT / "data" / "vectors",
}

# 图数据库配置
GRAPH_DB_CONFIG = {
    "provider": "memory",  # memory / neo4j
    "storage_path": PROJECT_ROOT / "data" / "graph",
}

# 用户数据存储
USER_DATA_CONFIG = {
    "storage_path": PROJECT_ROOT / "data" / "users",
    "max_memory_items": 1000,
}

# 人格模型配置
PERSONALITY_CONFIG = {
    "embedding_model": "text-embedding-3-small",
    "vector_dimension": 1536,
    "big_five_dimensions": [
        "openness",        # 开放性
        "conscientiousness",  # 尽责性
        "extraversion",    # 外向性
        "agreeableness",   # 宜人性
        "neuroticism"      # 神经质
    ],
}

# 数字人输出配置
AVATAR_CONFIG = {
    "voice_enabled": False,
    "video_enabled": False,
    "default_language": "zh-CN",
}

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": PROJECT_ROOT / "logs" / "digital_human.log",
}

# 知识库配置
KNOWLEDGE_CONFIG = {
    "enable_knowledge_graph": True,
    "enable_vector_memory": True,
    "memory_window": 10,  # 对话窗口大小
}
