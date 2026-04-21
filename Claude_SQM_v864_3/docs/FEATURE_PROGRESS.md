# FEATURE PROGRESS — v864.3 Tier 2/3 실시간 체크리스트

> 최초 생성: 2026-04-21 (Ruby, Stage 1 PREP)
> 최신 갱신: 2026-04-21T04:17:52 (Ruby, Stage 7 완료 반영)
> 갱신 주체: Ruby 자율 실행 + 각 Sub-Agent PR 병합 시

## 범례
- ⬜ pending / 🟡 in_progress / ✅ completed / 🟠 deferred / ❌ failed

## 통계
- 총 기능: **85**
- completed: **85** (100.0%)
- pending: 0

## 카테고리별
- menubar 62 → completed 62
- sidebar_tab 8 → completed 8
- toolbar_button 2 → completed 2
- keyboard 13 → completed 13

## 체크리스트 (85)

| ID | 카테고리 | 위치 | 라벨 | 상태 |
|---|---|---|---|---|
| `F001` | menubar | 파일 > 입고 | 📄  PDF 스캔 입고 | ✅ |
| `F002` | menubar | 파일 > 입고 | 📊  엑셀 파일 수동 입고 | ✅ |
| `F003` | menubar | 파일 > 입고 | 📋  D/O 후속 연결 | ✅ |
| `F004` | menubar | 파일 > 입고 | 📍  톤백 위치 매핑 | ✅ |
| `F005` | menubar | 파일 > 입고 | ✅  대량 이동 승인 | ✅ |
| `F006` | menubar | 파일 > 입고 | 🔄  반품 (재입고) | ✅ |
| `F007` | menubar | 파일 > 입고 | 📂  반품 입고 (Excel) | ✅ |
| `F008` | menubar | 파일 > 입고 | 📊  반품 사유 통계 | ✅ |
| `F009` | menubar | 파일 > 입고 | 📋  입고 현황 조회 | ✅ |
| `F010` | menubar | 파일 > 입고 | 📝  입고 파싱 템플릿 관리 | ✅ |
| `F011` | menubar | 파일 > 입고 | 📦  제품 마스터 관리 | ✅ |
| `F012` | menubar | 파일 > 입고 | ⚙️  이메일 설정 | ✅ |
| `F013` | menubar | 파일 > 입고 | 🔍  정합성 검증 (시각화) | ✅ |
| `F014` | menubar | 파일 > 입고 | 🛠️  LOT 상태 정합성 복구 | ✅ |
| `F015` | menubar | 파일 > 출고 | 🚀  즉시 출고 (원스톱) | ✅ |
| `F016` | menubar | 파일 > 출고 | 📤  빠른 출고 (붙여넣기) | ✅ |
| `F017` | menubar | 파일 > 출고 | 📋  Picking List 업로드 (PDF) | ✅ |
| `F018` | menubar | 파일 > 출고 | 📊  바코드 스캔 업로드 | ✅ |
| `F019` | menubar | 파일 > 출고 | 📷  스캔 탭으로 이동 | ✅ |
| `F020` | menubar | 파일 > 출고 | 📋  Allocation 입력 | ✅ |
| `F021` | menubar | 파일 > 출고 | ✅  승인 대기 | ✅ |
| `F022` | menubar | 파일 > 출고 | 📌  예약 반영 (승인분) | ✅ |
| `F023` | menubar | 파일 > 출고 | 📜  승인 이력 조회 | ✅ |
| `F024` | menubar | 파일 > 출고 | 📋  판매 배정 탭으로 이동 | ✅ |
| `F025` | menubar | 파일 > 출고 | 📋  출고 현황 조회 | ✅ |
| `F026` | menubar | 파일 > 출고 | 📊  Sales Order 업로드 | ✅ |
| `F027` | menubar | 파일 > 출고 | 🔁  Swap 리포트 | ✅ |
| `F028` | menubar | 파일 > 출고 | 📦  출고 피킹 템플릿 관리 | ✅ |
| `F029` | menubar | 파일 > 백업 | 💾 백업 생성 | ✅ |
| `F030` | menubar | 파일 > 백업 | 🔄 복원 | ✅ |
| `F031` | menubar | 파일 > 백업 | 📋 백업 목록 | ✅ |
| `F032` | menubar | 파일 > AI 도구 | 🚢 선사 BL 등록 도구 | ✅ |
| `F033` | menubar | 파일 > AI 도구 | 🔬 선사 패턴 분석 | ✅ |
| `F034` | menubar | 도구 | 📋 감사 로그 조회 / Export | ✅ |
| `F035` | menubar | 재고 | 📊 LOT 리스트 Excel | ✅ |
| `F036` | menubar | 재고 | 🎒 톤백리스트 Excel | ✅ |
| `F037` | menubar | 재고 | 📋 출고 현황 조회 | ✅ |
| `F038` | menubar | 재고 | 📊 재고 추이 차트 | ✅ |
| `F039` | menubar | 보고서 | 📄 거래명세서 생성 | ✅ |
| `F040` | menubar | 보고서 | 📦 Detail of Outbound | ✅ |
| `F041` | menubar | 보고서 | 📋 Sales Order DN | ✅ |
| `F042` | menubar | 보고서 | 🔍 DN 교차검증 | ✅ |
| `F043` | menubar | 보고서 | 📝 고객 보고서 생성 | ✅ |
| `F044` | menubar | 보고서 | 📂 보고서 양식 관리 | ✅ |
| `F045` | menubar | 보고서 | 📋 보고서 이력 조회 | ✅ |
| `F046` | menubar | 보고서 | 📦 재고 현황 보고서 | ✅ |
| `F047` | menubar | 보고서 | 📈 입출고 내역 | ✅ |
| `F048` | menubar | 보고서 | 📅 월간 실적 PDF | ✅ |
| `F049` | menubar | 보고서 | 📊 일일 현황 PDF | ✅ |
| `F050` | menubar | 보고서 | 🔖 LOT 상세 | ✅ |
| `F051` | menubar | 설정/도구 | 🔄 새로고침 (F5) | ✅ |
| `F052` | menubar | 설정/도구 | 💾 현재 창 크기 저장 | ✅ |
| `F053` | menubar | 설정/도구 | ↩️ 기본 창 크기 초기화 | ✅ |
| `F054` | menubar | 설정/도구 | 📦 제품 마스터 관리 | ✅ |
| `F055` | menubar | 설정/도구 | 📊 제품별 재고 현황 | ✅ |
| `F056` | menubar | 설정/도구 | 📋 D/O 후속 연결 | ✅ |
| `F057` | menubar | 도움말 | 📖 사용법 | ✅ |
| `F058` | menubar | 도움말 | ⌨️ 단축키 안내 | ✅ |
| `F059` | menubar | 도움말 | 📊 STATUS 상태값 안내 | ✅ |
| `F060` | menubar | 도움말 | 💾 DB 백업/복구 가이드 | ✅ |
| `F061` | menubar | 도움말 | ℹ️ 시스템 정보 | ✅ |
| `F062` | menubar | 도움말 | 📝 버전 정보 | ✅ |
| `F063` | keyboard | 단축키 | <Control-o>: 파일 열기 | ✅ |
| `F064` | keyboard | 단축키 | <Control-s>: 파일 저장 | ✅ |
| `F065` | keyboard | 단축키 | <Control-Shift-s>: 파일 다른 이름으로 저장 | ✅ |
| `F066` | keyboard | 단축키 | <Control-f>: 검색 포커스 | ✅ |
| `F067` | keyboard | 단축키 | <F5>: 데이터 새로고침 | ✅ |
| `F068` | keyboard | 단축키 | <Control-r>: 데이터 새로고침 | ✅ |
| `F069` | keyboard | 단축키 | <Control-Tab>: 다음 탭 | ✅ |
| `F070` | keyboard | 단축키 | <Control-Shift-Tab>: 이전 탭 | ✅ |
| `F071` | keyboard | 단축키 | <F11>: 전체 화면 | ✅ |
| `F072` | keyboard | 단축키 | <Escape>: 닫기 | ✅ |
| `F073` | keyboard | 단축키 | <Control-q>: 종료 | ✅ |
| `F074` | keyboard | 단축키 | <Control-n>: 신규 입고 | ✅ |
| `F075` | keyboard | 단축키 | <Control-e>: 내보내기 | ✅ |
| `F076` | sidebar_tab | 사이드바 | 재고 | ✅ |
| `F077` | sidebar_tab | 사이드바 | 판매 배정 | ✅ |
| `F078` | sidebar_tab | 사이드바 | 선택됨 | ✅ |
| `F079` | sidebar_tab | 사이드바 | 출고 | ✅ |
| `F080` | sidebar_tab | 사이드바 | 반품 | ✅ |
| `F081` | sidebar_tab | 사이드바 | 이동 | ✅ |
| `F082` | sidebar_tab | 사이드바 | 대시보드 | ✅ |
| `F083` | sidebar_tab | 사이드바 | 로그 | ✅ |
| `F084` | toolbar_button | 상단 우측 | 🔄 새로고침 | ✅ |
| `F085` | toolbar_button | 상단 우측 | 🎨 테마 토글 | ✅ |

---
## 갱신 로그
- 2026-04-21 Ruby — 초기화 (Stage 1 PREP)
- 2026-04-21 Ruby — Stage 7 완료. menubar/toolbar/sidebar/keyboard 전체 바인딩 반영