# -*- mode: python ; coding: utf-8 -*-
"""
SQM 재고관리 시스템 - PyInstaller 설정
버전은 version.py에서 관리 (Single Source of Truth)
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH)
sys.path.insert(0, str(PROJECT_ROOT))
from version import __version__

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('docs/*.md', 'docs'),
    ],
    hiddenimports=[
        'pandas',
        'openpyxl',
        'reportlab',
        'PIL',
        'ttkbootstrap',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['test', 'tests'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

_icon_path = PROJECT_ROOT / 'assets' / 'icon.ico'

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=f'SQM_Inventory_v{__version__}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(_icon_path) if _icon_path.exists() else None,
)
