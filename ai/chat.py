"""
AI对话服务模块
支持通义千问（DashScope）和 DeepSeek（OpenAI兼容接口）
"""
import os
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from config import Config
from .history import ConversationHistory


def create_llm() -> BaseChatModel:
    """
    根据配置创建对应的 LLM 实例
    支持通义千问和 DeepSeek
    """
    model = Config.AI_MODEL.lower()
    
    # DeepSeek 模型（使用 OpenAI 兼容接口）
    if "deepseek" in model:
        from langchain_openai import ChatOpenAI
        
        return ChatOpenAI(
            model=Config.AI_MODEL,
            api_key=Config.DASHSCOPE_API_KEY,  # 复用这个配置存 DeepSeek API Key
            base_url="https://api.deepseek.com/v1",
            temperature=Config.AI_TEMPERATURE,
            max_tokens=Config.AI_MAX_TOKENS,
        )
    
    # 通义千问模型（qwen-turbo, qwen-plus, qwen-max 等）
    else:
        from langchain_community.chat_models import ChatTongyi
        
        os.environ["DASHSCOPE_API_KEY"] = Config.DASHSCOPE_API_KEY
        
        return ChatTongyi(
            model=Config.AI_MODEL,
            temperature=Config.AI_TEMPERATURE,
            max_tokens=Config.AI_MAX_TOKENS,
        )


class ChatService:
    """AI对话服务"""
    
    # 系统提示词
    SYSTEM_PROMPT = """你是一个专业、友好的企业智能客服助手。你的职责是：
1. 准确理解用户的问题并提供有帮助的回答
2. 保持回答简洁明了，避免冗长
3. 如果不确定答案，诚实地表达并建议用户咨询人工客服
4. 保持专业、礼貌的语气

请用中文回复用户的问题。"""
    
    def __init__(self):
        # 根据配置创建 LLM
        self.llm = create_llm()
        
        # 初始化对话历史管理器
        self.history = ConversationHistory()
        
        # 构建对话提示模板
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # 构建对话链
        self.chain = self.prompt | self.llm
    
    def chat(self, session_id: str, user_input: str) -> str:
        """
        处理用户对话
        
        Args:
            session_id: 会话ID（通常是用户ID）
            user_input: 用户输入
        
        Returns:
            AI回复内容
        """
        try:
            # 检查是否是清除历史命令
            if user_input.strip().lower() in ["清除历史", "清除记录", "重新开始", "/clear"]:
                self.history.clear_history(session_id)
                return "对话历史已清除，我们可以重新开始了！"
            
            # 获取历史消息
            history_messages = self.history.get_messages(session_id)
            
            # 调用AI生成回复
            response = self.chain.invoke({
                "history": history_messages,
                "input": user_input
            })
            
            ai_reply = response.content
            
            # 保存对话历史
            self.history.add_user_message(session_id, user_input)
            self.history.add_ai_message(session_id, ai_reply)
            
            return ai_reply
            
        except Exception as e:
            error_msg = f"AI服务异常: {str(e)}"
            print(error_msg)
            return "抱歉，我现在无法处理您的请求，请稍后再试或联系人工客服。"
    
    def get_session_info(self, session_id: str) -> dict:
        """获取会话信息"""
        return self.history.get_session_info(session_id)
