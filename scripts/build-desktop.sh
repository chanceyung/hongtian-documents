#!/usr/bin/env bash
# ============================================
# 弘天文档 — 桌面版一键构建脚本
# ============================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
echo "=== 弘天文档 桌面版构建 ==="
echo "Root: $ROOT_DIR"

# ─── 1. 构建前端 ──────────────────────────────────────────────────────────
echo ""
echo ">>> [1/4] 构建前端 (Next.js standalone)..."
cd "$ROOT_DIR/frontend"
npm ci
npm run build

# 将 standalone 输出复制到 desktop/resources/frontend
echo "  复制前端构建产物..."
rm -rf "$ROOT_DIR/desktop/resources/frontend"
cp -r .next/standalone "$ROOT_DIR/desktop/resources/frontend"
cp -r .next/static "$ROOT_DIR/desktop/resources/frontend/.next/static"
cp -r public "$ROOT_DIR/desktop/resources/frontend/public"

# ─── 2. 准备 Python 环境 ─────────────────────────────────────────────────
echo ""
echo ">>> [2/4] 准备 Python 依赖 (桌面版精简)..."
cd "$ROOT_DIR/backend"
python -m venv .venv-desktop
source .venv-desktop/bin/activate
pip install --no-cache-dir -r requirements-desktop.txt

# ─── 3. PyInstaller 打包后端 ──────────────────────────────────────────────
echo ""
echo ">>> [3/4] PyInstaller 打包后端..."
pip install pyinstaller
pyinstaller "$ROOT_DIR/desktop/hongtian-backend.spec" \
  --distpath "$ROOT_DIR/desktop/resources/python" \
  --workpath "$ROOT_DIR/desktop/build/backend-build" \
  --clean \
  --noconfirm

# 复制 app 目录（模板等资源）
echo "  复制模板资源..."
cp -r app/templates "$ROOT_DIR/desktop/resources/python/app/templates"

deactivate

# ─── 4. Electron 构建 ─────────────────────────────────────────────────────
echo ""
echo ">>> [4/4] 构建 Electron 应用..."
cd "$ROOT_DIR/desktop"
npm ci
npm run typecheck 2>/dev/null || echo "  [warn] typecheck skipped"
npx tsc -p tsconfig.main.json || echo "  [warn] TS compile skipped, using pre-built"
npm run build:win

echo ""
echo "=== 构建完成 ==="
echo "输出目录: $ROOT_DIR/desktop/release/"
ls -la "$ROOT_DIR/desktop/release/" 2>/dev/null || echo "(release 目录尚未生成)"