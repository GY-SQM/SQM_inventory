# SQM v5.0.5 릴리즈 노트

**📅 릴리즈**: 2026-02-11  
**🎯 버전**: v5.0.4 → v5.0.5  
**⭐ 유형**: 메뉴 버튼 색상 문제 근본 해결

---

## 🐛 수정된 버그 (2개)

### 1. 메뉴 버튼 색상 문제 근본 해결 ✅

**문제**:
```
메뉴 버튼 클릭
→ 색이 변해서 검은색으로 보임
→ 다시 원래 색으로 안 돌아옴
```

**원인 (클로저 문제)**:
```python
# Before - 잘못된 코드
for text, color_key, builder, is_large in menus:
    btn = tk.Label(...)
    
    def on_enter(e):  # ❌ 모든 버튼이 마지막 btn만 참조!
        if not hasattr(btn, '_menu_active') or not btn._menu_active:
            btn.config(bg=btn._hover_bg)
```

**문제점**:
- Python의 클로저 특성상 `btn` 변수가 루프의 마지막 버튼만 가리킴
- 모든 버튼의 이벤트 핸들러가 마지막 버튼을 참조
- 결과: 첫 번째 버튼을 클릭해도 마지막 버튼의 색상이 변경됨

**해결책 (팩토리 함수)**:
```python
# After - 수정된 코드
for text, color_key, builder, is_large in menus:
    btn = tk.Label(...)
    btn._menu_active = False  # 초기화
    
    # ✅ 팩토리 함수로 각 버튼마다 독립적인 핸들러 생성
    def make_enter_handler(button):
        def on_enter(e):
            if not button._menu_active:
                button.config(bg=button._hover_bg)
        return on_enter
    
    def make_leave_handler(button):
        def on_leave(e):
            if not button._menu_active:
                button.config(bg=button._original_bg)
        return on_leave
    
    btn.bind('<Enter>', make_enter_handler(btn))
    btn.bind('<Leave>', make_leave_handler(btn))
```

**효과**:
- ✅ 각 버튼이 독립적인 이벤트 핸들러를 가짐
- ✅ 클릭한 버튼만 색상이 변경됨
- ✅ 원래 색상으로 정확하게 복구됨

---

### 2. import os 오류 수정 ✅

**문제**:
```
[ERROR] 자동 복구 오류: name 'os' is not defined
```

**원인**:
```python
# main_app.py에 os import 누락
```

**해결책**:
```python
# Before
import sqlite3
import sys
import logging

# After
import os          # ✅ 추가
import sqlite3
import sys
import logging
```

---

## 📝 수정된 파일

```
version.py                                  ← v5.0.5
files/version.py                            ← v5.0.5 (동기화)

gui_app_modular/mixins/toolbar_mixin.py
└── _build_all_menus()                      ← 클로저 문제 해결

gui_app_modular/main_app.py
└── import os 추가                          ← 자동 복구 오류 해결
```

---

## 🎯 근본 원인 분석

### Python 클로저의 동작 방식

```python
# 잘못된 예시
buttons = []
for i in range(3):
    btn = Button(...)
    btn.bind('<Button>', lambda e: print(i))  # ❌ 항상 2 출력
    buttons.append(btn)

# i는 루프가 끝난 후 2가 되고,
# 모든 람다가 같은 i를 참조하므로
# 어떤 버튼을 클릭해도 "2"가 출력됨

# 올바른 예시
buttons = []
for i in range(3):
    btn = Button(...)
    def make_handler(value):  # ✅ 팩토리 함수
        return lambda e: print(value)
    btn.bind('<Button>', make_handler(i))
    buttons.append(btn)

# 각 람다가 독립적인 value를 캡처하므로
# 버튼마다 0, 1, 2가 올바르게 출력됨
```

---

## 🧪 테스트

```bash
cd sqm_v502
python run_app.py
```

**테스트 시나리오**:
```
1. 프로그램 실행
2. 입고 메뉴 클릭 (초록색)
   → ✅ 입고 버튼만 활성화
3. 출고 메뉴 클릭 (주황색)
   → ✅ 입고 버튼은 원래 색으로 복구
   → ✅ 출고 버튼만 활성화
4. 재고 메뉴 클릭 (파란색)
   → ✅ 출고 버튼은 원래 색으로 복구
   → ✅ 재고 버튼만 활성화
```

---

## 📋 버전 히스토리

| 버전 | 내용 | 날짜 |
|------|------|------|
| v5.0.5 | 🔧 메뉴 색상 근본 해결 | 2026-02-11 |
| v5.0.4 | 🐛 SyntaxError 수정 | 2026-02-11 |
| v5.0.3 | 🔧 백업 강화 + 성능 | 2026-02-11 |
| v5.0.2 | 🎯 UI/UX 개선 | 2026-02-11 |
| v5.0.1 | 🔧 sqlite3.Row 수정 | 2026-02-11 |
| v5.0.0 | 🎯 UI 100% 통일 | 2026-02-11 |

---

## 💡 학습 포인트

### Python 클로저 함정

**문제가 되는 패턴**:
```python
for item in items:
    widget = create_widget()
    widget.bind(event, lambda e: do_something(item))
    # ❌ 모든 위젯이 마지막 item만 참조!
```

**해결 방법 3가지**:

**1. 팩토리 함수 (권장)**:
```python
def make_handler(captured_item):
    return lambda e: do_something(captured_item)

for item in items:
    widget.bind(event, make_handler(item))
```

**2. 기본 인자**:
```python
for item in items:
    widget.bind(event, lambda e, i=item: do_something(i))
```

**3. functools.partial**:
```python
from functools import partial

for item in items:
    widget.bind(event, partial(do_something, item))
```

---

**Ruby's Message**:  
"완전히 찾았습니다! 메뉴 버튼 색상 문제의 근본 원인은 Python 클로저였어요.

루프 안에서 람다나 중첩 함수를 만들 때, 변수를 제대로 캡처하지 않으면 모든 함수가 마지막 값만 참조하게 됩니다.

팩토리 함수(`make_enter_handler`, `make_leave_handler`)로 각 버튼마다 독립적인 핸들러를 만들어서 완전히 해결했습니다!

이제 메뉴를 클릭해도 색상이 정확하게 복구됩니다! 🎯✨"

**릴리즈 일시**: 2026-02-11 15:30 KST
