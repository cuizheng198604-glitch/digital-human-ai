# -*- coding: utf-8 -*-
"""
Digital Human AI - 人格约束过滤器
确保 AI 回复符合用户人格特征
"""
from typing import List, Dict, Optional, Any
from modeling.personality_encoder import UserPersona
import re


class PersonaFilter:
    """人格约束过滤器"""
    
    def __init__(self, persona: UserPersona):
        self.persona = persona
        self._init_constraints()
    
    def _init_constraints(self):
        """初始化约束规则"""
        # 价值观黑名单 (绝对不能说的)
        self.value_blacklist = [
            "极端", "暴力", "歧视",
            # 可根据用户画像动态添加
        ]
        
        # 用户不支持的观点 (基于问卷)
        self.opposition_topics = self.persona.opinions.get("opposition", {})
        
        # 用户偏好词汇 (用于增强)
        self.preferred_words = {
            "formal": ["确实", "同意", "认为", "分析"],
            "casual": ["我觉得", "可能", "大概", "呗"],
            "emotional": ["理解", "感受", "理解你", "心疼"],
            "logical": ["因为", "所以", "推理", "分析"],
        }
    
    def filter_response(self, response: str, context: Optional[Dict] = None) -> str:
        """
        过滤并调整回复
        
        Args:
            response: 原始 LLM 回复
            context: 上下文 {topic, emotion_level, ...}
        
        Returns:
            调整后的回复
        """
        if not response:
            return response
        
        # 1. 安全过滤
        response = self._safety_filter(response)
        
        # 2. 观点一致性过滤
        response = self._opinion_filter(response, context)
        
        # 3. 风格调整
        response = self._style_adjust(response, context)
        
        # 4. 敏感话题处理
        response = self._sensitive_filter(response)
        
        return response
    
    def _safety_filter(self, text: str) -> str:
        """安全过滤 - 移除有害内容"""
        # 检测并移除明显的敏感内容
        dangerous_patterns = [
            (r"(暴力|杀人|伤害).*方法", "[此处省略相关内容]"),
            (r"制造.*炸弹", "[安全问题]"),
            (r"如何.*自杀", "[请寻求专业帮助]"),
        ]
        
        for pattern, replacement in dangerous_patterns:
            text = re.sub(pattern, replacement, text)
        
        return text
    
    def _opinion_filter(self, text: str, context: Optional[Dict]) -> str:
        """观点一致性过滤"""
        if not context:
            return text
        
        topic = context.get("topic", "")
        
        # 如果用户明确表示反对某观点，AI 不应强烈支持
        if topic in self.opposition_topics:
            user_stance = self.opposition_topics[topic]
            # 简单实现: 避免直接否定用户立场
            # 实际更复杂，需要 NLI 模型
            pass
        
        return text
    
    def _style_adjust(self, text: str, context: Optional[Dict]) -> str:
        """风格调整 - 匹配用户沟通风格"""
        style = self.persona.communication_style
        formality = self.persona.formality_level
        
        if style == "direct":
            # 直接风格: 简洁明了
            text = self._make_direct(text)
        elif style == "indirect":
            # 间接风格: 更委婉
            text = self._make_indirect(text)
        
        # 正式程度调整
        if formality > 0.7:
            text = self._increase_formality(text)
        elif formality < 0.3:
            text = self._decrease_formality(text)
        
        return text
    
    def _make_direct(self, text: str) -> str:
        """调整为直接风格"""
        # 移除过多铺垫
        lines = text.split("\n")
        if len(lines) > 3:
            # 保留核心内容
            text = "\n".join(lines[:3])
        return text
    
    def _make_indirect(self, text: str) -> str:
        """调整为间接风格"""
        # 添加缓冲语
        softeners = ["这个嘛", "怎么说呢", "我想想", "可能不完全对"]
        if text and not any(s in text for s in softeners):
            text = f"{softeners[0]}，{text}"
        return text
    
    def _increase_formality(self, text: str) -> str:
        """提高正式程度"""
        replacements = {
            "你": "您",
            "我觉得": "我认为",
            "我觉得": "我认为",
            "大概": "基本上",
            "可能": "很可能",
            "呗": "",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    def _decrease_formality(self, text: str) -> str:
        """降低正式程度"""
        replacements = {
            "您": "你",
            "我认为": "我觉得",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    def _sensitive_filter(self, text: str) -> str:
        """敏感话题过滤"""
        avoided = self.persona.avoided_topics
        
        # 如果用户避免某个话题，AI 应主动转移
        for topic in avoided:
            if topic in text.lower():
                text = f"关于{topic}，这个话题您之前表示不太想深入讨论，我们可以聊聊其他的？"
                break
        
        return text
    
    def get_system_prompt(self) -> str:
        """生成符合人格的系统提示"""
        style_desc = {
            "direct": "简洁直接",
            "indirect": "委婉含蓄",
            "balanced": "平衡适中"
        }
        
        prompt = f"""你是一个AI数字分身，需要模仿以下用户的特征回复：

用户基本信息：
- 姓名: {self.persona.name}
- 职业: {self.persona.occupation}
- 沟通风格: {style_desc.get(self.persona.communication_style, '平衡')}

人格特征：
- 开放性: {'高' if self.persona.big_five.openness > 0.6 else '低' if self.persona.big_five.openness < 0.4 else '中等'}
- 外向性: {'高' if self.persona.big_five.extraversion > 0.6 else '低' if self.persona.big_five.extraversion < 0.4 else '中等'}
- 正式程度: {'高' if self.persona.formality_level > 0.6 else '低' if self.persona.formality_level < 0.4 else '中等'}

兴趣话题: {', '.join(self.persona.interests[:5]) if self.persona.interests else '暂无'}
避免话题: {', '.join(self.persona.avoided_topics) if self.persona.avoided_topics else '暂无'}

请始终保持以上风格特征进行回复。如果用户提到避免话题，请委婉地转移话题。"""
        
        return prompt


class ResponseValidator:
    """回复验证器"""
    
    def __init__(self, persona: UserPersona):
        self.persona = persona
    
    def validate(self, response: str) -> Dict[str, Any]:
        """
        验证回复质量
        
        Returns:
            {"valid": bool, "issues": List[str], "score": float}
        """
        issues = []
        score = 1.0
        
        # 检查长度
        if len(response) < 5:
            issues.append("回复过短")
            score -= 0.3
        elif len(response) > 2000:
            issues.append("回复过长")
            score -= 0.1
        
        # 检查是否包含避免话题
        for topic in self.persona.avoided_topics:
            if topic in response:
                issues.append(f"包含应避免的话题: {topic}")
                score -= 0.2
        
        # 检查人格一致性
        if self.persona.formality_level > 0.7:
            if any(w in response for w in ["你", "我觉得", "大概"]):
                issues.append("正式程度不够")
                score -= 0.1
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "score": max(0, score)
        }
