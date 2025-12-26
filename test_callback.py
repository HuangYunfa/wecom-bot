"""
企业微信回调接口测试脚本
用于本地调试验证
"""
import hashlib
import time
import requests
from config import Config
from wecom.crypto import WXBizMsgCrypt

# 测试配置 - 请确保 .env 中已配置正确的值
TOKEN = Config.WECOM_TOKEN
ENCODING_AES_KEY = Config.WECOM_ENCODING_AES_KEY
CORP_ID = Config.WECOM_CORP_ID

BASE_URL = "http://127.0.0.1:5000"


def generate_signature(token: str, timestamp: str, nonce: str, encrypt: str = "") -> str:
    """生成签名"""
    sort_list = [token, timestamp, nonce]
    if encrypt:
        sort_list.append(encrypt)
    sort_list.sort()
    sha = hashlib.sha1()
    sha.update("".join(sort_list).encode("utf-8"))
    return sha.hexdigest()


def test_health():
    """测试健康检查接口"""
    print("=" * 50)
    print("测试健康检查接口")
    print("=" * 50)
    
    url = f"{BASE_URL}/health"
    print(f"GET {url}")
    
    resp = requests.get(url)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
    print()


def test_url_verify():
    """
    测试 URL 验证（模拟企业微信配置回调时的验证请求）
    注意：这需要正确的加密配置才能通过验证
    """
    print("=" * 50)
    print("测试 URL 验证 (GET)")
    print("=" * 50)
    
    # 创建加密器
    try:
        crypto = WXBizMsgCrypt(TOKEN, ENCODING_AES_KEY, CORP_ID)
    except Exception as e:
        print(f"加密器初始化失败: {e}")
        print("请检查 .env 中的 WECOM_TOKEN, WECOM_ENCODING_AES_KEY, WECOM_CORP_ID 配置")
        return
    
    # 模拟企业微信发送的验证请求
    timestamp = str(int(time.time()))
    nonce = "1234567890"
    
    # 加密 echostr（模拟企业微信发送的加密随机字符串）
    test_echostr = "test_echo_string_123"
    ret, encrypted_echostr = crypto._encrypt(test_echostr)
    
    if ret != 0:
        print(f"加密失败: {ret}")
        return
    
    # 生成签名
    msg_signature = generate_signature(TOKEN, timestamp, nonce, encrypted_echostr)
    
    url = f"{BASE_URL}/wecom/callback"
    params = {
        "msg_signature": msg_signature,
        "timestamp": timestamp,
        "nonce": nonce,
        "echostr": encrypted_echostr
    }
    
    print(f"GET {url}")
    print(f"Params: {params}")
    
    resp = requests.get(url, params=params)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
    
    if resp.text == test_echostr:
        print("[OK] URL 验证成功!")
    else:
        print("[FAIL] URL 验证失败")
    print()


def test_message_receive():
    """
    测试消息接收（模拟企业微信发送用户消息）
    """
    print("=" * 50)
    print("测试消息接收 (POST)")
    print("=" * 50)
    
    try:
        crypto = WXBizMsgCrypt(TOKEN, ENCODING_AES_KEY, CORP_ID)
    except Exception as e:
        print(f"加密器初始化失败: {e}")
        return
    
    timestamp = str(int(time.time()))
    nonce = "1234567890"
    
    # 构造用户发送的消息 XML
    user_msg = f"""<xml>
<ToUserName><![CDATA[{CORP_ID}]]></ToUserName>
<FromUserName><![CDATA[TestUser001]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[你好，请问有什么可以帮助你的？]]></Content>
<MsgId>1234567890123456</MsgId>
<AgentID>{Config.WECOM_AGENT_ID or '1000001'}</AgentID>
</xml>"""
    
    print(f"原始消息:\n{user_msg}\n")
    
    # 加密消息
    ret, encrypted_msg = crypto.encrypt_msg(user_msg, nonce, timestamp)
    
    if ret != 0:
        print(f"加密失败: {ret}")
        return
    
    # 从加密后的 XML 中提取 Encrypt 字段用于签名
    import xml.etree.ElementTree as ET
    root = ET.fromstring(encrypted_msg)
    encrypt_text = root.find("Encrypt").text
    
    # 生成签名
    msg_signature = generate_signature(TOKEN, timestamp, nonce, encrypt_text)
    
    url = f"{BASE_URL}/wecom/callback"
    params = {
        "msg_signature": msg_signature,
        "timestamp": timestamp,
        "nonce": nonce
    }
    
    # 构造 POST body（只包含 Encrypt 字段）
    post_body = f"""<xml>
<ToUserName><![CDATA[{CORP_ID}]]></ToUserName>
<Encrypt><![CDATA[{encrypt_text}]]></Encrypt>
<AgentID><![CDATA[{Config.WECOM_AGENT_ID or '1000001'}]]></AgentID>
</xml>"""
    
    print(f"POST {url}")
    print(f"Params: {params}")
    print(f"Body:\n{post_body[:200]}...\n")
    
    resp = requests.post(url, params=params, data=post_body.encode("utf-8"))
    print(f"Status: {resp.status_code}")
    print(f"Response:\n{resp.text[:500]}...")
    print()


def test_simple_requests():
    """
    简单请求测试（不需要正确的加密配置）
    """
    print("=" * 50)
    print("简单请求测试")
    print("=" * 50)
    
    # 1. 不带参数的 GET 请求
    print("\n1. GET 请求（无参数）:")
    url = f"{BASE_URL}/wecom/callback"
    resp = requests.get(url)
    print(f"   Status: {resp.status_code}, Response: {resp.text[:100]}")
    
    # 2. 带错误签名的 GET 请求
    print("\n2. GET 请求（错误签名）:")
    params = {
        "msg_signature": "wrong_signature",
        "timestamp": str(int(time.time())),
        "nonce": "123456",
        "echostr": "test_echostr"
    }
    resp = requests.get(url, params=params)
    print(f"   Status: {resp.status_code}, Response: {resp.text[:100]}")
    
    # 3. POST 请求（空 body）
    print("\n3. POST 请求（空 body）:")
    resp = requests.post(url, params=params, data="")
    print(f"   Status: {resp.status_code}, Response: {resp.text[:100]}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("企业微信回调接口测试")
    print("=" * 50 + "\n")
    
    # 1. 测试健康检查
    test_health()
    
    # 2. 简单请求测试
    test_simple_requests()
    
    # 3. URL 验证测试（需要正确配置）
    print("\n--- 以下测试需要正确配置 .env ---\n")
    
    if TOKEN and ENCODING_AES_KEY and CORP_ID:
        test_url_verify()
        test_message_receive()
    else:
        print("请先配置 .env 文件中的 WECOM_TOKEN, WECOM_ENCODING_AES_KEY, WECOM_CORP_ID")

