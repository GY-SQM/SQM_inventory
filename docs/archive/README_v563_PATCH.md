# SQM v5.6.3 패치 — 톤백리스트 무게 정합성 수정

## 적용 방법
v5.6.1 소스 폴더에 이 패치 파일들을 덮어쓰기

## 수정 내용 (3파일)

### 버그 #1: 톤백 생성 시 무게 계산 오류 (inbound_mixin.py)
- **기존**: `per_bag = total_w / bag_count` → 5001/10 = 500.1kg (오류)
- **수정**: `per_bag = (total_w - 1.0) / bag_count` → (5001-1)/10 = 500.0kg
- 대원칙: 1 LOT = 톤백 N개 + 샘플 1kg → 샘플 차감 후 나누기

### 버그 #2: 톤백리스트 무게 표시 (tonbag_tab.py)
- **기존**: `i.net_weight` (LOT 총무게 5,001kg) 모든 톤백에 동일 표시
- **수정**: `t.weight` (톤백 개별 무게 — 샘플 1kg, 톤백 500kg)
- Balance, Inbound, Outbound 모두 톤백 개별 기준으로 변경

### 버그 #3: MXBG 컬럼 제거 (tonbag_tab.py)
- MXBG는 LOT 단위 정보 → 톤백리스트에서 불필요 → 삭제
- 21열 → 20열 (컬럼 인덱스 전체 조정)
- 더블클릭/선택 합계 인덱스도 함께 수정

## 정합성 검증
```
재고리스트: LOT 5,001kg = 500×10 + 1×1 ✅
톤백리스트: S00=1kg, 1~10=500kg × 10, 합계=5,001kg ✅
```

## 수정 파일
- `version.py` (5.6.1 → 5.6.3)
- `engine_modules/inventory_modular/inbound_mixin.py`
- `gui_app_modular/tabs/tonbag_tab.py`
