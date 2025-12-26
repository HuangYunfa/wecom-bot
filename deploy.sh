#!/bin/bash
#
# 企业微信智能机器人 - Docker 部署脚本
# 使用方法: chmod +x deploy.sh && ./deploy.sh
#
# 安全说明:
# - 此脚本只操作 wecom-bot 容器，不会影响其他容器（如 Dify）
# - 只使用独立的端口 5000（可配置）
# - 只读取 Redis 网络信息，不修改网络配置
#

set -e

# ========== 配置区域 ==========
APP_NAME="wecom-bot"
APP_PORT=8092
# ==============================

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

echo ""
echo "========================================"
echo "   企业微信智能机器人 - Docker 部署"
echo "========================================"
echo "   容器名称: $APP_NAME"
echo "   服务端口: $APP_PORT"
echo "========================================"
echo ""

# ========== 安全检查 ==========

log_step "执行部署前安全检查..."

# 检查是否在正确的目录
if [ ! -f "Dockerfile" ]; then
    log_error "请在项目根目录执行此脚本（未找到 Dockerfile）"
    exit 1
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    log_error ".env 配置文件不存在，请先创建配置文件"
    log_info "执行: cp env.example .env && vim .env"
    exit 1
fi

# 检查端口是否被占用（排除自己）
log_info "检查端口 $APP_PORT 是否可用..."
PORT_IN_USE=$(docker ps --format '{{.Names}} {{.Ports}}' | grep -v "^$APP_NAME " | grep ":$APP_PORT->" || echo "")
if [ -n "$PORT_IN_USE" ]; then
    log_error "端口 $APP_PORT 已被其他容器占用:"
    echo "  $PORT_IN_USE"
    log_info "请修改脚本中的 APP_PORT 变量使用其他端口"
    exit 1
fi
log_info "端口 $APP_PORT 可用"

# 显示当前运行的容器（仅供参考，不做任何修改）
log_info "当前运行的 Docker 容器（仅显示，不会修改）:"
echo "----------------------------------------"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -15
echo "----------------------------------------"
echo ""

# 确认部署
read -p "确认部署 $APP_NAME？此操作不会影响其他容器 [y/N]: " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warn "部署已取消"
    exit 0
fi

echo ""

# ========== 网络配置 ==========

# 使用默认 bridge 网络，可以访问外部网络（包括阿里云 Redis）
# 如果你使用本地 Docker Redis，可以修改为对应的网络名
DOCKER_NETWORK="bridge"

log_info "使用 Docker 网络: $DOCKER_NETWORK"
log_info "Redis 连接地址将从 .env 文件读取"

# ========== 停止旧容器（仅 wecom-bot）==========

log_step "停止旧的 $APP_NAME 容器（如果存在）..."

# 只操作 wecom-bot 容器，使用精确匹配
if docker ps -a --format '{{.Names}}' | grep -q "^${APP_NAME}$"; then
    docker stop "$APP_NAME" 2>/dev/null || true
    docker rm "$APP_NAME" 2>/dev/null || true
    log_info "已停止并删除旧容器"
else
    log_info "未发现旧容器，跳过"
fi

# ========== 构建镜像 ==========

log_step "构建 Docker 镜像: $APP_NAME:latest"
docker build -t "$APP_NAME:latest" .

# ========== 启动容器 ==========

log_step "启动新容器..."
docker run -d \
  --name "$APP_NAME" \
  --network "$DOCKER_NETWORK" \
  --restart unless-stopped \
  -p "$APP_PORT:5000" \
  --env-file .env \
  "$APP_NAME:latest"

log_info "容器已启动"

# ========== 等待并检查 ==========

log_step "等待服务启动..."
sleep 5

log_step "执行健康检查..."
HEALTH_CHECK=$(curl -s "http://127.0.0.1:$APP_PORT/health" 2>/dev/null || echo "")

if echo "$HEALTH_CHECK" | grep -q "ok"; then
    echo ""
    echo "========================================"
    echo -e "   ${GREEN}部署成功！${NC}"
    echo "========================================"
    echo ""
    echo "服务地址:"
    echo "  - 健康检查: http://127.0.0.1:$APP_PORT/health"
    echo "  - 回调接口: http://127.0.0.1:$APP_PORT/wecom/callback"
    echo ""
    echo "常用命令:"
    echo "  - 查看日志: docker logs -f $APP_NAME"
    echo "  - 重启服务: docker restart $APP_NAME"
    echo "  - 停止服务: docker stop $APP_NAME"
    echo ""
    
    # 再次显示所有容器，确认其他服务正常
    log_info "当前所有运行中的容器:"
    docker ps --format "table {{.Names}}\t{{.Status}}" | head -15
    echo ""
else
    echo ""
    log_error "部署可能失败，请检查日志:"
    echo ""
    docker logs --tail 30 "$APP_NAME"
    exit 1
fi
