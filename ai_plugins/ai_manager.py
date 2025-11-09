from typing import Dict, List, Optional
import os
import importlib

from .base.base_ai import BaseAI
from .openai.openai_service import OpenAIService

class AIManager:
    """AI服务管理器，用于管理和选择不同的AI服务"""
    
    def __init__(self, default_service: str = "openai"):
        """
        初始化AI服务管理器
        
        Args:
            default_service: 默认使用的AI服务名称
        """
        self.services = {}
        self.default_service = default_service
        self.user_history = {}  # 用户会话历史 {user_id: [messages]}
        
        # 初始化服务
        self._init_services()
    
    def _init_services(self):
        """初始化可用的AI服务"""
        # 添加OpenAI服务
        try:
            self.services["openai"] = OpenAIService()
        except Exception as e:
            print(f"无法初始化OpenAI服务: {e}")
    
    def get_ai_service(self, service_name: Optional[str] = None) -> BaseAI:
        """
        获取AI服务实例
        
        Args:
            service_name: 服务名称，如果为空则使用默认服务
            
        Returns:
            AI服务实例
        """
        name = service_name or self.default_service
        if name not in self.services:
            raise ValueError(f"未找到名为 {name} 的AI服务")
        return self.services[name]
    
    def list_services(self) -> List[str]:
        """列出所有可用的AI服务名称"""
        return list(self.services.keys())
    
    def chat(self, user_id: str, message: str, service_name: Optional[str] = None) -> str:
        """
        发送消息到AI服务并获取回复
        
        Args:
            user_id: 用户ID，用于跟踪会话
            message: 用户消息
            service_name: 可选的服务名称，如果为空则使用默认服务
            
        Returns:
            AI的回复文本
        """
        service = self.get_ai_service(service_name)
        
        # 获取用户历史记录
        history = self.user_history.get(user_id, [])
        
        # 调用AI服务获取回复
        response = service.chat(message, history)
        
        # 更新历史记录
        if user_id not in self.user_history:
            self.user_history[user_id] = []
            
        # 添加当前对话到历史记录
        self.user_history[user_id].append({"role": "user", "content": message})
        self.user_history[user_id].append({"role": "assistant", "content": response})
        
        # 保持历史记录长度在合理范围内（这里限制为10轮对话）
        if len(self.user_history[user_id]) > 20:
            self.user_history[user_id] = self.user_history[user_id][-20:]
        
        return response
    
    def clear_history(self, user_id: str):
        """清除特定用户的对话历史"""
        if user_id in self.user_history:
            del self.user_history[user_id]