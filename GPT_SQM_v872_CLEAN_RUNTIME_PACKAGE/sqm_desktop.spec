# -*- mode: python ; coding: utf-8 -*-
"""
SQM v8.7.1 PyInstaller 스펙 v2
Q1: run.py → run_bootstrap.py 자동 폴백
Q3: 광양 PC에서 Python 없이 실행 보장
    - 상대경로 DB 설정
    - .env 자동 포함
    - data/ 폴더 내장
"""
import os
import sys
from pathlib import Path

PROJECT = Path(SPECPATH)

# ── Q1: 진입점 자동 감지 ─────────────────────────────────────
# run.py → run_bootstrap.py 순서로 폴백
ENTRY = None
for candidate in ['run.py', 'run_bootstrap.py', 'gui_app_modular/__main__.py']:
    if (PROJECT / candidate).exists():
        ENTRY = str(PROJECT / candidate)
        print(f"[SQM Spec] 진입점: {candidate}")
        break

if ENTRY is None:
    raise RuntimeError("진입점 파일을 찾을 수 없습니다 (run.py / run_bootstrap.py 없음)")

# ── Q3: 광양 PC 실행 보장 — 포함 데이터 ─────────────────────
datas = []

# DB 디렉토리 (상대경로 유지)
db_dir = PROJECT / 'data'
if db_dir.exists():
    datas.append((str(db_dir), 'data'))
else:
    # data 폴더 없으면 빈 폴더라도 포함
    db_dir.mkdir(parents=True, exist_ok=True)
    (db_dir / 'db').mkdir(exist_ok=True)
    datas.append((str(db_dir), 'data'))

# .env 설정 파일
env_file = PROJECT / '.env'
if env_file.exists():
    datas.append((str(env_file), '.'))

# 설정 파일들
for cfg in ['config.py', 'version.py']:
    f = PROJECT / cfg
    if f.exists():
        datas.append((str(f), '.'))

# GUI 리소스 데이터
gui_data = PROJECT / 'gui_app_modular' / 'utils' / 'data'
if gui_data.exists():
    datas.append((str(gui_data), 'gui_app_modular/utils/data'))

# backup 디렉토리
backup_dir = PROJECT / 'backup'
backup_dir.mkdir(exist_ok=True)
datas.append((str(backup_dir), 'backup'))

# logs 디렉토리
logs_dir = PROJECT / 'logs'
logs_dir.mkdir(exist_ok=True)
datas.append((str(logs_dir), 'logs'))

print(f"[SQM Spec] 포함 데이터: {len(datas)}개")

# ── 숨겨진 import ────────────────────────────────────────────
hiddenimports = [
    # UI
    'tkinter', 'tkinter.ttk', 'tkinter.messagebox',
    'tkinter.filedialog', 'tkinter.simpledialog',
    'ttkbootstrap', 'ttkbootstrap.themes',
    'ttkbootstrap.constants',
    # 이미지
    'PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL.ImageDraw',
    # DB
    'sqlite3',
    # 데이터
    'pandas', 'openpyxl', 'openpyxl.styles',
    'numpy',
    # PDF
    'reportlab', 'reportlab.pdfgen', 'reportlab.lib',
    'pdfplumber', 'fitz',
    # 보안
    'keyring', 'keyring.backend',
    # 네트워크
    'requests', 'urllib3',
    # AI
    'google.generativeai',
    # SQM 모듈
    'engine_modules',
    'engine_modules.database',
    'engine_modules.inventory_modular',
    'engine_modules.inventory_modular.engine',
    'gui_app_modular',
    'gui_app_modular.main_app',
]

# ── 분석 ─────────────────────────────────────────────────────
a = Analysis(
    [ENTRY],
    pathex=[str(PROJECT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # 불필요 → 크기 감소
        'matplotlib', 'scipy', 'sklearn', 'tensorflow',
        'IPython', 'jupyter', 'notebook',
        'pytest', 'hypothesis',
        # API 서버 (Tkinter 앱에는 불필요)
        'uvicorn', 'fastapi', 'starlette', 'httpx',
        'aiohttp', 'aiofiles',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SQM',
    debug=False,
    strip=False,
    upx=True,
    console=False,   # 콘솔 창 숨김 (GUI 앱)
    # icon=str(PROJECT / 'gui_app_modular' / 'utils' / 'data' / 'sqm_icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='SQM',
)
