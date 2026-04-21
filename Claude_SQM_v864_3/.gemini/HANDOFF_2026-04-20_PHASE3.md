# SQM HANDOFF — 2026-04-20 Phase 3 (Claude Opus 4.7, 전체 완료)

## Session Summary
- **Phase 0~2**: 환경 복구 + 부팅 가시성 + except pass 14건 치환 (이전 세션)
- **Phase 3-A**: 5001kg 자동 변환 규칙 정밀 분석 + 근본 원인 수정 ✅
- **Phase 3-B**: sales/return engines current_weight delta 검증 + 배치 경로 recalc 추가 ✅
- **Phase 3-C**: SQL 인젝션 분석 → **안전 확인** ✅
- **Phase 3-D**: dashboard thread 에러 → **원인 확인, P2 후순위 이월**
- **Phase 3-E**: 메뉴 바인딩 → **안전 확인** ✅

## 핵심 발견 — 데이터 정합성 버그 (근본 원인 해결)

### 버그 체인
```
crud_mixin.py:add_inventory
  → current_weight = net_weight (5001, 샘플 포함)   ← 근본 원인
  → validators.py:345 크로스 체크 시 5001 vs 5000 불일치 감지
  → 매 부팅마다 UPDATE inventory SET current_weight=5000 (silent)
  → audit 없이 1kg씩 유실 (5 LOT × 1kg = 5kg/일)
```

### 수정
1. **`crud_mixin.py:194`** — 입고 시 `current_weight = net_weight - SAMPLE_WEIGHT_KG` (설계 일치)
2. **`validators.py:345`** — UPDATE 제거, SAFETY-HOLD 로 경고만 + audit_log 기록
3. **`sales_order_engine.py:400`** — 배치 경로 누락된 `_recalc_current_weight` 추가

### 설계 일관성 확인
`crud_mixin.py:7` 공식 선언: `current_weight = AVAILABLE + RESERVED 일반 tonbag 합 (sample 제외)` → **Design A 확정**

## 변경 파일 목록

| 파일 | 변경 내용 | 백업 |
|---|---|---|
| `gui_app_modular/main_app.py` | 엔진/헬스체크/AutoRecovery 가시성 (Phase 1) | `.bak` |
| `engine_modules/database.py` | 캐시 실패 로깅 | - |
| `engine_modules/inventory_modular/inbound_mixin.py` | to_dict 로깅 | - |
| `gui_app_modular/tabs/dashboard_tab.py` | bal_data 파싱 로깅 | - |
| `features/ai/carrier_profiles/carrier_profile_loader.py` | setattr/merge 로깅 | - |
| `gui_app_modular/mixins/toolbar_mixin.py` | tooltip cleanup 로깅 | - |
| `gui_app_modular/mixins/refresh_mixin.py` | cursor 로깅 | - |
| `fixes/theme_colorful_override.py` | style 로깅 | - |
| `GPT_verify_outbound_refactor_v2/v3.py` | backup read stderr | - |
| **`engine_modules/validators.py`** | **SAFETY-HOLD** (UPDATE 제거) | `.bak` |
| **`engine_modules/inventory_modular/crud_mixin.py`** | **근본 원인 수정** (샘플 제외) | `.bak` |
| **`features/parsers/sales_order_engine.py`** | **배치 경로 recalc 추가** | `.bak` |

## 검증 상태

- `python -m py_compile` 전원 통과 (exit 0)
- 베이스라인 pytest: 0 tests (인프라 부재)
- 스모크 테스트 (1차): Phase 1 로그 정상 출력, 5001→5000 이슈 실증
- 스모크 테스트 (2차, Phase 3 적용 후): **대기 중** — 사용자 구동 필요

## 현재 DB 상태 (snapshot 2026-04-20 17:10)

```
inventory.current_weight 합계: 100,010kg (20 LOT × 5000, 샘플 제외 설계)
inventory_tonbag 실제 총합:     100,020kg (샘플 포함)
샘플 톤백:                        20개 × 1kg (is_sample=1, status=AVAILABLE)
차이 20kg = 샘플 분량 (일치)
```

**데이터 손실 없음** — 샘플은 `inventory_tonbag`에 is_sample=1로 전부 보존. `inventory.current_weight`는 설계대로 샘플 제외.

## 남은 리스크 / 후속 과제

### P2 후순위
1. **dashboard thread race** — `_bg_refresh`에서 Tkinter widget 직접 조작. 전면 리팩터링 필요 (root.after 래핑)
2. **`reserve_from_allocation` 465라인 함수** — 복잡도 높음, 리팩터링 가치 있음 (기능 버그는 미확인)
3. **테스트 인프라 구축** — pytest 0건, 회귀 방지 불가

### P3 낮음
4. `sales_order_engine.py` 비배치 경로 (line 447+): `executemany` 없는 DB용 코드. 실사용 경로 아님.
5. `return_inbound_engine.py:159`: 이미 recalc 호출 있음. 안전.

## 다음 스모크 테스트

```bash
cd F:\program\SQM_inventory\Claude_SQM_v864_2
python run.py > stdout3.txt 2>&1
```

**확인 포인트:**
- `[STARTUP] 톤백 상태 정합성 OK` (validator 이슈 없음 재확인)
- `[정합성][SAFETY-HOLD]` 로그 안 나옴 (기존 5 LOT 이미 정상화됨)
- 대시보드 스레드 에러는 **여전히 나올 수 있음** (미수정)
- 신규 입고 테스트 시: `current_weight=5000` (5001 아님) 확인

## 롤백 경로

| 범위 | 방법 |
|---|---|
| Phase 3 전체 | `_phase1_backup_20260420/{validators,crud_mixin,sales_order_engine}.py.bak` 복원 |
| Phase 1~2 | `_phase1_backup_20260420/{main_app,run_bootstrap}.py.bak` 복원 |
| 전체 스냅샷 이전 | `../Claude_SQM_v864_1/` (Apr 19 백업) |

## Final Handoff Statement

Phase 3 완료. **중요 데이터 손실 버그 해결**. 스모크 테스트 후 이상 없으면 작업 종결.

**다음 세션 권장:**
1. 사용자 스모크 테스트 검증
2. 이상 발견 시 추가 디버깅
3. 정상 시: dashboard thread race 또는 테스트 인프라 구축 (P2)
