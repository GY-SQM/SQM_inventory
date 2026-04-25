# -*- mode: python ; coding: utf-8 -*-
# SQM Inventory v864.3 — PyInstaller Spec (Phase 6)
# 빌드: pyinstaller build/SQM_v864_3.spec --noconfirm
# 출력: build/dist/SQM_v864_3.exe

import os
from pathlib import Path

project_root = Path(os.path.abspath(SPECPATH)).parent

a = Analysis(
    [str(project_root / 'main_webview.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Frontend (HTML/CSS/JS)
        (str(project_root / 'frontend'), 'frontend'),
        # Backend API (FastAPI routes)
        (str(project_root / 'backend'), 'backend'),
        # Business logic modules (v864.2 원본)
        (str(project_root / 'engine_modules'), 'engine_modules'),
        (str(project_root / 'features'),       'features'),
        (str(project_root / 'parsers'),         'parsers'),
        (str(project_root / 'utils'),           'utils'),
        (str(project_root / 'gui_app_modular'), 'gui_app_modular'),
        # 데이터베이스 (초기 DB)
        (str(project_root / 'data' / 'db' / 'sqm_inventory.db'), os.path.join('data', 'db')),
        # 설정/버전 파일
        (str(project_root / 'config.py'),       '.'),
        (str(project_root / 'config_sql.py'),   '.'),
        (str(project_root / 'version.py'),      '.'),
        (str(project_root / 'settings.ini'),    '.'),
    ],
    hiddenimports=[
        # PyWebView (WinForms backend)
        'webview', 'webview.platforms', 'webview.platforms.winforms',
        'clr', 'clr_loader', 'pythonnet',
        'System', 'System.Windows.Forms', 'System.Drawing',
        'System.Threading',
        # FastAPI / Uvicorn / Starlette
        'fastapi', 'fastapi.middleware', 'fastapi.middleware.cors',
        'fastapi.staticfiles', 'fastapi.responses',
        'starlette', 'starlette.responses', 'starlette.staticfiles',
        'starlette.routing', 'starlette.middleware',
        'uvicorn', 'uvicorn.main', 'uvicorn.config',
        'uvicorn.lifespan', 'uvicorn.lifespan.on',
        'uvicorn.protocols', 'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
        'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.loops.asyncio',
        'uvicorn.logging',
        'anyio', 'anyio._backends', 'anyio._backends._asyncio',
        'httptools', 'h11',
        # Data / DB
        'pandas', 'pandas.io.formats.style',
        'openpyxl', 'openpyxl.styles', 'openpyxl.utils',
        'sqlite3',
        # PDF (PyMuPDF)
        'fitz',
        # Project modules
        'engine_modules', 'engine_modules.inventory_modular',
        'engine_modules.inventory_modular.engine',
        'engine_modules.database', 'engine_modules.integrity_engine',
        'features', 'features.parsers', 'features.reports',
        'parsers', 'parsers.base',
        'utils',
        'backend', 'backend.api', 'backend.common', 'backend.common.errors',
        'gui_app_modular',
        # stdlib extras
        'email.mime.multipart', 'email.mime.text', 'email.mime.base',
        'encodings', 'encodings.utf_8', 'encodings.cp949',
        'multiprocessing',
        'pkg_resources', 'pkg_resources.py2_warn',
        'importlib', 'importlib.util', 'importlib.metadata',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Tkinter (v864.2 전용, v864.3에서 불필요)
        'tkinter', 'ttkbootstrap', '_tkinter',
        # 무거운 과학 라이브러리 (사용 안 함)
        'matplotlib', 'scipy', 'numpy.testing',
        'IPython', 'jupyter', 'notebook',
        # PyWebView WinForms 사용 → PyQt5/gtk 제외
        'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
        'PyQt5.QtNetwork', 'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineWidgets',
        'PySide2', 'PySide6',
        'gi', 'gtk', 'qtpy',
        # 테스트/개발 도구
        'pytest', 'playwright', 'setuptools',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SQM_v864_3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # GUI 앱 — 콘솔창 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,               # TODO: ico 파일 있으면 경로 지정
    onefile=True,
)
