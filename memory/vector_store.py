# -*- coding: utf-8 -*-
"""
向量存储 - 基于 ChromaDB
用于存储和检索用户记忆的嵌入向量
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import numpy as np


class VectorStore:
    """向量数据库封装"""
    
    def __init__(self, persist_dir: str = "./data/vectors"):
        self.persist_dir = persist_dir
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="persona_memories",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_memory(
        self,
        user_id: str,
        content: str,
        embedding: List[float],
        metadata: Dict = None
    ) -> str:
        """添加记忆
        
        Args:
            user_id: 用户ID
            content: 记忆内容文本
            embedding: 128维嵌入向量
            metadata: 额外元数据
        
        Returns:
            str: 记忆ID
        """
        import uuid
        memory_id = str(uuid.uuid4())
        
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "user_id": user_id,
                **(metadata or {})
            }]
        )
        return memory_id
    
    def search(
        self,
        query_embedding: List[float],
        user_id: str,
        top_k: int = 5,
        filter_metadata: Dict = None
    ) -> List[Dict]:
        """检索相关记忆
        
        Args:
            query_embedding: 查询向量
            user_id: 用户ID
            top_k: 返回数量
            filter_metadata: 额外过滤条件
        
        Returns:
            List[Dict]: 相关记忆列表
        """
        where_filter = {"user_id": user_id}
        if filter_metadata:
            where_filter.update(filter_metadata)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter
        )
        
        memories = []
        if results["ids"] and len(results["ids"]) > 0:
            for i in range(len(results["ids"][0])):
                memories.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i] if results["documents"] else "",
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                })
        return memories
    
    def delete_user_memories(self, user_id: str):
        """删除用户所有记忆
        
        Args:
            user_id: 用户ID
        """
        self.collection.delete(where={"user_id": user_id})
    
    def get_collection_count(self) -> int:
        """获取记忆总数"""
        return self.collection.count()
    
    def get_user_memories(self, user_id: str, limit: int = 100) -> List[Dict]:
        """获取用户所有记忆
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
        
        Returns:
            List[Dict]: 用户记忆列表
        """
        results = self.collection.get(
            where={"user_id": user_id},
            limit=limit
        )
        
        memories = []
        if results["ids"]:
            for i in range(len(results["ids"])):
                memories.append({
                    "id": results["ids"][i],
                    "content": results["documents"][i] if results["documents"] else "",
                    "metadata": results["metadatas"][i] if results["metadatas"] else {}
                })
        return memories


# 测试
if __name__ == "__main__":
    store = VectorStore("./data/test_vectors")
    
    # 测试添加
    test_embedding = [0.1] * 128
    memory_id = store.add_memory(
        user_id="test_user",
        content="用户喜欢科技和AI领域",
        embedding=test_embedding,
        metadata={"source": "questionnaire"}
    )
    print(f"Added memory: {memory_id}")
    
    # 测试检索
    results = store.search(
        query_embedding=test_embedding,
        user_id="test_user",
        top_k=5
    )
    print(f"Search results: {len(results)} memories")
    for r in results:
        print(f"  - {r['content']} (distance: {r['distance']:.4f})")
    
    print(f"\nTotal memories: {store.get_collection_count()}")
