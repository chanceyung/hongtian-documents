# -*- mode: python ; coding: utf-8 -*-
"""
弘天文档 — PyInstaller 打包配置

用法:
  cd backend
  pyinstaller ../desktop/hongtian-backend.spec

输出:
  dist/hongtian-backend/  — 包含 Python 运行时 + app + 依赖
"""

import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# 项目根路径
backend_dir = os.path.abspath('.')

# 收集所有隐式依赖
hidden_imports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'aiosqlite',
    'pydantic',
    'pydantic_settings',
    'fastapi',
    'starlette',
    'starlette.responses',
    'starlette.routing',
    'starlette.middleware',
    'starlette.middleware.cors',
    'anyio',
    'sniffio',
    'httpx',
    'httpcore',
    'instructor',
    'openai',
    'tenacity',
    'structlog',
    'bs4',
    'lxml',
    'pptx',
    'docx',
    'openpyxl',
    'fitz',
    'PIL',
    'markdown_it',
    'PyPDF2',
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
]

# WeasyPrint 和 Playwright 是可选的，只在存在时包含
try:
    import weasyprint
    hidden_imports.extend(collect_submodules('weasyprint'))
except ImportError:
    pass

# 前端静态文件目录（相对于 backend_dir 的上一级）
frontend_dir = os.path.join(os.path.dirname(backend_dir), 'desktop', 'resources', 'frontend')

# 数据文件
datas = [
    ('app/templates', 'app/templates'),
    ('app/*.py', 'app'),
]

# 包含前端静态文件（如果存在）
if os.path.isdir(frontend_dir):
    datas.append((frontend_dir, 'app/static'))

# 排除大型不必要的包
excludes = [
    'torch', 'transformers', 'scipy', 'cv2', 'numba', 'llvmlite',
    'sympy', 'skimage', 'pandas', 'matplotlib', 'tkinter', 'tcl',
    'test', 'unittest', 'setuptools', 'pip', 'wheel',
    'docling', 'docling_parse',  # 太大，降级到 PyMuPDF
]

a = Analysis(
    ['app/main.py'],
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

# 排除 torch 等大型二进制文件
def remove_large_binaries(toc_list, patterns):
    """Remove binaries matching patterns to reduce size."""
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