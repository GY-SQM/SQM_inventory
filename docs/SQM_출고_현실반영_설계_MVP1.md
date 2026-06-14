# SQM 출고 현실반영 설계 — MVP-1

> 작성: 2026-06-14 · 3-AI 협업(Claude+Codex+Gemini) 종합
> 목적: "모든 화물이 랙 보관 + 바코드 스캔된다"는 현재 전제를 깨고, 현실(비-랙 일반창고 / 입고 즉시 LOT 출고 / LOT 부분 출고)을 반영.
> 원칙: **기존 톤백 단위 모델·무게보존 검증을 깨지 않고 점진 확장.** MVP-1은 컬럼 추가만 — 기존 동작 100% 보존.

---

## 1. 핵심 설계 한 줄 요약

**`fulfillment_mode`(이행 방식) 컬럼 하나로 3가지 현실을 분기하고, "어떤 톤백인지"는 몰라도 "LOT에서 몇 kg 나갔는지"는 반드시 기록해 무게보존 법칙을 유지한다.**

```
fulfillment_mode
 ├─ SCAN_TONBAG  : 기존 3단계 (랙 + 바코드 스캔) — 변경 없음
 ├─ LOT_QTY      : 스캔 없이 LOT 수량/무게로 출고 (현실 ②③)
 └─ DIRECT       : 기존 quick_outbound 흡수 (예약 없이 즉시)

location_state
 └─ UNLOCATED    : 비-랙 일반창고, 위치 모름 (현실 ①)
```

---

## 2. 현실 3가지 → 데이터 표현

| 현실 | 표현 방법 | 기존 모델 영향 |
|---|---|---|
| ① 비-랙 일반창고 (위치 모름) | `inventory_tonbag.location_state='UNLOCATED'` (실제 위치 `location`과 의미 분리) | 위치만 비움. 무게/수량 추적은 그대로 |
| ② 입고 즉시 LOT 출고 (스캔 X) | `allocation_plan.fulfillment_mode='LOT_QTY'`, `scan_required=0`, `tonbag_id=NULL`, 수량·무게만 | 톤백 개별식별 생략, `current_weight` 차감은 동일 |
| ③ LOT 부분 출고 | LOT 수량 원장에 `outbound_qty_mt` 일부만 → LOT은 `PARTIAL` | 부분 차감 후 잔량 계속 가용 |

> **중요 구분:** 현재 `tonbag_id=NULL`은 "스캔 대기(LOT-MODE)" 의미인데, 여기에 "스캔 생략(LOT_QTY)"이 겹치면 충돌. → `fulfillment_mode`로 명확히 분리한다.

---

## 3. 스키마 변경 (MVP-1) — 컬럼 추가만, idempotent

기존 마이그레이션 패턴(`db_migration_mixin.py:104` 등 `PRAGMA table_info` 후 조건부 `ALTER`)을 그대로 따른다.

```python
def _migrate_v874_outbound_reality(self) -> None:
    """v8.7.4: 출고 현실반영 — fulfillment_mode / scan_required / location_state 추가.
    모두 nullable 또는 DEFAULT 값 → 기존 레코드/동작 무영향."""
    try:
        # allocation_plan: 이행 방식 + 스캔 선택성
        ap_cols = {r[1].lower() for r in
                   self.execute("PRAGMA table_info(allocation_plan)").fetchall()}
        if 'fulfillment_mode' not in ap_cols:
            self.execute("ALTER TABLE allocation_plan "
                         "ADD COLUMN fulfillment_mode TEXT DEFAULT 'SCAN_TONBAG'")
        if 'scan_required' not in ap_cols:
            self.execute("ALTER TABLE allocation_plan "
                         "ADD COLUMN scan_required INTEGER DEFAULT 1")
        if 'outbound_qty_mt' not in ap_cols:
            self.execute("ALTER TABLE allocation_plan "
                         "ADD COLUMN outbound_qty_mt REAL DEFAULT 0")

        # inventory_tonbag: 위치 상태 (실제 location 문자열과 의미 분리)
        tb_cols = {r[1].lower() for r in
                   self.execute("PRAGMA table_info(inventory_tonbag)").fetchall()}
        if 'location_state' not in tb_cols:
            self.execute("ALTER TABLE inventory_tonbag "
                         "ADD COLUMN location_state TEXT")  # NULL=일반, 'UNLOCATED'=위치모름

        # inventory: LOT 레벨에도 위치상태 요약(선택)
        inv_cols = {r[1].lower() for r in
                    self.execute("PRAGMA table_info(inventory)").fetchall()}
        if 'location_state' not in inv_cols:
            self.execute("ALTER TABLE inventory ADD COLUMN location_state TEXT")

        # 이중출고 방지 보조 키 (톤백 없는 LOT 출고용) — 부분 인덱스
        self.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_alloc_lotqty_dedup
            ON allocation_plan(lot_no, customer, sale_ref, outbound_date)
            WHERE fulfillment_mode='LOT_QTY' AND status IN ('PICKED','OUTBOUND','SOLD')
        """)
        logger.info("[v8.7.4] 출고 현실반영 컬럼/인덱스 추가 완료")
    except (sqlite3.OperationalError, OSError) as e:
        if "duplicate column" not in str(e).lower():
            logger.warning(f"[v8.7.4] 출고 현실반영 마이그레이션 오류: {e}")
```

> 등록: 다른 `_migrate_*` 호출부와 동일한 순서 지점에 추가.

### 필드 의미 정의

| 테이블.컬럼 | 값 | 의미 |
|---|---|---|
| `allocation_plan.fulfillment_mode` | `SCAN_TONBAG`(기본) / `LOT_QTY` / `DIRECT` | 출고 이행 방식 |
| `allocation_plan.scan_required` | `1`(기본) / `0` | 바코드 스캔 필요 여부 |
| `allocation_plan.outbound_qty_mt` | REAL | LOT_QTY 경로의 실제 출고 무게(MT). 부분출고 누적 |
| `inventory_tonbag.location_state` | `NULL` / `'UNLOCATED'` | 위치 추적 가능 여부 |
| `inventory.location_state` | `NULL` / `'UNLOCATED'` / `'MIXED'` | LOT 단위 위치상태 요약 |

---

## 4. 워크플로우 — 스캔은 선택, 무게는 진실

### 기존 (유지, 변경 0)
```
AVAILABLE → [예약] RESERVED → [스캔] PICKED → [확정] OUTBOUND
fulfillment_mode = SCAN_TONBAG
```

### 신규 LOT_QTY 경로 (병렬 추가)
```
[LOT 수량 출고]  (tonbag_id=NULL, scan_required=0)
 1. LOT 선택 + 고객/sale_ref + 출고무게(전량 또는 부분)
 2. allocation_plan INSERT (fulfillment_mode='LOT_QTY', outbound_qty_mt=X, status='OUTBOUND')
 3. inventory.current_weight -= X,  picked_weight += X
 4. stock_movement INSERT (movement_type='LOT_OUTBOUND')
 5. _recalc_lot_status() — 잔량>0 이면 PARTIAL, 0 이면 OUTBOUND
```

핵심: 톤백 1:1 매칭은 생략하되 **LOT 무게 장부는 정확히 차감** → `initial = current + picked (±1kg)` 불변.

---

## 5. 무결성 규칙 (절대 안 깨지게)

| 검증 | 기존 | LOT_QTY 경로 대응 |
|---|---|---|
| 무게보존 `initial=current+picked±1kg` | confirm 후 검증 (`outbound_mixin.py:2773`) | 동일 검증 함수 재사용. 차감 후 호출 |
| 음수재고 | TRIGGER `current_weight>=0` (`db_migration_mixin.py:2676`) | 동일 TRIGGER에 자동 적용 |
| 이중출고 | `sold_table` tonbag_id 기반 (`:2756`) | tonbag 없으니 **별도 부분 UNIQUE 인덱스**(§3 `idx_alloc_lotqty_dedup`) |
| 가용 초과 | `[QTY_EXCEEDS_AVAILABLE]` (`:2235`) | 출고무게 ≤ current_weight 선검증 |

---

## 6. LOT 상태 재계산 확장 (확장 단계, MVP-1 이후)

현재 `_recalc_lot_status()`(`outbound_mixin.py:1114~1174`)는 **톤백 상태 집계**만 본다.
→ **톤백 집계 + LOT_QTY 출고 누적**을 함께 보도록 확장:

```
출고무게 = (PICKED/OUTBOUND 톤백 무게 합) + (allocation_plan.outbound_qty_mt 합 where LOT_QTY)
LOT 상태:
  출고무게 == 0           → AVAILABLE
  0 < 출고무게 < initial  → PARTIAL
  출고무게 >= initial-1kg → OUTBOUND
```

---

## 7. 영향받는 코드 위치

| 파일:줄 | 변경 |
|---|---|
| `engine_modules/db_migration_mixin.py` (신규 `_migrate_v874_*`) | 컬럼/인덱스 추가 |
| `engine_modules/inventory_modular/outbound_mixin.py:4074` (quick_outbound) | `DIRECT` 모드로 흡수(확장단계) |
| `outbound_mixin.py` 신규 `outbound_lot_qty()` | LOT_QTY 출고 진입점 |
| `outbound_mixin.py:1114` (_recalc_lot_status) | 원장 누적 합산 추가(확장단계) |
| `backend/api/outbound_api.py` | `POST /api/outbound/lot-qty` 신규 + 통합(확장단계) |

---

## 8. 위험과 완화책

| 위험 | 완화 |
|---|---|
| 추적성 상실(어느 톤백 나갔는지 모름) | 출고시점·고객·LOT·무게는 `stock_movement`에 100% 기록 → LOT 단위 감사추적 유지 |
| 재고 부정확(스캔 안 함) | 무게보존 ±1kg 강제 + 주기적 재고실사. UNLOCATED 우선 실사 표시 |
| 사후 톤백 식별 필요 | 원장에 역소급(reconcile) 여지 남김 (사후 tonbag_id 매핑 허용) |
| 두 경로 혼용 시 LOT 상태 꼬임 | 상태 재계산을 톤백+원장 통합 기준으로 일원화(§6) |

---

## 9. 테스트 계획 (회귀 방지)

1. **마이그레이션 idempotent**: 두 번 실행해도 오류 없음 + 기존 데이터 무변경.
2. **기존 SCAN_TONBAG 경로 무영향**: 기존 출고 테스트 전부 통과.
3. **LOT_QTY 전량 출고**: current_weight=0, picked_weight=initial, LOT=OUTBOUND, 무게보존 OK.
4. **LOT_QTY 부분 출고**: 잔량>0, LOT=PARTIAL, 두 번째 부분출고 누적 정확.
5. **이중출고 차단**: 동일 (lot,customer,sale_ref,date) LOT_QTY 재시도 → UNIQUE 위반 차단.
6. **음수 방지**: current_weight 초과 출고 시도 → 차단.
7. **UNLOCATED 톤백**: location_state='UNLOCATED'여도 출고/조회 정상.

---

## 10. 단계별 로드맵

- **MVP-1 (본 문서)**: §3 컬럼/인덱스 추가만. 안전·무영향. ← **지금 구현 대상**
- **MVP-2**: `outbound_lot_qty()` + `POST /api/outbound/lot-qty` 구현 (수량/무게 출고).
- **확장-3**: SCAN_TONBAG / quick / LOT_QTY 단일 출고 API 통합.
- **확장-4**: `_recalc_lot_status` 원장 통합 + 재고실사 보정 화면.

---

## 부록: 3-AI 합의점

- **Codex**(코드 기반): `fulfillment_mode` 분기 + LOT 수량 원장 + nullable 마이그레이션. 이중출고 별도키 필요성 지적.
- **Gemini**(설계): 이벤트/원장(ledger)으로 변경을 기록, `available/reserved` 상태 명시화, 재고실사 보정.
- **Claude**(종합): 현실 3시나리오 매핑 + 무게보존 불변 보장 + 점진 로드맵.
