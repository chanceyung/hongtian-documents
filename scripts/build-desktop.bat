@echo off
REM ============================================
REM 弘天文档 — 桌面版一键构建脚本 (Windows)
REM ============================================
setlocal enabledelayedexpansion

set ROOT_DIR=%~dp0..
echo === 弘天文档 桌面版构建 ===

REM ─── 1. 构建前端 ──────────────────────────────────────
echo.
echo ^>^>^> [1/4] 构建前端 (Next.js standalone)...
cd /d "%ROOT_DIR%\frontend"
call npm ci
call npm run build

echo   复制前端构建产物...
if exist "%ROOT_DIR%\desktop\resources\frontend" rmdir /s /q "%ROOT_DIR%\desktop\resources\frontend"
xcopy /e /i /y ".next\standalone" "%ROOT_DIR%\desktop\resources\frontend\"
xcopy /e /i /y ".next\static" "%ROOT_DIR%\desktop\resources\frontend\.next\static\"
xcopy /e /i /y "public" "%ROOT_DIR%\desktop\resources\frontend\public\"

REM ─── 2. 准备 Python 环境 ──────────────────────────────
echo.
echo ^>^>^> [2/4] 准备 Python 依赖 (桌面版精简)...
cd /d "%ROOT_DIR%\backend"
python -m venv .venv-desktop
call .venv-desktop\Scripts\activate.bat
pip install --no-cache-dir -r requirements-desktop.txt

REM ─── 3. PyInstaller 打包后端 ──────────────────────────
echo.
echo ^>^>^> [3/4] PyInstaller 打包后端...
pip install pyinstaller
pyinstaller "%ROOT_DIR%\desktop\hongtian-backend.spec" ^
  --distpath "%ROOT_DIR%\desktop\resources\python" ^
  --workpath "%ROOT_DIR%\desktop\build\backend-build" ^
  --clean --noconfirm

echo   复制模板资源...
xcopy /e /i /y "app\templates" "%ROOT_DIR%\desktop\resources\python\app\templates\"

call deactivate

REM ─── 4. Electron 构建 ─────────────────────────────────
echo.
echo ^>^>^> [4/4] 构建 Electron 应用...
cd /d "%ROOT_DIR%\desktop"
call npm ci
call npx tsc -p tsconfig.main.json 2>nul || echo   [warn] TS compile skipped
call npm run build:win

echo.
echo === 构建完成 ===
echo 输出目录: %ROOT_DIR%\desktop\release\
dir /b "%ROOT_DIR%\desktop\release\" 2>nul || echo (release 目录尚未生成)

pause