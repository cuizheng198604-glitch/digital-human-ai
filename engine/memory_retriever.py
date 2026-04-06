# -*- coding: utf-8 -*-
"""
Digital Human AI - 记忆检索模块 (RAG)
支持向量检索 + 知识图谱 + 长期记忆
集成 memory/ 模块
"""
import json
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

# 导入新的记忆模块
from memory.vector_store import VectorStore
from memory.knowledge_graph import KnowledgeGraph
from memory.conversation_memory import ConversationMemory
from memory.long_term_memory import LongTermMemory


@dataclass
class MemoryItem:
    """记忆条目"""
    id: str
    content: str
    memory_type: str  # conversation / fact / opinion / knowledge
    timestamp: str
    embedding: List[float] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)  # topic, importance, source
    user_id: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "metadata": self.metadata
        }


class MemoryRetriever:
    """记忆检索器 - RAG 核心"""
    
    def __init__(
        self,
        llm_engine=None,
        config: Optional[Dict] = None,
        storage_dir: str = "./data"
    ):
        self.llm_engine = llm_engine
        self.config = config or {}
        self.storage_dir = storage_dir
        
        # 向量存储 (ChromaDB)
        vector_dir = os.path.join(storage_dir, "vectors")
        self.vector_store = VectorStore(persist_dir=vector_dir)
        
        # 知识图谱 (NetworkX)
        self.knowledge_graph = KnowledgeGraph()
        kg_path = os.path.join(storage_dir, "knowledge_graph.json")
        self.knowledge_graph.load(kg_path)
        
        # 对话记忆 (短期)
        conv_dir = os.path.join(storage_dir, "conversations")
        self.conversation_memory = ConversationMemory(
            max_turns=self.config.get("max_conversation_turns", 20),
            storage_dir=conv_dir
        )
        
        # 长期记忆
        memory_dir = os.path.join(storage_dir, "memory")
        self.long_term_memory = LongTermMemory(storage_dir=memory_dir)
        
        # 对话历史 (内存缓存, 用于快速访问)
        self._conversation_cache: Dict[str, List[Dict]] = {}
        
        self._memory_id_counter = 0
    
    def _generate_id(self) -> str:
        """生成记忆ID"""
        self._memory_id_counter += 1
        return f"mem_{self._memory_id_counter}_{int(datetime.now().timestamp())}"
    
    def _get_embedding(self, texts: List[str]) -> List[List[float]]:
        """获取文本嵌入向量"""
        if self.llm_engine:
            try:
                return self.llm_engine.embed(texts)
            except:
                pass
        # 如果没有 LLM engine，返回零向量
        dimension = self.config.get("embedding_dimension", 128)
        return [[0.0] * dimension for _ in texts]
    
    def add_conversation(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: str = None,
        metadata: Dict = None
    ):
        """添加对话到记忆
        
        Args:
            session_id: 会话ID
            role: 角色 (user/assistant)
            content: 对话内容
            user_id: 用户ID
            metadata: 额外元数据
        """
        # 1. 添加到短期对话记忆
        self.conversation_memory.add_turn(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata
        )
        
        # 2. 生成嵌入向量
        embeddings = self._get_embedding([content])
        embedding = embeddings[0] if embeddings else []
        
        # 3. 添加到向量存储
        memory_id = self._generate_id()
        self.vector_store.add_memory(
            user_id=user_id or "default",
            content=content,
            embedding=embedding,
            metadata={
                "memory_type": "conversation",
                "role": role,
                "session_id": session_id,
                **(metadata or {})
            }
        )
        
        # 4. 更新长期记忆
        if role == "user" and content.strip():
            self.long_term_memory.store_fact(
                user_id=user_id or "default",
                fact=content,
                category="conversation",
                importance=0.5,
                source="conversation"
            )
    
    def add_fact(
        self,
        user_id: str,
        fact: str,
        fact_type: str = "general",
        importance: float = 0.7,
        metadata: Dict = None
    ):
        """添加事实记忆
        
        Args:
            user_id: 用户ID
            fact: 事实内容
            fact_type: 事实类型
            importance: 重要性 0.0-1.0
            metadata: 额外元数据
        """
        # 1. 生成嵌入向量
        embeddings = self._get_embedding([fact])
        embedding = embeddings[0] if embeddings else []
        
        # 2. 添加到向量存储
        memory_id = self._generate_id()
        self.vector_store.add_memory(
            user_id=user_id,
            content=fact,
            embedding=embedding,
            metadata={
                "memory_type": f"fact_{fact_type}",
                "fact_type": fact_type,
                **(metadata or {})
            }
        )
        
        # 3. 更新长期记忆
        self.long_term_memory.store_fact(
            user_id=user_id,
            fact=fact,
            category=fact_type,
            importance=importance,
            source=metadata.get("source", "explicit") if metadata else "explicit"
        )
        
        # 4. 更新知识图谱
        self._update_knowledge_graph(user_id, fact, fact_type)
    
    def _update_knowledge_graph(
        self,
        user_id: str,
        content: str,
        entity_type: str = "general"
    ):
        """更新知识图谱
        
        Args:
            user_id: 用户ID
            content: 内容
            entity_type: 实体类型
        """
        # 简化实现: 基于关键词的实体提取
        keywords = {
            "interest": ["喜欢", "爱好", "感兴趣", "热衷"],
            "work": ["工作", "职业", "公司", "职位"],
            "education": ["学习", "学校", "学历", "专业"],
            "location": ["住在", "位于", "城市", "地点"]
        }
        
        detected_type = entity_type
        for k, v in keywords.items():
            for keyword in v:
                if keyword in content:
                    detected_type = k
                    break
        
        # 添加实体
        import hashlib
        entity_id = hashlib.md5(content.encode()).hexdigest()[:8]
        self.knowledge_graph.add_entity(
            user_id=user_id,
            entity=entity_id,
            entity_type=detected_type,
            properties={"content": content}
        )
        
        # 添加与用户的关联
        self.knowledge_graph.add_relation(
            user_id=user_id,
            entity1=user_id,
            relation="has_fact",
            entity2=entity_id
        )
    
    def retrieve(
        self,
        query: str,
        user_id: str = None,
        session_id: str = None,
        top_k: int = 5
    ) -> Dict[str, List[str]]:
        """检索相关记忆
        
        Args:
            query: 查询文本
            user_id: 用户ID (用于过滤)
            session_id: 会话ID
            top_k: 返回数量
        
        Returns:
            Dict: 分类的记忆结果
        """
        results = {
            "vector_memories": [],
            "long_term_memories": [],
            "recent_conversation": [],
            "knowledge_graph": []
        }
        
        # 1. 向量检索
        query_embedding = self._get_embedding([query])[0]
        if user_id:
            vector_results = self.vector_store.search(
                query_embedding=query_embedding,
                user_id=user_id,
                top_k=top_k
            )
            results["vector_memories"] = [r["content"] for r in vector_results]
        
        # 2. 长期记忆检索
        if user_id:
            ltm_memories = self.long_term_memory.get_memories(
                user_id=user_id,
                min_importance=0.3
            )
            results["long_term_memories"] = [m["content"] for m in ltm_memories[:top_k]]
        
        # 3. 近期对话
        if session_id:
            recent = self.conversation_memory.get_recent(session_id, turns=top_k * 2)
            results["recent_conversation"] = [
                f"{'用户' if t['role'] == 'user' else 'AI'}: {t['content']}"
                for t in recent
            ]
        
        # 4. 知识图谱关联
        if user_id:
            # 获取用户相关的实体
            entities = self.knowledge_graph.get_user_entities(user_id)
            results["knowledge_graph"] = [e["name"] for e in entities[:10]]
        
        return results
    
    def get_conversation_context(
        self,
        session_id: str,
        window_size: int = 5
    ) -> str:
        """获取对话上下文
        
        Args:
            session_id: 会话ID
            window_size: 窗口大小
        
        Returns:
            str: 格式化的对话上下文
        """
        return self.conversation_memory.get_context_window(
            session_id=session_id,
            window_size=window_size
        )
    
    def get_user_memories_summary(self, user_id: str) -> Dict:
        """获取用户记忆摘要
        
        Args:
            user_id: 用户ID
        
        Returns:
            Dict: 记忆摘要
        """
        summary = {
            "total_memories": self.vector_store.collection.count(),
            "long_term_memory": self.long_term_memory.get_user_summary(user_id),
            "knowledge_graph_entities": len(self.knowledge_graph.get_user_entities(user_id))
        }
        return summary
    
    def build_rag_context(self, query: str, user_id: str = None, session_id: str = None) -> str:
        """构建 RAG 上下文
        
        Args:
            query: 查询文本
            user_id: 用户ID
            session_id: 会话ID
        
        Returns:
            str: RAG 上下文字符串
        """
        retrieved = self.retrieve(
            query=query,
            user_id=user_id,
            session_id=session_id,
            top_k=5
        )
        
        context_parts = []
        
        # 添加长期记忆
        if retrieved["long_term_memories"]:
            context_parts.append("【用户记忆】")
            for m in retrieved["long_term_memories"][:3]:
                context_parts.append(f"- {m}")
        
        # 添加向量记忆
        if retrieved["vector_memories"]:
            context_parts.append("\n【相关记忆】")
            for m in retrieved["vector_memories"][:3]:
                context_parts.append(f"- {m}")
        
        # 添加近期对话
        if retrieved["recent_conversation"]:
            context_parts.append("\n【近期对话】")
            for conv in retrieved["recent_conversation"][-3:]:
                context_parts.append(conv)
        
        return "\n".join(context_parts) if context_parts else ""
    
    def save_all(self):
        """保存所有记忆到磁盘"""
        # 保存知识图谱
        kg_path = os.path.join(self.storage_dir, "knowledge_graph.json")
        self.knowledge_graph.save(kg_path)
    
    def clear_user_memory(self, user_id: str):
        """清除用户所有记忆
        
        Args:
            user_id: 用户ID
        """
        # 清除向量存储
        self.vector_store.delete_user_memories(user_id)
        
        # 清除长期记忆
        self.long_term_memory.delete_user_memory(user_id)
        
        # 清除知识图谱
        self.knowledge_graph.clear_user_data(user_id)
        
        self.save_all()


# 测试
if __name__ == "__main__":
    # 测试初始化
    retriever = MemoryRetriever(
        config={"embedding_dimension": 128},
        storage_dir="./data/test"
    )
    
    print("=== MemoryRetriever 初始化成功 ===")
    
    # 测试添加对话
    retriever.add_conversation(
        session_id="test_session",
        role="user",
        content="我叫张三，对AI技术很感兴趣",
        user_id="user_001"
    )
    retriever.add_conversation(
        session_id="test_session",
        role="assistant",
        content="很高兴认识你，张三！AI是个很棒的领域。",
        user_id="user_001"
    )
    
    print("\n=== 添加对话成功 ===")
    
    # 测试检索
    results = retriever.retrieve(
        query="用户叫什么名字",
        user_id="user_001",
        session_id="test_session"
    )
    
    print("\n=== 检索结果 ===")
    for key, value in results.items():
        print(f"{key}: {value}")
    
    # 测试 RAG 上下文构建
    rag_context = retriever.build_rag_context(
        query="介绍一下自己",
        user_id="user_001",
        session_id="test_session"
    )
    
    print("\n=== RAG 上下文 ===")
    print(rag_context)
