# SQM v5.8.5 — 샘플 톤백 No 표기 S → S0

## 개요
샘플 톤백 번호가 **"S"** 한 글자로 표시되어 숫자와 혼동될 수 있어, **"S0"** 으로 통일했습니다.  
DB 저장값(tonbag_no `S00`, tonbag_uid `-S0`)은 기존과 동일하며, **UI 표시만** S → S0 으로 변경됩니다.  
버전 **5.8.5** 반영.

---

## v5.8.5에서 반영한 내용

| 항목 | 내용 |
|------|------|
| **LOT 상세 다이얼로그** | 톤백 목록에서 샘플 톤백 No 표기: `S` → `S0` |
| **톤백 탭 리스트** | TONBAG NO 컬럼·출고 선택 목록·상세 정보에서 샘플 표기: `S` → `S0` |
| **입력 인식** | 기존처럼 `S`, `S0`, `S00` 입력 모두 sub_lt=0(샘플)으로 인식 (변경 없음) |

---

## 변경된 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| version.py | __version__ = 5.8.5, VERSION_HISTORY |
| gui_app_modular/dialogs/lot_detail_dialog.py | tb_no_disp: 'S' → 'S0' |
| gui_app_modular/tabs/tonbag_tab.py | 샘플 표기 'S' → 'S0' (리스트, 출고 선택, 톤백 NO 라벨), 주석 정리 |
| docs/RELEASE_NOTES_v585.md | **신규** — 본 릴리스 노트 |

---

*작성일: 2026-02-16 | SQM v5.8.5*
