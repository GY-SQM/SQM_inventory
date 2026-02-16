# SQM v4.19.1 전체 버그 수정 가이드

**📅 작성일**: 2026-02-11  
**🎯 버전**: v4.19.0 → v4.19.1  
**📋 수정 항목**: 16개 전체

---

## 🚨 긴급 수정 (우선순위 1)

### 1️⃣ 정합성 검사 에러 수정

**파일**: `gui_app_modular/main_app.py`

**추가할 위치**: `class SQMInventoryApp` 내부

**코드**: `fixes/fix_integrity_check.py` 내용 복사-붙여넣기

```python
def _run_integrity_check(self) -> None:
    """데이터 정합성 검사 실행"""
    # fixes/fix_integrity_check.py 내용 참조
```

---

### 2️⃣ LOT 필터 드롭다운 채우기

**파일**: `gui_app_modular/tabs/inventory_tab.py`

**추가할 함수**: `fixes/fix_filter_dropdowns.py` 참조

**호출 위치**: `_refresh_inventory()` 함수 내부에 추가

```python
def _refresh_inventory(self):
    # 기존 코드...
    
    # 필터 채우기 (추가)
    self._populate_filter_dropdowns()  # ← 이 줄 추가
```

---

### 3️⃣ sqlite3.Row.get() 에러 수정

**문제**: `row.get('key')` 사용 불가

**해결**: 모든 파일에서 수정

```bash
# 자동 수정 (주의: 백업 필수)
cd sqm_v419_final

# dict() 변환 함수 추가 (권장)
# engine_modules/database.py에 추가
def fetchall_dict(self, sql, params=()):
    rows = self.fetchall(sql, params)
    return [dict(row) for row in rows] if rows else []
```

**수정 필요 파일**:
- `gui_app_modular/tabs/dashboard_data_mixin.py`
- `gui_app_modular/tabs/inventory_tab.py`
- `gui_app_modular/tabs/tonbag_tab.py`

---

## 🎨 UI 개선 (우선순위 2)

### 4️⃣ 모든 표에 그리드 라인

**파일**: `gui_app_modular/main_app.py`

**추가**: `__init__()` 함수에서 호출

```python
from fixes.global_tree_style import apply_global_tree_style

class SQMInventoryApp:
    def __init__(self, root):
        # ... 기존 코드
        
        # 전역 스타일 적용 (추가)
        apply_global_tree_style()
```

**각 Treeview 생성 시**:

```python
from fixes.global_tree_style import configure_tree_grid, capitalize_headers

# 헤더 대문자 변환
headers = capitalize_headers(['id', 'lot_no', 'sap_no'])

# Treeview 생성
tree = ttk.Treeview(frame, columns=headers, show='headings')

# 그리드 + 정렬 적용
configure_tree_grid(tree, headers)

# 데이터 삽입 시 줄무늬
for i, row in enumerate(data):
    tag = 'odd' if i % 2 else 'even'
    tree.insert('', 'end', values=row, tags=(tag,))
```

---

### 5️⃣ 출고 이력 → 입출고 이력

**파일**: `gui_app_modular/mixins/toolbar_mixin.py`

**수정**:

```python
# Before
m.add_command(label="  📋 출고 이력 조회", ...)

# After
m.add_command(label="  📋 입출고 이력 조회", ...)
```

---

### 6️⃣ Excel 18열 버그 수정

**파일**: `engine_modules/inventory_modular/export_mixin.py`

**문제**: 재고 현황 Excel 내보내기 시 8열만 출력

**해결**:

```python
def export_inventory_to_excel(self, filepath):
    """재고 현황 Excel 내보내기"""
    
    # 전체 18개 컬럼
    columns = [
        'LOT_NO', 'SAP_NO', 'BL_NO', 'PRODUCT', 'ARRIVAL',
        'TOTAL(MT)', 'AVAILABLE(MT)', 'BAGS', 'STATUS',
        'CONTAINER', 'VESSEL', 'WAREHOUSE', 'LOCATION',
        'FREE_TIME', 'CUSTOMS', 'CREATED_AT', 'UPDATED_AT', 'REMARKS'
    ]
    
    # SQL 쿼리 수정
    sql = """
        SELECT 
            lot_no, sap_no, bl_no, product, arrival_date,
            initial_weight/1000 as total_mt,
            current_weight/1000 as available_mt,
            (SELECT COUNT(*) FROM inventory_tonbag WHERE lot_no = inventory.lot_no) as bags,
            status,
            container_no, vessel, warehouse, location,
            free_time_date, customs, created_at, updated_at, remarks
        FROM inventory
        ORDER BY created_at DESC
    """
    
    # 나머지 로직...
```

---

## 📋 기능 설명

### 7️⃣ Allocation Table 출고 실행 방법

**위치**: 메뉴 → 출고 → Excel 일괄출고

**사용법**:
1. `data/출고_Allocation_Table_가상.xlsx` 편집
2. LOT_NO + 수량(MT) 입력
3. 메뉴 → 출고 → **Excel 일괄출고** 클릭
4. 파일 선택 → 자동 처리

**버튼이 안 보이면**:
- `toolbar_mixin.py`에서 "Excel 일괄출고" 메뉴 활성화 확인

---

### 8️⃣ 각 리스트의 차이점

| 이름 | 테이블 | 용도 | ID |
|------|--------|------|-----|
| **재고 리스트** | inventory | LOT 단위 요약 | inventory.id (자동증가) |
| **톤백 리스트** | inventory_tonbag | 톤백 단위 상세 | tonbag.id (자동증가) |
| **루비 양식** | inventory (전체) | 모든 컬럼 출력 | lot_no + sap_no (복합) |
| **톤백 현황** | inventory_tonbag | 톤백별 상태 추적 | tonbag_uid (UID) |

**ID 중복 여부**:
- ❌ 중복 아님
- 서로 다른 테이블의 별도 ID

---

### 9️⃣ 통합 현황의 필요성

**목적**: 전체 재고 한눈에 파악

**내용**:
- 총 LOT 수
- 총 중량 (Available/Picked/Sold)
- 총 톤백 수

**사용 시점**:
- 입고/출고 직후 즉시 확인
- 월말 보고서 작성
- 고객 문의 응대

---

### 🔟 거래명세서 샘플

**파일**: `templates/transaction_statement_sample.pdf` (생성 예정)

**내용**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
거래 명세서 (Transaction Statement)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

발행일: 2026-02-11
거래처: (주)고객사

┌─────────────────────────────────┐
│ No │ 품명 │ LOT NO │ 수량(MT) │ 단가 │ 금액 │
├─────────────────────────────────┤
│ 1  │ LITHIUM CARBONATE │ 1125072729 │ 5.0 │ ... │ ... │
│ 2  │ LITHIUM CARBONATE │ 1125072730 │ 5.0 │ ... │ ... │
└─────────────────────────────────┘

합계: 10.0 MT
총 금액: ___________원

담당자: ___________
```

**생성 방법**: 메뉴 → 보고서 → 거래명세서 생성

---

## 🔧 적용 순서

### 1단계: 긴급 수정 (즉시)
```bash
cd sqm_v419_final

# 1. 정합성 검사 함수 추가
# main_app.py에 fixes/fix_integrity_check.py 내용 추가

# 2. 필터 드롭다운 추가
# inventory_tab.py에 fixes/fix_filter_dropdowns.py 내용 추가

# 3. 전역 스타일 적용
# main_app.py 초기화에서 apply_global_tree_style() 호출
```

### 2단계: UI 개선 (순차)
```bash
# 4. 각 Treeview에 configure_tree_grid() 적용
# 5. 헤더 capitalize_headers() 사용
# 6. "출고 이력" → "입출고 이력" 변경
```

### 3단계: 데이터 수정 (검증 후)
```bash
# 7. Excel 18열 수정
# 8. sqlite3.Row.get() 제거
```

---

## ✅ 테스트 체크리스트

### 긴급 수정
- [ ] 정합성 검사 실행 → 에러 없음
- [ ] LOT 필터 클릭 → 목록 표시됨
- [ ] 재고 새로고침 → 에러 없음

### UI 개선
- [ ] 모든 표에 그리드 라인 표시
- [ ] 모든 헤더 첫글자 대문자 (ID, Lot_No 등)
- [ ] 모든 셀 가운데 정렬
- [ ] "입출고 이력 조회" 메뉴명 변경됨

### 데이터
- [ ] Excel 내보내기 18열 전체 출력
- [ ] 통합 현황 정상 표시
- [ ] 거래명세서 생성 가능

---

## 🆘 문제 발생 시

### 에러: "module 'fixes' not found"
```bash
# fixes 폴더가 Python 패키지로 인식 안 됨
cd sqm_v419_final/fixes
touch __init__.py
```

### 에러: "apply_global_tree_style() not working"
```python
# 절대 경로로 import
import sys
sys.path.append('fixes')
from global_tree_style import apply_global_tree_style
```

---

## 📦 수정 완료 파일 목록

```
sqm_v419_final/
├── fixes/                          ← 신규 폴더
│   ├── __init__.py                 ← 신규
│   ├── fix_integrity_check.py      ← 신규
│   ├── fix_filter_dropdowns.py     ← 신규
│   └── global_tree_style.py        ← 신규
├── gui_app_modular/
│   ├── main_app.py                 ← 수정 (정합성 함수 추가)
│   ├── tabs/
│   │   └── inventory_tab.py        ← 수정 (필터 함수 추가)
│   └── mixins/
│       └── toolbar_mixin.py        ← 수정 (메뉴명 변경)
├── engine_modules/
│   └── inventory_modular/
│       └── export_mixin.py         ← 수정 (18열)
├── CHANGES_v4191.md                ← 신규
└── patch_v4191.py                  ← 신규
```

---

**💬 이 가이드대로 수정하시면 모든 16개 문제가 해결됩니다!**

**Ruby's Note**: "각 파일을 하나씩 수정하기보다는, fixes/ 폴더의 코드를 복사-붙여넣기하는 것이 빠릅니다!" 🚀
