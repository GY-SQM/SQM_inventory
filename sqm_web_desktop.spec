# -*- mode: python ; coding: utf-8 -*-
"""
SQM Web Desktop — pywebview + React + FastAPI .exe
배치: sqm_web_desktop.spec
빌드: pyinstaller sqm_web_desktop.spec
결과: dist/SQM_Web/SQM_Web.exe
"""
from pathlib import Path
PROJECT = Path(SPECPATH)

# React 빌드 파일 포함 (필수)
react_dist = PROJECT / 'web' / 'dist'
if not react_dist.exists():
    raise RuntimeError(
        "React 빌드 파일 없음!\n"
        "먼저 실행: cd web && npm run build"
    )

datas = [
    (str(react_dist),            'web/dist'),       # React 빌드
    (str(PROJECT / 'data'),      'data'),           # DB
    (str(PROJECT / '.env'),      '.'),              # 설정
    (str(PROJECT / 'react_api'), 'react_api'),      # FastAPI
    (str(PROJECT / 'engine_modules'), 'engine_modules'),
    (str(PROJECT / 'core'),      'core'),
    (str(PROJECT / 'features'),  'features'),
]

# .env 없으면 건너뜀
for i, (src, dst) in enumerate(datas):
    if not Path(src).exists():
        print(f"[경고] 없음: {src}")

datas = [(s,d) for s,d in datas if Path(s).exists()]

hiddenimports = [
    'webview', 'webview.platforms',
    'uvicorn', 'uvicorn.config', 'uvicorn.main',
    'fastapi', 'starlette', 'pydantic',
    'httpx', 'anyio', 'sniffio',
    'sqlite3',
    'pandas', 'openpyxl', 'numpy',
    'PIL', 'PIL.Image',
    'google.generativeai',
    'engine_modules.database',
    'engine_modules.inventory_modular.engine',
    'react_api.main',
]

a = Analysis(
    [str(PROJECT / 'run_desktop.py')],
    pathex=[str(PROJECT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=['tkinter', 'ttkbootstrap', 'matplotlib', 'scipy', 'pytest'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='SQM_Web',
    debug=False,
    console=False,   # 콘솔 숨김
    upx=True,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True,
    name='SQM_Web',
)
