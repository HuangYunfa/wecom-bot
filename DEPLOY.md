# 企业微信智能机器人 - 阿里云 Docker 部署指南

本文档介绍如何在阿里云 Linux 服务器上使用 Docker 部署企业微信智能机器人。

## 环境要求

- 阿里云 ECS 服务器（已安装 Docker）
- 开放端口：5000（或自定义端口）
- Redis 服务（可使用已有的 docker-redis-1 或新建）

## 部署步骤

### 1. 上传项目代码

**方式一：Git 克隆（推荐）**

```bash
cd /opt
git clone https://your-repo-url/wecom-bot.git
cd wecom-bot
```

**方式二：手动上传**

将本地项目文件上传到服务器 `/opt/wecom-bot/` 目录。

```bash
# 本地执行（Windows PowerShell）
scp -r D:\git\python-dev\wecom-bot root@172.17.91.218:/opt/
```

### 2. 创建配置文件

```bash
cd /opt/wecom-bot

# 复制配置模板
cp env.example .env

# 编辑配置文件
vim .env
```

**配置文件内容（根据实际情况修改）：**

```bash
# 企业微信配置（从企业微信管理后台获取）
WECOM_CORP_ID=你的企业ID
WECOM_AGENT_ID=你的应用AgentId
WECOM_SECRET=你的应用Secret
WECOM_TOKEN=你的回调Token
WECOM_ENCODING_AES_KEY=你的EncodingAESKey

# AI API 配置
# 通义千问: https://dashscope.console.aliyun.com/
# DeepSeek: https://platform.deepseek.com/
DASHSCOPE_API_KEY=你的API_Key

# Redis 配置（使用已有的 docker-redis-1）
REDIS_HOST=docker-redis-1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=1

# Flask 配置
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false

# AI 配置
# 通义千问: qwen-turbo, qwen-plus, qwen-max
# DeepSeek: deepseek-chat, deepseek-coder
AI_MODEL=qwen-turbo
AI_MAX_TOKENS=2048
AI_TEMPERATURE=0.7

# 对话历史配置
CONVERSATION_MAX_HISTORY=20
CONVERSATION_TTL_SECONDS=86400
```

### 3. 构建 Docker 镜像

```bash
cd /opt/wecom-bot

# 构建镜像
docker build -t wecom-bot:latest .

# 查看构建的镜像
docker images | grep wecom-bot
```

### 4. 创建 Docker 网络（如果不存在）

你的 Dify 服务已经在运行，需要让 wecom-bot 加入同一个网络以访问 Redis。

```bash
# 查看现有网络
docker network ls

# 查看 Dify 使用的网络（通常是 dify_default 或 bridge）
docker inspect docker-redis-1 | grep -A 10 "Networks"

# 如果 Redis 在默认 bridge 网络，可以创建自定义网络
# docker network create wecom-net
```

### 5. 启动容器

**方式一：使用已有的 Redis（推荐）**

```bash
# 获取 Redis 容器所在的网络名称
REDIS_NETWORK=$(docker inspect docker-redis-1 --format='{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}')
echo "Redis network: $REDIS_NETWORK"

# 启动 wecom-bot 并加入同一网络
docker run -d --name wecom-bot -p 8092:5000 --env-file .env wecom-bot:latest
```

**方式二：使用 Docker Compose（包含独立 Redis）**

```bash
# 使用项目自带的 docker-compose.yml
docker-compose up -d
```

### 6. 验证部署

```bash
# 查看容器状态
docker ps | grep wecom-bot

# 查看容器日志
docker logs -f wecom-bot

# 测试健康检查接口
curl http://127.0.0.1:5000/health
# 预期输出: {"service":"wecom-bot","status":"ok"}

# 测试回调接口（会返回验证失败，这是正常的）
curl "http://127.0.0.1:5000/wecom/callback?msg_signature=test&timestamp=123&nonce=456&echostr=hello"
```

### 7. 配置 Nginx 反向代理

企业微信回调需要 HTTPS，配置 Nginx 反向代理：

```bash
# 编辑 Nginx 配置
vim /etc/nginx/conf.d/wecom-bot.conf
```

**Nginx 配置内容：**

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;  # 替换为你的域名

    # SSL 证书配置
    ssl_certificate /etc/nginx/ssl/your-domain.com.pem;
    ssl_certificate_key /etc/nginx/ssl/your-domain.com.key;
    
    # 可选：指定 TLS 版本和加密套件（提高安全性）
    # ssl_protocols TLSv1.2 TLSv1.3;
    # ssl_ciphers HIGH:!aNULL:!MD5;

    # 企业微信回调接口
    location /wecom/ {
        proxy_pass http://127.0.0.1:8092;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置（AI 响应可能较慢）
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 健康检查接口
    location /health {
        proxy_pass http://127.0.0.1:8092;
    }
}

# HTTP 跳转 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

**重载 Nginx：**

```bash
# 测试配置
nginx -t

# 重载配置
nginx -s reload
```

### 8. 配置阿里云安全组

在阿里云控制台配置安全组规则，开放以下端口：

| 端口 | 协议 | 说明 |
|------|------|------|
| 443 | TCP | HTTPS（企业微信回调） |
| 80 | TCP | HTTP（可选，用于跳转） |
| 5000 | TCP | 直接访问（可选，仅内网） |

### 9. 配置企业微信

1. 登录 [企业微信管理后台](https://work.weixin.qq.com/)
2. 进入 **应用管理** → **自建应用**
3. 设置 **接收消息** → **API接收消息**
   - URL: `https://your-domain.com/wecom/callback`
   - Token: 与 `.env` 中 `WECOM_TOKEN` 一致
   - EncodingAESKey: 与 `.env` 中 `WECOM_ENCODING_AES_KEY` 一致
4. 点击保存，企业微信会验证 URL

## 常用运维命令

```bash
# 查看容器状态
docker ps -a | grep wecom-bot

# 查看实时日志
docker logs -f wecom-bot

# 查看最近100行日志
docker logs --tail 100 wecom-bot

# 重启容器
docker restart wecom-bot

# 停止容器
docker stop wecom-bot

# 删除容器
docker rm wecom-bot

# 重新构建并部署
docker stop wecom-bot && docker rm wecom-bot
docker build -t wecom-bot:latest .
docker run -d --name wecom-bot --network $REDIS_NETWORK --restart unless-stopped -p 5000:5000 --env-file .env wecom-bot:latest

# 进入容器调试
docker exec -it wecom-bot /bin/bash

# 查看容器资源使用
docker stats wecom-bot
```

## 故障排查

### 1. 容器启动失败

```bash
# 查看详细日志
docker logs wecom-bot

# 常见问题：
# - 配置文件 .env 缺少必要参数
# - Redis 连接失败（检查网络和配置）
# - API Key 无效
```

### 2. Redis 连接失败

```bash
# 检查 Redis 容器是否运行
docker ps | grep redis

# 检查网络连通性
docker exec wecom-bot ping docker-redis-1

# 如果使用外部 Redis，确保 REDIS_HOST 配置正确
```

### 3. AI 服务调用失败

```bash
# 查看日志中的错误信息
docker logs wecom-bot | grep -i error

# 常见问题：
# - API Key 无效或过期
# - 模型名称错误
# - 网络无法访问 AI API
```

### 4. 企业微信回调失败

```bash
# 本地测试回调接口
curl -X GET "http://127.0.0.1:5000/wecom/callback?msg_signature=test&timestamp=123&nonce=456&echostr=hello"

# 检查 Nginx 代理
curl -I https://your-domain.com/wecom/callback

# 常见问题：
# - SSL 证书配置错误
# - Token/EncodingAESKey 不匹配
# - 安全组未开放 443 端口
```

## 更新部署

当代码更新时，执行以下命令重新部署：

```bash
cd /opt/wecom-bot

# 拉取最新代码（如果使用 Git）
git pull

# 重新构建镜像
docker build -t wecom-bot:latest .

# 重启容器
docker stop wecom-bot && docker rm wecom-bot
docker run -d \
  --name wecom-bot \
  --network $REDIS_NETWORK \
  --restart unless-stopped \
  -p 5000:5000 \
  --env-file .env \
  wecom-bot:latest

# 验证
docker logs -f wecom-bot
```

## 一键部署脚本

创建部署脚本 `deploy.sh`：

```bash
#!/bin/bash
set -e

APP_NAME="wecom-bot"
APP_DIR="/opt/wecom-bot"
REDIS_NETWORK=$(docker inspect docker-redis-1 --format='{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' 2>/dev/null || echo "bridge")

echo "=== 开始部署 $APP_NAME ==="

cd $APP_DIR

# 停止并删除旧容器
echo "停止旧容器..."
docker stop $APP_NAME 2>/dev/null || true
docker rm $APP_NAME 2>/dev/null || true

# 构建新镜像
echo "构建镜像..."
docker build -t $APP_NAME:latest .

# 启动新容器
echo "启动容器..."
docker run -d \
  --name $APP_NAME \
  --network $REDIS_NETWORK \
  --restart unless-stopped \
  -p 5000:5000 \
  --env-file .env \
  $APP_NAME:latest

# 等待启动
sleep 3

# 健康检查
echo "健康检查..."
if curl -s http://127.0.0.1:5000/health | grep -q "ok"; then
    echo "=== 部署成功！ ==="
else
    echo "=== 部署可能失败，请检查日志 ==="
    docker logs --tail 50 $APP_NAME
fi
```

使用方法：

```bash
chmod +x deploy.sh
./deploy.sh
```

## 架构说明

```
┌─────────────────────────────────────────────────────────────┐
│                    阿里云 ECS 服务器                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Docker                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │ wecom-bot   │  │docker-redis │  │ Dify 服务   │  │   │
│  │  │   :5000     │◄─┤    :6379    │  │   :80/443   │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Nginx                             │   │
│  │    :443 (HTTPS) ─► /wecom/* ─► 127.0.0.1:5000       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │    企业微信服务器    │
              │   (回调推送消息)     │
              └─────────────────────┘
```

## 相关链接

- [企业微信管理后台](https://work.weixin.qq.com/)
- [企业微信 API 文档](https://work.weixin.qq.com/api/doc/)
- [阿里云 DashScope](https://dashscope.console.aliyun.com/)
- [DeepSeek 平台](https://platform.deepseek.com/)

