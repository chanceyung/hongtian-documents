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
echo -e "${BLUE}  弘天文档 - 开发环境搭建脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. 检查 Python 版本
echo -e "${YELLOW}[1/8] 检查 Python 版本...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: Python 未安装${NC}"
    echo -e "${YELLOW}请安装 Python 3.11 或更高版本${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ $PYTHON_MAJOR -lt 3 ] || ([ $PYTHON_MAJOR -eq 3 ] && [ $PYTHON_MINOR -lt 11 ]); then
    echo -e "${RED}错误: Python 版本过低 (当前: $PYTHON_VERSION, 要求: ≥3.11)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python 版本: $PYTHON_VERSION${NC}"
echo ""

# 2. 检查 Node.js 版本
echo -e "${YELLOW}[2/8] 检查 Node.js 版本...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}错误: Node.js 未安装${NC}"
    echo -e "${YELLOW}请安装 Node.js 20 或更高版本${NC}"
    exit 1
fi

NODE_VERSION=$(node --version | sed 's/v//')
NODE_MAJOR=$(echo $NODE_VERSION | cut -d. -f1)

if [ $NODE_MAJOR -lt 20 ]; then
    echo -e "${RED}错误: Node.js 版本过低 (当前: $NODE_VERSION, 要求: ≥20)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Node.js 版本: v$NODE_VERSION${NC}"
echo ""

# 3. 检查 Redis
echo -e "${YELLOW}[3/8] 检查 Redis...${NC}"
if command -v redis-server &> /dev/null; then
    echo -e "${GREEN}✓ Redis 已安装${NC}"
elif command -v redis-cli &> /dev/null; then
    echo -e "${GREEN}✓ Redis 客户端已安装${NC}"
    echo -e "${YELLOW}  提示: 请确保 Redis 服务已启动${NC}"
else
    echo -e "${YELLOW}警告: Redis 未安装${NC}"
    echo -e "${YELLOW}  可以使用 Docker 运行: docker run -d -p 6379:6379 redis${NC}"
fi
echo ""

# 4. 创建 Python 虚拟环境
echo -e "${YELLOW}[4/8] 创建 Python 虚拟环境...${NC}"
if [ ! -d "$PROJECT_ROOT/backend/venv" ]; then
    python3 -m venv "$PROJECT_ROOT/backend/venv"
    echo -e "${GREEN}✓ 虚拟环境已创建${NC}"
else
    echo -e "${YELLOW}  虚拟环境已存在${NC}"
fi
echo ""

# 5. 安装后端依赖
echo -e "${YELLOW}[5/8] 安装后端依赖...${NC}"
if [ -f "$PROJECT_ROOT/backend/requirements-v4.txt" ]; then
    source "$PROJECT_ROOT/backend/venv/bin/activate"
    pip install --upgrade pip
    pip install -r "$PROJECT_ROOT/backend/requirements-v4.txt"
    echo -e "${GREEN}✓ 后端依赖已安装${NC}"
else
    echo -e "${RED}错误: 未找到 requirements-v4.txt${NC}"
    exit 1
fi
echo ""

# 6. 安装 Playwright 浏览器
echo -e "${YELLOW}[6/8] 安装 Playwright 浏览器...${NC}"
source "$PROJECT_ROOT/backend/venv/bin/activate"
playwright install chromium
echo -e "${GREEN}✓ Playwright 浏览器已安装${NC}"
echo ""

# 7. 安装前端依赖
echo -e "${YELLOW}[7/8] 安装前端依赖...${NC}"
if [ -f "$PROJECT_ROOT/frontend/package.json" ]; then
    cd "$PROJECT_ROOT/frontend"
    npm install
    cd "$PROJECT_ROOT"
    echo -e "${GREEN}✓ 前端依赖已安装${NC}"
else
    echo -e "${RED}错误: 未找到 frontend/package.json${NC}"
    exit 1
fi
echo ""

# 8. 创建环境配置文件
echo -e "${YELLOW}[8/8] 创建环境配置文件...${NC}"
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        echo -e "${GREEN}✓ 已创建 .env 文件${NC}"
        echo -e "${YELLOW}  请根据需要修改配置${NC}"
    else
        echo -e "${RED}错误: 未找到 .env.example${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}  .env 文件已存在${NC}"
fi
echo ""

# 显示完成信息
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  开发环境搭建完成${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}下一步操作:${NC}"
echo ""
echo -e "${YELLOW}1. 配置环境变量:${NC}"
echo -e "   编辑 $PROJECT_ROOT/.env 文件"
echo ""
echo -e "${YELLOW}2. 启动 Redis:${NC}"
echo -e "   docker run -d -p 6379:6379 redis"
echo "   或使用系统的 Redis 服务"
echo ""
echo -e "${YELLOW}3. 启动后端服务:${NC}"
echo -e "   cd $PROJECT_ROOT/backend"
echo -e "   source venv/bin/activate"
echo -e "   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo -e "${YELLOW}4. 启动前端服务:${NC}"
echo -e "   cd $PROJECT_ROOT/frontend"
echo -e "   npm run dev"
echo ""
echo -e "${YELLOW}5. 访问应用:${NC}"
echo -e "   - 前端: ${BLUE}http://localhost:3000${NC}"
echo -e "   - 后端 API: ${BLUE}http://localhost:8000${NC}"
echo -e "   - API 文档: ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "${YELLOW}常用开发命令:${NC}"
echo -e "   - 运行测试: cd backend && pytest tests/"
echo -e "   - 代码检查: cd backend && ruff check app/"
echo -e "   - 格式化代码: cd backend && ruff format app/"
echo ""