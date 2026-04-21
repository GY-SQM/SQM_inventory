# -*- mode: python ; coding: utf-8 -*-
# SQM Inventory v864.3 — PyInstaller Spec
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
        # Business logic modules (v864.2 원본 — 수정 없이 그대로 포함)
        (str(project_root / 'engine_modules'), 'engine_modules'),
        (str(project_root / 'features'),       'features'),
        (str(project_root / 'parsers'),         'parsers'),
        (str(project_root / 'utils'),           'utils'),
        # 설정 파일
        (str(project_root / 'config.py'),       '.'),
        (str(project_root / 'settings.ini'),    '.'),
    ],
    hiddenimports=[
        # PyWebView
        'webview', 'webview.platforms', 'webview.platforms.winforms',
        'clr', 'System', 'System.Windows.Forms',
        # FastAPI / Uvicorn
        'fastapi', 'fastapi.middleware.cors',
        'uvicorn', 'uvicorn.main', 'uvicorn.config',
        'uvicorn.lifespan.on', 'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.loops.auto',
        # Data
        'pandas', 'openpyxl', 'openpyxl.styles', 'sqlite3',
        # Project modules
        'engine_modules', 'features', 'parsers', 'utils',
        'backend', 'backend.api',
        # stdlib extras
        'email.mime.multipart', 'email.mime.text',
        'pkg_resources.py2_warn',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'ttkbootstrap',
        'matplotlib', 'scipy', 'numpy.testing',
        'IPython', 'jupyter',
        # PyWebView WinForms 백엔드 사용 → PyQt5/gtk 제외
        'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
        'PyQt5.QtNetwork', 'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineWidgets',
        'gi', 'gtk', 'qtpy',
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
