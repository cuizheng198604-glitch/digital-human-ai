# -*- coding: utf-8 -*-
"""
Digital Human AI - 主程序入口
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from engine.llm_engine import LLMEngine, get_llm_engine
from engine.persona_filter import PersonaFilter, ResponseValidator
from engine.memory_retriever import MemoryRetriever
from modeling.personality_encoder import PersonalityEncoder, UserPersona, BigFiveTraits
from config.settings import LLM_CONFIG, PERSONALITY_CONFIG


class DigitalHumanAI:
    """数字人 AI 系统"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        
        # 初始化 LLM 引擎
        llm_config = self.config.get("llm", LLM_CONFIG)
        self.llm = LLMEngine(llm_config)
        
        # 初始化人格编码器
        self.personality_encoder = PersonalityEncoder(self.llm)
        
        # 记忆检索器
        self.memory = MemoryRetriever(self.llm)
        
        # 当前用户画像
        self.current_persona: UserPersona = None
        self.persona_filter: PersonaFilter = None
        
        # 对话历史
        self.conversation_history = []
    
    def create_persona(
        self,
        user_id: str,
        basic_info: dict = None,
        questionnaire_results: dict = None
    ) -> UserPersona:
        """创建用户画像"""
        self.current_persona = self.personality_encoder.build_persona(
            user_id=user_id,
            basic_info=basic_info,
            questionnaire_results=questionnaire_results or {}
        )
        
        # 创建人格过滤器
        self.persona_filter = PersonaFilter(self.current_persona)
        
        return self.current_persona
    
    def load_persona(self, persona: UserPersona):
        """加载已有画像"""
        self.current_persona = persona
        self.persona_filter = PersonaFilter(persona)
    
    def chat(self, user_input: str) -> str:
        """
        对话接口
        
        Args:
            user_input: 用户输入
        
        Returns:
            AI 回复
        """
        # 添加用户输入到记忆
        self.memory.add_conversation(
            role="user",
            content=user_input,
            metadata={"user_id": self.current_persona.user_id if self.current_persona else "unknown"}
        )
        
        # 构建系统提示
        system_prompt = self._build_system_prompt()
        
        # 构建 RAG 上下文
        rag_context = self.memory.build_rag_prompt(
            user_input,
            self.current_persona.user_id if self.current_persona else None
        )
        
        # 构建消息
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加对话历史 (最近 10 轮)
        recent_history = self.conversation_history[-10:] if self.conversation_history else []
        for msg in recent_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # 添加 RAG 上下文
        if rag_context:
            messages.append({
                "role": "system",
                "content": f"[参考信息]\n{rag_context}"
            })
        
        # 添加用户输入
        messages.append({"role": "user", "content": user_input})
        
        # 调用 LLM
        response = self.llm.chat(messages)
        
        # 人格过滤
        if self.persona_filter:
            response = self.persona_filter.filter_response(
                response,
                context={"topic": self._extract_topic(user_input)}
            )
        
        # 添加到对话历史
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        # 添加到记忆
        self.memory.add_conversation(
            role="assistant",
            content=response,
            metadata={"user_id": self.current_persona.user_id if self.current_persona else "unknown"}
        )
        
        return response
    
    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        if self.persona_filter:
            return self.persona_filter.get_system_prompt()
        
        return """你是一个友好的 AI 助手，请用自然、亲切的方式回复用户。"""
    
    def _extract_topic(self, text: str) -> str:
        """提取话题关键词"""
        topics = ["工作", "学习", "生活", "感情", "技术", "体育", "音乐", "电影", "新闻"]
        for topic in topics:
            if topic in text:
                return topic
        return "general"
    
    def get_persona_info(self) -> dict:
        """获取当前用户画像信息"""
        if not self.current_persona:
            return {"error": "No persona loaded"}
        
        return {
            "user_id": self.current_persona.user_id,
            "name": self.current_persona.name,
            "big_five": self.current_persona.big_five.to_vector(),
            "interests": self.current_persona.interests,
            "communication_style": self.current_persona.communication_style,
            "formality_level": self.current_persona.formality_level,
        }
    
    def save_session(self, path: str):
        """保存会话"""
        import json
        
        data = {
            "conversation_history": self.conversation_history,
            "persona": self.current_persona.to_dict() if self.current_persona else None,
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 保存记忆
        memory_path = path.replace(".json", "_memory.json")
        self.memory.save(memory_path)
    
    def load_session(self, path: str):
        """加载会话"""
        import json
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.conversation_history = data.get("conversation_history", [])
        
        if data.get("persona"):
            self.current_persona = UserPersona.from_dict(data["persona"])
            self.persona_filter = PersonaFilter(self.current_persona)
        
        # 加载记忆
        memory_path = path.replace(".json", "_memory.json")
        if os.path.exists(memory_path):
            self.memory.load(memory_path)


def demo():
    """演示"""
    print("=" * 50)
    print("数字人 AI 系统 - 演示")
    print("=" * 50)
    
    # 创建系统
    ai = DigitalHumanAI()
    
    # 创建演示用户画像
    print("\n[1] 创建用户画像...")
    ai.create_persona(
        user_id="demo_user",
        basic_info={
            "name": "演示用户",
            "age_range": "25-35",
            "occupation": "产品经理",
            "location": "北京"
        },
        questionnaire_results={
            "性格特质": [
                {"score": 0.8},  # 高开放性
                {"score": 0.7},  # 高尽责性
            ],
            "社交关系": [
                {"score": 0.6},
            ],
            "观点态度": [
                {"score": 0.7},
            ]
        }
    )
    
    print(f"画像创建完成: {ai.current_persona.name}")
    print(f"大五人格: {ai.current_persona.big_five.to_vector()}")
    
    # 对话演示
    print("\n[2] 开始对话演示...")
    print("-" * 40)
    
    questions = [
        "你好，我最近在考虑转行，你觉得 AI 行业怎么样？",
        "我对机器学习特别感兴趣，有什么入门建议吗？",
        "工作压力大的话，你有什么放松的方法推荐？",
    ]
    
    for q in questions:
        print(f"\n用户: {q}")
        response = ai.chat(q)
        print(f"AI: {response}")
    
    print("\n" + "=" * 50)
    print("演示完成!")
    print("=" * 50)
    
    # 保存会话
    save_path = project_root / "data" / "demo_session.json"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    ai.save_session(str(save_path))
    print(f"\n会话已保存到: {save_path}")


if __name__ == "__main__":
    demo()
