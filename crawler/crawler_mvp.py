# -*- coding: utf-8 -*-
"""
Crawler MVP - 社交媒体数据采集器
支持 Twitter/X, 微博, 知乎 等平台
"""
import os
import re
import json
import time
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib


@dataclass
class Post:
    """帖子/推文"""
    platform: str
    post_id: str
    author_id: str
    author_name: str
    content: str
    timestamp: str
    likes: int = 0
    reposts: int = 0
    comments: int = 0
    url: str = ""
    media_urls: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class UserProfile:
    """用户画像数据"""
    platform: str
    user_id: str
    username: str
    display_name: str
    bio: str = ""
    followers: int = 0
    following: int = 0
    posts_count: int = 0
    location: str = ""
    website: str = ""
    verified: bool = False
    created_at: str = ""
    avatar_url: str = ""
    posts: List[Post] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


class BaseCrawler(ABC):
    """爬虫基类"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.name = self.__class__.__name__
        self.rate_limit = self.config.get("rate_limit", 1)  # 请求间隔(秒)
        self.timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
    
    @abstractmethod
    async def get_user_profile(self, username: str) -> Optional[UserProfile]:
        """获取用户资料"""
        pass
    
    @abstractmethod
    async def get_user_posts(self, username: str, limit: int = 100) -> List[Post]:
        """获取用户帖子"""
        pass
    
    def _rate_limit(self):
        """速率限制"""
        time.sleep(self.rate_limit)
    
    def _generate_id(self, *args) -> str:
        """生成唯一ID"""
        content = "_".join(str(a) for a in args)
        return hashlib.md5(content.encode()).hexdigest()[:12]


class TwitterCrawler(BaseCrawler):
    """Twitter/X 爬虫"""
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.api_key = self.config.get("twitter_api_key", os.getenv("TWITTER_API_KEY"))
        self.api_secret = self.config.get("twitter_api_secret", os.getenv("TWITTER_API_SECRET"))
        self.access_token = self.config.get("twitter_access_token", os.getenv("TWITTER_ACCESS_TOKEN"))
        self.bearer_token = self.config.get("twitter_bearer_token", os.getenv("TWITTER_BEARER_TOKEN"))
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化 Twitter API 客户端"""
        if self.bearer_token:
            try:
                import requests
                self.client = requests.Session()
                self.client.headers.update({"Authorization": f"Bearer {self.bearer_token}"})
                self.client.timeout = self.timeout
            except ImportError:
                print("Warning: requests library not installed")
    
    async def get_user_profile(self, username: str) -> Optional[UserProfile]:
        """获取 Twitter 用户资料"""
        if not self.client:
            return self._mock_profile(username)
        
        url = f"https://api.twitter.com/2/users/by/username/{username}"
        
        for retry in range(self.max_retries):
            try:
                self._rate_limit()
                response = self.client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    user_data = data.get("data", {})
                    
                    return UserProfile(
                        platform="twitter",
                        user_id=user_data.get("id", ""),
                        username=username,
                        display_name=user_data.get("name", ""),
                        bio=user_data.get("description", ""),
                        followers=user_data.get("public_metrics", {}).get("followers_count", 0),
                        following=user_data.get("public_metrics", {}).get("following_count", 0),
                        posts_count=user_data.get("public_metrics", {}).get("tweet_count", 0),
                        verified=user_data.get("verified", False),
                        created_at=user_data.get("created_at", ""),
                        avatar_url=user_data.get("profile_image_url", ""),
                    )
                elif response.status_code == 429:
                    # Rate limited
                    time.sleep(60)
                else:
                    return None
            
            except Exception as e:
                if retry < self.max_retries - 1:
                    time.sleep(2 ** retry)
                    continue
                print(f"Twitter API Error: {e}")
        
        return None
    
    async def get_user_posts(self, username: str, limit: int = 100) -> List[Post]:
        """获取 Twitter 用户推文"""
        if not self.client:
            return self._mock_posts(username, limit)
        
        # 先获取用户ID
        profile = await self.get_user_profile(username)
        if not profile or not profile.user_id:
            return []
        
        user_id = profile.user_id
        url = f"https://api.twitter.com/2/users/{user_id}/tweets"
        
        params = {
            "max_results": min(limit, 100),
            "tweet.fields": "created_at,public_metrics,attachments,entities",
            "expansions": "author_id",
        }
        
        posts = []
        remaining = limit
        
        while remaining > 0:
            params["max_results"] = min(remaining, 100)
            
            for retry in range(self.max_retries):
                try:
                    self._rate_limit()
                    response = self.client.get(url, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        tweets = data.get("data", [])
                        
                        for tweet in tweets:
                            metrics = tweet.get("public_metrics", {})
                            posts.append(Post(
                                platform="twitter",
                                post_id=tweet.get("id", ""),
                                author_id=tweet.get("author_id", ""),
                                author_name=username,
                                content=tweet.get("text", ""),
                                timestamp=tweet.get("created_at", ""),
                                likes=metrics.get("like_count", 0),
                                reposts=metrics.get("retweet_count", 0),
                                comments=metrics.get("reply_count", 0),
                                url=f"https://twitter.com/{username}/status/{tweet.get('id')}",
                            ))
                        
                        remaining -= len(tweets)
                        
                        # 检查是否有下一页
                        meta = data.get("meta", {})
                        next_token = meta.get("next_token")
                        if not next_token or len(tweets) == 0:
                            return posts
                        params["pagination_token"] = next_token
                        break
                    
                    elif response.status_code == 429:
                        time.sleep(60)
                    else:
                        return posts
                
                except Exception as e:
                    if retry < self.max_retries - 1:
                        time.sleep(2 ** retry)
                        continue
                    print(f"Twitter API Error: {e}")
        
        return posts
    
    def _mock_profile(self, username: str) -> UserProfile:
        """模拟用户资料"""
        return UserProfile(
            platform="twitter",
            user_id=self._generate_id("twitter", username),
            username=username,
            display_name=f"@{username}",
            bio="这是模拟的用户简介",
            followers=1000,
            following=500,
            posts_count=200,
            verified=False,
        )
    
    def _mock_posts(self, username: str, limit: int) -> List[Post]:
        """模拟推文数据"""
        posts = []
        topics = [
            "今天天气真好，适合出门散步",
            "刚看完一本书，有很多感悟想分享",
            "工作中遇到了一些挑战，正在努力解决",
            "学习新技能的第三天，感觉进步明显",
            "和朋友聚会很开心，回忆满满",
        ]
        
        for i in range(min(limit, 10)):
            posts.append(Post(
                platform="twitter",
                post_id=self._generate_id("twitter", username, i),
                author_id=self._generate_id("twitter", username),
                author_name=username,
                content=topics[i % len(topics)],
                timestamp=datetime.now().isoformat(),
                likes=(i + 1) * 10,
                reposts=i * 5,
                comments=i * 2,
                url=f"https://twitter.com/{username}/status/{i+1}",
            ))
        
        return posts


class WeiboCrawler(BaseCrawler):
    """微博爬虫"""
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        # 微博API配置
        self.cookie = self.config.get("weibo_cookie", os.getenv("WEIBO_COOKIE"))
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Cookie": self.cookie or "",
        }
    
    async def get_user_profile(self, uid: str) -> Optional[UserProfile]:
        """获取微博用户资料"""
        # TODO: 实现微博API调用
        return UserProfile(
            platform="weibo",
            user_id=uid,
            username=uid,
            display_name=f"微博用户{uid[:6]}",
            bio="微博用户",
        )
    
    async def get_user_posts(self, uid: str, limit: int = 100) -> List[Post]:
        """获取微博帖子"""
        # TODO: 实现微博API调用
        return []


class CrawlerManager:
    """爬虫管理器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.crawlers: Dict[str, BaseCrawler] = {}
        self._init_crawlers()
    
    def _init_crawlers(self):
        """初始化爬虫"""
        # Twitter
        twitter_config = self.config.get("twitter", {})
        if twitter_config.get("enabled", True):
            self.crawlers["twitter"] = TwitterCrawler(twitter_config)
        
        # 微博
        weibo_config = self.config.get("weibo", {})
        if weibo_config.get("enabled", False):
            self.crawlers["weibo"] = WeiboCrawler(weibo_config)
    
    async def crawl_user(
        self,
        platform: str,
        username: str,
        include_posts: bool = True,
        posts_limit: int = 100
    ) -> Optional[UserProfile]:
        """
        采集用户数据
        
        Args:
            platform: 平台 (twitter, weibo, etc.)
            username: 用户名
            include_posts: 是否采集帖子
            posts_limit: 帖子数量限制
        
        Returns:
            UserProfile with posts
        """
        crawler = self.crawlers.get(platform)
        if not crawler:
            print(f"Crawler for {platform} not found")
            return None
        
        # 获取用户资料
        profile = await crawler.get_user_profile(username)
        if not profile:
            return None
        
        # 获取帖子
        if include_posts:
            posts = await crawler.get_user_posts(username, posts_limit)
            profile.posts = posts
            profile.metadata["posts_fetched"] = len(posts)
        
        return profile
    
    async def crawl_multiple_users(
        self,
        targets: List[Dict],
        max_workers: int = 3
    ) -> List[UserProfile]:
        """
        并行采集多个用户
        
        Args:
            targets: [{"platform": "twitter", "username": "xxx"}, ...]
            max_workers: 最大并发数
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.crawl_user,
                    t["platform"],
                    t["username"],
                    t.get("include_posts", True),
                    t.get("posts_limit", 100)
                ): t
                for t in targets
            }
            
            for future in as_completed(futures):
                target = futures[future]
                try:
                    profile = await future
                    if profile:
                        results.append(profile)
                except Exception as e:
                    print(f"Error crawling {target}: {e}")
        
        return results
    
    def save_profile(self, profile: UserProfile, path: str):
        """保存用户资料"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_profile(self, path: str) -> Optional[UserProfile]:
        """加载用户资料"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return UserProfile(**data)


class DataAnalyzer:
    """数据分析器 - 从采集的数据中提取特征"""
    
    def __init__(self):
        self.personality_keywords = {
            "openness": ["创新", "创意", "艺术", "哲学", "探索", "好奇", "想象"],
            "conscientiousness": ["计划", "组织", "目标", "完成", "责任", "效率", "自律"],
            "extraversion": ["社交", "聚会", "朋友", "活力", "能量", "开朗", "健谈"],
            "agreeableness": ["帮助", "合作", "理解", "信任", "同理心", "友善", "和谐"],
            "neuroticism": ["焦虑", "担心", "压力", "情绪", "敏感", "不安", "紧张"],
        }
    
    def analyze_posts(self, posts: List[Post]) -> Dict[str, Any]:
        """分析帖子内容，提取特征"""
        if not posts:
            return {}
        
        all_text = " ".join([p.content for p in posts])
        
        # 统计特征
        stats = {
            "total_posts": len(posts),
            "avg_likes": sum(p.likes for p in posts) / len(posts),
            "avg_reposts": sum(p.reposts for p in posts) / len(posts),
            "total_engagement": sum(p.likes + p.reposts + p.comments for p in posts),
            "most_active_hour": self._get_most_active_hour(posts),
            "posting_frequency": self._get_posting_frequency(posts),
        }
        
        # 人格倾向分析
        personality_tendencies = self._analyze_personality(all_text)
        
        # 兴趣领域分析
        interests = self._analyze_interests(all_text)
        
        # 情感分析
        sentiment = self._analyze_sentiment(all_text)
        
        return {
            "stats": stats,
            "personality_tendencies": personality_tendencies,
            "interests": interests,
            "sentiment": sentiment,
            "sample_posts": [p.content[:100] for p in posts[:5]],
        }
    
    def _get_most_active_hour(self, posts: List[Post]) -> int:
        """获取最活跃小时"""
        from collections import Counter
        hours = []
        for p in posts:
            try:
                dt = datetime.fromisoformat(p.timestamp.replace("Z", "+00:00"))
                hours.append(dt.hour)
            except:
                pass
        
        if hours:
            return Counter(hours).most_common(1)[0][0]
        return 12
    
    def _get_posting_frequency(self, posts: List[Post]) -> str:
        """获取发帖频率"""
        if len(posts) < 2:
            return "insufficient_data"
        
        try:
            timestamps = []
            for p in posts:
                try:
                    dt = datetime.fromisoformat(p.timestamp.replace("Z", "+00:00"))
                    timestamps.append(dt)
                except:
                    pass
            
            if len(timestamps) < 2:
                return "insufficient_data"
            
            timestamps.sort()
            days = (timestamps[-1] - timestamps[0]).days
            
            if days == 0:
                return "very_high"
            posts_per_day = len(timestamps) / max(days, 1)
            
            if posts_per_day > 5:
                return "high"
            elif posts_per_day > 1:
                return "medium"
            elif posts_per_day > 0.1:
                return "low"
            return "very_low"
        except:
            return "unknown"
    
    def _analyze_personality(self, text: str) -> Dict[str, float]:
        """分析人格倾向"""
        scores = {}
        text_lower = text.lower()
        
        for dimension, keywords in self.personality_keywords.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            scores[dimension] = min(count / len(keywords), 1.0)
        
        return scores
    
    def _analyze_interests(self, text: str) -> List[str]:
        """分析兴趣领域"""
        interest_keywords = {
            "科技": ["AI", "技术", "编程", "代码", "软件", "互联网", "产品"],
            "金融": ["投资", "股票", "基金", "理财", "经济", "财富"],
            "体育": ["足球", "篮球", "跑步", "健身", "运动", "比赛"],
            "娱乐": ["电影", "音乐", "游戏", "综艺", "明星", "追剧"],
            "旅行": ["旅游", "旅行", "目的地", "酒店", "机票", "攻略"],
            "美食": ["餐厅", "美食", "烹饪", "食谱", "吃货", "探店"],
            "教育": ["学习", "读书", "课程", "培训", "知识", "技能"],
        }
        
        interests = []
        text_lower = text.lower()
        
        for category, keywords in interest_keywords.items():
            if any(kw in text_lower for kw in keywords):
                interests.append(category)
        
        return interests
    
    def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """情感分析"""
        positive_words = ["好", "棒", "喜欢", "开心", "快乐", "幸福", "满意", "感谢", "赞"]
        negative_words = ["坏", "差", "讨厌", "难过", "痛苦", "失望", "糟糕", "问题", "困难"]
        
        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)
        
        total = pos_count + neg_count
        if total == 0:
            return {"positive": 0.5, "negative": 0.5}
        
        return {
            "positive": pos_count / total,
            "negative": neg_count / total,
        }


# 测试
if __name__ == "__main__":
    async def main():
        print("=" * 50)
        print("Crawler MVP - 测试")
        print("=" * 50)
        
        # 创建爬虫管理器
        manager = CrawlerManager()
        
        # 采集 Twitter 用户
        print("\n[1] 采集 Twitter 用户...")
        profile = await manager.crawl_user(
            platform="twitter",
            username="example_user",
            include_posts=True,
            posts_limit=10
        )
        
        if profile:
            print(f"用户名: {profile.username}")
            print(f"显示名: {profile.display_name}")
            print(f"简介: {profile.bio}")
            print(f"粉丝: {profile.followers}")
            print(f"发帖数: {profile.posts_count}")
            print(f"\n采集到 {len(profile.posts)} 条推文")
        
        # 分析数据
        print("\n[2] 分析数据...")
        if profile and profile.posts:
            analyzer = DataAnalyzer()
            analysis = analyzer.analyze_posts(profile.posts)
            
            print(f"统计: {analysis.get('stats', {})}")
            print(f"人格倾向: {analysis.get('personality_tendencies', {})}")
            print(f"兴趣领域: {analysis.get('interests', [])}")
            print(f"情感: {analysis.get('sentiment', {})}")
        
        # 保存数据
        print("\n[3] 保存数据...")
        if profile:
            save_path = Path(__file__).parent.parent / "data" / f"{profile.username}_profile.json"
            manager.save_profile(profile, str(save_path))
            print(f"数据已保存到: {save_path}")
        
        print("\n" + "=" * 50)
        print("测试完成!")
        print("=" * 50)
    
    asyncio.run(main())
