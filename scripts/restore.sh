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
echo -e "${BLUE}  弘天文档 - 数据恢复脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查参数
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}用法: $0 <备份文件路径>${NC}"
    echo ""
    echo -e "${YELLOW}可用的备份文件:${NC}"
    if [ -d "$PROJECT_ROOT/backups" ]; then
        ls -lht "$PROJECT_ROOT/backups"/backup_*.tar.gz 2>/dev/null | awk '{print $9}' | head -5
    fi
    exit 1
fi

BACKUP_FILE="$1"

# 检查备份文件是否存在
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}错误: 备份文件不存在: $BACKUP_FILE${NC}"
    exit 1
fi

# 显示备份信息
echo -e "${YELLOW}备份文件: $BACKUP_FILE${NC}"
echo -e "${YELLOW}文件大小: $(du -h "$BACKUP_FILE" | cut -f1)${NC}"
echo -e "${YELLOW}修改时间: $(stat -c %y "$BACKUP_FILE")${NC}"
echo ""

# 确认恢复
echo -e "${RED}警告: 此操作将覆盖现有数据！${NC}"
read -p "确认恢复？(yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}操作已取消${NC}"
    exit 0
fi
echo ""

# 1. 停止服务
echo -e "${YELLOW}[1/4] 停止服务...${NC}"
if docker compose -f docker-compose-v4.yml ps -q 2>/dev/null | grep -q .; then
    docker compose -f docker-compose-v4.yml down
    echo -e "${GREEN}✓ 服务已停止${NC}"
else
    echo -e "${YELLOW}  跳过: 服务未运行${NC}"
fi
echo ""

# 2. 备份当前数据（以防万一）
echo -e "${YELLOW}[2/4] 备份当前数据...${NC}"
"$PROJECT_ROOT/scripts/backup.sh"
echo ""

# 3. 解压备份文件
echo -e "${YELLOW}[3/4] 解压备份文件...${NC}"
TEMP_DIR=$(mktemp -d)
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# 恢复数据库
if [ -d "$TEMP_DIR/database" ]; then
    mkdir -p "$PROJECT_ROOT/backend/data"
    cp -r "$TEMP_DIR/database/"* "$PROJECT_ROOT/backend/data/"
    echo -e "${GREEN}✓ 数据库已恢复${NC}"
else
    echo -e "${YELLOW}  跳过: 备份中无数据库${NC}"
fi

# 恢复上传目录
if [ -d "$TEMP_DIR/uploads" ]; then
    mkdir -p "$PROJECT_ROOT/backend/uploads"
    cp -r "$TEMP_DIR/uploads/"* "$PROJECT_ROOT/backend/uploads/"
    echo -e "${GREEN}✓ 上传文件已恢复${NC}"
else
    echo -e "${YELLOW}  跳过: 备份中无上传文件${NC}"
fi

# 恢复输出目录
if [ -d "$TEMP_DIR/output" ]; then
    mkdir -p "$PROJECT_ROOT/backend/output"
    cp -r "$TEMP_DIR/output/"* "$PROJECT_ROOT/backend/output/"
    echo -e "${GREEN}✓ 输出文件已恢复${NC}"
else
    echo -e "${YELLOW}  跳过: 备份中无输出文件${NC}"
fi

rm -rf "$TEMP_DIR"
echo ""

# 4. 重启服务
echo -e "${YELLOW}[4/4] 重启服务...${NC}"
docker compose -f docker-compose-v4.yml up -d
echo ""

# 等待服务启动
echo -e "${YELLOW}等待服务启动...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2

    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✓ 服务已启动${NC}"
        break
    fi
done
echo ""

# 显示结果
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  恢复完成${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}数据已从以下备份恢复:${NC}"
echo -e "${GREEN}  $BACKUP_FILE${NC}"
echo ""
echo -e "${YELLOW}服务状态:${NC}"
docker compose -f docker-compose-v4.yml ps
echo ""