"""
企业微信消息处理模块
参考文档: https://work.weixin.qq.com/api/doc/90000/90135/90238
"""
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional
import requests

from config import Config


@dataclass
class WeChatMessage:
    """企业微信消息数据类"""
    to_user_name: str  # 企业微信CorpID
    from_user_name: str  # 发送消息的成员UserID
    create_time: int  # 消息创建时间戳
    msg_type: str  # 消息类型
    content: str  # 文本消息内容
    msg_id: str  # 消息ID
    agent_id: str  # 企业应用ID


class MessageHandler:
    """消息处理器"""
    
    def __init__(self):
        self._access_token = None
        self._token_expires_at = 0
    
    @staticmethod
    def parse_message(xml_data: str) -> Optional[WeChatMessage]:
        """
        解析XML消息
        
        Args:
            xml_data: 解密后的XML消息
        
        Returns:
            WeChatMessage对象或None
        """
        try:
            root = ET.fromstring(xml_data)
            
            to_user_name = root.find("ToUserName")
            from_user_name = root.find("FromUserName")
            create_time = root.find("CreateTime")
            msg_type = root.find("MsgType")
            content = root.find("Content")
            msg_id = root.find("MsgId")
            agent_id = root.find("AgentID")
            
            return WeChatMessage(
                to_user_name=to_user_name.text if to_user_name is not None else "",
                from_user_name=from_user_name.text if from_user_name is not None else "",
                create_time=int(create_time.text) if create_time is not None else 0,
                msg_type=msg_type.text if msg_type is not None else "",
                content=content.text if content is not None else "",
                msg_id=msg_id.text if msg_id is not None else "",
                agent_id=agent_id.text if agent_id is not None else ""
            )
        except Exception:
            return None
    
    @staticmethod
    def build_text_reply(to_user: str, from_user: str, content: str) -> str:
        """
        构建文本回复消息XML
        
        Args:
            to_user: 接收者
            from_user: 发送者
            content: 回复内容
        
        Returns:
            XML格式的回复消息
        """
        timestamp = int(time.time())
        return f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{timestamp}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""
    
    def get_access_token(self) -> Optional[str]:
        """
        获取企业微信access_token
        
        Returns:
            access_token或None
        """
        # 检查token是否过期
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {
            "corpid": Config.WECOM_CORP_ID,
            "corpsecret": Config.WECOM_SECRET
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get("errcode") == 0:
                self._access_token = data["access_token"]
                # 提前5分钟过期
                self._token_expires_at = time.time() + data["expires_in"] - 300
                return self._access_token
            else:
                print(f"获取access_token失败: {data}")
                return None
        except Exception as e:
            print(f"获取access_token异常: {e}")
            return None
    
    def send_text_message(self, user_id: str, content: str) -> bool:
        """
        主动发送文本消息给用户
        
        Args:
            user_id: 用户ID
            content: 消息内容
        
        Returns:
            是否发送成功
        """
        access_token = self.get_access_token()
        if not access_token:
            return False
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        data = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": Config.WECOM_AGENT_ID,
            "text": {
                "content": content
            },
            "safe": 0
        }
        
        try:
            resp = requests.post(url, json=data, timeout=10)
            result = resp.json()
            
            if result.get("errcode") == 0:
                return True
            else:
                print(f"发送消息失败: {result}")
                return False
        except Exception as e:
            print(f"发送消息异常: {e}")
            return False

