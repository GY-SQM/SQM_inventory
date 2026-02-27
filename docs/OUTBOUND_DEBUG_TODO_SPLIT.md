# 출고 전·중 디버깅 구분 — 해야 할 것 vs 이미 반영된 것

> **목적**: 아직 손대지 않은 항목 중, **이미 반영된 것**(문서만 갱신)과 **진짜 앞으로 할 것**을 구분하고,  
> **출고 로직 들어가기 전**에 할 일 vs **출고 로직 개발하면서** 할 일을 정리합니다.  
> **작성일**: 2026-02-16

---

## 1. 이미 반영된 항목 (문서만 갱신하면 됨)

아래는 **코드에는 이미 적용**되어 있으나, REFACTORING_MASTER_PLAN §7 체크리스트·DEBUGGING_RISK_OVERVIEW §8.2 표가 예전 상태로 남아 있는 항목입니다. **추가 코딩 없이 문서만 수정**하면 됩니다.

| 항목 | 실제 상태 | 문서에서 할 일 |
|------|-----------|----------------|
| **safe_int** | utils/common 단일 소스, helpers는 re-export 또는 common 사용으로 정리됨 | §7 [ ] → [x], §8.2 표에서 "이미 정리됨"으로 이동 또는 삭제 |
| **safe_date** | 용도별 구분(safe_date_to_date / safe_date_str 등) 적용 완료 | §7 [ ] → [x], §8.2 표에서 "이미 정리됨"으로 이동 |
| **버전·APP_NAME** | version.py 단일 소스, fallback 0.0.0 등 통일 완료 | §8.2 "버전/앱명" 행을 "이미 정리됨"으로 이동 |
| **메시지박스** | CustomMessageBox 통일 적용(직접 messagebox 호출 → CustomMessageBox 변환 완료) | §7 [ ] → [x], §8.2 "메시지 박스" 행을 "이미 정리됨"으로 이동 |

→ **조치**: REFACTORING_MASTER_PLAN.md §7 체크리스트와 DEBUGGING_RISK_OVERVIEW.md §8.2 표를 위 내용에 맞춰 갱신.

---

## 2. 진짜 앞으로 해야 할 사항 (코드/정책 작업 필요)

### 2.1 출고 로직 들어가기 **전**에 할 것

| 항목 | 내용 | 비고 |
|------|------|------|
| **문서 갱신** | §7 체크리스트·§8.2 표를 "이미 반영된 항목"에 맞춰 수정 | 코딩 없음, 문서만 |

**선택(출고 전에 해두면 좋음) — 완료 반영:**

| 항목 | 내용 | 비고 |
|------|------|------|
| **상수 중복** | DEFAULT_WAREHOUSE 등 — gui_bootstrap에서 로컬 fallback 제거, core.constants만 re-export | ✅ 적용 완료. |
| **onestop safe_float** | onestop_inbound는 이미 core.types.safe_float 사용(로컬 _safe_float 없음). 문서만 갱신. | ✅ 적용 완료. |

→ 출고 **전** 필수(문서 갱신) + 선택(상수·safe_float) 모두 반영 완료.

---

### 2.2 출고 로직 **개발하면서** 할 것

| 항목 | 내용 | 비고 |
|------|------|------|
| **고객명 표준화** | sold_to / picked_to / customer — 테이블·API마다 이름이 다름. 출고 시 "어디에 기록할지" 단일 규칙으로 통일 | DB 컬럼 변경 리스크 있으므로 **출고 로직 구현과 함께** 처리 (DEBUGGING_RISK_OVERVIEW §5 ④, v5.7.0 출고와 함께). |

→ 고객명만 **출고 로직과 함께** 반드시 정리하는 항목으로 두고, 나머지(상수·safe_float)는 같은 시기에 같이 정리하거나 그 전후로 처리하면 됨.

---

## 3. 보류·건드리지 않음 (출고 전·중 구분 없음)

| 항목 | 내용 | 비고 |
|------|------|------|
| **§5 ⑤ 톤백 번호** | sub_lt / tonbag_no / tonbag_uid — 역할이 다르므로 문서대로 "건드리지 않음" | tonbag_compat 헬퍼로 접근 유지 |
| **§3 데드코드** | picking_list_* 테이블, tonbag_mapping_history, inbound_preview.py, 미사용 컬럼 | 제거/복구/ deprecated **결정**만 필요. 출고 필수 아님. 적절한 시점에 별도 작업 |
| **§8.2 용어(참고)** | lot_no / lot_number / lotno | 의도적 구분. 변경 없음 |

---

## 4. 요약 표

| 구분 | 항목 | 시점 | 작업 내용 |
|------|------|------|-----------|
| **이미 반영** | safe_int, safe_date, 버전, 메시지박스 | — | **문서만** §7·§8.2 갱신 |
| **출고 전** | 문서 갱신 | 지금 | REFACTORING_MASTER_PLAN §7, DEBUGGING_RISK_OVERVIEW §8.2 수정 |
| **출고 전(선택)** | DEFAULT_WAREHOUSE 등 상수 중복 | 출고 전 또는 출고 중 | GUI는 engine re-export만 사용하도록 정리 |
| **출고 전(선택)** | onestop _safe_float | 출고 전 또는 출고 중 | 로컬 제거, utils.common.safe_float(core.types) 통합 |
| **출고와 함께** | 고객명 (sold_to / picked_to / customer) | 출고 로직 개발 시 | 표준화·DB/API와 함께 처리 |
| **보류** | 톤백 번호, 데드코드 | 별도 결정 | 건드리지 않음 / 적절한 시점에 결정 |

---

*작성일: 2026-02-16 | SQM*
