# SQM v8.7.1 최종 배포 패키지
생성일: 2026-04-08
파일수: 59개 | ZIP 크기: 160KB

## 배포 방법
deploy.bat 더블클릭 → 모든 파일 자동 배치

## 빌드 방법
build_all.bat 더블클릭 → React + pywebview + Electron 전체 빌드

## 포함 내용

### Python 백엔드 (24개)
- P2-B Outbound 리팩토링 (outbound_service, outbound_query, outbound_state_rules)
- P2-C DB 구조 통합 (base/inbound/inventory/outbound Repository)
- Dashboard con_return 경고 (dashboard_read_service, schemas/dashboard)
- API 에러 Telegram 알림 (telegram_alert, main)
- QueryCache TTL 지능화 (query_cache)
- DB 복합 인덱스 최적화 (db_optimize)
- Telegram 봇 v3 (/재고 /출고 /대기 /만료 /비교 /확정 /취소)
- 백업 스케줄러 v2 (Con Return 만료 경고 + 로그 로테이션)
- pywebview 데스크탑 앱 (run_desktop.py)

### React 프론트엔드 (22개) — 100% 완성
- DashboardPage: KPI카드 + Con Return 경고 + 30초 갱신
- InventoryPage: 입고버튼 + 우클릭메뉴
- AllocationPage: 예약등록 + 실행 + 취소 + 복귀
- PickedPage: 체크박스 + 일괄확정 (병렬처리)
- OutboundPage: 출고실행버튼 + 상태탭
- SoldPage: 취소버튼 + 날짜필터
- TonbagPage: 위치 인라인 수정
- CargoOverviewPage: KPI + 비율바 + 30초 갱신
- OutboundHistoryPage: 날짜/고객 필터
- ProductMasterPage: CRUD 완성
- IntegrityPage: 자동실행 + DB최적화 버튼
- LogPage: 레벨 필터 + 페이징
- SummaryPage: Excel + 30초 갱신
- MovePage: 이동실행 + 이력
- HelpPage: 검색 + 모바일 가이드
- TemplatesPage: 다크테마 완성
- MobileDashboard: 모바일 전용 + 바코드 스캔 탭
- BarcodeScanner: 카메라 스캔 컴포넌트

### 빌드/배포 스크립트 (4개)
- deploy.bat: 전체 파일 자동 배치
- build_all.bat: React + pywebview + Electron 전체 빌드
- build_exe.bat: Tkinter .exe 빌드
- verify.bat: pytest 자동 실행

### 데스크탑 앱
- sqm_desktop.spec: Tkinter PyInstaller
- sqm_web_desktop.spec: pywebview PyInstaller
- electron/main.js: Electron 메인 프로세스

## 실행 방법
| 방식 | 명령 |
|------|------|
| 개발 서버 | cd web && npm run dev |
| pywebview | python run_desktop.py |
| Tkinter | python run.py |
| 전체 빌드 | build_all.bat |

## 문의
@Claude_kdnbot /상태
