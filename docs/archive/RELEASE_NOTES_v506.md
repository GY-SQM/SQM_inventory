# SQM v5.0.6 릴리즈 노트

**📅 릴리즈**: 2026-02-11  
**🎯 버전**: v5.0.5 → v5.0.6  
**⭐ 유형**: 긴급 수정 (4개 핵심 버그)

---

## 🐛 수정된 버그 (4개)

### 1️⃣ 컬럼 ID 불일치 수정 ✅✅✅

**가장 큰 버그!** 표시 컬럼 토글이 작동하지 않던 핵심 원인!

**문제**:
```python
# inventory_tab.py (Before - 잘못된 ID)
('vessel', 'SHIP DATE')           # ❌ vessel은 존재하지 않음!
('free_time_date', 'FREE TIME')   # ❌ free_time_date도 없음!

# tonbag_tab.py (Before - 잘못된 ID)
('weight', 'WEIGHT')              # ❌ weight 없음!
('status', 'STATUS')              # ❌ status 없음!
```

**실제 컬럼**:
```python
# INVENTORY_COLUMNS
'ship_date'      # ✅ SHIP DATE의 실제 ID
'free_time'      # ✅ FREE TIME의 실제 ID

# TONBAG_COLUMNS  
'net_weight'     # ✅ WEIGHT의 실제 ID
'tonbag_status'  # ✅ STATUS의 실제 ID
```

**수정**:
```python
# inventory_tab.py (After)
('ship_date', 'SHIP DATE'),      # ✅ v5.0.6 수정
('free_time', 'FREE TIME'),      # ✅ v5.0.6 수정

# tonbag_tab.py (After)
('net_weight', 'WEIGHT'),        # ✅ v5.0.6 수정
('tonbag_status', 'STATUS'),     # ✅ v5.0.6 수정
```

**효과**:
- ✅ 표시 컬럼 체크박스 정상 작동
- ✅ SHIP DATE 체크 해제 → 열 사라짐!
- ✅ FREE TIME 체크 해제 → 열 사라짐!
- ✅ 톤백 리스트도 동일하게 작동!

---

### 2️⃣ displaycolumns를 tuple로 변경 ✅

**문제**:
```python
# Before
self.tree['displaycolumns'] = current_display  # list
```

**원인**:
- Tkinter는 내부적으로 Tcl과 통신
- list를 보내면 가끔 Tcl 변환 이슈 발생
- 특정 OS/Python 버전에서 먹통처럼 보임

**수정**:
```python
# After
self.tree['displaycolumns'] = tuple(current_display)  # ✅ tuple
```

**효과**:
- ✅ 모든 환경에서 안정적으로 작동
- ✅ Tcl 변환 이슈 해결

---

### 3️⃣ StatusBar 에러 수정 ✅

**문제**:
```
[ERROR] '... has no attribute main_frame'
```

**원인**:
```python
# Before
self.notebook = ttk.Notebook(self.root)  # root에 직접 배치
```

**StatusBar**가 `self.main_frame`을 찾는데 존재하지 않음

**수정**:
```python
# After
self.main_frame = ttk.Frame(self.root)        # ✅ main_frame 생성
self.main_frame.pack(fill=BOTH, expand=YES)

self.notebook = ttk.Notebook(self.main_frame) # ✅ main_frame 안에 배치
self.notebook.pack(fill=BOTH, expand=YES)
```

**효과**:
- ✅ StatusBar 정상 작동
- ✅ 에러 로그 사라짐

---

### 4️⃣ 메뉴 tk_popup 방식으로 변경 ✅

**문제**:
```python
# Before - post + 폴링 방식
menu.post(x, y)
def check_menu_closed():
    try:
        menu.index('end')  # ❌ 닫혀도 예외 안 남!
        self.root.after(100, check_menu_closed)
    except:
        # 버튼 복구
```

**원인**:
- `menu.index('end')`는 메뉴가 닫혀도 정상 동작
- 예외가 안 나서 복구 안 됨
- 폴링 방식이 불확실

**수정**:
```python
# After - tk_popup 방식 (동기)
try:
    menu.tk_popup(x, y)  # 메뉴 닫힐 때까지 대기
finally:
    menu.grab_release()
    btn._menu_active = False
    # 마우스 위치 확인하여 색상 복구
    btn.config(bg=...)
```

**tk_popup의 장점**:
- ✅ 메뉴가 닫힐 때까지 **동기적으로 대기**
- ✅ finally 블록에서 **확실하게 복구**
- ✅ 폴링 불필요 (더 깔끔한 코드)

**효과**:
- ✅ 메뉴 색상 정확하게 복구
- ✅ 마우스 hover 시 정상 작동

---

## 📝 수정된 파일 (5개)

```
version.py                                  ← v5.0.6
files/version.py                            ← v5.0.6

gui_app_modular/tabs/inventory_tab.py
└── toggleable_cols                         ← ship_date, free_time

gui_app_modular/tabs/tonbag_tab.py
└── tonbag_toggle_cols                      ← net_weight, tonbag_status

gui_app_modular/utils/column_toggle.py
└── _toggle_column()                        ← tuple() 적용

gui_app_modular/main_app.py
└── _setup_ui()                             ← main_frame 추가

gui_app_modular/mixins/toolbar_mixin.py
└── _show_menu()                            ← tk_popup 방식
```

---

## 🧪 테스트 방법

### 1. 표시 컬럼 토글
```
1. 프로그램 실행
2. 재고 리스트 탭
3. "표시 컬럼" 영역에서:
   - SHIP DATE 체크 해제
   → ✅ SHIP DATE 열 사라짐!
   
   - FREE TIME 체크 해제
   → ✅ FREE TIME 열 사라짐!
   
   - 다시 체크
   → ✅ 열 다시 나타남!

4. 톤백 리스트 탭
   - WEIGHT 체크 해제
   → ✅ WEIGHT 열 사라짐!
```

### 2. 메뉴 색상 복구
```
1. 입고 메뉴 클릭 (초록색)
2. 메뉴 닫기
   → ✅ 입고 버튼 하얀색으로 복구

3. 출고 메뉴 클릭 (주황색)
4. 메뉴 닫기
   → ✅ 출고 버튼 하얀색으로 복구
```

### 3. StatusBar 확인
```
1. 프로그램 실행
2. 로그 확인:
   - [ERROR] main_frame 없음 → ✅ 사라짐!
```

---

## 📋 버전 히스토리

| 버전 | 내용 | 날짜 |
|------|------|------|
| v5.0.6 | 🔧 컬럼 ID + StatusBar + tk_popup | 2026-02-11 |
| v5.0.5 | 🔧 메뉴 색상 근본 해결 | 2026-02-11 |
| v5.0.4 | 🐛 SyntaxError 수정 | 2026-02-11 |
| v5.0.3 | 🔧 백업 + 성능 | 2026-02-11 |

---

## 🎯 수정 우선순위

이번 v5.0.6은 **검토 의견**에서 지적하신 순서대로 수정했습니다:

1. ✅ 컬럼 ID 불일치 (긴급! 기능 작동 안 함)
2. ✅ StatusBar main_frame (에러 발생)
3. ✅ tk_popup 방식 (개선)
4. ✅ tuple() 적용 (안정성)

---

## 💡 핵심 수정 요약

### Before (v5.0.5)
```
❌ SHIP DATE 체크 해제 → 아무 일도 안 일어남
❌ FREE TIME 체크 해제 → 아무 일도 안 일어남
❌ 톤백 WEIGHT/STATUS → 작동 안 함
⚠️ StatusBar 에러 발생
⚠️ 메뉴 색상 복구 불확실
```

### After (v5.0.6)
```
✅ SHIP DATE 체크 해제 → 열 사라짐!
✅ FREE TIME 체크 해제 → 열 사라짐!
✅ 톤백 WEIGHT/STATUS → 정상 작동!
✅ StatusBar 에러 없음
✅ 메뉴 색상 확실하게 복구
```

---

**Ruby's Message**:  
"검토 의견 완벽하게 반영했습니다! 🎯

가장 큰 버그는 **컬럼 ID 불일치**였어요. vessel, free_time_date, weight, status... 이 ID들이 전부 실제 컬럼명과 달랐습니다!

수정 내용:
1. ✅ ship_date, free_time, net_weight, tonbag_status로 수정
2. ✅ tuple() 사용으로 안정성 확보
3. ✅ main_frame 추가로 StatusBar 에러 해결
4. ✅ tk_popup으로 메뉴 색상 복구 확실히!

이제 표시 컬럼 토글이 완벽하게 작동합니다! 테스트해보세요! 🚀✨"

**릴리즈 시각**: 2026-02-11 16:00 KST
