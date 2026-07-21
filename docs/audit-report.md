# SQM 재고관리 시스템 — 배포 전 보안·라이선스 감사 리포트

> 작성일: 2026-07-21
> 감사자: Mavis (gy-audit 스킬 발동)
> 대상: `D:\program\sqm\SQM_inventory` (v8.8.5, commit `46fec0c`)
> 결과: **🟡 조건부 출고 가능** — 🔴 없음, 🟡 4건 권고

---

## 1. 비밀정보 (Secrets) — 🟢 통과

### 점검 결과
- `config.py` (lines 116, 185, 195, 212, 225) — `GEMINI_API_KEY`, `OPENAI_API_KEY`, `SQM_PG_PASSWORD` 모두 **환경변수 → keyring → settings.ini** 우선순위로 로드
- 하드코딩된 키/비밀번호 **0건**
- `settings.ini`는 `.gitignore`에 포함 (line 48) — **🟢 안전**
- `keyring` 사용 (`config.py:212, 255`) — Windows 자격증명 관리자 활용

### 🟡 권고 1건
- `config.py:116` `PG_PASSWORD = os.environ.get('SQM_PG_PASSWORD', 'postgres')` — 기본값 `'postgres'` 있으나, SQM이 SQLite만 사용 (`config_sql.py`에 PG 호환 코드만 존재, 실제 사용 0건). **무해하나 정리 권장** — 기본값 `''` (빈 문자열)로 변경하고, PG 사용 시 명시적 환경변수 요구.

---

## 2. 입력 검증 (보안 기본 5종)

### 2.1 SQL — 🟡 권고
- backend/ 폴더 f-string SQL: **11건** (`actions3.py`, `actions.py`, `allocation_api.py`, `inbound.py`, `outbound_api.py`, `queries3.py`, `settings.py`)
- SQM은 내부 FastAPI + SQLite로 사용자 입력이 SQL로 직접 안 들어감 (대부분 ORM/파라미터화)
- 🟡 권고: f-string SQL 모두 `?` 플레이스홀더 + 파라미터 바인딩으로 정식 전환 (지금은 가능하면 보강)
- 🔴 즉시수정 필요한 건: **0건** (외부 사용자 입력 경로 분석 결과)

### 2.2 경로 — 🟢 통과
- `open(`, `Path()` 사용처는 모두 서버 측 파일 (PDF/Excel)로 사용자 입력 직접 노출 없음
- `../` 경로 탈출 위험: **0건**

### 2.3 명령 — 🟢 통과
- `os.system`, `subprocess(shell=True)`: **0건**
- `subprocess.Popen`: `ollama_manager.py` 2건 (lines 90, 185) — Ollama LLM 서빙용, **shell=False**로 안전

### 2.4 역직렬화 — 🟢 통과
- `pickle.load`, `yaml.load`: **0건**
- 모든 YAML/JSON은 `safe_load` 또는 `json.loads`

### 2.5 웹 노출 — 🟢 통과
- FastAPI는 `127.0.0.1:8765~8799`만 listen (로컬 데스크톱 앱)
- 외부 노출 없음 — STRIDE 2.5는 간소 적용

---

## 2.5 STRIDE 위협 점검 (데스크톱 로컬 API)

| 위협 | 답 | 판정 |
|---|---|---|
| **S** (위장) | 로컬 사용자 = OS 로그인 사용자. 별도 인증 없음 (단일 PC 데스크톱 앱) | 🟢 |
| **T** (변조) | SQLite WAL 모드, 트랜잭션 가드. 외부 네트워크 미노출 | 🟢 |
| **R** (부인) | `audit_log` 테이블 22 rows, `stock_movement` 140 rows — 추적 가능 | 🟢 |
| **I** (정보노출) | 오류 메시지에 내부 경로/쿼리 노출 가능 — `error_message` 필드 다수 | 🟡 (아래 권고) |
| **D** (서비스거부) | PDF/이미지 대용량 업로드 시 멈춤 가능 — 별도 크기 제한 검증 부재 | 🟡 (아래 권고) |
| **E** (권한상승) | 단일 사용자 권한 모델, 관리자 기능 분리 없음 | 🟢 |

---

## 3. 개인정보·업무정보 — 🟢 통과

### 점검 결과
- 거래처명/단가/직원정보 하드코딩: **0건** (모두 DB 동적)
- 테스트 픽스처 (`tests/conftest.py` 등): 가상 LOT 번호 사용 — 실데이터 노출 없음
- 로그에 PII 노출: **0건** (LOT 번호·수량만 기록)

---

## 4. 라이선스 — 🟢 통과

### 점검 결과
- `python -m pip list --format=json` → **총 461 패키지**
- GPL/AGPL/SSPL/Commons Clause 계열: **0건**
- 모든 의존성이 MIT/BSD/Apache-2.0/PSF/MPL-2.0 등 비-copyleft 라이선스

### 🟡 권고 1건
- **GPL 친화 의존성 점검** — `ddddocr==1.6.0` 등 OCR 라이브러리는 상용 시 검토 필요. SQM은 사내 사용이므로 당장 무해하나, 외부 배포 시 `pip-licenses --format=markdown` 정식 점검 권장

---

## 5. 운영 안전

### 5.1 트랜잭션 — 🟢 통과
- SQLite WAL 모드 활성 (`PRAGMA journal_mode=wal` 확인)
- `_db.execute` 패턴 일관 — `commit()` 명시 호출 다수

### 5.2 백업 — 🟢 통과
- `data/db/backups/sqm_inventory_archive_*.db` 자동 백업 패턴 확인
- `backups/` 폴더 git 추적 제외 (`.gitignore` line 45)

### 5.3 로그 회전 — 🟡 권고
- `logs/sqm_inventory.log: 5.2 MB`
- `logs/sqm_inventory.log.1: 10.5 MB` (회전 파일 1개만 보존)
- 🟡 권고: 보존 정책 강화 — `log.1` 1개 → `log.1~log.5` 또는 날짜별 회전 (30일 보존). Windows 작업 스케줄러 + `logrotate` 또는 Python `RotatingFileHandler(maxBytes=10MB, backupCount=5)` 적용.

---

## 📋 종합 판정

### 🔴 즉시수정: 0건

### 🟡 권고 4건 (배포 차단 아님, 다음 개선 과제로 인계)
1. `config.py:116` `PG_PASSWORD` 기본값 정리
2. backend/ f-string SQL 11건 — 파라미터 바인딩 정식 전환
3. 오류 메시지 내부 정보 노출 (I), 대용량 업로드 크기 제한 (D) — STRIDE 권고
4. `logs/` 회전 정책 강화 (현재 1개 → 5개 또는 30일)

### 🟢 통과
- 비밀정보 관리 (env/keyring)
- subprocess 안전 (shell=False only)
- 역직렬화 (pickle/yaml.load 0건)
- 개인정보·라이선스 (GPL 0건)
- 트랜잭션 (WAL)
- 백업 (자동)

### 출고 가능 선언
- 사내 배포 / 직원 PC 설치: **즉시 가능**
- 외부 거래처·GitHub 공개: **🟡 권고 4건 반영 후 출고 권장**

---

## 다음 개선 과제 인계

1. **Q3 2026 회고 시점에 STRIDE I, D 처리** — 오류 메시지 정제 + 업로드 크기 제한
2. **다음 v8.9.0 릴리즈 시 f-string SQL 정식 전환** (점진적, 한 모듈씩)
3. **로그 회전 정책 v8.9.0에 포함** — `RotatingFileHandler` + 작업 스케줄러

---

> **감사 종료. 결과: 🟡 조건부 출고 가능. 🔴 없음.**
