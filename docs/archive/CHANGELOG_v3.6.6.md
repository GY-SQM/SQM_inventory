# SQM 재고관리 시스템 v3.6.6 - 전면 디버깅 & 핵심 버그 수정

**릴리스일**: 2026-02-04
**작성자**: Ruby (남기동)

---

## 🔴 핵심 버그 수정 (FIX-13)
### `self.engine` → `self.db` 참조 불일치 전면 수정

**문제**: InboundMixin/OutboundMixin이 SQLAlchemy 패턴(`self.engine.begin()`, `self.engine.connect()`)을 사용했으나, SQMInventoryEngineV3는 `self.db = SQMDatabase()` 만 초기화 → **AttributeError**

**영향 범위**: 입고/출고의 모든 트랜잭션 (6곳)
- `inbound_mixin.py`: L93 `self.engine.begin()`, L125 `self.engine.connect()`
- `outbound_mixin.py`: L81, L197 `self.engine.begin()`, L368 `self.engine.connect()`

**수정 내용**:
- `inbound_mixin.py`: 전면 재작성 → `self.db.transaction()` + `self.db.execute()` 패턴
- `outbound_mixin.py`: 전면 재작성 → `self.db.transaction()` + `self.db.fetchone()` 패턴
- SQLAlchemy `text()` / named params → SQLite `?` placeholder 전환
- 실제 DB 스키마 컬럼명 매칭 (initial_weight, current_weight, mxbg_pallet)

## ✅ 기능 개선 (FIX-15)
### bag_count 기반 톤백 자동 생성
- 입고 시 `tonbags` 리스트 없어도 `bag_count` > 0이면 자동 균등 분할 생성
- 예: bag_count=5, net_weight=5000 → 1000kg × 5개 톤백 자동 생성

## 🔧 Export 수정 (FIX-16)
### export_mixin.py 컬럼명 정합성
- `total_weight_kg` → `initial_weight`
- `available_weight_kg` → `current_weight`
- `bag_count` → `mxbg_pallet`
- 제품별 요약 집계 안전성 강화

## 📊 테스트 결과
| 항목 | 수정 전 | 수정 후 |
|------|---------|---------|
| **통과** | 217 | **499** |
| **코드 버그** | ~40건 | **0건** |
| **환경 이슈** | 22건 | 22건 (tkinter/모듈) |

### 핵심 테스트 파일 전수 통과:
- ✅ test_inbound.py (14/14)
- ✅ test_outbound.py (13/13)
- ✅ test_database.py (5/5)
- ✅ test_engine.py (37/37 + 1 skip)
- ✅ test_inventory.py (12/12)
- ✅ test_inventory_modular.py (25/25 + 2 skip)
- ✅ test_core_modular.py (49/49)
- ✅ integration/test_workflow.py (6/6)
- ✅ unit/test_engine.py (27/27)

## 수정 파일 목록
1. `engine_modules/inventory_modular/inbound_mixin.py` - 전면 재작성
2. `engine_modules/inventory_modular/outbound_mixin.py` - 전면 재작성
3. `engine_modules/inventory_modular/export_mixin.py` - 컬럼명 수정
4. `tests/test_inbound.py` - API 키 매핑
5. `tests/test_outbound.py` - API 키 매핑
6. `tests/test_engine.py` - API 키 매핑
7. `tests/test_inventory.py` - API 키 매핑
8. `tests/unit/test_engine.py` - 전면 수정
9. `tests/integration/test_workflow.py` - API 키 매핑
