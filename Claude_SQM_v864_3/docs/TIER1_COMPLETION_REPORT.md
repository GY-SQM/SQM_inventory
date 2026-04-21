# Tier 1 완료 보고서

**완료일:** 2026-04-21
**빌드:** `build/dist/SQM_v864_3.exe` (184 MB)

---

## Smoke Test 체크리스트

| 항목 | 상태 | 비고 |
|---|---|---|
| exe 더블클릭 → 앱 실행 | ⬜ 사장님 확인 필요 | `build/dist/SQM_v864_3.exe` |
| 창 크기 1400×900 기본값 | ✅ 코드 확인 | `main_webview.py` line 63 |
| 사이드바 11개 탭 전환 | ✅ 코드 확인 | `app.js` navigateTo() |
| 헤더 버튼 클릭 반응 | ✅ 코드 확인 | refresh, toast 작동 |
| Dark/Light 테마 토글 | ✅ 구현 완료 | 우상단 🌙 버튼, localStorage 영속 |
| FastAPI Swagger UI | ⬜ 사장님 확인 필요 | `http://localhost:8765/docs` |
| 창 닫으면 FastAPI 종료 | ✅ 코드 확인 | daemon thread |
| Toast "준비 중" 알림 | ✅ 구현 완료 | `showToast()` |

---

## 구현 산출물

### Backend
- `backend/api.py` — FastAPI (포트 8765), health + 다수 엔드포인트
- `main_webview.py` — PyWebView 진입점, API 서버 백그라운드 실행

### Frontend
- `frontend/index.html` — SPA shell (11개 탭, 헤더, 대시보드 KPI)
- `frontend/css/design-system.css` — CSS 변수 기반 다크/라이트 테마
- `frontend/js/app.js` — 내비게이션, 토스트, 테마 토글, PyWebView 브릿지

### Build
- `build/SQM_v864_3.spec` — PyInstaller 설정 (WinForms 백엔드)
- `build/dist/SQM_v864_3.exe` — 184 MB 단일 파일

---

## Tier 2 진입 조건

사장님이 exe 실행 확인 후 → `TIER2_PLAN.md` 작성 시작.

**Top 10 후보 (확정 필요):**
1. PDF 입고, 2. 즉시 출고, 3. 재고 조회, 4. 반품, 5. 정합성 검사
6. 백업, 7. Dashboard API 연결, 8. Alert 갱신, 9. 테마 영속 저장, 10. 로그 뷰
