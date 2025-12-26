"""配置管理模块"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """应用配置类"""
    
    # 企业微信配置
    WECOM_CORP_ID = os.getenv("WECOM_CORP_ID", "")
    WECOM_AGENT_ID = os.getenv("WECOM_AGENT_ID", "")
    WECOM_SECRET = os.getenv("WECOM_SECRET", "")
    WECOM_TOKEN = os.getenv("WECOM_TOKEN", "")
    WECOM_ENCODING_AES_KEY = os.getenv("WECOM_ENCODING_AES_KEY", "")
    
    # DashScope 配置
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
    
    # Redis 配置
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    
    # Flask 配置
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    # AI 配置
    AI_MODEL = os.getenv("AI_MODEL", "qwen-turbo")
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", 2048))
    AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", 0.7))
    
    # 对话历史配置
    CONVERSATION_MAX_HISTORY = int(os.getenv("CONVERSATION_MAX_HISTORY", 20))
    CONVERSATION_TTL_SECONDS = int(os.getenv("CONVERSATION_TTL_SECONDS", 86400))
    
    @classmethod
    def validate(cls):
        """验证必要配置是否存在"""
        required_fields = [
            "WECOM_CORP_ID",
            "WECOM_SECRET", 
            "WECOM_TOKEN",
            "WECOM_ENCODING_AES_KEY",
            "DASHSCOPE_API_KEY"
        ]
        missing = []
        for field in required_fields:
            if not getattr(cls, field):
                missing.append(field)
        if missing:
            raise ValueError(f"缺少必要配置: {', '.join(missing)}")

