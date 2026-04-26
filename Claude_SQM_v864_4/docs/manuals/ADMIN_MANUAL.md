# 🛡️ SQM Inventory v8.6.4.3 — 관리자 매뉴얼

> **대상:** 시스템 관리자 / 사장님 (직접 운영)
> 작성: 2026-04-21 | 버전: v8.6.4.3

---

## 1. 시스템 개요

- **아키텍처:** PyWebView (UI) + FastAPI (Backend) + SQLite (DB)
- **포트:** 127.0.0.1:8765 (외부 접근 차단)
- **핵심 폴더:**
  - 설치: `C:\Program Files\SQM\v864.3\`
  - 사용자 데이터: `%APPDATA%\SQM\`
  - 로그: `%APPDATA%\SQM\logs\`
  - 백업: `%APPDATA%\SQM\backups\`

---

## 2. 설치/제거

### 2.1 설치
- **인스톨러:** `installer\dist\SQM_v864_3_Setup.exe` 더블클릭. 모든 설정 기본값 권장.
- **포터블:** `build\dist\SQM_v864_3.exe` 단독 실행 (설치 없이 가능)
- **개발자 모드:** `python main_webview.py` (Python 3.10+ 필요)

### 2.2 제거
- 제어판 → 프로그램 추가/제거 → SQM Inventory → 제거
- 사용자 데이터(`%APPDATA%\SQM\`)는 자동 삭제되지 않음. 완전 제거 시 수동 삭제.

### 2.3 업데이트
1. 신버전 `Setup.exe` 실행 (이전 버전 자동 덮어쓰기)
2. DB 자동 마이그레이션 (호환 보장)
3. 첫 실행 시 무결성 자동 검사

---

## 3. 환경 설정

### 3.1 settings.ini 위치
- 설치 폴더: `C:\Program Files\SQM\v864.3\settings.ini`
- 사용자 우선: `%APPDATA%\SQM\settings.ini` (있으면 이쪽 우선)

### 3.2 주요 설정 키
```ini
[database]
path = %APPDATA%\SQM\sqm.db

[server]
host = 127.0.0.1
port = 8765

[ui]
theme = darkly
language = ko-KR
auto_refresh_seconds = 30

[backup]
auto_backup_daily = true
keep_backups_days = 30
backup_dir = %APPDATA%\SQM\backups
```

---

## 4. 일일 점검 체크리스트

| 시각 | 작업 | 도구 |
|---|---|---|
| 09:00 | 백업 폴더 용량 확인 | 탐색기 |
| 09:30 | ALERTS 패널 0건 확인 | 메인 화면 |
| 12:00 | 정합성 검사 1회 | 툴바 ✅ 정합성 |
| 17:00 | 일일 보고서 생성 | 보고서 → 일일 |
| 17:30 | 수동 백업 1회 | 툴바 💾 백업 |

---

## 5. 백업 / 복원

### 5.1 자동 백업
`settings.ini` 의 `auto_backup_daily=true` 시 매일 06:00 자동 실행.
저장 위치: `%APPDATA%\SQM\backups\YYYY-MM-DD.db`
30일 이상 된 백업은 자동 삭제.

### 5.2 수동 백업
- 툴바 💾 백업 → 파일명 자동 생성
- 또는 `%APPDATA%\SQM\sqm.db` 를 외부 USB 에 직접 복사

### 5.3 복원
1. 프로그램 종료
2. `%APPDATA%\SQM\sqm.db` 를 백업 파일로 덮어쓰기
3. 프로그램 재실행
4. Dashboard 에서 "마지막 경신" 시각이 백업 시점 이전인지 확인

### 5.4 복구 (장애 발생 시)
```cmd
python tools\rollback.py --to-backup latest
```
가장 최근 백업으로 자동 복원.

---

## 6. 로그 / 진단

### 6.1 로그 위치
- 앱 로그: `%APPDATA%\SQM\logs\sqm_webview.log`
- API 로그: `%APPDATA%\SQM\logs\api.log`
- 회전: 일별 분리, 30일 보관

### 6.2 진단 패키지
사장님이 "이상해" 하실 때:
```cmd
python tools\log_collector.py
```
→ `%TEMP%\sqm_diagnostics_<ts>.zip` 생성. 이 파일을 개발자에게 전달.

### 6.3 헬스체크
브라우저로 `http://127.0.0.1:8765/api/health` 접속 → `{"status":"ok"}` 반환되어야 정상.

---

## 7. 권한 / 보안

- 외부 네트워크 노출 없음 (127.0.0.1 바인딩)
- 방화벽 인바운드 규칙 불필요
- 안티바이러스 화이트리스트 등록 권장: `SQM_v864_3.exe`
- 사용자 데이터 폴더 접근 권한: 현재 사용자만

---

## 8. 트러블슈팅

| 증상 | 원인 | 조치 |
|---|---|---|
| 창이 안 열림 | 포트 8765 충돌 | `netstat -ano | findstr 8765` 후 충돌 PID 종료 |
| ALERTS 안 뜸 | 자동 갱신 OFF | 상태바 "자동 새로고침" 체크박스 ON |
| Dark 테마 깨짐 | CSS 로드 실패 | 브라우저 캐시 무시 새로고침 (Ctrl+Shift+R) |
| 데이터 누락 | DB 파일 손상 | `sqlite3 sqm.db ".dump"` 후 복구 |
| 응답 느림 | LRU 캐시 무효화 | 메뉴 [설정 → 캐시 비우기] |

---

## 9. 정기 유지보수

- **주간:** 정합성 검사 자동 1회 + 결과 메일 통보
- **월간:** DB VACUUM (`sqlite3 sqm.db VACUUM`)
- **분기:** 신버전 체크 (`tools\check_update.py`)
- **반기:** 매뉴얼 갱신 + 직원 재교육

---

## 10. 비상 연락 / 에스컬레이션

| 우선순위 | 연락처 | 처리 |
|---|---|---|
| P0 (서비스 정지) | 사장님 본인 | 즉시 `tools\rollback.py` 실행 |
| P1 (데이터 오류) | 사장님 → 개발자 | 진단 ZIP 전달 후 24h 내 수정 |
| P2 (UI 불편) | 다음 패치 | 차기 버전 반영 |

---

**본 매뉴얼 버전:** v1.0 (2026-04-21, Ruby 작성)
