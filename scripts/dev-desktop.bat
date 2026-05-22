@echo off
REM ============================================
REM 弘天文档 — 桌面开发模式启动
REM ============================================
REM 同时启动后端 + 前端，模拟 Electron 环境
REM 后端以 DESKTOP_MODE=true 运行（使用 SQLite 替代 Redis）

setlocal

set DESKTOP_MODE=true
set PYTHONUNBUFFERED=1
set PORT=8000
set CORS_ORIGINS=["http://localhost:3000"]

echo === 弘天文档 桌面开发模式 ===
echo.
echo 后端: http://localhost:8000  (DESKTOP_MODE=true, SQLite)
echo 前端: http://localhost:3000  (Next.js dev)
echo.

REM 启动后端
start "弘天文档-后端" cmd /c "cd /d %~dp0backend && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --log-level info"

REM 等待后端启动
timeout /t 3 /nobreak >nul

REM 启动前端
start "弘天文档-前端" cmd /c "cd /d %~dp0frontend && npm run dev"

echo.
echo 两个服务已在新窗口中启动，关闭窗口即可停止。
pause