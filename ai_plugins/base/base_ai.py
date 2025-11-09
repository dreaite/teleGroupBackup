from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseAI(ABC):
    """AI服务的基础抽象类"""
    
    @abstractmethod
    def chat(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        发送消息并获取AI回复
        
        Args:
            message: 用户发送的消息
            history: 可选的对话历史记录，格式为[{"role": "user", "content": "消息"}, {"role": "assistant", "content": "回复"}]
            
        Returns:
            AI的回复文本
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """获取AI服务的名称"""
        pass