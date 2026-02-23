# SQM v6.1.0 — 출고 로직 개편

**릴리즈 일자:** 2026-02-23  
**기준 버전:** v6.0.9  
**전제:** 기존 UI 틀 변경 없음 (하부 메뉴 추가는 사용자 확인 시에만)

---

## 1. 요약

- **피킹리스트 PDF 파서** 신규 추가 (`parsers/document_parser_modular/picking_mixin.py`)
- **Gate-1 교차검증** — 피킹 LOT ↔ allocation_plan RESERVED 완전 일치 후에만 RESERVED→PICKED 실행
- **빠른 출고** — 8개 **톤백** 초과 시 차단 후 일반 출고(배정표) 전환 안내, allocation_plan에 `source='QUICK'` 기록
- **Picking List 업로드** — 기존 메뉴 진입점에서 Gate-1 경로 우선 사용 (파싱 → Gate-1 → 판매화물 결정)

---

## 2. 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `parsers/document_parser_modular/picking_mixin.py` | **신규** — PickingListParserMixin, PickingListResult/Meta/PickingLotItem |
| `parsers/document_parser_modular/__init__.py` | PickingListParserMixin·Result·Meta·PickingLotItem export |
| `engine_modules/inventory_modular/outbound_mixin.py` | gate1_verify_picking(), execute_from_picking() 추가 |
| `engine_modules/db_migration_mixin.py` | _migrate_v601_picking_list_meta() — picking_list_order 메타 컬럼 10개 추가 |
| `gui_app_modular/handlers/outbound_handlers.py` | 빠른 출고 8톤백 제한·QUICK 마킹·확인/완료 메시지 한글화, _on_picking_list_upload Gate-1 경로, _save_gate1_report() |
| `version.py` | __version__ = 6.1.0, VERSION_HISTORY 6.1.0 항목 |

---

## 3. DB 마이그레이션

- **picking_list_order** 테이블에 아래 컬럼 추가 (앱 재실행 시 자동 적용):
  - picking_no, delivery_terms, port_loading, port_discharge, containers  
  - contact_person, contact_email, total_nw_kg, total_gw_kg, gate1_result  

---

## 4. 동작 요약

- **피킹리스트 업로드 (PDF)**  
  - PDF 선택 → `PickingListParserMixin.parse_picking_list()` → 미리보기 확인 → Gate-1 검증 → 통과 시 `execute_from_picking()` (RESERVED→PICKED) → 완료 메시지 후 새로고침  
  - Gate-1 실패 시 에러 리포트 표시 + 바탕화면에 `Gate1_실패_{picking_no}_{timestamp}.txt` 저장  

- **빠른 출고**  
  - 톤백 8개 초과 시 "일반 출고(배정표)로 전환하시겠습니까?" 팝업, 전환 시 Allocation 다이얼로그 오픈  
  - 8개 이하: allocation_items에 source='QUICK' 설정 후 기존 process_outbound(..., source='QUICK', stop_at_picked=True) 호출  
  - 완료 메시지: "판매화물 결정 완료" + "현장 출고 확인 후 [출고 확정]을 실행하세요."  

---

## 5. 테스트 제안

1. **빠른 출고** — 톤백 9개 이상 선택 시 차단·전환 안내 동작 확인  
2. **피킹리스트** — LBM 스타일 PDF 업로드 → Gate-1 통과 시 RESERVED→PICKED 전환 및 picking_list_order/ detail 기록 확인  
3. **Gate-1 실패** — RESERVED 없는 LOT만 있는 PDF로 실패 시 에러 리포트 및 바탕화면 파일 생성 확인  

---

*v6.0.9 + sqm_outbound_patches_v601 참고 반영.*
