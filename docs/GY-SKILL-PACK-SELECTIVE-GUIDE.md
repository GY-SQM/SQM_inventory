# GY 스킬팩 v1.5 — SQM 재고관리 선별 적용 가이드

> 작성일: 2026-07-21
> 대상: `D:\program\sqm\SQM_inventory` (SQM_inventory v8.8.5)
> 전제: `C:\Users\남기동\.claude\` 에 GY 스킬팩 v1.5가 **이미 전부 설치된 상태**
> 위치 확인: `Get-ChildItem C:\Users\남기동\.claude\skills\gy-*` → 9개 모두 존재
> 위치 확인: `Get-ChildItem C:\Users\남기동\.claude\constitutions\` → 5개 모두 존재
> 위치 확인: `Get-ChildItem C:\Users\남기동\.claude\agents\` → 6개 모두 존재

---

## 🎯 한 줄 결론

**통째로 다 쓰지 마라. SQM 스택에 맞는 6개 + 맞지 않는 11개를 분리해서 써라.**

SQM은 이미 자체 PDCA 시스템(`DEBUG_GOALS.md`)을 운영 중이라
GY의 일부 기능은 이중화되어 오히려 혼란을 만든다.

---

## ✅ SQM에 적용 (쓸 것) — 6개

### 헌법 (2개)
| 파일 | 용도 | SQM 매칭 |
|---|---|---|
| `~/.claude/constitutions/common.md` | Python 일반 코딩 규칙 | ✅ 전 모듈 공통 |
| `~/.claude/constitutions/fastapi.md` | FastAPI 백엔드 규칙 | ✅ `backend/api/` FastAPI 직접 사용 |

### 스킬 (3개)
| 스킬 | 용도 | SQM 적용 포인트 |
|---|---|---|
| `gy-improve` | 자가개선 루프 (실행→관찰→가설→수정→재검증) | `sqm_debug.log` 15MB, v8.7→v8.8 다수 패치 이력 정돈 |
| `gy-audit` | 배포 전 보안·라이선스·개인정보 감사 | 외부 배포 전 체크리스트 |
| `gy-handover` | 직원용 한글 사용설명서 + 인수인계 자동 생성 | 광양 창고 직원 교육용 |

### 에이전트 (3개) — 독립 검증 자동화
| 에이전트 | 용도 | SQM 적용 포인트 |
|---|---|---|
| `verifier` | 빌드 후 산출물 독립 검증 | `main_webview.py` 변경 후 회귀 점검 |
| `tester` | 테스트 시나리오 자동 생성/실행 | `tests/` 보강, 회귀 테스트 추가 |
| `security-auditor` | 시크릿·하드코딩 키·SQL 인젝션 감사 | SQLite 직접 쿼리 + 외부 API 키 점검 |

---

## ❌ SQM에 적용 금지 (안 쓸 것) — 11개

### ❌ 헌법 (3개) — 스택 불일치
| 파일 | 안 쓰는 이유 |
|---|---|
| `~/.claude/constitutions/pyside6.md` | SQM은 PySide6 안 씀 (PyWebView + HTML/JS) |
| `~/.claude/constitutions/nextjs.md` | SQM 프론트는 순수 HTML/JS (Next.js 아님) |
| `~/.claude/constitutions/supabase-edge.md` | SQM은 SQLite 로컬 DB (Supabase 안 씀) |

### ❌ 스킬 (6개) — 이중화 또는 미스매치
| 스킬 | 안 쓰는 이유 |
|---|---|
| `gy-start` | 진입 라우터 — 이미 SQM은 `CLAUDE.md`가 진입점 |
| `gy-plan` | 아이디어 기획 — SQM은 이미 운영 중 프로젝트, 신규 기획 단계 아님 |
| `gy-spec` | 화면 명세·태스크 분해 — **`DEBUG_GOALS.md`가 이미 그 역할** |
| `gy-orchestrate` | tasks.md 자동 실행 — **`DEBUG_GOALS.md` 골 시스템과 중복** |
| `gy-harness` | 빌드+독립검증 — verifier/tester 에이전트로 대체 가능 |
| `gy-release` | 백업·버전·빌드·동기화 — `RELEASE_NOTES_v*.md` 수동 운영 중, 강제 개입 불필요 |

### ❌ 에이전트 (2개) — 스택 불일치
| 에이전트 | 안 쓰는 이유 |
|---|---|
| `builder-frontend` | Next.js 기반 전제 — SQM 프론트와 안 맞음 |
| `builder-database` | Supabase/PostgreSQL 가정 — SQM은 SQLite, `builder-backend`이 처리 |

> 참고: `builder-backend`는 FastAPI 매칭이니 사용 가능. 단, `engine_modules/` 구조와 충돌 가능성 있어 **소규모 보강 작업에만** 사용 권장.

---

## 📐 적용 순서 (4단계)

### 1단계: 헌법 연결
SQM `CLAUDE.md` 상단에 아래 두 줄 추가:
```markdown
## 헌법
- `C:\Users\남기동\.claude\constitutions\common.md` 규칙을 따른다
- `C:\Users\남기동\.claude\constitutions\fastapi.md` 규칙을 따른다
```

### 2단계: 디버깅 백로그 흡수
```powershell
# SQM 폴더에서
cd D:\program\sqm\SQM_inventory
# DEBUG_GOALS.md 의 첫 미체크 골을 gy-improve 루프로 끝까지 진행
```
> 지시 예: "DEBUG_GOALS.md 첫 미체크 골을 gy-improve 패턴으로 끝까지 밀어줘."

### 3단계: 배포 전 감사 (릴리즈 직전 1회)
```powershell
# SQM 폴더에서
# gy-audit 스킬 발동
```
> 체크리스트: 시크릿 누출 / 하드코딩 키 / SQL 인젝션 / 의존성 CVE / 라이선스

### 4단계: 인수인계 문서 생성 (필요 시)
```powershell
# 광양 창고 직원 교육용
# gy-handover 스킬 발동
```

---

## 🧪 빠른 점검 (PowerShell)

```powershell
# 1) 설치 상태 확인
Get-ChildItem C:\Users\남기동\.claude\skills\gy-* | Select-Object Name
Get-ChildItem C:\Users\남기동\.claude\constitutions | Select-Object Name
Get-ChildItem C:\Users\남기동\.claude\agents | Select-Object Name

# 2) SQM 미커밋 정리
cd D:\program\sqm\SQM_inventory
git status
# CLAUDE.md 한글 깨짐 복구본은 커밋 권장 (origin/main엔 깨진 채로 있음)

# 3) 회귀 테스트 베이스라인
python -m pytest tests/ -q `
  --deselect tests/test_phase1_db_index.py::test_real_db_has_indexes
```

---

## ⚠️ 주의사항

1. **`.bkit` 폴더 충돌**: SQM에 이미 `.bkit`, `.brainstorm`, `.claude` 흔적이 있음. bkit은 GY 스킬팩의 전신/평행 프로젝트로, 명령어 충돌 가능. 동시에 활성화하지 말 것.
2. **`gy-spec` / `gy-orchestrate` 충돌**: `DEBUG_GOALS.md` 골 형식 vs GY의 tasks.md 형식이 다름. 한쪽만 쓸 것. SQM엔 이미 `DEBUG_GOALS.md`가 있어 GY 측을 비활성.
3. **강제 개입 회피**: `gy-release`의 자동 백업·버전업은 SQM의 수동 `RELEASE_NOTES` 작업과 충돌. 운영자 판단 하에 수동 병행.
4. **Windows 전용 실행**: SQM 앱 자체는 `r1.vbs` → `main_webview.py` (PyWebView) — Windows 전용. GY 스킬 적용은 코드/문서 단계로, GUI 실행은 별도.

---

## 📊 요약 표

| 분류 | 총 설치 | SQM 사용 | SQM 미사용 |
|---|---|---|---|
| 헌법 | 5 | 2 (common, fastapi) | 3 (pyside6, nextjs, supabase-edge) |
| 스킬 | 9 | 3 (improve, audit, handover) | 6 (start, plan, spec, orchestrate, harness, release) |
| 에이전트 | 6 | 3 (verifier, tester, security-auditor) | 2 (builder-frontend, builder-database) + 1 조건부 (builder-backend) |
| **합계** | **20** | **8** | **12** |

---

## 🔄 롤백

만약 GY 적용 후 충돌이 심하면:
```powershell
# SQM 폴더의 .bkit/.brainstorm 메타 폴더만 정리 (코드는 손대지 않음)
Remove-Item -Recurse -Force D:\program\sqm\SQM_inventory\.bkit
Remove-Item -Recurse -Force D:\program\sqm\SQM_inventory\.brainstorm
# CLAUDE.md에서 헌법 참조 2줄 제거
# SQM 자체 PDCA(DEBUG_GOALS.md)는 그대로 유지
```

이 가이드 자체는 **추천사항**일 뿐, 강제는 아님.
SQM은 이미 자체 시스템으로 잘 굴러가는 프로젝트라 GY는 "보조 도구"로만 쓸 것.
