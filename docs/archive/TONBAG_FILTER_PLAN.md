# 톤백 리스트 필터 및 표시 옵션 추가

**요청 사항**: 재고 리스트와 동일한 UI를 톤백 리스트에도 적용

---

## 📋 현재 상태

### ✅ 이미 있는 것
```python
# tonbag_tab.py에 이미 HeaderFilterBar 적용됨
self._tonbag_filter_bar = HeaderFilterBar(
    self.tab_tonbag, None, tonbag_filter_cols,
    on_filter=self._on_tonbag_filter_apply,
    is_dark=_is_dark_filter
)
```

**필터 컬럼**:
- LOT NO
- SAP NO
- BL NO
- CONTAINER
- PRODUCT
- STATUS

---

## 🎯 추가해야 할 것

### 1. 표시 옵션 (체크박스)
```
표시 옵션: 
☑ SAP NO  ☑ BL NO  ☑ CONTAINER  
☑ SHIP DATE  ☑ FREE TIME  ☑ CUSTOMS
```

### 2. 표시 모드 (라디오 버튼)
```
표시 모드: 
◉ 컴팩트  ○ 보통  ○ 넓게
```

---

## 🔧 구현 방법

### 방법 1: HeaderFilterBar 확장
```python
# tree_enhancements.py의 HeaderFilterBar 클래스 수정
# 표시 옵션 체크박스 추가
# 표시 모드 라디오 버튼 추가
```

**장점**: 재사용 가능  
**단점**: 기존 코드 수정 필요

### 방법 2: 별도 위젯 추가
```python
# tonbag_tab.py에 별도 프레임 추가
# 체크박스와 라디오 버튼 직접 생성
```

**장점**: 간단함  
**단점**: 코드 중복

---

## 💡 Ruby의 제안

**"방법 2가 빠릅니다"**

이유:
1. 기존 HeaderFilterBar는 그대로 유지
2. 표시 옵션은 별도 프레임으로 추가
3. 재고 탭과 톤백 탭 모두 동일한 패턴 적용

---

## 📝 구현 코드 (예시)

```python
# tonbag_tab.py에 추가

# 표시 옵션 프레임
display_frame = tk.Frame(self.tab_tonbag, bg=_bg)
display_frame.pack(fill=X, padx=5, pady=(0, 5))

# 왼쪽: 표시 컬럼
col_frame = tk.Frame(display_frame, bg=_bg)
col_frame.pack(side=LEFT, padx=5)

tk.Label(col_frame, text="표시 컬럼:", bg=_bg, fg=_text,
         font=('맑은 고딕', 9, 'bold')).pack(side=LEFT, padx=(0, 5))

# 체크박스들
self._tonbag_col_vars = {}
for col_name in ['SAP NO', 'BL NO', 'CONTAINER', 'SHIP DATE', 'FREE TIME', 'CUSTOMS']:
    var = tk.BooleanVar(value=True)
    cb = tk.Checkbutton(col_frame, text=col_name, variable=var,
                        bg=_bg, fg=_text, selectcolor=_card,
                        command=self._on_tonbag_column_toggle)
    cb.pack(side=LEFT, padx=3)
    self._tonbag_col_vars[col_name] = var

# 오른쪽: 표시 모드
mode_frame = tk.Frame(display_frame, bg=_bg)
mode_frame.pack(side=LEFT, padx=20)

tk.Label(mode_frame, text="표시 모드:", bg=_bg, fg=_text,
         font=('맑은 고딕', 9, 'bold')).pack(side=LEFT, padx=(0, 5))

self._tonbag_mode_var = tk.StringVar(value="컴팩트")
for mode in ['컴팩트', '보통', '넓게']:
    rb = tk.Radiobutton(mode_frame, text=mode, variable=self._tonbag_mode_var,
                        value=mode, bg=_bg, fg=_text, selectcolor=_card,
                        command=self._on_tonbag_mode_change)
    rb.pack(side=LEFT, padx=3)
```

---

## 🎯 다음 단계

**지금 구현하시겠어요?**

1. **즉시 구현** - 10~15분 소요
2. **Phase 2와 함께** - Allocation 미리보기와 같이
3. **나중에** - 다른 우선순위 작업 먼저

말씀해주시면 바로 작업하겠습니다! 😊

---

**Ruby's Note**:  
"표시 옵션과 모드 선택은 사용자 편의성을 크게 높여주는 기능이에요. 재고 탭에 있으면 톤백 탭에도 있어야 일관성이 있죠!" 💡
