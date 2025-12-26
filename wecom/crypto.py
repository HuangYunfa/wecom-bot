"""
企业微信消息加解密模块
参考文档: https://work.weixin.qq.com/api/doc/90000/90135/90968
"""
import base64
import hashlib
import random
import socket
import struct
import time
import xml.etree.ElementTree as ET
from typing import Tuple, Optional

from Crypto.Cipher import AES


class WXBizMsgCrypt:
    """企业微信消息加解密类"""
    
    # 错误码定义
    WXBizMsgCrypt_OK = 0
    WXBizMsgCrypt_ValidateSignature_Error = -40001
    WXBizMsgCrypt_ParseXml_Error = -40002
    WXBizMsgCrypt_ComputeSignature_Error = -40003
    WXBizMsgCrypt_IllegalAesKey = -40004
    WXBizMsgCrypt_ValidateCorpid_Error = -40005
    WXBizMsgCrypt_EncryptAES_Error = -40006
    WXBizMsgCrypt_DecryptAES_Error = -40007
    WXBizMsgCrypt_IllegalBuffer = -40008
    WXBizMsgCrypt_EncodeBase64_Error = -40009
    WXBizMsgCrypt_DecodeBase64_Error = -40010
    WXBizMsgCrypt_GenReturnXml_Error = -40011
    
    def __init__(self, token: str, encoding_aes_key: str, corp_id: str):
        """
        初始化加解密类
        
        Args:
            token: 企业微信后台配置的Token
            encoding_aes_key: 企业微信后台配置的EncodingAESKey
            corp_id: 企业ID
        """
        self.token = token
        self.corp_id = corp_id
        
        try:
            self.aes_key = base64.b64decode(encoding_aes_key + "=")
            if len(self.aes_key) != 32:
                raise ValueError("Invalid AES key length")
        except Exception:
            raise ValueError("EncodingAESKey 无效")
    
    def _get_signature(self, timestamp: str, nonce: str, encrypt: str) -> str:
        """计算签名"""
        try:
            sort_list = [self.token, timestamp, nonce, encrypt]
            sort_list.sort()
            sha = hashlib.sha1()
            sha.update("".join(sort_list).encode("utf-8"))
            return sha.hexdigest()
        except Exception:
            return ""
    
    def _pkcs7_encode(self, text: bytes) -> bytes:
        """PKCS7填充"""
        block_size = 32
        text_length = len(text)
        amount_to_pad = block_size - (text_length % block_size)
        if amount_to_pad == 0:
            amount_to_pad = block_size
        pad = chr(amount_to_pad).encode()
        return text + pad * amount_to_pad
    
    def _pkcs7_decode(self, decrypted: bytes) -> bytes:
        """PKCS7去填充"""
        pad = decrypted[-1]
        if pad < 1 or pad > 32:
            pad = 0
        return decrypted[:-pad]
    
    def _encrypt(self, text: str) -> Tuple[int, Optional[str]]:
        """对明文进行加密"""
        try:
            text = text.encode("utf-8")
            # 16字节随机字符串
            random_str = str(random.randint(1000000000000000, 9999999999999999)).encode("utf-8")
            # 网络字节序
            text_length = struct.pack("I", socket.htonl(len(text)))
            # 拼接
            text = random_str + text_length + text + self.corp_id.encode("utf-8")
            # 填充
            text = self._pkcs7_encode(text)
            # 加密
            cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
            encrypted = cipher.encrypt(text)
            return self.WXBizMsgCrypt_OK, base64.b64encode(encrypted).decode("utf-8")
        except Exception:
            return self.WXBizMsgCrypt_EncryptAES_Error, None
    
    def _decrypt(self, text: str) -> Tuple[int, Optional[str]]:
        """对密文进行解密"""
        try:
            cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
            decrypted = cipher.decrypt(base64.b64decode(text))
            decrypted = self._pkcs7_decode(decrypted)
            
            # 去掉16字节随机字符串
            content = decrypted[16:]
            # 获取消息长度
            xml_length = socket.ntohl(struct.unpack("I", content[:4])[0])
            # 获取消息内容
            xml_content = content[4:xml_length + 4].decode("utf-8")
            # 获取corpid
            from_corp_id = content[xml_length + 4:].decode("utf-8")
            
            if from_corp_id != self.corp_id:
                return self.WXBizMsgCrypt_ValidateCorpid_Error, None
            
            return self.WXBizMsgCrypt_OK, xml_content
        except Exception:
            return self.WXBizMsgCrypt_DecryptAES_Error, None
    
    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> Tuple[int, Optional[str]]:
        """
        验证URL有效性（用于配置回调URL时的验证）
        
        Args:
            msg_signature: 签名
            timestamp: 时间戳
            nonce: 随机数
            echostr: 加密的随机字符串
        
        Returns:
            (错误码, 解密后的echostr或None)
        """
        signature = self._get_signature(timestamp, nonce, echostr)
        if signature != msg_signature:
            return self.WXBizMsgCrypt_ValidateSignature_Error, None
        
        ret, reply_echostr = self._decrypt(echostr)
        return ret, reply_echostr
    
    def decrypt_msg(self, post_data: str, msg_signature: str, timestamp: str, nonce: str) -> Tuple[int, Optional[str]]:
        """
        解密企业微信发送的消息
        
        Args:
            post_data: 收到的POST数据（XML格式）
            msg_signature: 签名
            timestamp: 时间戳
            nonce: 随机数
        
        Returns:
            (错误码, 解密后的XML消息或None)
        """
        try:
            root = ET.fromstring(post_data)
            encrypt = root.find("Encrypt")
            if encrypt is None:
                return self.WXBizMsgCrypt_ParseXml_Error, None
            encrypt_text = encrypt.text
        except Exception:
            return self.WXBizMsgCrypt_ParseXml_Error, None
        
        signature = self._get_signature(timestamp, nonce, encrypt_text)
        if signature != msg_signature:
            return self.WXBizMsgCrypt_ValidateSignature_Error, None
        
        ret, xml_content = self._decrypt(encrypt_text)
        return ret, xml_content
    
    def encrypt_msg(self, reply_msg: str, nonce: str, timestamp: Optional[str] = None) -> Tuple[int, Optional[str]]:
        """
        加密回复消息
        
        Args:
            reply_msg: 回复的消息内容（XML格式）
            nonce: 随机数
            timestamp: 时间戳（可选，默认使用当前时间）
        
        Returns:
            (错误码, 加密后的XML消息或None)
        """
        if timestamp is None:
            timestamp = str(int(time.time()))
        
        ret, encrypt = self._encrypt(reply_msg)
        if ret != self.WXBizMsgCrypt_OK:
            return ret, None
        
        signature = self._get_signature(timestamp, nonce, encrypt)
        
        resp_xml = f"""<xml>
<Encrypt><![CDATA[{encrypt}]]></Encrypt>
<MsgSignature><![CDATA[{signature}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>"""
        
        return self.WXBizMsgCrypt_OK, resp_xml

