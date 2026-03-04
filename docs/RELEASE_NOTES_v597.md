# SQM v5.9.7 Release Notes

**Release Date:** 2026-02-18  
**Phase:** 문서·UX 보강

---

## 변경 요약

### 1. Picking List 파서·출고 로직 설계 검토안

- **파일:** `docs/PICKING_LIST_PARSER_DESIGN_REVIEW.md` (신규)
- 출고 매핑 설계서 v1 기반 Picking List 파싱·피킹 지시 로직 초안을 검토한 문서
- 내용: 문서 구조, Text/OCR 파이프라인, 정규식·상태머신 보완점, 데이터 모델·하드스톱 7개, SQM 3단계(Allocation→Picking→Sales Order) 연동 권장사항

### 2. 입고 파싱 경과 시간(elapsed time) 표시

- **대상:** 원스톱 입고 다이얼로그 (`onestop_inbound.py`)
- 파싱 완료 시:
  - 진행 메시지: `✅ 파싱 완료 — N개 LOT (12.3초)` 또는 `(1분 5초)`
  - 로그: `✅ 파싱 완료: N LOT, M종 서류 (경과: 12.3초)`

### 3. 출고(Allocation) 파싱 경과 시간 표시

- **대상:** Allocation 출고 예약 다이얼로그 (`allocation_dialog.py`)
- 파싱 후 요약란에 **파싱 소요 시간** 추가:  
  `고객: ... | 총 N행 | 총량: ... MT | 파싱: 0.45초 | 파일명.xlsx`

---

## 변경된 파일 (6개)

| 파일 | 변경 유형 |
|------|---------|
| `docs/PICKING_LIST_PARSER_DESIGN_REVIEW.md` | **신규** |
| `docs/RELEASE_NOTES_v597.md` | **신규** |
| `gui_app_modular/dialogs/onestop_inbound.py` | 수정 (elapsed 표시) |
| `gui_app_modular/dialogs/allocation_dialog.py` | 수정 (elapsed 표시) |
| `version.py`, `VERSION.txt`, `updates/latest.json` | 버전 5.9.7 |

---

**(주) 지와이로지스 2026년 2월 18일**
