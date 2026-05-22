# -*- mode: python ; coding: utf-8 -*-
"""弘天文档桌面版 PyInstaller 打包配置"""
import os
import glob
from pathlib import Path

backend_dir = os.path.abspath('.')
app_dir = os.path.join(backend_dir, 'app')

hidden_imports = [
    'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
    'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan', 'uvicorn.lifespan.on',
    'aiosqlite', 'pydantic', 'pydantic_settings', 'pydantic.deprecated.class_validators',
    'fastapi', 'starlette', 'starlette.responses', 'starlette.routing',
    'starlette.middleware', 'starlette.middleware.cors', 'starlette.staticfiles',
    'anyio', 'sniffio', 'httpx', 'httpcore',
    'instructor', 'openai', 'tenacity', 'structlog',
    'bs4', 'lxml', 'html5lib', 'html.parser',
    'pptx', 'docx', 'openpyxl', 'fitz', 'PIL', 'markdown_it', 'PyPDF2',
    'cryptography', 'cryptography.fernet', 'cryptography.hazmat',
    'cryptography.hazmat.primitives', 'cryptography.hazmat.primitives.kdf',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
    'weasyprint',
    'email.mime.multipart', 'email.mime.text',
    # 所有 app 子模块
    'app', 'app.main', 'app.middleware', 'app.exceptions',
    'app.core', 'app.core.config', 'app.core.database', 'app.core.redis',
    'app.core.cache', 'app.core.logging', 'app.core.retry', 'app.core.task_tracker',
    'app.core.kv_store',
    'app.models', 'app.models.unified_document', 'app.models.edit_actions', 'app.models.design_spec',
    'app.parsers', 'app.parsers.pptx_parser', 'app.parsers.pdf_parser',
    'app.parsers.docx_parser', 'app.parsers.xlsx_parser', 'app.parsers.md_parser',
    'app.agents', 'app.agents.parser_agent', 'app.agents.analyzer_agent',
    'app.agents.designer_agent', 'app.agents.renderer_agent',
    'app.agents.fidelity_agent', 'app.agents.supplement_agent',
    'app.exporters', 'app.exporters.pdf_renderer',
    'app.exporters.ppt_master', 'app.exporters.ppt_master.svg_to_pptx',
    'app.exporters.ppt_master.finalize_svg',
    'app.workflow', 'app.workflow.magazine_pipeline',
    'app.api', 'app.api.router', 'app.api.v1',
    'app.services', 'app.services.zhipu_client',
]

excludes = [
    'torch', 'transformers', 'scipy', 'cv2', 'numba', 'llvmlite',
    'sympy', 'skimage', 'pandas', 'matplotlib', 'tkinter', 'tcl',
    'setuptools', 'pip', 'wheel',
    'docling', 'docling_parse', 'langgraph', 'langsmith',
    'pytest', '_pytest',
]

# 收集 app 包的所有 Python 文件
datas = []
for py_file in glob.glob(os.path.join(app_dir, '**', '*.py'), recursive=True):
    rel_path = os.path.relpath(py_file, backend_dir)
    datas.append((py_file, os.path.dirname(rel_path)))

# 添加模板和静态文件
datas.append((os.path.join(app_dir, 'templates'), 'app/templates'))
if os.path.exists(os.path.join(app_dir, 'static', 'index.html')):
    datas.append((os.path.join(app_dir, 'static'), 'app/static'))

print(f"Collecting {len(datas)} data entries")
print(f"Collecting {len(hidden_imports)} hidden imports")

a = Analysis(
    ['desktop_main.py'],
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
    cipher=None,
    noarchive=False,
)

# 移除大型二进制
def filter_binaries(toc, patterns):
    return [t for t in toc if not any(p in t[0].lower() for p in patterns)]

large = ['torch', 'numpy.libs', 'mkl', 'libopenblas', 'scipy', 'cv2', 'libtorch']
a.binaries = filter_binaries(a.binaries, large)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='弘天文档',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='弘天文档',
)