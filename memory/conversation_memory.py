# -*- coding: utf-8 -*-
"""
对话记忆管理 - 短期记忆
管理用户会话期间的短期对话上下文
"""
from typing import List, Dict, Optional
from datetime import datetime
from collections import deque
import json
import os


class ConversationMemory:
    """短期对话记忆"""
    
    def __init__(self, max_turns: int = 20, storage_dir: str = "./data/conversations"):
        self.max_turns = max_turns
        self.storage_dir = storage_dir
        self.sessions: Dict[str, deque] = {}
        os.makedirs(storage_dir, exist_ok=True)
    
    def add_turn(
        self,
        session_id: str,
        role: str,  # "user" / "assistant"
        content: str,
        metadata: Dict = None
    ):
        """添加对话轮次
        
        Args:
            session_id: 会话ID
            role: 角色 (user/assistant)
            content: 对话内容
            metadata: 额外元数据
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = deque(maxlen=self.max_turns)
        
        self.sessions[session_id].append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        })
        
        # 持久化
        self._persist_session(session_id)
    
    def get_recent(
        self,
        session_id: str,
        turns: int = 10
    ) -> List[Dict]:
        """获取最近对话
        
        Args:
            session_id: 会话ID
            turns: 获取轮数
        
        Returns:
            List[Dict]: 最近对话列表
        """
        if session_id not in self.sessions:
            self._load_session(session_id)
        
        if session_id not in self.sessions:
            return []
        
        memory = list(self.sessions[session_id])
        return memory[-turns:] if len(memory) > turns else memory
    
    def get_context_window(
        self,
        session_id: str,
        window_size: int = 5
    ) -> str:
        """获取上下文窗口文本
        
        Args:
            session_id: 会话ID
            window_size: 窗口大小
        
        Returns:
            str: 格式化的对话上下文
        """
        recent = self.get_recent(session_id, window_size * 2)
        
        context = []
        for turn in recent:
            role_label = "用户" if turn["role"] == "user" else "AI"
            context.append(f"{role_label}: {turn['content']}")
        
        return "\n".join(context)
    
    def get_conversation_history(
        self,
        session_id: str,
        include_metadata: bool = False
    ) -> List[Dict]:
        """获取完整对话历史
        
        Args:
            session_id: 会话ID
            include_metadata: 是否包含元数据
        
        Returns:
            List[Dict]: 对话历史
        """
        if session_id not in self.sessions:
            self._load_session(session_id)
        
        if session_id not in self.sessions:
            return []
        
        history = []
        for turn in self.sessions[session_id]:
            if include_metadata:
                history.append(turn)
            else:
                history.append({
                    "role": turn["role"],
                    "content": turn["content"]
                })
        return history
    
    def get_user_sessions(self, user_id: str) -> List[str]:
        """获取用户的所有会话ID
        
        Args:
            user_id: 用户ID
        
        Returns:
            List[str]: 会话ID列表
        """
        sessions = []
        prefix = f"{user_id}_"
        
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json") and filename.startswith(prefix):
                session_id = filename[:-5]  # 去除 .json
                sessions.append(session_id)
        
        return sessions
    
    def clear_session(self, session_id: str):
        """清除会话记忆
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        session_file = os.path.join(self.storage_dir, f"{session_id}.json")
        if os.path.exists(session_file):
            os.remove(session_file)
    
    def _persist_session(self, session_id: str):
        """持久化会话到文件"""
        if session_id not in self.sessions:
            return
        
        session_file = os.path.join(self.storage_dir, f"{session_id}.json")
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump({
                "session_id": session_id,
                "turns": list(self.sessions[session_id])
            }, f, ensure_ascii=False, indent=2)
    
    def _load_session(self, session_id: str):
        """从文件加载会话"""
        session_file = os.path.join(self.storage_dir, f"{session_id}.json")
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    turns = deque(data.get("turns", []), maxlen=self.max_turns)
                    self.sessions[session_id] = turns
            except:
                pass
    
    def get_session_summary(
        self,
        session_id: str
    ) -> Dict:
        """获取会话摘要
        
        Args:
            session_id: 会话ID
        
        Returns:
            Dict: 会话摘要信息
        """
        history = self.get_conversation_history(session_id)
        
        if not history:
            return {"turn_count": 0, "user_turns": 0, "assistant_turns": 0}
        
        user_turns = sum(1 for h in history if h["role"] == "user")
        assistant_turns = sum(1 for h in history if h["role"] == "assistant")
        
        first_turn = history[0] if history else {}
        last_turn = history[-1] if history else {}
        
        return {
            "turn_count": len(history),
            "user_turns": user_turns,
            "assistant_turns": assistant_turns,
            "first_timestamp": first_turn.get("timestamp", ""),
            "last_timestamp": last_turn.get("timestamp", ""),
            "started_with": first_turn.get("content", "")[:50] if first_turn else ""
        }


# 测试
if __name__ == "__main__":
    memory = ConversationMemory("./data/test_conversations")
    
    session_id = "user1_session_001"
    
    # 添加对话
    memory.add_turn(session_id, "user", "我最近在学习AI技术")
    memory.add_turn(session_id, "assistant", "AI是一个很棒的领域！有什么具体方向想深入吗？")
    memory.add_turn(session_id, "user", "我对机器学习和自然语言处理比较感兴趣")
    memory.add_turn(session_id, "assistant", "那很好！NLP是非常有趣的方向。")
    
    # 获取上下文
    print("=== 对话上下文 ===")
    context = memory.get_context_window(session_id, window_size=2)
    print(context)
    
    print("\n=== 会话摘要 ===")
    summary = memory.get_session_summary(session_id)
    for k, v in summary.items():
        print(f"  {k}: {v}")
