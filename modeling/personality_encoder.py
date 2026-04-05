# -*- coding: utf-8 -*-
"""
Digital Human AI - 人格建模模块
基于大五人格模型 + 语义向量
"""
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import numpy as np


@dataclass
class BigFiveTraits:
    """大五人格维度"""
    openness: float = 0.5          # 开放性: 好奇心、创造力
    conscientiousness: float = 0.5  # 尽责性: 自律、可靠性
    extraversion: float = 0.5       # 外向性: 社交、活力
    agreeableness: float = 0.5      # 宜人性: 同理心、合作
    neuroticism: float = 0.5        # 神经质: 情绪稳定
    
    def to_vector(self) -> List[float]:
        return [
            self.openness,
            self.conscientiousness,
            self.extraversion,
            self.agreeableness,
            self.neuroticism
        ]
    
    @classmethod
    def from_vector(cls, vector: List[float]) -> "BigFiveTraits":
        if len(vector) != 5:
            raise ValueError("向量长度必须为5")
        return cls(
            openness=vector[0],
            conscientiousness=vector[1],
            extraversion=vector[2],
            agreeableness=vector[3],
            neuroticism=vector[4]
        )


@dataclass
class UserPersona:
    """用户数字分身画像"""
    user_id: str
    name: str = ""
    created_at: str = ""
    updated_at: str = ""
    
    # 基础属性
    age_range: str = ""  # 年龄段
    gender: str = ""
    occupation: str = ""
    location: str = ""
    
    # 大五人格
    big_five: BigFiveTraits = field(default_factory=BigFiveTraits)
    
    # 语义向量 (用于 RAG 检索)
    embedding_vector: List[float] = field(default_factory=list)
    
    # 价值观与观点
    values: List[str] = field(default_factory=list)  # 核心价值观
    opinions: Dict[str, str] = field(default_factory=dict)  # 具体观点 {话题: 立场}
    
    # 说话风格
    communication_style: str = "balanced"  # direct / indirect / balanced
    formality_level: float = 0.5  # 0-1, 随意-正式
    emotional_level: float = 0.5  # 0-1, 理性-情感
    humor_level: float = 0.5  # 0-1, 严肃-幽默
    
    # 偏好
    interests: List[str] = field(default_factory=list)  # 兴趣领域
    preferred_topics: List[str] = field(default_factory=list)  # 喜欢聊的话题
    avoided_topics: List[str] = field(default_factory=list)  # 避免的话题
    
    # 知识库摘要
    knowledge_summary: str = ""  # 知识背景总结
    expertise_areas: List[str] = field(default_factory=list)  # 专业领域
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "UserPersona":
        if "big_five" in data and isinstance(data["big_five"], dict):
            data["big_five"] = BigFiveTraits(**data["big_five"])
        return cls(**data)
    
    def update(self, **kwargs):
        """更新画像"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now().isoformat()


class PersonalityEncoder:
    """人格编码器 - 从问卷和行为数据构建用户画像"""
    
    def __init__(self, llm_engine=None):
        self.llm_engine = llm_engine
        self._dimension_names = {
            "openness": "开放性",
            "conscientiousness": "尽责性",
            "extraversion": "外向性",
            "agreeableness": "宜人性",
            "neuroticism": "神经质"
        }
    
    def build_persona(
        self,
        user_id: str,
        questionnaire_results: Dict[str, List[Dict]],
        behavioral_data: Optional[Dict] = None,
        basic_info: Optional[Dict] = None
    ) -> UserPersona:
        """
        构建用户画像
        
        Args:
            user_id: 用户ID
            questionnaire_results: 问卷结果 {问卷类型: [{题号, 答案, 分数}]}
            behavioral_data: 行为数据 {行为类型: [记录]}
            basic_info: 基础信息 {姓名, 年龄, 职业等}
        
        Returns:
            UserPersona 对象
        """
        persona = UserPersona(
            user_id=user_id,
            name=basic_info.get("name", "") if basic_info else "",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        
        if basic_info:
            persona.age_range = basic_info.get("age_range", "")
            persona.gender = basic_info.get("gender", "")
            persona.occupation = basic_info.get("occupation", "")
            persona.location = basic_info.get("location", "")
        
        # 从问卷计算大五人格
        if questionnaire_results:
            big_five = self._calculate_big_five(questionnaire_results)
            persona.big_five = big_five
            
            # 从问卷提取价值观和偏好
            persona.values = self._extract_values(questionnaire_results)
            persona.interests = self._extract_interests(questionnaire_results)
        
        # 从行为数据补充
        if behavioral_data:
            self._enrich_from_behavior(persona, behavioral_data)
        
        return persona
    
    def _calculate_big_five(self, questionnaire_results: Dict) -> BigFiveTraits:
        """根据问卷结果计算大五人格分数"""
        # 简化实现: 实际应根据具体问卷题目计分
        scores = {
            "openness": [],
            "conscientiousness": [],
            "extraversion": [],
            "agreeableness": [],
            "neuroticism": []
        }
        
        # 问卷类型到大五维度的映射
        questionnaire_dimensions = {
            "认知测评": "openness",
            "社交关系": "extraversion",
            "观点态度": "agreeableness",
            "性格特质": "conscientiousness",
            "行为模式": "neuroticism"
        }
        
        for q_type, dimension in questionnaire_dimensions.items():
            if q_type in questionnaire_results:
                results = questionnaire_results[q_type]
                if results:
                    avg_score = sum(r.get("score", 0.5) for r in results) / len(results)
                    scores[dimension].append(avg_score)
        
        # 计算平均分
        final_scores = {}
        for dim, dim_scores in scores.items():
            if dim_scores:
                final_scores[dim] = sum(dim_scores) / len(dim_scores)
            else:
                final_scores[dim] = 0.5  # 默认值
        
        return BigFiveTraits(**final_scores)
    
    def _extract_values(self, questionnaire_results: Dict) -> List[str]:
        """提取核心价值观"""
        values = []
        if "观点态度" in questionnaire_results:
            for q in questionnaire_results["观点态度"]:
                if q.get("is_value", False):
                    values.append(q.get("answer", ""))
        return values
    
    def _extract_interests(self, questionnaire_results: Dict) -> List[str]:
        """提取兴趣领域"""
        interests = []
        if "认知测评" in questionnaire_results:
            for q in questionnaire_results["认知测评"]:
                if q.get("is_interest", False):
                    interests.append(q.get("answer", ""))
        return interests
    
    def _enrich_from_behavior(self, persona: UserPersona, behavioral_data: Dict):
        """从行为数据丰富画像"""
        # 沟通风格推断
        if "chat_history" in behavioral_data:
            chat_history = behavioral_data["chat_history"]
            persona.communication_style = self._infer_communication_style(chat_history)
            persona.formality_level = self._infer_formality(chat_history)
    
    def _infer_communication_style(self, chat_history: List[Dict]) -> str:
        """从聊天历史推断沟通风格"""
        if not chat_history:
            return "balanced"
        
        # 简单实现: 检查简短回复比例
        short_count = sum(1 for m in chat_history if len(m.get("content", "")) < 20)
        ratio = short_count / len(chat_history)
        
        if ratio > 0.6:
            return "direct"
        elif ratio < 0.2:
            return "indirect"
        return "balanced"
    
    def _infer_formality(self, chat_history: List[Dict]) -> float:
        """推断正式程度"""
        if not chat_history:
            return 0.5
        
        formal_indicators = ["您", "请问", "谢谢", "非常", "确实"]
        informal_indicators = ["你", "呗", "哈", "呀", "啦"]
        
        formal_count = 0
        informal_count = 0
        
        for m in chat_history:
            content = m.get("content", "")
            for indicator in formal_indicators:
                if indicator in content:
                    formal_count += 1
            for indicator in informal_indicators:
                if indicator in content:
                    informal_count += 1
        
        total = formal_count + informal_count
        if total == 0:
            return 0.5
        
        return formal_count / total
    
    def generate_persona_description(self, persona: UserPersona) -> str:
        """生成人格描述文本"""
        if self.llm_engine:
            prompt = f"""请根据以下用户画像生成一段简洁的描述：

姓名: {persona.name}
年龄: {persona.age_range}
职业: {persona.occupation}

大五人格:
- 开放性: {persona.big_five.openness:.2f}
- 尽责性: {persona.big_five.conscientiousness:.2f}
- 外向性: {persona.big_five.extraversion:.2f}
- 宜人性: {persona.big_five.agreeableness:.2f}
- 神经质: {persona.big_five.neuroticism:.2f}

兴趣: {', '.join(persona.interests)}
价值观: {', '.join(persona.values)}
沟通风格: {persona.communication_style}

请生成一段 50-100 字的人格描述。"""
            
            response = self.llm_engine.chat([
                {"role": "user", "content": prompt}
            ])
            return response
        
        # 无 LLM 时的简单描述
        traits = []
        if persona.big_five.openness > 0.6:
            traits.append("高开放性")
        if persona.big_five.extraversion > 0.6:
            traits.append("高外向性")
        
        return f"{persona.name}，{persona.age_range}，{'，'.join(traits) if traits else '中等人格特质'}"


# 测试
if __name__ == "__main__":
    encoder = PersonalityEncoder()
    
    # 模拟问卷数据
    test_data = {
        "性格特质": [
            {"score": 0.7},
            {"score": 0.8},
        ],
        "社交关系": [
            {"score": 0.6},
        ]
    }
    
    persona = encoder.build_persona(
        user_id="test_user",
        questionnaire_results=test_data,
        basic_info={"name": "张三", "age_range": "25-35", "occupation": "工程师"}
    )
    
    print("=== 用户画像 ===")
    print(f"ID: {persona.user_id}")
    print(f"姓名: {persona.name}")
    print(f"大五人格: {persona.big_five.to_vector()}")
    print(f"兴趣: {persona.interests}")
