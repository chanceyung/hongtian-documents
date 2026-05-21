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

# 备份目录
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/backup_${TIMESTAMP}.tar.gz"

# 保留天数
RETENTION_DAYS=7

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  弘天文档 - 数据备份脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 创建备份目录
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${YELLOW}创建备份目录: $BACKUP_DIR${NC}"
    mkdir -p "$BACKUP_DIR"
fi

echo -e "${YELLOW}[1/4] 创建备份文件...${NC}"
echo -e "${GREEN}备份文件: $BACKUP_FILE${NC}"
echo ""

# 创建临时目录用于收集备份文件
TEMP_DIR=$(mktemp -d)

# 备份数据库文件（如果存在）
echo -e "${YELLOW}[2/4] 备份数据库...${NC}"
if [ -f "$PROJECT_ROOT/backend/data/database.db" ]; then
    mkdir -p "$TEMP_DIR/database"
    cp -r "$PROJECT_ROOT/backend/data/database.db" "$TEMP_DIR/database/"
    echo -e "${GREEN}✓ 数据库已备份${NC}"
else
    echo -e "${YELLOW}  跳过: 未找到数据库文件${NC}"
fi
echo ""

# 备份上传目录
echo -e "${YELLOW}[3/4] 备份上传文件...${NC}"
if [ -d "$PROJECT_ROOT/backend/uploads" ]; then
    mkdir -p "$TEMP_DIR/uploads"
    cp -r "$PROJECT_ROOT/backend/uploads/"* "$TEMP_DIR/uploads/" 2>/dev/null || true
    echo -e "${GREEN}✓ 上传文件已备份${NC}"
else
    echo -e "${YELLOW}  跳过: 未找到上传目录${NC}"
fi
echo ""

# 备份输出目录
echo -e "${YELLOW}[4/4] 备份输出文件...${NC}"
if [ -d "$PROJECT_ROOT/backend/output" ]; then
    mkdir -p "$TEMP_DIR/output"
    cp -r "$PROJECT_ROOT/backend/output/"* "$TEMP_DIR/output/" 2>/dev/null || true
    echo -e "${GREEN}✓ 输出文件已备份${NC}"
else
    echo -e "${YELLOW}  跳过: 未找到输出目录${NC}"
fi
echo ""

# 打包备份文件
echo -e "${YELLOW}打包备份文件...${NC}"
tar -czf "$BACKUP_FILE" -C "$TEMP_DIR" .
rm -rf "$TEMP_DIR"
echo -e "${GREEN}✓ 备份完成: $BACKUP_FILE${NC}"
echo ""

# 清理旧备份
echo -e "${YELLOW}清理 $RETENTION_DAYS 天前的备份...${NC}"
find "$BACKUP_DIR" -name "backup_*.tar.gz" -type f -mtime +$RETENTION_DAYS -delete
echo -e "${GREEN}✓ 旧备份已清理${NC}"
echo ""

# 显示备份信息
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  备份完成${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}备份文件: $BACKUP_FILE${NC}"
echo -e "${GREEN}文件大小: $(du -h "$BACKUP_FILE" | cut -f1)${NC}"
echo -e "${GREEN}现有备份: $(find "$BACKUP_DIR" -name "backup_*.tar.gz" | wc -l) 个${NC}"
echo ""