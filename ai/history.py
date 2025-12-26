"""
对话历史持久化模块
使用Redis存储对话历史
"""
import json
from typing import List, Optional
import redis

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, messages_from_dict, messages_to_dict
from config import Config


class ConversationHistory:
    """基于Redis的对话历史管理"""
    
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
    
    @property
    def redis_client(self) -> redis.Redis:
        """懒加载Redis客户端"""
        if self._redis_client is None:
            self._redis_client = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                password=Config.REDIS_PASSWORD or None,
                db=Config.REDIS_DB,
                decode_responses=True
            )
        return self._redis_client
    
    def _get_key(self, session_id: str) -> str:
        """生成Redis key"""
        return f"wecom:chat:history:{session_id}"
    
    def get_messages(self, session_id: str) -> List[BaseMessage]:
        """
        获取会话的历史消息
        
        Args:
            session_id: 会话ID（通常是用户ID）
        
        Returns:
            消息列表
        """
        key = self._get_key(session_id)
        try:
            data = self.redis_client.get(key)
            if data:
                messages_data = json.loads(data)
                return messages_from_dict(messages_data)
            return []
        except Exception as e:
            print(f"获取对话历史失败: {e}")
            return []
    
    def add_message(self, session_id: str, message: BaseMessage) -> None:
        """
        添加消息到历史记录
        
        Args:
            session_id: 会话ID
            message: 消息对象
        """
        key = self._get_key(session_id)
        try:
            messages = self.get_messages(session_id)
            messages.append(message)
            
            # 限制历史消息数量
            if len(messages) > Config.CONVERSATION_MAX_HISTORY:
                messages = messages[-Config.CONVERSATION_MAX_HISTORY:]
            
            # 序列化并保存
            messages_data = messages_to_dict(messages)
            self.redis_client.setex(
                key,
                Config.CONVERSATION_TTL_SECONDS,
                json.dumps(messages_data)
            )
        except Exception as e:
            print(f"保存对话历史失败: {e}")
    
    def add_user_message(self, session_id: str, content: str) -> None:
        """添加用户消息"""
        self.add_message(session_id, HumanMessage(content=content))
    
    def add_ai_message(self, session_id: str, content: str) -> None:
        """添加AI回复消息"""
        self.add_message(session_id, AIMessage(content=content))
    
    def clear_history(self, session_id: str) -> None:
        """
        清除会话历史
        
        Args:
            session_id: 会话ID
        """
        key = self._get_key(session_id)
        try:
            self.redis_client.delete(key)
        except Exception as e:
            print(f"清除对话历史失败: {e}")
    
    def get_session_info(self, session_id: str) -> dict:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
        
        Returns:
            会话信息字典
        """
        key = self._get_key(session_id)
        try:
            ttl = self.redis_client.ttl(key)
            messages = self.get_messages(session_id)
            return {
                "session_id": session_id,
                "message_count": len(messages),
                "ttl_seconds": ttl if ttl > 0 else 0
            }
        except Exception as e:
            print(f"获取会话信息失败: {e}")
            return {
                "session_id": session_id,
                "message_count": 0,
                "ttl_seconds": 0
            }

