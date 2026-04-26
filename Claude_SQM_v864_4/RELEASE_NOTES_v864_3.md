# 🚀 SQM Inventory v8.6.4.3 — Release Notes

**릴리즈 일자:** 2026-04-21
**이전 버전:** v8.6.4.2 (Tkinter)
**작성:** Ruby (Senior Software Architect)

---

## ✨ Highlights

- **Tkinter → PyWebView 전면 마이그레이션 완료**
- v864.2 와 **시각적·기능적 100% 동등** (메뉴 7 + 툴바 7 + 사이드바 9 + 단축키 13)
- Backend API 113+ 엔드포인트 자동 생성
- Dark/Light 테마 토글 + localStorage 상태 복원
- 30초 자동 갱신 + 백오프 정책

---

## 🆕 신규 기능

| # | 기능 | 비고 |
|---|---|---|
| 1 | PyWebView 기반 네이티브 창 | 1400×900 기본 |
| 2 | FastAPI Backend (포트 8765) | Swagger UI 내장 |
| 3 | ESM 기반 모듈러 Frontend | 번들러 없이 |
| 4 | 동적 라우터 (9탭) | localStorage 마지막 탭 복원 |
| 5 | LRU @cached 데코레이터 | hot-path 5초 TTL |
| 6 | Inno Setup 인스톨러 | `Setup.exe` 단일 배포 |
| 7 | 자동 업데이트 체크 | `tools/check_update.py` |
| 8 | 진단 ZIP 수집기 | `tools/log_collector.py` |
| 9 | 자동 롤백 스크립트 | `tools/rollback.py` |
| 10 | UAT 시나리오 20종 | `tests/uat_scenarios.json` |
| 11 | Per-Stage Gate Test | 12 Stage 자동 검증 |

---

## 🔄 변경

- 메뉴바 한글 라벨 정렬 (v864.2 동일)
- 사이드바 9탭 영문 라벨 + 이모지 (Inventory~Scan)
- ALERTS 패널 30초 자동 갱신
- Toast 4타입 통일 (success/info/warning/error)

---

## 🐛 수정

- Tier 1 단계 main_webview.py 구문 오류 복구
- backend/api.py truncation 복구
- index.html 잘못된 디자인 → v864.2 레이아웃으로 전면 교체
- TIER1_PLAN.md 의 포트 8000 → 8765 정정

---

## ⚠️ 알려진 제약

- optional 11 기능 일부는 "준비 중" 응답 (501) — 외부 라이브러리(SMTP, 바코드 생성) 의존
- Inno Setup 미설치 환경에서는 ZIP 포터블 폴백
- 코드서명 인증서 미보유 — Windows SmartScreen 첫 실행 경고 가능
- macOS/Linux 미지원 (Windows 전용)

---

## 📦 다운로드

- **Installer:** `installer/dist/SQM_v864_3_Setup.exe` (약 200MB)
- **Portable:** `build/dist/SQM_v864_3.exe` (약 192MB)
- **Source:** GitHub (사장님 비공개 저장소)

---

## 📋 마이그레이션 가이드 (v864.2 → v864.3)

1. v864.2 종료 → 데이터 자동 보존 (DB 경로 동일)
2. `Setup.exe` 실행 → 기본 경로 설치
3. 첫 실행 시 자동 무결성 체크 + 마이그레이션 (필요 시)
4. 기존 단축키·테마 복원

---

## 🙏 Credits

- **개발 디렉터:** Nam Ki-dong (사장님)
- **수석 아키텍트:** Ruby (Sub-Agent 13명 오케스트레이션)
- **참조:** v864.2 원본 (`engine_modules/`, `features/`, `parsers/`, `utils/`)

---

**라이센스:** GY Logis 내부 사용 전용
**문의:** kidong.nam@gmail.com
