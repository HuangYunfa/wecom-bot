# 企业微信智能机器人

基于 Flask + LangChain + 通义千问(Qwen) + Redis 的企业微信智能客服机器人。

## 功能特性

- ✅ 企业微信消息接收和回复
- ✅ 消息加解密处理
- ✅ 通义千问(Qwen) AI 对话
- ✅ Redis 对话历史持久化
- ✅ 支持多轮对话
- ✅ 会话管理 API

## 项目结构

```
wecom-bot/
├── app.py              # Flask 应用主入口
├── run.py              # 启动脚本
├── config.py           # 配置管理
├── requirements.txt    # 依赖包
├── env.example         # 环境变量示例
├── wecom/              # 企业微信模块
│   ├── __init__.py
│   ├── crypto.py       # 消息加解密
│   └── message.py      # 消息处理
└── ai/                 # AI 模块
    ├── __init__.py
    ├── chat.py         # 对话服务
    └── history.py      # 对话历史管理
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `env.example` 为 `.env` 并填写配置：

```bash
cp env.example .env
```

配置项说明：

| 配置项 | 说明 |
|--------|------|
| WECOM_CORP_ID | 企业微信企业ID |
| WECOM_AGENT_ID | 应用AgentId |
| WECOM_SECRET | 应用Secret |
| WECOM_TOKEN | 回调Token |
| WECOM_ENCODING_AES_KEY | 回调EncodingAESKey |
| DASHSCOPE_API_KEY | 通义千问API Key |
| REDIS_HOST | Redis 地址 |
| REDIS_PORT | Redis 端口 |
| REDIS_PASSWORD | Redis 密码（可选） |

### 3. 启动 Redis

```bash
# Docker 方式
docker run -d --name redis -p 6379:6379 redis:latest

# 或使用本地 Redis
redis-server
```

### 4. 启动服务

```bash
python run.py
```

### 5. 配置企业微信

1. 登录 [企业微信管理后台](https://work.weixin.qq.com/)
2. 进入 **应用管理** → **自建应用** → 创建应用
3. 获取 `AgentId` 和 `Secret`
4. 设置 **接收消息** → **API接收消息**
   - URL: `https://your-domain.com/wecom/callback`
   - Token: 自定义，与配置保持一致
   - EncodingAESKey: 自动生成或自定义
5. 保存后企业微信会验证URL有效性

## API 接口

### 健康检查

```
GET /health
```

### 获取会话信息

```
GET /session/<user_id>
```

### 清除会话历史

```
DELETE /session/<user_id>
```

## 特殊命令

用户可以发送以下命令清除对话历史：
- `清除历史`
- `清除记录`
- `重新开始`
- `/clear`

## 生产部署

### 使用 Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 使用 Docker

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8092", "app:app"]
```

构建并运行：

```bash
docker build -t wecom-bot .
docker run -d -p 8092:5000 --env-file .env wecom-bot
```

### 使用 Nginx 反向代理

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location /wecom/ {
        proxy_pass http://172.17.91.218:8092;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 自定义 AI 行为

修改 `ai/chat.py` 中的 `SYSTEM_PROMPT` 来自定义 AI 的行为：

```python
SYSTEM_PROMPT = """你是一个专业的企业客服助手..."""
```

## 注意事项

1. **HTTPS 要求**: 企业微信回调必须使用 HTTPS
2. **响应时间**: 企业微信要求在 5 秒内响应
3. **消息去重**: 企业微信可能重复推送消息，建议实现消息去重
4. **Token 安全**: 请勿将 `.env` 文件提交到版本控制

## 参考文档

- [企业微信接收消息](https://work.weixin.qq.com/api/doc/90000/90135/90238)
- [企业微信加解密说明](https://work.weixin.qq.com/api/doc/90000/90135/90968)
- [LangChain DashScope 集成](https://python.langchain.com/docs/integrations/chat/dashscope/)
- [DashScope Qwen 文档](https://help.aliyun.com/zh/dashscope/)

## License

MIT

