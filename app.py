"""
企业微信智能机器人 Flask 应用
处理企业微信回调消息，集成AI对话服务
"""
from flask import Flask, request, make_response
import logging

from config import Config
from wecom.crypto import WXBizMsgCrypt
from wecom.message import MessageHandler, WeChatMessage
from ai.chat import ChatService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)

# 初始化组件
crypto: WXBizMsgCrypt = None
message_handler: MessageHandler = None
chat_service: ChatService = None


def init_app():
    """初始化应用组件"""
    global crypto, message_handler, chat_service
    
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"配置验证失败: {e}")
        raise
    
    crypto = WXBizMsgCrypt(
        token=Config.WECOM_TOKEN,
        encoding_aes_key=Config.WECOM_ENCODING_AES_KEY,
        corp_id=Config.WECOM_CORP_ID
    )
    
    message_handler = MessageHandler()
    chat_service = ChatService()
    
    logger.info("应用组件初始化完成")


@app.route("/wecom/callback", methods=["GET", "POST"])
def wecom_callback():
    """
    企业微信回调接口
    
    GET: 验证URL有效性
    POST: 接收消息
    """
    # 获取公共参数
    msg_signature = request.args.get("msg_signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")
    
    if request.method == "GET":
        # URL验证
        echostr = request.args.get("echostr", "")
        logger.info(f"收到URL验证请求: timestamp={timestamp}, nonce={nonce}")
        
        ret, reply_echostr = crypto.verify_url(msg_signature, timestamp, nonce, echostr)
        
        if ret == WXBizMsgCrypt.WXBizMsgCrypt_OK:
            logger.info("URL验证成功")
            return reply_echostr
        else:
            logger.error(f"URL验证失败, 错误码: {ret}")
            return "验证失败", 403
    
    else:
        # 接收消息
        post_data = request.data.decode("utf-8")
        logger.info(f"收到消息回调: timestamp={timestamp}, nonce={nonce}")
        
        # 解密消息
        ret, xml_content = crypto.decrypt_msg(post_data, msg_signature, timestamp, nonce)
        
        if ret != WXBizMsgCrypt.WXBizMsgCrypt_OK:
            logger.error(f"消息解密失败, 错误码: {ret}")
            return "解密失败", 400
        
        # 解析消息
        msg = message_handler.parse_message(xml_content)
        if msg is None:
            logger.error("消息解析失败")
            return "解析失败", 400
        
        logger.info(f"收到消息: from={msg.from_user_name}, type={msg.msg_type}, content={msg.content[:50] if msg.content else ''}")
        
        # 只处理文本消息
        if msg.msg_type != "text":
            logger.info(f"忽略非文本消息: {msg.msg_type}")
            return "success"
        
        # 调用AI服务处理消息
        try:
            ai_reply = chat_service.chat(
                session_id=msg.from_user_name,
                user_input=msg.content
            )
            logger.info(f"AI回复: {ai_reply[:50]}...")
        except Exception as e:
            logger.error(f"AI服务调用失败: {e}")
            ai_reply = "抱歉，服务暂时不可用，请稍后再试。"
        
        # 构建回复消息
        reply_xml = message_handler.build_text_reply(
            to_user=msg.from_user_name,
            from_user=msg.to_user_name,
            content=ai_reply
        )
        
        # 加密回复消息
        ret, encrypted_reply = crypto.encrypt_msg(reply_xml, nonce, timestamp)
        
        if ret != WXBizMsgCrypt.WXBizMsgCrypt_OK:
            logger.error(f"回复消息加密失败, 错误码: {ret}")
            # 如果被动回复失败，尝试主动发送
            message_handler.send_text_message(msg.from_user_name, ai_reply)
            return "success"
        
        response = make_response(encrypted_reply)
        response.headers["Content-Type"] = "application/xml"
        return response


@app.route("/health", methods=["GET"])
def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "wecom-bot"}


@app.route("/session/<user_id>", methods=["GET"])
def get_session_info(user_id: str):
    """获取用户会话信息"""
    if chat_service is None:
        return {"error": "服务未初始化"}, 500
    
    info = chat_service.get_session_info(user_id)
    return info


@app.route("/session/<user_id>", methods=["DELETE"])
def clear_session(user_id: str):
    """清除用户会话历史"""
    if chat_service is None:
        return {"error": "服务未初始化"}, 500
    
    chat_service.history.clear_history(user_id)
    return {"status": "ok", "message": f"用户 {user_id} 的会话历史已清除"}


# 应用启动时初始化
with app.app_context():
    try:
        init_app()
    except Exception as e:
        logger.warning(f"应用初始化警告（如果是开发环境可忽略）: {e}")


if __name__ == "__main__":
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )

