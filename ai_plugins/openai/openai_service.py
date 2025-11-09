from typing import List, Dict, Optional
import os
from openai import OpenAI
from dotenv import load_dotenv
from ..base.base_ai import BaseAI

# 加载环境变量
load_dotenv()

class OpenAIService(BaseAI):
    """OpenAI服务实现"""
    
    def __init__(self, model="o3-mini"):
        """
        初始化OpenAI服务
        
        Args:
            model: 使用的模型名称，默认为o3-mini
        """
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("没有找到OPENAI_API_KEY环境变量")
        
        self.client = OpenAI()
        self.model = model
    
    def chat(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        使用OpenAI进行对话
        
        Args:
            message: 用户消息
            history: 对话历史记录
            
        Returns:
            AI回复的文本
        """
        # 构建消息列表
        messages = []
        
        # 添加系统消息
        messages.append({"role": "system", "content": "You are a helpful assistant."})
        
        # 添加历史消息（如果有）
        if history:
            messages.extend(history)
        
        # 添加用户当前消息
        messages.append({"role": "user", "content": message})
        
        # 调用API
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"OpenAI服务出错: {str(e)}"
    
    def get_name(self) -> str:
        """获取服务名称"""
        return f"OpenAI ({self.model})"