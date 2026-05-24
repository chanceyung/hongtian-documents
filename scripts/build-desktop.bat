@echo off
REM ============================================
REM 弘天文档 — 桌面版一键构建脚本 (Windows)
REM 使用 electron-packager 替代 electron-builder
REM 避免 winCodeSign 符号链接权限问题
REM ============================================
setlocal enabledelayedexpansion

set ROOT_DIR=%~dp0..
echo === 弘天文档 桌面版构建 ===

REM ─── 1. 构建前端 (Vite + React) ──────────────────────
echo.
echo ^>^>^> [1/5] 构建前端 (Vite + React)...
cd /d "%ROOT_DIR%\app"
call npm ci
call npm run build

echo   复制前端构建产物到 desktop/resources...
xcopy /e /i /y "dist\public" "%ROOT_DIR%\desktop\resources\app-server\public\"
copy /y "dist\boot.js" "%ROOT_DIR%\desktop\resources\app-server\boot.mjs"
if exist "dist\sql-wasm.wasm" copy /y "dist\sql-wasm.wasm" "%ROOT_DIR%\desktop\resources\app-server\"

if exist "%ROOT_DIR%\desktop\resources\frontend" rmdir /s /q "%ROOT_DIR%\desktop\resources\frontend"
xcopy /e /i /y "dist\public" "%ROOT_DIR%\desktop\resources\frontend\"

REM ─── 2. 复制 node.exe ────────────────────────────────────
echo.
echo ^>^>^> [2/5] 复制 Node.js 运行时...
if not exist "%ROOT_DIR%\desktop\resources\node" mkdir "%ROOT_DIR%\desktop\resources\node"
for /f "tokens=*" %%i in ('where node') do (
    copy /y "%%i" "%ROOT_DIR%\desktop\resources\node\node.exe"
    goto :node_done
)
:node_done
echo   node.exe 已复制

REM ─── 3. 生成 Windows 图标 ────────────────────────────────
echo.
echo ^>^>^> [3/5] 生成图标...
python -c "from PIL import Image; img=Image.open(r'%ROOT_DIR%\desktop\resources\icon.png'); sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]; imgs=[img.resize(s,Image.LANCZOS) for s in sizes]; imgs[-1].save(r'%ROOT_DIR%\desktop\resources\icon.ico',format='ICO',sizes=[(i.width,i.height) for i in imgs],append_images=imgs[:-1])" 2>nul
if errorlevel 1 echo   [warn] 图标生成失败，需要 Pillow

REM ─── 4. 打包 Python 后端 (PyInstaller) ──────────────────
echo.
echo ^>^>^> [4/5] 检查 Python 后端...
if not exist "%ROOT_DIR%\desktop\resources\python\hongtian-backend\hongtian-backend.exe" (
    echo   Python 后端不存在，开始打包...
    cd /d "%ROOT_DIR%\backend"
    if not exist ".venv-desktop" python -m venv .venv-desktop
    call .venv-desktop\Scripts\activate.bat
    pip install --no-cache-dir -r requirements-desktop.txt
    pip install pyinstaller
    pyinstaller "%ROOT_DIR%\desktop\hongtian-backend.spec" --distpath "%ROOT_DIR%\desktop\resources\python" --workpath "%ROOT_DIR%\desktop\build\backend-build" --clean --noconfirm
    call deactivate
) else (
    echo   Python 后端已存在，跳过打包
)

REM ─── 5. 编译 TypeScript + 打包 Electron ─────────────────
echo.
echo ^>^>^> [5/5] 打包 Electron 应用...
cd /d "%ROOT_DIR%\desktop"
call npm ci
call npx tsc -p tsconfig.main.json 2>nul || echo   [warn] TS compile skipped

REM 使用 electron-packager（避免 electron-builder 的 winCodeSign 符号链接问题）
call npx electron-packager . "弘天文档" --platform=win32 --arch=x64 --overwrite --icon=resources/icon.ico --app-version=4.0.0 --win32metadata.FileDescription="弘天文档" --win32metadata.ProductName="弘天文档" --out=release --prune

if errorlevel 1 (
    echo   [ERROR] electron-packager 失败
    pause
    exit /b 1
)

REM 创建 ZIP 分发包
echo.
echo   创建 ZIP 分发包...
powershell -Command "Compress-Archive -Path '%ROOT_DIR%\desktop\release\弘天文档-win32-x64' -DestinationPath '%ROOT_DIR%\desktop\release\弘天文档-v4.0.0-win32-x64.zip' -Force" 2>nul

echo.
echo === 构建完成 ===
echo 输出目录: %ROOT_DIR%\desktop\release\
dir /b "%ROOT_DIR%\desktop\release\" 2>nul

pause
