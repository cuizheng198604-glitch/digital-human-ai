# -*- coding: utf-8 -*-
"""
Digital Human AI - LLM 引擎
支持 OpenAI / Anthropic / 本地模型
"""
import os
import json
from typing import List, Dict, Optional, Any
from config.settings import LLM_CONFIG


class LLMEngine:
    """LLM 引擎封装"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or LLM_CONFIG
        self.provider = self.config.get("provider", "openai")
        self.model = self.config.get("model", "gpt-4o-mini")
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化 LLM 客户端"""
        if self.provider == "openai":
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.config.get("api_key") or os.getenv("OPENAI_API_KEY"),
                    base_url=self.config.get("base_url") or "https://api.openai.com/v1",
                )
            except ImportError:
                print("Warning: openai package not installed")
                self.client = None
        
        elif self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                self.client = Anthropic(
                    api_key=self.config.get("api_key") or os.getenv("ANTHROPIC_API_KEY"),
                )
            except ImportError:
                print("Warning: anthropic package not installed")
                self.client = None
        
        elif self.provider == "local":
            # 本地模型 (如 LLaMA, Qwen)
            self.client = self._init_local_client()
    
    def _init_local_client(self):
        """初始化本地模型客户端"""
        # TODO: 支持 Ollama, vLLM 等本地部署
        return None
    
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """
        对话生成
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            **kwargs: 额外参数 (temperature, max_tokens 等)
        
        Returns:
            生成的文本回复
        """
        if not self.client:
            return self._mock_response(messages)
        
        temperature = kwargs.get("temperature", self.config.get("temperature", 0.7))
        max_tokens = kwargs.get("max_tokens", self.config.get("max_tokens", 2000))
        
        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content
            
            elif self.provider == "anthropic":
                # 构建 Anthropic 格式的消息
                system = ""
                anthropic_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        system = msg["content"]
                    else:
                        anthropic_messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
                
                response = self.client.messages.create(
                    model=self.model,
                    system=system,
                    messages=anthropic_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.content[0].text
            
        except Exception as e:
            print(f"LLM API Error: {e}")
            return self._mock_response(messages)
        
        return ""
    
    def _mock_response(self, messages: List[Dict]) -> str:
        """模拟回复 (当没有 API Key 时)"""
        last_message = messages[-1]["content"] if messages else ""
        
        mock_responses = [
            f"这是一个模拟回复。您说的是：「{last_message[:20]}...」",
            f"我理解了您的意思。关于「{last_message[:15]}...」这个话题，",
            "抱歉，当前没有配置 LLM API Key，这是一个占位回复。",
        ]
        
        return mock_responses[0]
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        文本向量化
        
        Args:
            texts: 文本列表
        
        Returns:
            向量列表
        """
        if not self.client or self.provider != "openai":
            # 返回随机向量作为占位
            dimension = self.config.get("embedding_model", "text-embedding-3-small")
            dim_map = {
                "text-embedding-3-small": 1536,
                "text-embedding-3-large": 3072,
                "text-embedding-ada-002": 1536,
            }
            dim = dim_map.get(dimension, 1536)
            import random
            return [[random.random() for _ in range(dim)] for _ in texts]
        
        try:
            response = self.client.embeddings.create(
                model=self.config.get("embedding_model", "text-embedding-3-small"),
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"Embedding Error: {e}")
            return []
    
    def get_token_count(self, text: str) -> int:
        """估算 token 数量"""
        # 简单估算: 中文约 2 字符 = 1 token, 英文约 4 字符 = 1 token
        return len(text) // 2


# 全局单例
_llm_engine = None

def get_llm_engine() -> LLMEngine:
    """获取 LLM 引擎单例"""
    global _llm_engine
    if _llm_engine is None:
        _llm_engine = LLMEngine()
    return _llm_engine
