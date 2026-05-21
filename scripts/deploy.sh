#!/bin/bash
set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  弘天文档 - 一键部署脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. 检查 Docker
echo -e "${YELLOW}[1/6] 检查 Docker 环境...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装，请先安装 Docker${NC}"
    exit 1
fi
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}错误: docker compose 未安装，请先安装 Docker Compose${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker 环境检查通过${NC}"
echo ""

# 2. 检查 .env 文件
echo -e "${YELLOW}[2/6] 检查环境配置文件...${NC}"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo -e "${YELLOW}  未找到 .env 文件，从 .env.example 复制...${NC}"
        cp .env.example .env
        echo -e "${GREEN}✓ 已创建 .env 文件，请根据需要修改配置${NC}"
    else
        echo -e "${RED}错误: 未找到 .env 和 .env.example 文件${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ .env 文件已存在${NC}"
fi
echo ""

# 3. 拉取最新代码
echo -e "${YELLOW}[3/6] 拉取最新代码...${NC}"
if [ -d .git ]; then
    git pull origin main || echo -e "${YELLOW}  警告: 无法拉取代码，可能是首次部署${NC}"
else
    echo -e "${YELLOW}  跳过: 非 Git 仓库${NC}"
fi
echo ""

# 4. 停止现有容器
echo -e "${YELLOW}[4/6] 停止现有容器...${NC}"
if docker compose -f docker-compose-v4.yml ps -q 2>/dev/null | grep -q .; then
    echo -e "${YELLOW}  停止并移除现有容器...${NC}"
    docker compose -f docker-compose-v4.yml down
fi
echo -e "${GREEN}✓ 容器已停止${NC}"
echo ""

# 5. 构建并启动服务
echo -e "${YELLOW}[5/6] 构建并启动 Docker 容器...${NC}"
docker compose -f docker-compose-v4.yml up -d --build
echo ""

# 6. 等待服务健康检查
echo -e "${YELLOW}[6/6] 等待服务启动...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2

    # 检查后端服务
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✓ 后端服务已启动${NC}"
        break
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo ""
    echo -e "${RED}错误: 服务启动超时${NC}"
    echo -e "${YELLOW}查看日志: docker compose -f docker-compose-v4.yml logs${NC}"
    exit 1
fi
echo ""

# 显示服务状态
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  部署完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}服务状态:${NC}"
docker compose -f docker-compose-v4.yml ps
echo ""
echo -e "${GREEN}访问地址:${NC}"
echo -e "  - 前端: ${BLUE}http://localhost:3000${NC}"
echo -e "  - 后端 API: ${BLUE}http://localhost:8000${NC}"
echo -e "  - API 文档: ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "${YELLOW}常用命令:${NC}"
echo -e "  - 查看日志: docker compose -f docker-compose-v4.yml logs -f"
echo -e "  - 停止服务: docker compose -f docker-compose-v4.yml down"
echo -e "  - 重启服务: docker compose -f docker-compose-v4.yml restart"
echo ""