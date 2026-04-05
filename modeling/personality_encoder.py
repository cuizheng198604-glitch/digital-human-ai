# -*- coding: utf-8 -*-
"""
Digital Human AI - 人格建模模块
基于大五人格模型 + 语义向量
"""
import json
import hashlib
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
    
    def get_level(self, score: float) -> str:
        """根据分数返回等级描述"""
        if score >= 0.8: return "极高"
        if score >= 0.6: return "较高"
        if score >= 0.4: return "中等"
        if score >= 0.2: return "较低"
        return "极低"


@dataclass
class UserPersona:
    """用户数字分身画像"""
    user_id: str
    name: str = ""
    created_at: str = ""
    updated_at: str = ""
    
    # 基础属性
    age_range: str = ""
    gender: str = ""
    occupation: str = ""
    location: str = ""
    
    # 大五人格
    big_five: BigFiveTraits = field(default_factory=BigFiveTraits)
    
    # 语义向量 (用于 RAG 检索) - 128维
    embedding_vector: List[float] = field(default_factory=list)
    
    # 人格描述
    personality_description: str = ""
    
    # 价值观与观点
    values: List[str] = field(default_factory=list)
    opinions: Dict[str, str] = field(default_factory=dict)
    
    # 说话风格
    communication_style: str = "balanced"
    formality_level: float = 0.5
    emotional_level: float = 0.5
    humor_level: float = 0.5
    
    # 偏好
    interests: List[str] = field(default_factory=list)
    preferred_topics: List[str] = field(default_factory=list)
    avoided_topics: List[str] = field(default_factory=list)
    
    # 知识库摘要
    knowledge_summary: str = ""
    expertise_areas: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "UserPersona":
        if "big_five" in data and isinstance(data["big_five"], dict):
            data["big_five"] = BigFiveTraits(**data["big_five"])
        return cls(**data)
    
    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now().isoformat()


class PersonalityEncoder:
    """人格编码器 - 从问卷和行为数据构建用户画像"""
    
    # 兴趣领域关键词
    INTEREST_KEYWORDS = {
        "科技/互联网": ["科技", "互联网", "编程", "AI", "人工智能", "软件", "App", "网站", "代码"],
        "金融/投资": ["投资", "理财", "股票", "基金", "加密货币", "银行", "财务", "经济"],
        "文化/艺术": ["艺术", "音乐", "电影", "书籍", "文学", "绘画", "摄影", "设计", "戏剧"],
        "体育/健身": ["运动", "健身", "跑步", "游泳", "篮球", "足球", "瑜伽", "爬山", "骑行"],
        "旅行/户外": ["旅行", "旅游", "户外", "露营", "徒步", "自然", "探索", "冒险"],
        "美食/生活": ["美食", "烹饪", "餐厅", "美食家", "生活品质", "家居"],
        "教育/自我提升": ["学习", "教育", "读书", "课程", "培训", "自我提升", "成长"],
        "娱乐/影视": ["娱乐", "综艺", "追星", "游戏", "电竞", "短视频", "电视剧", "明星"]
    }
    
    # 价值观关键词
    VALUE_KEYWORDS = {
        "成就感": ["成就感", "成功", "成就", "成就动机", "目标达成"],
        "人际关系": ["人际关系", "友谊", "亲情", "爱情", "社交", "人际"],
        "个人成长": ["成长", "自我提升", "学习", "进步", "发展"],
        "生活平衡": ["平衡", "工作生活平衡", "生活品质", "休闲"],
        "安全感": ["安全", "稳定", "保障", "确定性", "安全感"]
    }
    
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
        raw_answers: Optional[Dict[str, List[Dict]]] = None,
        behavioral_data: Optional[Dict] = None,
        basic_info: Optional[Dict] = None
    ) -> UserPersona:
        """构建用户画像"""
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
            
            # 提取价值观和偏好
            persona.values = self._extract_values(questionnaire_results, raw_answers)
            persona.interests = self._extract_interests(questionnaire_results, raw_answers)
        
        # 生成人格描述
        persona.personality_description = self.generate_personality_description(persona)
        
        # 生成 embedding 向量
        persona.embedding_vector = self.generate_embedding_vector(persona)
        
        # 从行为数据补充
        if behavioral_data:
            self._enrich_from_behavior(persona, behavioral_data)
        
        return persona
    
    def _calculate_big_five(self, questionnaire_results: Dict) -> BigFiveTraits:
        """根据问卷结果计算大五人格分数"""
        scores = {
            "openness": [],
            "conscientiousness": [],
            "extraversion": [],
            "agreeableness": [],
            "neuroticism": []
        }
        
        # 问卷类型到大五维度的映射
        questionnaire_dimensions = {
            "big_five": ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"],
            "social": ["extraversion", "agreeableness"],
            "values": ["agreeableness", "openness"],
            "interests": ["openness", "conscientiousness"]
        }
        
        for q_id, dimensions in questionnaire_dimensions.items():
            if q_id in questionnaire_results:
                results = questionnaire_results[q_id]
                if results:
                    dim_scores = {d: [] for d in dimensions}
                    for r in results:
                        dim = r.get("dimension", "")
                        if dim in dim_scores:
                            dim_scores[dim].append(r.get("score", 0.5))
                    
                    for dim, dim_list in dim_scores.items():
                        if dim_list:
                            scores[dim].extend(dim_list)
        
        # 计算平均分
        final_scores = {}
        for dim, dim_scores in scores.items():
            if dim_scores:
                final_scores[dim] = sum(dim_scores) / len(dim_scores)
            else:
                final_scores[dim] = 0.5
        
        return BigFiveTraits(**final_scores)
    
    def _extract_interests(self, questionnaire_results: Dict, raw_answers: Optional[Dict] = None) -> List[str]:
        """提取兴趣领域"""
        interests = set()
        
        # 方法1: 从原始答案中提取多选题选项
        if raw_answers:
            interest_keywords = [
                "科技/互联网", "金融/投资", "文化/艺术", "体育/健身",
                "旅行/户外", "美食/生活", "教育/自我提升", "娱乐/影视"
            ]
            
            for q_id, answers in raw_answers.items():
                for answer in answers:
                    answer_text = str(answer.get("answer", ""))
                    answer_value = answer.get("answer", "")
                    
                    # 检查多选题选项
                    if isinstance(answer_value, list):
                        for opt in answer_value:
                            for interest in interest_keywords:
                                if interest in opt:
                                    interests.add(interest)
                    elif isinstance(answer_value, str):
                        for interest in interest_keywords:
                            if interest in answer_value:
                                interests.add(interest)
        
        # 方法2: 从问卷结果中查找兴趣相关维度
        if "interests" in questionnaire_results:
            for item in questionnaire_results["interests"]:
                # 检查原始答案文本
                answer = item.get("answer", "")
                if isinstance(answer, list):
                    interests.update([str(a) for a in answer])
                elif answer:
                    interests.add(str(answer))
        
        # 过滤并返回
        return list(interests)[:10]  # 最多10个
    
    def _extract_values(self, questionnaire_results: Dict, raw_answers: Optional[Dict] = None) -> List[str]:
        """提取核心价值观"""
        values = set()
        
        if raw_answers:
            value_keywords = {
                "成就感": ["成就感", "成就", "成功", "目标"],
                "人际关系": ["人际", "友谊", "朋友", "关系", "社交"],
                "个人成长": ["成长", "学习", "进步", "提升"],
                "生活平衡": ["平衡", "生活", "休闲", "享受"],
                "安全感": ["安全", "稳定", "保障"]
            }
            
            for q_id, answers in raw_answers.items():
                for answer in answers:
                    answer_text = str(answer.get("answer", ""))
                    for value_name, keywords in value_keywords.items():
                        for kw in keywords:
                            if kw in answer_text:
                                values.add(value_name)
        
        if "values" in questionnaire_results:
            for item in questionnaire_results["values"]:
                answer = item.get("answer", "")
                if isinstance(answer, list):
                    values.update([str(a) for a in answer])
                elif answer:
                    values.add(str(answer))
        
        return list(values)[:5]  # 最多5个
    
    def generate_personality_description(self, persona: UserPersona) -> str:
        """生成人格描述文本"""
        bf = persona.big_five
        
        # 分析各维度
        openness_level = bf.get_level(bf.openness)
        conscientiousness_level = bf.get_level(bf.conscientiousness)
        extraversion_level = bf.get_level(bf.extraversion)
        agreeableness_level = bf.get_level(bf.agreeableness)
        neuroticism_level = bf.get_level(bf.neuroticism)
        
        # 生成描述
        descriptions = []
        
        # 开放性描述
        if bf.openness >= 0.7:
            descriptions.append("思维开放，好奇心强，喜欢尝试新事物")
        elif bf.openness <= 0.3:
            descriptions.append("务实稳重，偏好熟悉的事物")
        else:
            descriptions.append("视野适中，既能创新也注重实际")
        
        # 尽责性描述
        if bf.conscientiousness >= 0.7:
            descriptions.append("责任心强，做事有计划，自律性高")
        elif bf.conscientiousness <= 0.3:
            descriptions.append("随性自在，不喜欢被约束")
        else:
            descriptions.append("有一定的自律性，工作中能保持专注")
        
        # 外向性描述
        if bf.extraversion >= 0.7:
            descriptions.append("性格外向开朗，喜欢社交，精力充沛")
        elif bf.extraversion <= 0.3:
            descriptions.append("性格内敛沉稳，享受独处时光")
        else:
            descriptions.append("社交有度，既能独处也善交流")
        
        # 宜人性描述
        if bf.agreeableness >= 0.7:
            descriptions.append("为人友善，乐于助人，合作性强")
        elif bf.agreeableness <= 0.3:
            descriptions.append("独立自主，观点鲜明")
        else:
            descriptions.append("善于换位思考，人际关系和谐")
        
        # 神经质描述
        if bf.neuroticism >= 0.7:
            descriptions.append("情感细腻，对压力较敏感")
        elif bf.neuroticism <= 0.3:
            descriptions.append("情绪稳定，内心平和，抗压能力强")
        else:
            descriptions.append("情绪管理能力适中")
        
        # 添加兴趣
        if persona.interests:
            interests_str = "、".join(persona.interests[:3])
            descriptions.append(f"兴趣领域: {interests_str}")
        
        # 添加价值观
        if persona.values:
            values_str = "、".join(persona.values[:3])
            descriptions.append(f"核心价值: {values_str}")
        
        return " | ".join(descriptions)
    
    def generate_embedding_vector(self, persona: UserPersona) -> List[float]:
        """生成128维人格向量用于RAG检索"""
        bf = persona.big_five
        
        # 基础向量: 大五人格 (5维)
        base = np.array([
            bf.openness,
            bf.conscientiousness,
            bf.extraversion,
            bf.agreeableness,
            bf.neuroticism
        ])
        
        # 扩展到128维
        # 使用多个正交基函数创建更丰富的表示
        vector = np.zeros(128)
        
        # 前5维: 直接使用大五分数
        vector[:5] = base
        
        # 6-20维: 人格维度的二阶组合 (15维)
        combinations = [
            bf.openness * bf.conscientiousness,
            bf.openness * bf.extraversion,
            bf.openness * bf.agreeableness,
            bf.openness * bf.neuroticism,
            bf.conscientiousness * bf.extraversion,
            bf.conscientiousness * bf.agreeableness,
            bf.conscientiousness * bf.neuroticism,
            bf.extraversion * bf.agreeableness,
            bf.extraversion * bf.neuroticism,
            bf.agreeableness * bf.neuroticism,
            bf.openness ** 2,
            bf.conscientiousness ** 2,
            bf.extraversion ** 2,
            bf.agreeableness ** 2,
            bf.neuroticism ** 2
        ]
        vector[5:20] = combinations
        
        # 21-40维: 风格特征 (20维)
        style_features = np.array([
            persona.formality_level,
            persona.emotional_level,
            persona.humor_level,
            1.0 if persona.communication_style == "direct" else 0.0,
            1.0 if persona.communication_style == "indirect" else 0.0,
            1.0 if persona.communication_style == "balanced" else 0.0,
        ] + [0.0] * 14)
        vector[20:26] = style_features[:6]
        
        # 26-50维: 兴趣编码 (25维)
        interest_vector = self._encode_interests(persona.interests)
        vector[26:51] = interest_vector[:25]
        
        # 51-75维: 价值观编码 (25维)
        value_vector = self._encode_values(persona.values)
        vector[51:76] = value_vector[:25]
        
        # 76-128维: 基于哈希的确定性噪声 (53维)
        # 使用人格特征的哈希来生成一致的随机种子
        seed_str = f"{persona.user_id}_{bf.openness:.2f}_{bf.conscientiousness:.2f}"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        np.random.seed(seed % (2**32))
        vector[76:128] = np.random.randn(52) * 0.1
        
        # L2归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector.tolist()
    
    def _encode_interests(self, interests: List[str]) -> np.ndarray:
        """编码兴趣领域为向量"""
        all_interests = list(self.INTEREST_KEYWORDS.keys())
        vector = np.zeros(25)
        
        for interest in interests:
            for i, category in enumerate(all_interests):
                if interest in category or category in interest:
                    vector[i] = 1.0
                    break
        
        return vector
    
    def _encode_values(self, values: List[str]) -> np.ndarray:
        """编码价值观为向量"""
        all_values = list(self.VALUE_KEYWORDS.keys())
        vector = np.zeros(25)
        
        for value in values:
            for i, category in enumerate(all_values):
                if value in category or category in value:
                    vector[i] = 1.0
                    break
        
        return vector
    
    def _enrich_from_behavior(self, persona: UserPersona, behavioral_data: Dict):
        """从行为数据丰富画像"""
        if "chat_history" in behavioral_data:
            chat_history = behavioral_data["chat_history"]
            persona.communication_style = self._infer_communication_style(chat_history)
            persona.formality_level = self._infer_formality(chat_history)
    
    def _infer_communication_style(self, chat_history: List[Dict]) -> str:
        """从聊天历史推断沟通风格"""
        if not chat_history:
            return "balanced"
        
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
    
    def compute_similarity(self, persona1: UserPersona, persona2: UserPersona) -> float:
        """计算两个人格画像的余弦相似度"""
        if not persona1.embedding_vector or not persona2.embedding_vector:
            return 0.5
        
        v1 = np.array(persona1.embedding_vector)
        v2 = np.array(persona2.embedding_vector)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.5
        
        return (dot_product + 1) / 2  # 归一化到 0-1
    
    def find_similar_personas(
        self, 
        target_persona: UserPersona, 
        all_personas: List[UserPersona],
        top_k: int = 5
    ) -> List[tuple]:
        """查找最相似的人格画像"""
        similarities = []
        
        for persona in all_personas:
            if persona.user_id == target_persona.user_id:
                continue
            sim = self.compute_similarity(target_persona, persona)
            similarities.append((persona, sim))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


# 测试
if __name__ == "__main__":
    encoder = PersonalityEncoder()
    
    # 模拟问卷数据
    test_data = {
        "big_five": [
            {"dimension": "openness", "score": 0.8},
            {"dimension": "conscientiousness", "score": 0.9},
            {"dimension": "extraversion", "score": 0.3},
            {"dimension": "agreeableness", "score": 0.7},
            {"dimension": "neuroticism", "score": 0.2},
        ],
        "interests": [
            {"dimension": "reading", "score": 0.8},
        ],
        "values": [
            {"dimension": "achievement", "score": 0.7},
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
    print(f"大五人格: openness={persona.big_five.openness}, conscientiousness={persona.big_five.conscientiousness}")
    print(f"外向性: {persona.big_five.extraversion}, 宜人性: {persona.big_five.agreeableness}, 神经质: {persona.big_five.neuroticism}")
    print(f"兴趣: {persona.interests}")
    print(f"价值观: {persona.values}")
    print(f"人格描述: {persona.personality_description}")
    print(f"向量维度: {len(persona.embedding_vector)}")
    print(f"向量前10维: {persona.embedding_vector[:10]}")
