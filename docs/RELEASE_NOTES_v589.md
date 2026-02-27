# SQM v5.8.9 — 원스톱 입고 한 화면 처리·DateEntry 통일·Location 엑셀 UID

## 개요
- **원스톱 입고**: 파싱 결과 확인 팝업에서 바로 DB 업로드/Excel 내보내기/취소 선택 (업로드 2 단계 제거).
- **파싱 실시간 표시**: 서류별 파싱·병합 직후 미리보기 테이블 갱신.
- **DateEntry 통일**: onestop_inbound 날짜 입력을 gui_bootstrap(ttkbootstrap.DateEntry)로 통일, tkcalendar 직접 의존 제거.
- **Location 엑셀**: 양식2에 UID(또는 tonbag_uid) 컬럼 선택 지원.

---

## v5.8.9에서 반영한 내용

| 항목 | 내용 |
|------|------|
| **원스톱 입고** | 파싱 결과 확인 팝업 버튼: "맞음 — 다음 단계" / "아니오" 제거 → **📥 Excel 내보내기**, **📤 DB 업로드**, **❌ 취소** 세 가지만 표시. 두 번째 팝업(다음 작업 선택) 제거. |
| **실시간 미리보기** | 서류 1종 파싱·병합 후마다 `_refresh_preview_tree_only()` 호출로 미리보기 테이블 즉시 갱신. |
| **DateEntry 통일** | `onestop_inbound.py`: `tkcalendar.DateEntry` 제거 → `gui_bootstrap.DateEntry`, `HAS_DATEENTRY` 사용. `_ask_missing_dates()`에서 ttkbootstrap API(`dateformat='%Y-%m-%d'`, `startdate`, `bootstyle`) 적용. |
| **Location 엑셀** | `tonbag_location_uploader.py`: 양식2(lot_no + tonbag_no + location)에 **uid** 또는 **tonbag_uid** 컬럼 선택 지원. 행에 UID가 있으면 해당 값으로 매칭, 없으면 기존처럼 lot_no+tonbag_no로 조회/생성. |
| **문서** | `docs/UI_FRAMEWORK_AND_DATEENTRY_REVIEW.md` — UI 프레임워크 구조·DateEntry 통일 검토 정리. |
| **버전** | `version.py` — __version__ = 5.8.9 |

---

## 변경된 파일 요약

| 구분 | 파일 |
|------|------|
| **버전** | version.py |
| **원스톱 입고** | gui_app_modular/dialogs/onestop_inbound.py |
| **Location 엑셀** | gui_app_modular/utils/tonbag_location_uploader.py |
| **문서** | docs/UI_FRAMEWORK_AND_DATEENTRY_REVIEW.md, docs/RELEASE_NOTES_v589.md |

---

## 사용자 영향
- 입고 시 파싱 완료 후 **한 번의 팝업**에서 DB 업로드/Excel/취소만 선택하면 됨 (추가 단계 없음).
- 파싱 중 **서류별로 미리보기 테이블이 바로 갱신**되어 진행 상황을 확인하기 쉬움.
- 톤백 위치 Excel 업로드 시 **양식2에 UID 컬럼을 넣으면** 해당 값으로 매칭 가능.

---

*작성일: 2026-02-17 | SQM v5.8.9*
