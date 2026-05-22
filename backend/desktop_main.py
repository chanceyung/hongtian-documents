"""弘天文档 — 桌面版启动器"""
import os
import sys

os.environ["DESKTOP_MODE"] = "true"
os.environ["PYTHONUNBUFFERED"] = "1"

if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
    os.environ["MAGAZINE_TEMPLATES_DIR"] = os.path.join(application_path, "app", "templates")
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

import webbrowser
import threading
import time

def open_browser(port):
    time.sleep(2)
    url = f"http://127.0.0.1:{port}"
    print(f"\n  浏览器即将打开: {url}\n")
    webbrowser.open(url)

def main():
    import uvicorn
    from app.core.config import settings
    from app.main import app
    port = int(os.environ.get("PORT", "8000"))
    print("=" * 50)
    print("  弘天文档 v4.0 — 杂志级文档重构智能体")
    print("=" * 50)
    print(f"  后端地址: http://127.0.0.1:{port}")
    print(f"  按 Ctrl+C 退出")
    print("=" * 50)
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )

if __name__ == "__main__":
    main()