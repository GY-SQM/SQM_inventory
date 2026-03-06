# CONTRIBUTING.md — SQM 재고관리 시스템

> **(주) 지와이로지스 — SQM Inventory Management System v4.0.3**

---

## 1. 브랜치 전략

```
main (Production)
│   ← PR 머지로만 배포. 직접 push 금지.
│
├── develop (Staging)
│   ← 기능 개발 완료 후 머지. 테스트 통과 필수.
│   │
│   ├── feature/기능명    ← 신규 기능 개발
│   │   예: feature/multi-user-network
│   │       feature/qr-code-scan
│   │
│   ├── fix/버그명        ← 버그 수정
│   │   예: fix/lot-duplicate-check
│   │       fix/excel-export-encoding
│   │
│   └── refactor/대상     ← 리팩토링
│       예: refactor/pivot-tab-split
│           refactor/database-migration
│
└── hotfix/긴급명         ← main에서 직접 분기 (긴급 수정)
    예: hotfix/db-corruption-fix
```

### 브랜치 규칙

| 규칙 | 설명 |
|------|------|
| `main` 직접 push 금지 | 반드시 PR → 리뷰 → 머지 |
| `develop`에서 feature 분기 | `git checkout -b feature/기능명 develop` |
| feature 완료 → develop PR | 테스트 통과 + 컴파일 검증 필수 |
| develop → main 릴리스 | version.py 업데이트 + 태그 생성 |
| hotfix는 main에서 분기 | 완료 후 main + develop 양쪽 머지 |

### 일반적인 작업 흐름

```bash
# 1. 기능 개발 시작
git checkout develop
git pull origin develop
git checkout -b feature/lot-qr-code

# 2. 작업 + 커밋
git add -A
git commit -m "feat: LOT QR코드 생성 기능 추가"

# 3. develop으로 PR
git push origin feature/lot-qr-code
# → GitHub에서 PR 생성 (develop ← feature/lot-qr-code)

# 4. 리뷰 + 머지 후 브랜치 삭제
git checkout develop
git pull origin develop
git branch -d feature/lot-qr-code

# 5. 릴리스 (develop → main)
git checkout main
git merge develop
git tag -a v4.1.0 -m "v4.1.0: LOT QR코드"
git push origin main --tags
```

---

## 2. 커밋 메시지 규칙

```
<타입>: <설명> (50자 이내)

<본문> (선택, 72자 줄바꿈)
```

### 타입

| 타입 | 용도 | 예시 |
|------|------|------|
| `feat` | 신규 기능 | `feat: 출고 진행률 프로그레스 바 추가` |
| `fix` | 버그 수정 | `fix: LOT 중복 입고 시 All-or-Nothing 위반` |
| `refactor` | 리팩토링 | `refactor: pivot_tab.py 분할 (963+530줄)` |
| `test` | 테스트 추가 | `test: InboundDialogBase 유닛 테스트 7건` |
| `docs` | 문서 | `docs: CONTRIBUTING.md 작성` |
| `style` | 코드 스타일 | `style: 한글 헤더 → 영문 대문자 통일` |
| `perf` | 성능 개선 | `perf: 대시보드 threaded 갱신` |
| `chore` | 빌드/설정 | `chore: .gitignore 업데이트` |

---

## 3. 코드 품질 기준

### 필수 (머지 전 통과)

| 항목 | 기준 | 검증 방법 |
|------|------|----------|
| 컴파일 | 전체 .py 100% 통과 | `python -m py_compile 파일명` |
| bare except | 0건 | `grep -rn "except:" --include="*.py"` |
| Exception+pass | 0건 (logger.debug 사용) | `grep -A1 "except" \| grep "pass$"` |
| camelCase 변수 | 0건 | CODING_STYLE.md 참조 |
| 테스트 | 신규 Mixin마다 테스트 추가 | `pytest tests/` |

### 권장

| 항목 | 기준 |
|------|------|
| 파일 크기 | 800줄 이하 (초과 시 분할 검토) |
| 함수 길이 | 50줄 이하 |
| Docstring | 모든 public 메서드에 작성 |
| Type Hint | 함수 인자/반환값에 명시 |

---

## 4. 릴리스 절차

```
1. develop 브랜치에서 모든 기능 머지 완료
2. version.py 버전 업데이트
3. CHANGELOG 작성 (VERSION_HISTORY 딕셔너리)
4. 전체 컴파일 검증 (220+ 파일)
5. 테스트 실행 (pytest tests/)
6. develop → main PR 생성
7. 머지 후 태그: git tag -a v4.x.x
8. ZIP 패키지 생성 + 배포
```

### 버전 번호 규칙

```
v메이저.마이너.패치

메이저: 대규모 변경 (아키텍처, DB 스키마)  예: v4.0.0
마이너: 기능 추가                          예: v4.1.0
패치:   버그 수정, 소규모 개선             예: v4.0.3
```

---

## 5. 디렉토리 구조

```
sqm/
├── run.py                  ← 진입점
├── version.py              ← 버전 (Single Source of Truth)
├── config.py               ← 설정 관리
├── engine.py               ← 엔진 초기화
├── engine_modules/          ← DB, 인벤토리 로직
│   ├── database.py
│   ├── db_migration_mixin.py
│   ├── db_validation_mixin.py
│   └── inventory_modular/   ← 11개 Mixin
├── gui_app_modular/         ← GUI (tkinter)
│   ├── main_app.py          ← 앱 클래스
│   ├── tabs/                ← 탭 UI + 로직 Mixin
│   ├── handlers/            ← 이벤트 핸들러 + Mixin
│   ├── dialogs/             ← 팝업 다이얼로그
│   ├── mixins/              ← UI Mixin (메뉴, 툴바, 상태바)
│   └── utils/               ← 상수, 스타일, 유틸
├── parsers/                 ← PDF/Excel 파서
├── features/ai/             ← Gemini AI 연동
├── tests/                   ← pytest 테스트 (68개 파일)
├── docs/                    ← 문서
├── data/db/                 ← SQLite DB + 백업
└── _archive/                ← 제거된 데드 코드 보관
```

---

## 6. 필수 도구

| 도구 | 용도 | 설치 |
|------|------|------|
| Python 3.10+ | 런타임 | — |
| pytest | 테스트 | `pip install pytest` |
| openpyxl | Excel 처리 | `pip install openpyxl` |
| pdfplumber | PDF 파싱 | `pip install pdfplumber` |
| reportlab | PDF 생성 | `pip install reportlab` |
| keyring | API 키 보안 | `pip install keyring` |
| ttkbootstrap | UI 테마 | `pip install ttkbootstrap` |

---

*최종 수정: 2026-02-09 | SQM v4.0.3*
