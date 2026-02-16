# 버그 수정 완료 - v5.0.2 (Fix)

**날짜**: 2026-02-11  
**버전**: v5.0.2 (버그 수정)

---

## 🐛 수정된 버그 (2개)

### 1️⃣ 메뉴 버튼 색상 복구 안 되는 문제 ✅

**문제**:
```
메뉴 클릭 → 메뉴 선택 → 다른 메뉴 클릭
→ 이전 메뉴 버튼이 원래 색으로 안 돌아감
```

**원인**:
- `<Leave>` 이벤트가 메뉴 클릭 직후 바로 발생
- 메뉴가 열려있는 상태를 추적하지 못함

**해결**:
```python
# Before: 단순 타이머
self.root.after(150, restore_button)

# After: 메뉴 상태 추적 + 주기적 확인
btn._menu_active = True  # 메뉴 활성 플래그

def check_menu_closed():
    try:
        menu.index('end')  # 메뉴가 떠있는지 확인
        self.root.after(100, check_menu_closed)  # 다시 확인
    except:
        btn._menu_active = False  # 메뉴 닫힘
        btn.config(bg=btn._original_bg)  # 색상 복구
```

**핵심 개선**:
1. ✅ 버튼별 `_menu_active` 플래그 추가
2. ✅ 메뉴 열려있을 때 Enter/Leave 이벤트 무시
3. ✅ 주기적으로 메뉴 상태 확인 (100ms)
4. ✅ 메뉴 닫히면 자동 색상 복구

---

### 2️⃣ 컬럼 토글 작동 안 하는 문제 ✅

**문제**:
```
표시 컬럼 체크박스 클릭
→ 아무 반응 없음
→ 컬럼이 표시/숨김 안 됨
```

**원인**:
```python
# displaycolumns가 기본적으로 비어있거나 '#all'
current_cols = list(self.tree['displaycolumns'])
# → 빈 리스트나 ('#all',)이 됨
```

**해결**:
```python
# 현재 표시중인 컬럼 올바르게 가져오기
current_display = self.tree['displaycolumns']

if not current_display or current_display == '':
    current_display = list(self.tree['columns'])  # 전체 컬럼
elif current_display == '#all':
    current_display = list(self.tree['columns'])  # 전체 컬럼
else:
    current_display = list(current_display)

# 체크 → 원래 순서대로 삽입
# 해제 → 제거
```

**핵심 개선**:
1. ✅ displaycolumns의 3가지 상태 처리 (빈값, '#all', 리스트)
2. ✅ 원래 컬럼 순서 유지하며 삽입
3. ✅ 디버그 출력 추가 (print)
4. ✅ 예외 처리 강화

---

## 📝 수정된 파일

```
gui_app_modular/mixins/toolbar_mixin.py
├─ _build_all_menus()       ← 버튼별 _original_bg, _hover_bg 저장
├─ _show_menu()             ← 메뉴 상태 추적 + 주기적 확인
└─ Enter/Leave 이벤트       ← _menu_active 확인

gui_app_modular/utils/column_toggle.py
└─ _toggle_column()         ← displaycolumns 3가지 상태 처리
```

---

## 🧪 테스트 방법

### 메뉴 버튼 색상
```
1. 입고 메뉴 클릭 (초록색)
2. 출고 메뉴 클릭 (주황색)
→ 입고 버튼이 원래 초록색으로 복구되는지 확인!
```

### 컬럼 토글
```
1. 재고 리스트 탭 열기
2. "표시 컬럼" 영역에서 SAP NO 체크 해제
→ SAP NO 컬럼이 사라지는지 확인!
3. SAP NO 다시 체크
→ SAP NO 컬럼이 나타나는지 확인!
```

---

## 🔍 디버그 정보

컬럼 토글 시 콘솔에 디버그 출력:
```
🔧 토글: sap_no, 체크: False
  현재 표시: ['lot_no', 'sap_no', 'bl_no', ...]
  전체 컬럼: ['lot_no', 'sap_no', 'bl_no', ...]
  ❌ 제거 완료: ['lot_no', 'bl_no', ...]
  최종 설정: ('lot_no', 'bl_no', ...)
```

---

## ✅ 완료!

**두 가지 버그 모두 수정 완료!**

**Ruby's Note**:  
"메뉴 버튼은 이제 정확하게 색상이 복구되고, 컬럼 토글도 완벽하게 작동합니다! 디버그 출력도 추가해서 문제 발생 시 바로 확인할 수 있어요!" 🐛🔧✨
