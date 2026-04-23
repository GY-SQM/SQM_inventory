# Phase 6 작업 지시서 — PyInstaller EXE 빌드

> **목적**: SQM v864.3 을 단일 실행 파일(.exe)로 빌드하여 GY Logis 광양 현장 PC 에 배포 가능하게 함.
> **예상 소요**: 1~2시간 (첫 빌드 시) / 15분 (증분)
> **담당**: Claude Code (자동 실행)
> **선행 조건**: Phase 5 완료 (tag `v864.3-phase5`)

---

## 🎯 Definition of Done (DoD)

- [ ] `dist/SQM_v864_3.exe` 생성 (단일 파일, ~100-150MB)
- [ ] EXE 실행 시 PyWebView 창 정상 기동 (API + UI)
- [ ] favicon.ico, frontend/ , data/db/ 가 EXE 에 포함되거나 올바르게 외부 참조
- [ ] 실행 중 sqm_debug.log 가 EXE 옆 폴더에 생성됨
- [ ] `REPORTS/PHASE6_COMPLETE.md` 보고서 작성
- [ ] git 태그 `v864.3-phase6`

---

## 📋 작업 단계

### Step 1 — PyInstaller 설치 확인 (2분)

```bash
pip show pyinstaller 2>nul || pip install pyinstaller>=6.0
pyinstaller --version
# 기대: 6.x.x
```

---

### Step 2 — 빌드 스크립트 실행 (30분, 첫 빌드 기준)

```bash
python scripts/build_exe.py
```

**스크립트가 하는 일**:
1. 기존 `build/`, `dist/` 폴더 삭제 (clean build)
2. `SQM_v864_3.spec` 파일 생성 (아래 내용)
3. `pyinstaller SQM_v864_3.spec --clean --noconfirm` 실행
4. 빌드 성공 확인 (`dist/SQM_v864_3.exe` 존재 + 크기 ≥ 50MB)
5. 빌드 로그를 `REPORTS/phase6_build_<ts>.log` 에 저장

**spec 파일 구조 (build_exe.py 가 자동 생성)**:
```python
# SQM_v864_3.spec
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [
    ('frontend', 'frontend'),
    ('data/db', 'data/db'),  # 초기 DB 템플릿 (선택)
    ('data', 'data'),
    ('config.py', '.'),
    ('config_logging.py', '.'),
    ('config_sql.py', '.'),
]

# engine_modules 전체 + features + parsers 서브모듈 수집
hiddenimports = [
    *collect_submodules('engine_modules'),
    *collect_submodules('features'),
    *collect_submodules('parsers'),
    *collect_submodules('backend'),
]

# 바이너리 의존성
pandas_datas, pandas_binaries, pandas_hidden = collect_all('pandas')
openpyxl_datas, openpyxl_binaries, openpyxl_hidden = collect_all('openpyxl')
webview_datas, webview_binaries, webview_hidden = collect_all('webview')

datas += pandas_datas + openpyxl_datas + webview_datas
binaries = pandas_binaries + openpyxl_binaries + webview_binaries
hiddenimports += pandas_hidden + openpyxl_hidden + webview_hidden

a = Analysis(
    ['main_webview.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'tkinter.test', 'pytest', 'black'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='SQM_v864_3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX 압축 안 함 (윈도우 Defender 오탐 우려)
    runtime_tmpdir=None,
    console=False,  # --noconsole
    disable_windowed_traceback=False,
    icon='frontend/favicon.ico',
)
```

---

### Step 3 — EXE 실행 테스트 (10분)

```bash
cd dist
SQM_v864_3.exe
```

**검증 체크리스트**:
- [ ] 실행 후 3~5초 내 PyWebView 창 열림
- [ ] Dashboard KPI 카드 표시 (오늘 입고/출고/재고 LOT/미배정)
- [ ] 좌측 사이드바 클릭 → Inventory 탭 테이블 표시
- [ ] 메뉴바 "파일 > 수동 입고" → 모달 열림
- [ ] `sqm_debug.log` 가 `dist/` 에 생성됨
- [ ] 종료 시 깨끗하게 닫힘

**자동 검증 스크립트** (선택):
```python
# scripts/verify_exe.py
import subprocess, time, urllib.request, os, sys
proc = subprocess.Popen(['dist/SQM_v864_3.exe'])
time.sleep(10)
try:
    r = urllib.request.urlopen('http://127.0.0.1:8765/api/health', timeout=3)
    assert r.status == 200, f"API 응답 실패: {r.status}"
    print('✅ EXE HEALTHY')
    sys.exit(0)
except Exception as e:
    print(f'❌ EXE FAIL: {e}')
    sys.exit(1)
finally:
    proc.terminate()
```

---

### Step 4 — 실패 시 디버깅 (해당 시)

**증상 A**: EXE 실행 시 즉시 꺼짐 (창 안 뜸)
- 원인: frozen 모드에서 stdout/stderr 리다이렉트 문제
- 해결: `main_webview.py` 의 frozen 분기 확인 (이미 처리됨 — line 32)

**증상 B**: "ImportError: No module named ..."
- 원인: PyInstaller 가 모듈 발견 못 함
- 해결: spec 파일의 `hiddenimports` 에 해당 모듈 추가 → 재빌드

**증상 C**: "sqlite3.OperationalError: unable to open database file"
- 원인: DB 경로 계산 문제 (frozen 에서 sys.executable 기준)
- 해결: `config.py` 의 DB_PATH 가 `sys._MEIPASS` 대응하는지 확인
  ```python
  if getattr(sys, 'frozen', False):
      BASE = os.path.dirname(sys.executable)
  else:
      BASE = os.path.dirname(os.path.abspath(__file__))
  ```

**증상 D**: frontend 파일이 404
- 원인: datas 튜플이 올바르지 않음
- 해결: `main_webview.py` 의 `FRONTEND_DIR` 계산이 frozen 시 `sys._MEIPASS + 'frontend'` 를 찾도록

---

### Step 5 — 보고서 + 커밋 (5분)

**파일**: `REPORTS/PHASE6_COMPLETE.md`
```markdown
# SQM v864.3 — Phase 6 Complete Report
**Date**: <today>
**Status**: ✅ EXE 빌드 성공

## 빌드 결과
- 파일: dist/SQM_v864_3.exe
- 크기: XXX MB
- 빌드 시간: XX분

## 실행 테스트
- [x] PyWebView 창 정상 기동
- [x] API 엔드포인트 응답
- [x] UI 렌더링
- [x] 로그 파일 생성 (sqm_debug.log)

## 배포 준비
- 배포 방법: dist/SQM_v864_3.exe 를 USB 또는 네트워크 공유로 현장 PC에 복사
- 최초 실행 시 data/db/sqm_inventory.db 자동 생성 (또는 기존 DB 사용)
```

**커밋**:
```bash
git add scripts/build_exe.py SQM_v864_3.spec REPORTS/PHASE6_COMPLETE.md REPORTS/phase6_build_*.log
# dist/ 는 .gitignore 에 추가 (바이너리 커밋 안 함)
echo "dist/" >> .gitignore
echo "build/" >> .gitignore
git add .gitignore

git commit -m "$(cat <<'EOF'
build(v864.3): Phase 6 PyInstaller EXE 빌드 완성

- scripts/build_exe.py: clean build 자동화 스크립트
- SQM_v864_3.spec: PyInstaller 설정 (onefile, noconsole, favicon)
- dist/SQM_v864_3.exe 생성 (XXX MB) — GY Logis 현장 배포 준비 완료

.gitignore: dist/, build/ 추가

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"

git tag v864.3-phase6
```

---

## 🔄 자동 진입 조건 (Phase 7)

- [x] `dist/SQM_v864_3.exe` 존재 및 크기 > 50MB
- [x] `git tag v864.3-phase6` 성공
- [x] EXE 실행 테스트 PASS

→ `REPORTS/PHASE7_PLAN.md` 로 이동.

**⚠️ 주의**: Phase 7 은 사장님(Nam Ki-dong) 주도 실사용 기간이므로, Claude Code 는 **PHASE7_PLAN.md 를 생성만** 하고 **일일 체크리스트 대기**. 자동 진행 X.
