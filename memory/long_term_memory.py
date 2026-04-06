# -*- coding: utf-8 -*-
"""
长期记忆服务 - 用户事实和偏好存储
管理用户的持久化记忆、偏好设置和重要事实
"""
from typing import Dict, List, Optional
from datetime import datetime
import json
import os


class LongTermMemory:
    """长期记忆存储"""
    
    def __init__(self, storage_dir: str = "./data/memory"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.user_memories: Dict[str, Dict] = {}
        self._load_index()
    
    def _get_user_file(self, user_id: str) -> str:
        """获取用户记忆文件路径"""
        return os.path.join(self.storage_dir, f"{user_id}_memory.json")
    
    def _load_index(self):
        """加载用户索引"""
        index_file = os.path.join(self.storage_dir, "index.json")
        if os.path.exists(index_file):
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    self.user_memories = json.load(f)
            except:
                self.user_memories = {}
    
    def _save_index(self):
        """保存用户索引"""
        index_file = os.path.join(self.storage_dir, "index.json")
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(self.user_memories, f, ensure_ascii=False, indent=2)
    
    def store_fact(
        self,
        user_id: str,
        fact: str,
        category: str = "general",
        importance: float = 0.5,
        source: str = "conversation"
    ):
        """存储事实
        
        Args:
            user_id: 用户ID
            fact: 事实内容
            category: 分类 (interest/work/preference/experience等)
            importance: 重要性 0.0-1.0
            source: 来源 (questionnaire/conversation/explicit等)
        """
        user_file = self._get_user_file(user_id)
        
        if os.path.exists(user_file):
            try:
                with open(user_file, 'r', encoding='utf-8') as f:
                    memory_data = json.load(f)
            except:
                memory_data = {"facts": [], "preferences": {}, "interactions": []}
        else:
            memory_data = {"facts": [], "preferences": {}, "interactions": []}
        
        memory_data["facts"].append({
            "content": fact,
            "category": category,
            "importance": importance,
            "source": source,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "access_count": 0
        })
        
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)
        
        self.user_memories[user_id] = {
            "last_updated": datetime.now().isoformat(),
            "fact_count": len(memory_data["facts"])
        }
        self._save_index()
    
    def store_preference(
        self,
        user_id: str,
        key: str,
        value: str,
        source: str = "explicit"
    ):
        """存储偏好
        
        Args:
            user_id: 用户ID
            key: 偏好键 (language/style/tone等)
            value: 偏好值
            source: 来源 (explicit/learned/derived)
        """
        user_file = self._get_user_file(user_id)
        
        if os.path.exists(user_file):
            try:
                with open(user_file, 'r', encoding='utf-8') as f:
                    memory_data = json.load(f)
            except:
                memory_data = {"facts": [], "preferences": {}, "interactions": []}
        else:
            memory_data = {"facts": [], "preferences": {}, "interactions": []}
        
        memory_data["preferences"][key] = {
            "value": value,
            "source": source,
            "updated_at": datetime.now().isoformat()
        }
        
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)
    
    def get_memories(
        self,
        user_id: str,
        category: str = None,
        min_importance: float = 0.0
    ) -> List[Dict]:
        """获取记忆
        
        Args:
            user_id: 用户ID
            category: 过滤分类（可选）
            min_importance: 最低重要性过滤
        
        Returns:
            List[Dict]: 记忆列表
        """
        user_file = self._get_user_file(user_id)
        
        if not os.path.exists(user_file):
            return []
        
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                memory_data = json.load(f)
        except:
            return []
        
        facts = memory_data.get("facts", [])
        if category:
            facts = [f for f in facts if f.get("category") == category]
        
        facts = [f for f in facts if f.get("importance", 0) >= min_importance]
        return sorted(facts, key=lambda x: (x.get("importance", 0), x.get("access_count", 0)), reverse=True)
    
    def get_preferences(self, user_id: str) -> Dict:
        """获取偏好
        
        Args:
            user_id: 用户ID
        
        Returns:
            Dict: 偏好字典
        """
        user_file = self._get_user_file(user_id)
        
        if not os.path.exists(user_file):
            return {}
        
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                memory_data = json.load(f)
        except:
            return {}
        
        return memory_data.get("preferences", {})
    
    def update_access_count(self, user_id: str, fact_content: str):
        """更新记忆访问次数
        
        Args:
            user_id: 用户ID
            fact_content: 事实内容
        """
        user_file = self._get_user_file(user_id)
        
        if not os.path.exists(user_file):
            return
        
        with open(user_file, 'r', encoding='utf-8') as f:
            memory_data = json.load(f)
        
        for fact in memory_data.get("facts", []):
            if fact.get("content") == fact_content:
                fact["access_count"] = fact.get("access_count", 0) + 1
                fact["last_accessed"] = datetime.now().isoformat()
                break
        
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)
    
    def delete_user_memory(self, user_id: str):
        """删除用户所有记忆
        
        Args:
            user_id: 用户ID
        """
        user_file = self._get_user_file(user_id)
        if os.path.exists(user_file):
            os.remove(user_file)
        
        if user_id in self.user_memories:
            del self.user_memories[user_id]
            self._save_index()
    
    def get_user_summary(self, user_id: str) -> Dict:
        """获取用户记忆摘要
        
        Args:
            user_id: 用户ID
        
        Returns:
            Dict: 摘要信息
        """
        memories = self.get_memories(user_id)
        preferences = self.get_preferences(user_id)
        
        categories = {}
        for m in memories:
            cat = m.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total_facts": len(memories),
            "categories": categories,
            "preferences_count": len(preferences),
            "high_importance_count": len([m for m in memories if m.get("importance", 0) >= 0.7])
        }
    
    def merge_memories(
        self,
        user_id: str,
        new_facts: List[Dict]
    ):
        """批量合并新记忆
        
        Args:
            user_id: 用户ID
            new_facts: 新事实列表
        """
        for fact_data in new_facts:
            self.store_fact(
                user_id=user_id,
                fact=fact_data.get("content", ""),
                category=fact_data.get("category", "general"),
                importance=fact_data.get("importance", 0.5),
                source=fact_data.get("source", "merged")
            )


# 测试
if __name__ == "__main__":
    ltm = LongTermMemory("./data/test_memory")
    
    user_id = "test_user"
    
    # 存储事实
    ltm.store_fact(user_id, "用户喜欢AI技术", category="interest", importance=0.8)
    ltm.store_fact(user_id, "用户工作于互联网行业", category="work", importance=0.9)
    ltm.store_fact(user_id, "用户喜欢科幻电影", category="entertainment", importance=0.6)
    ltm.store_fact(user_id, "用户住在上海", category="location", importance=0.7)
    
    # 存储偏好
    ltm.store_preference(user_id, "language", "中文", source="explicit")
    ltm.store_preference(user_id, "communication_style", "direct", source="learned")
    ltm.store_preference(user_id, "tone", "friendly", source="learned")
    
    # 获取记忆
    print("=== 所有记忆 ===")
    for m in ltm.get_memories(user_id):
        print(f"  [{m['category']}] {m['content']} (importance: {m['importance']})")
    
    print("\n=== 按分类获取 ===")
    for m in ltm.get_memories(user_id, category="interest"):
        print(f"  - {m['content']}")
    
    print(f"\n=== 偏好 ===")
    prefs = ltm.get_preferences(user_id)
    for k, v in prefs.items():
        print(f"  {k}: {v['value']} (source: {v['source']})")
    
    print("\n=== 用户摘要 ===")
    summary = ltm.get_user_summary(user_id)
    for k, v in summary.items():
        print(f"  {k}: {v}")
