# SQM v5.9.6 Release Notes — 출고 순서 LIFO + Allocation 파서 검증

**Release Date:** 2026-02-18  
**Phase:** Allocation 출고 로직 강화

---

## 변경 요약

### 출고 순서: 톤백 큰 번호부터 (LIFO)

**변경 전:** `ORDER BY sub_lt ASC` (작은 번호부터 = FIFO)  
**변경 후:** `ORDER BY sub_lt DESC` (큰 번호부터 = LIFO)

예시: LOT에 톤백 10개(1~10), 5개 출고 시
- 이전: 1, 2, 3, 4, 5 출고 → 6~10 남음
- **현재: 10, 9, 8, 7, 6 출고 → 1~5 남음**

### 변경된 출고 경로 5곳

| 파일 | 함수 | 용도 |
|------|------|------|
| `outbound_mixin.py` L153 | `process_outbound()` | 일반 출고 |
| `outbound_mixin.py` L436 | `reserve_from_allocation()` | Allocation 예약 |
| `outbound_handlers.py` L88 | `_on_simple_outbound()` | 간편 출고 미리보기 |
| `import_handlers.py` L558 | Excel 출고 | Excel 배정표 출고 |
| `preflight_mixin.py` L189 | `process_outbound_safe()` | 프리플라이트 검증 |

### Allocation 파서 실데이터 검증

`Allocation - GY - PT LBM 300MT (2)-1.xlsx` 파일로 검증:

| 항목 | 결과 |
|------|------|
| 총 행 | 120행 (일반 60 + 샘플 60) |
| 고유 LOT | 60개 |
| 총 QTY | 300.060 MT |
| LOT당 출고 | 톤백 1개씩 (5MT = 약 5000kg) |
| SAP NO | 4개 (2200032552, 2200032555, 2200032574, 2200032713) |
| 고객 | PT LBM - September - Semarang |
| 헤더 파싱 | ✅ customer, product, total_qty, period, destination |
| 샘플 분리 | ✅ MIC9000 sample 정확 분리 |

---

## 변경된 파일 (5개)

| 파일 | 변경 유형 |
|------|---------|
| `engine_modules/inventory_modular/outbound_mixin.py` | 수정 (2곳 DESC) |
| `gui_app_modular/handlers/outbound_handlers.py` | 수정 (1곳 DESC) |
| `gui_app_modular/handlers/import_handlers.py` | 수정 (1곳 DESC) |
| `engine_modules/inventory_modular/preflight_mixin.py` | 수정 (1곳 DESC) |
| `version.py`, `VERSION.txt`, `updates/latest.json` | 버전 업데이트 |

---

## 비즈니스 로직 참고

- 출고 순서는 향후 변경될 수 있음 (현재: 큰 번호부터)
- 표시 순서(재고/톤백 리스트)는 기존 ASC 유지 — 출고 순서만 DESC
- 샘플 톤백(is_sample=1)은 출고 대상에서 자동 제외

---

**(주) 지와이로지스 2026년 2월 18일**
