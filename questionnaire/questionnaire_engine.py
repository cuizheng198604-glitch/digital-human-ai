# -*- coding: utf-8 -*-
"""
Digital Human AI - 问卷引擎
支持多类型问卷、进度保存、结果分析
"""
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class QuestionType(Enum):
    """题目类型"""
    SINGLE_CHOICE = "single_choice"      # 单选
    MULTIPLE_CHOICE = "multiple_choice"  # 多选
    SCALE = "scale"                       # 量表 (1-5, 1-7)
    TEXT = "text"                         # 文本输入


@dataclass
class Question:
    """题目"""
    id: str
    type: QuestionType
    text: str
    options: List[str] = field(default_factory=list)  # 选项
    scale_range: tuple = field(default=(1, 5))  # 量表范围
    dimension: str = ""  # 所属维度 (大五人格等)
    reverse_score: bool = False  # 反向计分
    is_value: bool = False  # 是否为价值观相关
    is_interest: bool = False  # 是否为兴趣相关


@dataclass
class Questionnaire:
    """问卷"""
    id: str
    name: str
    description: str
    questions: List[Question]
    estimated_time: int = 10  # 预计完成时间(分钟)


@dataclass
class Answer:
    """答案"""
    question_id: str
    answer: Any  # str / List[str] / int
    score: float = 0.0  # 计算后的分数


class QuestionnaireEngine:
    """问卷引擎"""
    
    def __init__(self):
        self.questionnaires: Dict[str, Questionnaire] = {}
        self.user_answers: Dict[str, Dict[str, Answer]] = {}  # {user_id: {questionnaire_id: [Answer]}}
        self._load_default_questionnaires()
    
    def _load_default_questionnaires(self):
        """加载默认问卷"""
        self.questionnaires = {
            "big_five": self._create_big_five_questionnaire(),
            "social": self._create_social_questionnaire(),
            "values": self._create_values_questionnaire(),
            "interests": self._create_interests_questionnaire(),
        }
    
    def _create_big_five_questionnaire(self) -> Questionnaire:
        """创建大五人格问卷"""
        questions = [
            Question(
                id="bf_1",
                type=QuestionType.SCALE,
                text="我愿意尝试新的活动和体验",
                scale_range=(1, 5),
                dimension="openness"
            ),
            Question(
                id="bf_2",
                type=QuestionType.SCALE,
                text="我通常会提前计划安排事情",
                scale_range=(1, 5),
                dimension="conscientiousness"
            ),
            Question(
                id="bf_3",
                type=QuestionType.SCALE,
                text="我喜欢和他人交流互动",
                scale_range=(1, 5),
                dimension="extraversion"
            ),
            Question(
                id="bf_4",
                type=QuestionType.SCALE,
                text="我信任他人并愿意合作",
                scale_range=(1, 5),
                dimension="agreeableness"
            ),
            Question(
                id="bf_5",
                type=QuestionType.SCALE,
                text="我容易感到焦虑或担忧",
                scale_range=(1, 5),
                dimension="neuroticism",
                reverse_score=True
            ),
            Question(
                id="bf_6",
                type=QuestionType.SCALE,
                text="我喜欢抽象思维和理论讨论",
                scale_range=(1, 5),
                dimension="openness"
            ),
            Question(
                id="bf_7",
                type=QuestionType.SCALE,
                text="我会坚持完成开始的任务",
                scale_range=(1, 5),
                dimension="conscientiousness"
            ),
            Question(
                id="bf_8",
                type=QuestionType.SCALE,
                text="在聚会中我通常比较安静",
                scale_range=(1, 5),
                dimension="extraversion",
                reverse_score=True
            ),
            Question(
                id="bf_9",
                type=QuestionType.SCALE,
                text="我善于理解他人感受",
                scale_range=(1, 5),
                dimension="agreeableness"
            ),
            Question(
                id="bf_10",
                type=QuestionType.SCALE,
                text="我的情绪比较稳定",
                scale_range=(1, 5),
                dimension="neuroticism",
                reverse_score=True
            ),
        ]
        
        return Questionnaire(
            id="big_five",
            name="大五人格测评",
            description="评估你在开放性、尽责性、外向性、宜人性和神经质五个维度的人格特质",
            questions=questions,
            estimated_time=5
        )
    
    def _create_social_questionnaire(self) -> Questionnaire:
        """创建社交关系问卷"""
        questions = [
            Question(
                id="social_1",
                type=QuestionType.SINGLE_CHOICE,
                text="你更喜欢什么样的沟通方式？",
                options=["面对面交流", "电话/视频", "文字聊天", "都可以"],
                dimension="communication_preference"
            ),
            Question(
                id="social_2",
                type=QuestionType.SCALE,
                text="我享受社交活动",
                scale_range=(1, 5),
                dimension="social_battery"  # 社交充电
            ),
            Question(
                id="social_3",
                type=QuestionType.SCALE,
                text="我倾向于主动结交新朋友",
                scale_range=(1, 5),
                dimension="proactivity"
            ),
            Question(
                id="social_4",
                type=QuestionType.MULTIPLE_CHOICE,
                text="你在社交中最看重什么？（可多选）",
                options=["真诚", "有趣", "有共同话题", "互相支持", "其他"],
                is_interest=True
            ),
            Question(
                id="social_5",
                type=QuestionType.TEXT,
                text="请描述一下你理想中的朋友关系是什么样的？",
                dimension="ideal_relationship"
            ),
        ]
        
        return Questionnaire(
            id="social",
            name="社交关系调查",
            description="了解你的社交风格和关系模式",
            questions=questions,
            estimated_time=5
        )
    
    def _create_values_questionnaire(self) -> Questionnaire:
        """创建价值观问卷"""
        questions = [
            Question(
                id="value_1",
                type=QuestionType.SINGLE_CHOICE,
                text="对你来说，最重要的是？",
                options=["成就感", "人际关系", "个人成长", "生活平衡", "安全感"],
                is_value=True
            ),
            Question(
                id="value_2",
                type=QuestionType.SCALE,
                text="我倾向于追求稳定而不是冒险",
                scale_range=(1, 5),
                dimension="risk_tolerance"
            ),
            Question(
                id="value_3",
                type=QuestionType.SCALE,
                text="我愿意为长远目标牺牲短期快乐",
                scale_range=(1, 5),
                dimension="delayed_gratification"
            ),
            Question(
                id="value_4",
                type=QuestionType.MULTIPLE_CHOICE,
                text="以下哪些观点你比较认同？（可多选）",
                options=[
                    "努力一定有回报",
                    "成功靠运气更重要",
                    "人应该不断学习",
                    "金钱不是万能的",
                    "家庭最重要"
                ],
                is_value=True
            ),
            Question(
                id="value_5",
                type=QuestionType.TEXT,
                text="有没有什么是你一直坚信的信念？",
                dimension="core_belief",
                is_value=True
            ),
        ]
        
        return Questionnaire(
            id="values",
            name="价值观与信念",
            description="探索你的核心价值观和人生信念",
            questions=questions,
            estimated_time=8
        )
    
    def _create_interests_questionnaire(self) -> Questionnaire:
        """创建兴趣问卷"""
        questions = [
            Question(
                id="interest_1",
                type=QuestionType.MULTIPLE_CHOICE,
                text="你平时喜欢关注哪些领域？（可多选）",
                options=[
                    "科技/互联网",
                    "金融/投资",
                    "文化/艺术",
                    "体育/健身",
                    "旅行/户外",
                    "美食/生活",
                    "教育/自我提升",
                    "娱乐/影视"
                ],
                is_interest=True
            ),
            Question(
                id="interest_2",
                type=QuestionType.SCALE,
                text="我经常阅读非工作相关的书籍",
                scale_range=(1, 5),
                dimension="reading_habit"
            ),
            Question(
                id="interest_3",
                type=QuestionType.SINGLE_CHOICE,
                text="周末你通常喜欢？",
                options=[
                    "在家休息",
                    "和朋友聚会",
                    "学习新技能",
                    "户外运动",
                    "不确定，看心情"
                ],
                is_interest=True
            ),
            Question(
                id="interest_4",
                type=QuestionType.TEXT,
                text="有没有什么是你一直想尝试但还没机会做的事？",
                dimension="untried_interests"
            ),
        ]
        
        return Questionnaire(
            id="interests",
            name="兴趣与爱好",
            description="了解你的兴趣领域和偏好",
            questions=questions,
            estimated_time=5
        )
    
    def get_questionnaire(self, questionnaire_id: str) -> Optional[Questionnaire]:
        """获取问卷"""
        return self.questionnaires.get(questionnaire_id)
    
    def get_all_questionnaires(self) -> List[Questionnaire]:
        """获取所有问卷"""
        return list(self.questionnaires.values())
    
    def submit_answer(
        self,
        user_id: str,
        questionnaire_id: str,
        question_id: str,
        answer: Any
    ) -> Answer:
        """提交答案"""
        if user_id not in self.user_answers:
            self.user_answers[user_id] = {}
        
        if questionnaire_id not in self.user_answers[user_id]:
            self.user_answers[user_id][questionnaire_id] = []
        
        # 计算分数
        score = self._calculate_score(questionnaire_id, question_id, answer)
        
        answer_obj = Answer(
            question_id=question_id,
            answer=answer,
            score=score
        )
        
        # 更新或添加答案
        existing = self.user_answers[user_id][questionnaire_id]
        for i, a in enumerate(existing):
            if a.question_id == question_id:
                existing[i] = answer_obj
                return answer_obj
        
        existing.append(answer_obj)
        return answer_obj
    
    def _calculate_score(
        self,
        questionnaire_id: str,
        question_id: str,
        answer: Any
    ) -> float:
        """计算答案分数"""
        q = self._get_question(questionnaire_id, question_id)
        if not q:
            return 0.0
        
        if q.type == QuestionType.SCALE:
            if isinstance(answer, int):
                score = answer / q.scale_range[1]  # 归一化到 0-1
                if q.reverse_score:
                    score = 1 - score
                return score
        
        # 其他类型暂时返回 0.5 (中等)
        return 0.5
    
    def _get_question(self, questionnaire_id: str, question_id: str) -> Optional[Question]:
        """获取题目"""
        questionnaire = self.questionnaires.get(questionnaire_id)
        if not questionnaire:
            return None
        
        for q in questionnaire.questions:
            if q.id == question_id:
                return q
        return None
    
    def get_user_results(self, user_id: str, questionnaire_id: str) -> Dict:
        """获取用户问卷结果"""
        answers = self.user_answers.get(user_id, {}).get(questionnaire_id, [])
        
        # 按维度分组
        dimension_scores = {}
        for answer in answers:
            q = self._get_question(questionnaire_id, answer.question_id)
            if q and q.dimension:
                if q.dimension not in dimension_scores:
                    dimension_scores[q.dimension] = []
                dimension_scores[q.dimension].append(answer.score)
        
        # 计算各维度平均分
        dimension_avg = {}
        for dim, scores in dimension_scores.items():
            if scores:
                dimension_avg[dim] = sum(scores) / len(scores)
        
        return {
            "questionnaire_id": questionnaire_id,
            "total_questions": len(answers),
            "dimension_scores": dimension_avg,
            "dimension_avg": dimension_avg,
            "raw_answers": [
                {"question_id": a.question_id, "answer": a.answer, "score": a.score}
                for a in answers
            ]
        }
    
    def get_all_results(self, user_id: str) -> Dict[str, Dict]:
        """获取用户所有问卷结果"""
        return {
            qid: self.get_user_results(user_id, qid)
            for qid in self.user_answers.get(user_id, {}).keys()
        }
    
    def export_results(self, user_id: str) -> Dict:
        """导出所有结果用于构建画像"""
        all_results = self.get_all_results(user_id)
        
        # 转换为建模格式
        questionnaire_results = {}
        for qid, results in all_results.items():
            dimension_avg = results.get("dimension_avg", {})
            answers = []
            for dim, score in dimension_avg.items():
                answers.append({
                    "dimension": dim,
                    "score": score,
                    "count": len([
                        a for a in results["raw_answers"]
                        if self._get_question(qid, a["question_id"]) and
                        self._get_question(qid, a["question_id"]).dimension == dim
                    ])
                })
            questionnaire_results[qid] = answers
        
        return questionnaire_results
    
    def save_progress(self, path: str):
        """保存进度"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.user_answers, f, ensure_ascii=False, indent=2)
    
    def load_progress(self, path: str):
        """加载进度"""
        with open(path, "r", encoding="utf-8") as f:
            self.user_answers = json.load(f)


# 测试
if __name__ == "__main__":
    engine = QuestionnaireEngine()
    
    print("=== 可用问卷 ===")
    for q in engine.get_all_questionnaires():
        print(f"- {q.name} ({q.id}): {len(q.questions)} 题, 约{q.estimated_time}分钟")
    
    print("\n=== 问卷内容示例 ===")
    bf = engine.get_questionnaire("big_five")
    for q in bf.questions[:3]:
        print(f"[{q.id}] {q.text}")
        if q.options:
            print(f"   选项: {q.options}")
        else:
            print(f"   量表: {q.scale_range}")
