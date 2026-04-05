# -*- coding: utf-8 -*-
"""
Digital Human AI - 社交媒体数据采集模块
"""
import asyncio
from typing import Dict, List, Optional
from crawler.crawler_mvp import CrawlerManager, DataAnalyzer, UserProfile, Post


class SocialMediaCollector:
    """社交媒体数据采集器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.crawler_manager = CrawlerManager(self.config.get("crawler", {}))
        self.analyzer = DataAnalyzer()
    
    async def collect_user_data(
        self,
        platform: str,
        username: str,
        posts_limit: int = 100
    ) -> Optional[Dict]:
        """
        采集用户社交媒体数据
        
        Args:
            platform: 平台 (twitter, weibo)
            username: 用户名
            posts_limit: 帖子数量
        
        Returns:
            用户数据和特征分析
        """
        # 采集数据
        profile = await self.crawler_manager.crawl_user(
            platform=platform,
            username=username,
            include_posts=True,
            posts_limit=posts_limit
        )
        
        if not profile:
            return None
        
        # 分析数据
        analysis = {}
        if profile.posts:
            analysis = self.analyzer.analyze_posts(profile.posts)
        
        return {
            "profile": profile,
            "analysis": analysis,
            "raw_posts": [p.to_dict() for p in profile.posts],
        }
    
    async def collect_multiple_users(
        self,
        targets: List[Dict]
    ) -> List[Dict]:
        """
        并行采集多个用户
        
        Args:
            targets: [{"platform": "twitter", "username": "xxx"}, ...]
        
        Returns:
            用户数据列表
        """
        results = await self.crawler_manager.crawl_multiple_users(targets)
        
        analyzed_results = []
        for profile in results:
            analysis = {}
            if profile.posts:
                analysis = self.analyzer.analyze_posts(profile.posts)
            
            analyzed_results.append({
                "profile": profile,
                "analysis": analysis,
            })
        
        return analyzed_results
    
    def extract_personality_features(self, analysis: Dict) -> Dict:
        """
        从社交媒体分析结果中提取人格特征
        
        用于补充问卷数据构建更完整的用户画像
        """
        features = {
            "social_metrics": {},
            "personality_signals": {},
            "interest_signals": [],
            "sentiment_signals": {},
        }
        
        if not analysis:
            return features
        
        # 社交指标
        stats = analysis.get("stats", {})
        features["social_metrics"] = {
            "posting_frequency": stats.get("posting_frequency", "unknown"),
            "avg_engagement": stats.get("avg_likes", 0) + stats.get("avg_reposts", 0),
            "total_posts": stats.get("total_posts", 0),
            "most_active_hour": stats.get("most_active_hour", 12),
        }
        
        # 人格信号
        personality = analysis.get("personality_tendencies", {})
        features["personality_signals"] = personality
        
        # 兴趣信号
        features["interest_signals"] = analysis.get("interests", [])
        
        # 情感信号
        features["sentiment_signals"] = analysis.get("sentiment", {})
        
        return features
    
    def generate_personality_questionnaire_boost(
        self,
        social_features: Dict
    ) -> Dict[str, List[Dict]]:
        """
        根据社交媒体特征，生成针对性的问卷题目权重
        
        用于在问卷中加强对已识别特征的测量
        """
        boosts = {}
        
        # 人格信号权重调整
        personality = social_features.get("personality_signals", {})
        for dimension, score in personality.items():
            if score > 0.6:  # 高倾向
                boosts[f"personality_{dimension}"] = {
                    "weight": 1.5,  # 提高权重
                    "direction": "confirm"  # 确认该特征
                }
            elif score < 0.3:  # 低倾向
                boosts[f"personality_{dimension}"] = {
                    "weight": 1.2,
                    "direction": "explore"  # 探索该特征
                }
        
        return boosts


# 测试
if __name__ == "__main__":
    async def test():
        print("=" * 50)
        print("社交媒体数据采集测试")
        print("=" * 50)
        
        collector = SocialMediaCollector()
        
        # 测试采集
        print("\n采集 Twitter 用户数据...")
        result = await collector.collect_user_data(
            platform="twitter",
            username="test_user",
            posts_limit=20
        )
        
        if result:
            profile = result["profile"]
            analysis = result["analysis"]
            
            print(f"\n用户: {profile.username}")
            print(f"粉丝: {profile.followers}")
            print(f"采集帖子: {len(profile.posts)}")
            
            print("\n分析结果:")
            print(f"- 人格倾向: {analysis.get('personality_tendencies', {})}")
            print(f"- 兴趣领域: {analysis.get('interests', [])}")
            
            # 提取特征
            features = collector.extract_personality_features(analysis)
            print(f"\n提取的人格特征:")
            print(f"- 社交指标: {features['social_metrics']}")
            print(f"- 兴趣信号: {features['interest_signals']}")
            
            # 生成问卷权重
            boosts = collector.generate_personality_questionnaire_boost(features)
            print(f"\n问卷权重调整: {boosts}")
        
        print("\n" + "=" * 50)
    
    asyncio.run(test())
