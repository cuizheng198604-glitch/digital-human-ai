# -*- coding: utf-8 -*-
"""
Digital Human AI - 记忆检索模块 (RAG)
支持向量检索 + 知识图谱
"""
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import numpy as np


@dataclass
class MemoryItem:
    """记忆条目"""
    id: str
    content: str
    memory_type: str  # conversation / fact / opinion / knowledge
    timestamp: str
    embedding: List[float] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)  # topic, importance, source
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


class SimpleVectorStore:
    """简单向量存储 (基于 FAISS 的简化实现)"""
    
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self.vectors = []  # List[List[float]]
        self.items = []  # List[MemoryItem]
    
    def add(self, item: MemoryItem, embedding: List[float]):
        """添加记忆"""
        self.vectors.append(embedding)
        self.items.append(item)
    
    def search(self, query_embedding: List[float], top_k: int = 5) -> List[MemoryItem]:
        """向量检索"""
        if not self.vectors:
            return []
        
        # 计算余弦相似度
        scores = []
        for vec in self.vectors:
            score = self._cosine_sim(query_embedding, vec)
            scores.append(score)
        
        # 取 top_k
        sorted_indices = np.argsort(scores)[::-1][:top_k]
        
        return [self.items[i] for i in sorted_indices]
    
    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        """余弦相似度"""
        if len(a) != len(b):
            return 0.0
        
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot / (norm_a * norm_b)
    
    def save(self, path: str):
        """保存到文件"""
        data = {
            "vectors": self.vectors,
            "items": [item.to_dict() for item in self.items]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    
    def load(self, path: str):
        """从文件加载"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.vectors = data["vectors"]
        self.items = [MemoryItem(**item) for item in data["items"]]


class KnowledgeGraph:
    """简化知识图谱"""
    
    def __init__(self):
        # 节点: {node_id: {"type": str, "content": str, "properties": Dict}}
        self.nodes = {}
        # 边: {from_id: [(to_id, relation_type)]}
        self.edges = {}
    
    def add_node(self, node_id: str, node_type: str, content: str, properties: Dict = None):
        """添加节点"""
        self.nodes[node_id] = {
            "type": node_type,
            "content": content,
            "properties": properties or {}
        }
        if node_id not in self.edges:
            self.edges[node_id] = []
    
    def add_edge(self, from_id: str, to_id: str, relation: str):
        """添加边"""
        if from_id not in self.edges:
            self.edges[from_id] = []
        self.edges[from_id].append((to_id, relation))
        
        # 双向边
        if to_id not in self.edges:
            self.edges[to_id] = []
        self.edges[to_id].append((from_id, f"rev_{relation}"))
    
    def get_related(self, node_id: str, max_hops: int = 2) -> List[Dict]:
        """获取关联节点"""
        if node_id not in self.nodes:
            return []
        
        visited = {node_id}
        result = [self.nodes[node_id]]
        
        current_level = [node_id]
        
        for _ in range(max_hops):
            next_level = []
            for nid in current_level:
                if nid not in self.edges:
                    continue
                for to_id, relation in self.edges[nid]:
                    if to_id not in visited:
                        visited.add(to_id)
                        next_level.append(to_id)
                        if to_id in self.nodes:
                            result.append({
                                **self.nodes[to_id],
                                "relation": relation,
                                "from_node": nid
                            })
            current_level = next_level
        
        return result
    
    def save(self, path: str):
        """保存"""
        data = {"nodes": self.nodes, "edges": self.edges}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    
    def load(self, path: str):
        """加载"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.nodes = data["nodes"]
        self.edges = data["edges"]


class MemoryRetriever:
    """记忆检索器 - RAG 核心"""
    
    def __init__(self, llm_engine=None, config: Optional[Dict] = None):
        self.llm_engine = llm_engine
        self.config = config or {}
        
        self.vector_store = SimpleVectorStore(
            dimension=self.config.get("dimension", 1536)
        )
        self.knowledge_graph = KnowledgeGraph()
        
        # 对话历史 (短期记忆)
        self.conversation_history = deque(maxlen=100)
        
        # 用户事实 (长期记忆)
        self.user_facts = {}  # {user_id: [MemoryItem]}
        
        self._memory_id_counter = 0
    
    def _generate_id(self) -> str:
        """生成记忆ID"""
        self._memory_id_counter += 1
        return f"mem_{self._memory_id_counter}_{int(datetime.now().timestamp())}"
    
    def add_conversation(self, role: str, content: str, metadata: Dict = None):
        """添加对话到记忆"""
        item = MemoryItem(
            id=self._generate_id(),
            content=content,
            memory_type="conversation",
            timestamp=datetime.now().isoformat(),
            metadata={
                "role": role,
                **(metadata or {})
            }
        )
        
        self.conversation_history.append(item)
        
        # 向量化存储
        if self.llm_engine:
            embeddings = self.llm_engine.embed([content])
            if embeddings:
                item.embedding = embeddings[0]
                self.vector_store.add(item, embeddings[0])
    
    def add_fact(self, user_id: str, fact: str, fact_type: str = "general", metadata: Dict = None):
        """添加事实记忆"""
        item = MemoryItem(
            id=self._generate_id(),
            content=fact,
            memory_type=f"fact_{fact_type}",
            timestamp=datetime.now().isoformat(),
            metadata={
                "user_id": user_id,
                **(metadata or {})
            }
        )
        
        if user_id not in self.user_facts:
            self.user_facts[user_id] = []
        self.user_facts[user_id].append(item)
        
        # 更新知识图谱
        self._update_knowledge_graph(item)
        
        # 向量化
        if self.llm_engine:
            embeddings = self.llm_engine.embed([fact])
            if embeddings:
                item.embedding = embeddings[0]
                self.vector_store.add(item, embeddings[0])
    
    def _update_knowledge_graph(self, item: MemoryItem):
        """更新知识图谱"""
        # 简化实现: 提取实体和关系
        # 实际应使用 NER + 关系抽取
        content = item.content
        
        # 简单实体识别 (关键词)
        keywords = ["喜欢", "讨厌", "想要", "认为", "觉得", "工作", "学习", "生活"]
        for keyword in keywords:
            if keyword in content:
                node_id = f"concept_{keyword}_{item.id}"
                self.knowledge_graph.add_node(
                    node_id,
                    node_type="concept",
                    content=f"{keyword}: {content}",
                    properties={"memory_id": item.id}
                )
                self.knowledge_graph.add_edge(
                    item.metadata.get("user_id", "unknown"),
                    node_id,
                    relation=f"related_to_{keyword}"
                )
    
    def retrieve(self, query: str, user_id: str = None, top_k: int = 5) -> List[str]:
        """
        检索相关记忆
        
        Args:
            query: 查询文本
            user_id: 用户ID (用于过滤)
            top_k: 返回数量
        
        Returns:
            相关记忆文本列表
        """
        results = []
        
        # 1. 向量检索
        if self.llm_engine:
            query_embedding = self.llm_engine.embed([query])
            if query_embedding:
                vector_results = self.vector_store.search(query_embedding[0], top_k)
                for item in vector_results:
                    # 过滤用户
                    if user_id and item.metadata.get("user_id") != user_id:
                        continue
                    results.append(item.content)
        
        # 2. 近期对话 (如果向量检索结果少)
        if len(results) < top_k:
            recent = list(self.conversation_history)[-10:]
            for item in reversed(recent):
                if item.content not in results:
                    results.append(item.content)
                if len(results) >= top_k:
                    break
        
        # 3. 用户事实
        if user_id and user_id in self.user_facts:
            for item in self.user_facts[user_id][-5:]:
                if item.content not in results:
                    results.append(item.content)
                if len(results) >= top_k:
                    break
        
        return results[:top_k]
    
    def get_conversation_context(self, last_n: int = 5) -> str:
        """获取对话上下文"""
        history = list(self.conversation_history)[-last_n:]
        return "\n".join([
            f"{'用户' if item.metadata.get('role') == 'user' else 'AI'}: {item.content}"
            for item in history
        ])
    
    def build_rag_prompt(self, query: str, user_id: str = None) -> str:
        """构建 RAG 提示"""
        relevant_memories = self.retrieve(query, user_id, top_k=5)
        
        context = ""
        if relevant_memories:
            context = "相关记忆:\n" + "\n".join([f"- {m}" for m in relevant_memories]) + "\n\n"
        
        return context
    
    def save(self, path: str):
        """保存所有记忆"""
        data = {
            "vector_store": {
                "vectors": self.vector_store.vectors,
                "items": [item.to_dict() for item in self.vector_store.items]
            },
            "knowledge_graph": {
                "nodes": self.knowledge_graph.nodes,
                "edges": self.knowledge_graph.edges
            },
            "conversation_history": [item.to_dict() for item in self.conversation_history],
            "user_facts": {
                uid: [item.to_dict() for item in items]
                for uid, items in self.user_facts.items()
            }
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, path: str):
        """加载记忆"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 恢复向量存储
        if "vector_store" in data:
            self.vector_store.vectors = data["vector_store"]["vectors"]
            self.vector_store.items = [
                MemoryItem(**item) for item in data["vector_store"]["items"]
            ]
        
        # 恢复知识图谱
        if "knowledge_graph" in data:
            self.knowledge_graph.nodes = data["knowledge_graph"]["nodes"]
            self.knowledge_graph.edges = data["knowledge_graph"]["edges"]
        
        # 恢复对话历史
        if "conversation_history" in data:
            self.conversation_history = deque([
                MemoryItem(**item) for item in data["conversation_history"]
            ], maxlen=100)
        
        # 恢复用户事实
        if "user_facts" in data:
            self.user_facts = {
                uid: [MemoryItem(**item) for item in items]
                for uid, items in data["user_facts"].items()
            }


# 测试
if __name__ == "__main__":
    retriever = MemoryRetriever()
    
    # 添加测试记忆
    retriever.add_conversation("user", "我叫张三，今年30岁，在互联网公司工作")
    retriever.add_conversation("assistant", "你好张三，很高兴认识你！")
    retriever.add_fact("user_1", "用户喜欢编程和人工智能", "interest")
    
    # 检索
    results = retriever.retrieve("用户叫什么名字")
    print("检索结果:", results)
    
    print("\n对话上下文:")
    print(retriever.get_conversation_context())
