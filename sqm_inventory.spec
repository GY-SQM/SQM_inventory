# -*- mode: python ; coding: utf-8 -*-
"""
SQM 재고관리 시스템 - PyInstaller 설정
버전: 3.8.3
"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('settings.ini', '.'),
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SQM_Inventory_v3.8.3',
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
    icon='assets/icon.ico' if (PROJECT_ROOT / 'assets/icon.ico').exists() else None,
)
