# -*- mode: python ; coding: utf-8 -*-
"""
弘天文档 — PyInstaller 打包配置

用法:
  cd backend
  pyinstaller ../desktop/hongtian-backend.spec --distpath ../desktop/resources/python --workpath ../desktop/build/backend-build --clean --noconfirm
"""
import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# SPECPATH 由 PyInstaller 注入，指向 spec 文件所在目录
backend_dir = os.path.normpath(os.path.join(SPECPATH, '..', 'backend'))

hidden_imports = [
    # uvicorn
    'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
    'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan', 'uvicorn.lifespan.on',
    # web framework
    'fastapi', 'starlette', 'starlette.responses', 'starlette.routing',
    'starlette.middleware', 'starlette.middleware.cors',
    # data
    'aiosqlite', 'pydantic', 'pydantic_settings',
    'zstandard', 'multidict', 'frozenlist',
    # http
    'httpx', 'httpcore', 'anyio', 'sniffio', 'h11',
    # llm
    'openai', 'instructor', 'tenacity', 'jinja2',
    # parsing
    'bs4', 'lxml', 'lxml.etree', 'lxml._elementpath',
    'pptx', 'docx', 'openpyxl', 'fitz', 'PIL',
    'markdown_it', 'PyPDF2',
    # crypto
    'cryptography', 'cryptography.fernet',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
    # logging & monitoring
    'structlog', 'prometheus_client',
    # pkg_resources namespace support
    'pkg_resources', 'jaraco.text', 'jaraco.functools',
    'jaraco.classes', 'jaraco.context',
]

# 动态收集 langgraph 相关子模块
for pkg in ['langgraph', 'langgraph.graph', 'langgraph.constants',
            'langgraph.pregel', 'langgraph.types']:
    try:
        hidden_imports.extend(collect_submodules(pkg))
    except Exception:
        hidden_imports.append(pkg)

# 前端静态文件（仅 Electron 桌面模式用）
frontend_dir = os.path.join(os.path.dirname(backend_dir), 'desktop', 'resources', 'frontend')

datas = [
    (os.path.join(backend_dir, 'app', 'templates'), 'app/templates'),
]
if os.path.isdir(frontend_dir):
    datas.append((frontend_dir, 'app/static'))

excludes = [
    'torch', 'transformers', 'scipy', 'cv2', 'numba', 'llvmlite',
    'sympy', 'skimage', 'pandas', 'matplotlib', 'tkinter', 'tcl',
    'test', 'unittest', 'docling', 'docling_parse',
    'playwright', 'weasyprint',
]

a = Analysis(
    [os.path.join(backend_dir, 'app', 'main.py')],
    pathex=[backend_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

def remove_large_binaries(toc_list, patterns):
    filtered = []
    for item in toc_list:
        skip = False
        for pattern in patterns:
            if pattern in item[0].lower():
                skip = True
                break
        if not skip:
            filtered.append(item)
    return filtered

large_patterns = ['torch', 'numpy.libs', 'mkl', 'libopenblas', 'scipy', 'cv2']
a.binaries = remove_large_binaries(a.binaries, large_patterns)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='hongtian-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='hongtian-backend',
)
