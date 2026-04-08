# SQM v869 — v864 기능 원장 감사 요약 (AUDIT SUMMARY)
작성일: 2026-04-05
재검증: 2026-04-05 (MASTER S1~S12 전체 재실행)

## 판정 기준
- ✅ PASS: 메뉴 노출 + 라우트 연결 + 실제 동작 코드 구현
- ⚠️ PARTIAL: 일부만 구현 (UI 있으나 실데이터 미확인)
- ❌ FAIL: 구현 안 됨

---

## 기능별 PASS/FAIL 판정

| 기능 | 메뉴 노출 | 라우트 연결 | export 동작 | 안전장치 | 종합 |
|------|-----------|-------------|-------------|----------|------|
| 총괄 재고 리스트 | ✅ View+Sidebar | ✅ /cargo | N/A | N/A | ✅ PASS |
| LOT 리스트 Excel | ✅ 내보내기 서브메뉴 | ✅ /api/tools/export-lot-list | ✅ CSV 다운로드 | N/A | ✅ PASS |
| 톤백리스트 Excel | ✅ 내보내기 서브메뉴 | ✅ /api/tools/export-tonbag-list | ✅ CSV 다운로드 | N/A | ✅ PASS |
| 로그 내보내기 | ✅ DB보호 서브메뉴+LogPage | ✅ /api/tools/export-logs | ✅ CSV/JSON | N/A | ✅ PASS |
| 최근 파일 목록 | ✅ 파일 메뉴 동적 | ✅ navigate 처리 | N/A | N/A | ⚠️ PARTIAL* |
| 정합성 검사 | ✅ 도구 메뉴 | ✅ /integrity | ✅ 결과 카드 | N/A | ✅ PASS |
| 정합성 복구 | ✅ 복구 버튼 | ✅ /api/tools/integrity-repair | ✅ 결과 테이블 | ✅ 2단계 모달 | ✅ PASS |
| 한글 Sidebar 라벨 | ✅ 10개 탭 한글 | N/A | N/A | N/A | ✅ PASS |
| 테스트 DB 초기화 | ✅ devMode 전용 | ✅ /api/tools/reset-test-db | ✅ 테이블 삭제 | ✅ 2단계 모달 + production 차단 | ✅ PASS |
| 레이아웃 초기화 | ✅ SettingsPage | N/A | ✅ localStorage 삭제 | ✅ confirm | ✅ PASS |
| 새로고침(데이터) | ✅ View 메뉴 | ✅ navigate refetch | N/A | N/A | ✅ PASS |
| 강제 새로고침 | ✅ View 메뉴 | ✅ window.reload | N/A | N/A | ✅ PASS |
| 종료 안내 | ✅ 파일>종료 | N/A | N/A | ✅ toast 안내 | ✅ PASS |
| DB 백업 생성 | ✅ 파일>백업 | ✅ /api/tools/backup/create | ✅ 파일 복사 | N/A | ✅ PASS |
| DB 최적화 | ✅ 도구 메뉴 | ✅ /api/tools/db-optimize | ✅ VACUUM+ANALYZE | N/A | ✅ PASS |

*최근 파일: UI는 동작하나 실제 작업 성공 시 addRecentFile() 트리거 미연결

---

## 요약

- **PASS**: 14개
- **PARTIAL**: 1개 (최근 파일 — 트리거 미연결)
- **FAIL**: 0개

**전체 이관율: 14/15 = 93%** (빌드 통과, 회귀 이슈 0건)
