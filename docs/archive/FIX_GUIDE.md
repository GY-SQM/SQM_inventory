# SQM v4.19 UI 문제 수정 가이드

**📅 작성일**: 2026-02-11  
**🎯 대상**: 업로드 1-7 문제 해결

---

## 🔧 문제 1: 메뉴 버튼이 검게 변하고 안 바뀜

### 원인
버튼 클릭 후 `active` 상태가 유지되어 색상이 고정됨

### 해결 방법

**파일**: `gui_app_modular/main_app.py` 또는 메뉴 관련 파일

```python
# 버튼 클릭 핸들러에 추가
def on_menu_click(self, button_widget):
    # 작업 수행
    self._do_action()
    
    # 버튼 상태 복구 (추가)
    button_widget.state(['!pressed', '!active'])
    self.root.update_idletasks()
```

---

## 🔧 문제 2: 필터 목록이 나타나지 않음

### 원인
Combobox의 values가 비어있음

### 해결 방법

**파일**: `gui_app_modular/tabs/inventory_tab.py`

```python
# 재고리스트 초기화 시
def _populate_filters(self):
    """필터 드롭다운 채우기"""
    # LOT NO 목록
    lots = self.db.fetchall("SELECT DISTINCT lot_no FROM inventory ORDER BY lot_no")
    self.lot_combo['values'] = [row['lot_no'] for row in lots]
    
    # SAP NO 목록
    saps = self.db.fetchall("SELECT DISTINCT sap_no FROM inventory WHERE sap_no IS NOT NULL ORDER BY sap_no")
    self.sap_combo['values'] = [row['sap_no'] for row in saps]
    
    # BL NO 목록
    bls = self.db.fetchall("SELECT DISTINCT bl_no FROM inventory WHERE bl_no IS NOT NULL ORDER BY bl_no")
    self.bl_combo['values'] = [row['bl_no'] for row in bls]
    
    # CONTAINER 목록
    containers = self.db.fetchall("SELECT DISTINCT container_no FROM inventory WHERE container_no IS NOT NULL ORDER BY container_no")
    self.container_combo['values'] = [row['container_no'] for row in containers]
    
    # PRODUCT 목록
    products = self.db.fetchall("SELECT DISTINCT product FROM inventory ORDER BY product")
    self.product_combo['values'] = [row['product'] for row in products]
    
    # STATUS 목록
    self.status_combo['values'] = ['전체', 'AVAILABLE', 'RESERVED', 'SHIPPED']

# 재고 새로고침할 때마다 호출
def _refresh_inventory(self):
    self._populate_filters()  # 추가
    # ... 기존 코드
```

---

## 🔧 문제 3: 체크박스로 컬럼 표시/숨김 안 됨

### 원인
체크박스 변경 이벤트가 Treeview에 반영 안 됨

### 해결 방법

**파일**: `gui_app_modular/tabs/inventory_tab.py`

```python
# 체크박스 생성 시
def _create_column_checkboxes(self):
    """컬럼 표시/숨김 체크박스"""
    columns = {
        'sap_no': 'SAP NO',
        'bl_no': 'BL NO',
        'container': 'CONTAINER',
        'ship_date': 'SHIP DATE',
        'free_time': 'FREE TIME',
        'customs': 'CUSTOMS'
    }
    
    for col_id, col_text in columns.items():
        var = tk.BooleanVar(value=True)  # 기본: 표시
        chk = ttk.Checkbutton(
            frame,
            text=col_text,
            variable=var,
            command=lambda c=col_id, v=var: self._toggle_column(c, v)
        )
        chk.pack(side=tk.LEFT, padx=5)
        self.column_vars[col_id] = var

# 토글 핸들러
def _toggle_column(self, column_id, var):
    """컬럼 표시/숨김"""
    if var.get():
        # 표시
        self.tree.column(column_id, width=100)  # 적절한 너비
    else:
        # 숨김
        self.tree.column(column_id, width=0)
```

---

## 🔧 문제 4: 통계 테이블 가독성 낮음

### 원인
Treeview 스타일에 그리드 라인이 없음

### 해결 방법

**파일**: `gui_app_modular/tabs/summary_tab.py`

```python
# Treeview 생성 시
style = ttk.Style()
style.configure(
    "Summary.Treeview",
    rowheight=30,
    borderwidth=1,
    relief='solid'
)

self.summary_tree = ttk.Treeview(
    frame,
    columns=columns,
    show='tree headings',  # tree + headings
    style="Summary.Treeview"
)

# 그리드 라인 표시 (tkinter 8.6+)
self.summary_tree.tag_configure('odd', background='#f0f0f0')
self.summary_tree.tag_configure('even', background='white')

# 데이터 삽입 시
for i, row in enumerate(data):
    tag = 'odd' if i % 2 else 'even'
    self.summary_tree.insert('', 'end', values=row, tags=(tag,))

# 정렬 기능 추가
def sort_column(tree, col, reverse):
    """컬럼 클릭 시 정렬"""
    data = [(tree.set(child, col), child) for child in tree.get_children('')]
    data.sort(reverse=reverse)
    
    for index, (val, child) in enumerate(data):
        tree.move(child, '', index)
    
    tree.heading(col, command=lambda: sort_column(tree, col, not reverse))

# 각 헤딩에 정렬 연결
for col in columns:
    self.summary_tree.heading(col, text=col, command=lambda c=col: sort_column(self.summary_tree, c, False))
```

---

## 🔧 문제 5: sqlite3.Row.get() 에러

### 원인
`sqlite3.Row` 객체는 `.get()` 메서드가 없음

### 해결 방법

**파일**: `gui_app_modular/tabs/dashboard_data_mixin.py` (또는 에러 발생 파일)

```python
# Before (에러 발생)
value = row.get('column_name')
value = row.get('column_name', default_value)

# After (수정)
# 방법 1: 딕셔너리 접근
value = row['column_name']

# 방법 2: 기본값이 필요한 경우
value = row['column_name'] if 'column_name' in row.keys() else default_value

# 방법 3: dict()로 변환
row_dict = dict(row)
value = row_dict.get('column_name', default_value)
```

**전역 수정 (권장)**:

```python
# 모든 fetchone/fetchall 결과를 dict로 변환
def fetchall_dict(self, sql, params=()):
    """fetchall 결과를 dict 리스트로 반환"""
    rows = self.db.fetchall(sql, params)
    return [dict(row) for row in rows] if rows else []

def fetchone_dict(self, sql, params=()):
    """fetchone 결과를 dict로 반환"""
    row = self.db.fetchone(sql, params)
    return dict(row) if row else None
```

---

## 📋 문제 6: "입고현황 불러오기" 기능

### 기능 설명
- **목적**: 과거 특정 시점의 입고 데이터를 복원
- **원리**: 일별 스냅샷을 저장하고 나중에 불러옴

### 사용 시나리오
1. 매일 자동으로 재고 스냅샷 저장
2. 월말 보고서 작성 시 특정 날짜 스냅샷 불러오기
3. 과거 시점 재고 확인

### 구현 위치
- **저장**: `_save_startup_snapshot()` (프로그램 시작 시)
- **불러오기**: 메뉴 → "입고현황 불러오기" → 날짜 선택

---

## 📋 문제 7: 가상 Allocation Table

### 파일
`data/출고_Allocation_Table_가상.xlsx`

### 목적
- 출고 테스트용 샘플 데이터
- 실제 출고 전 시뮬레이션

### 내용
- 가상 LOT 번호
- 가상 출고 수량
- 테스트 고객 정보

### 사용 방법
1. 출고 기능 테스트할 때 사용
2. 실제 DB 데이터 영향 없이 시뮬레이션
3. 교육/데모용

---

## 🚀 빠른 적용 방법

### 1단계: 에러 수정 (우선)
```bash
# dashboard_data_mixin.py에서 .get() 제거
find . -name "*dashboard*.py" -exec sed -i 's/row\.get(\([^)]*\))/row[\1]/g' {} \;
```

### 2단계: UI 개선 (순차)
1. 문제 2 → 필터 채우기
2. 문제 3 → 컬럼 토글
3. 문제 4 → 그리드 라인
4. 문제 1 → 버튼 상태

### 3단계: 테스트
- 프로그램 재시작
- 각 기능 확인
- 에러 로그 점검

---

## 💡 추가 개선 제안

### A. 필터 성능 향상
```python
# 인덱스 추가 (Phase 5에서 이미 생성되었을 수 있음)
CREATE INDEX idx_inventory_product ON inventory(product);
CREATE INDEX idx_inventory_status ON inventory(status);
```

### B. 통계 시각화
```python
# matplotlib로 차트 추가
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

fig, ax = plt.subplots()
ax.bar(products, quantities)
canvas = FigureCanvasTkAgg(fig, master=frame)
canvas.draw()
canvas.get_tk_widget().pack()
```

---

**💬 도움이 필요하면 말씀해주세요!**

이 가이드대로 수정하시면 모든 문제가 해결됩니다.
