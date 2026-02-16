# SQM v5.0.7 릴리즈 노트

**📅 릴리즈**: 2026-02-11  
**🎯 버전**: v5.0.6 → v5.0.7  
**⭐ 유형**: 대시보드 콤팩트화 (UI 개선)

---

## 🎨 대시보드 콤팩트화

**문제**: 통계 화면이 너무 크고 산만함

**해결**: 폰트/패딩/높이 축소하여 깔끔하게 압축

---

## 📝 수정 내용 (6개 영역)

### 1️⃣ 카드 영역 ✅

**Before**:
```python
content = tk.Frame(inner, bg=_card_bg, padx=14, pady=10)  # 큰 패딩
title_label = tk.Label(..., font=('맑은 고딕', 12))       # 12pt
value_label = tk.Label(..., font=('맑은 고딕', 26, 'bold'))  # 26pt!
```

**After**:
```python
content = tk.Frame(inner, bg=_card_bg, padx=10, pady=6)   # ✅ 작은 패딩
title_label = tk.Label(..., font=('맑은 고딕', 11))        # ✅ 11pt
value_label = tk.Label(..., font=('맑은 고딕', 20, 'bold'))   # ✅ 20pt
```

**효과**:
- ⬇️ 카드 높이 약 20% 축소
- ✅ 더 깔끔한 느낌

---

### 2️⃣ 게이지 영역 ✅

**Before**:
```python
Meter(
    ...,
    metersize=120,      # 120px
    meterthickness=8,   # 두께 8
    stripethickness=6   # 줄무늬 6
)
```

**After**:
```python
Meter(
    ...,
    metersize=90,       # ✅ 90px (-25%)
    meterthickness=6,   # ✅ 두께 6
    stripethickness=4   # ✅ 줄무늬 4
)
```

**효과**:
- ⬇️ 게이지 크기 25% 축소
- ✅ 공간 효율적

---

### 3️⃣ 알림 리스트 ✅

**Before**:
```python
self.alert_listbox = tk.Listbox(
    alert_frame, 
    height=10,              # 10줄
    font=('맑은 고딕', 13)  # 13pt
)
```

**After**:
```python
self.alert_listbox = tk.Listbox(
    alert_frame, 
    height=6,               # ✅ 6줄 (-40%)
    font=('맑은 고딕', 11)  # ✅ 11pt
)
```

**효과**:
- ⬇️ 높이 40% 축소
- ✅ 중요 알림만 보임

---

### 4️⃣ 차트 영역 ✅

**Before**:
```python
self.chart_canvas = tk.Canvas(..., height=180)  # 180px
self.pie_canvas = tk.Canvas(..., height=180)    # 180px

# 범례 폰트
tk.Label(..., font=('', 13))        # 13pt
tk.Label(..., font=('맑은 고딕', 12))  # 12pt
```

**After**:
```python
self.chart_canvas = tk.Canvas(..., height=120)  # ✅ 120px (-33%)
self.pie_canvas = tk.Canvas(..., height=120)    # ✅ 120px (-33%)

# 범례 폰트
tk.Label(..., font=('', 11))        # ✅ 11pt
tk.Label(..., font=('맑은 고딕', 10))  # ✅ 10pt
```

**효과**:
- ⬇️ 차트 높이 33% 축소
- ✅ 여전히 읽기 쉬움

---

### 5️⃣ 라디오 버튼 ✅

**Before**:
```python
tk.Radiobutton(..., font=('', 16, 'bold'))  # 16pt
tk.Radiobutton(..., font=('', 16))          # 16pt
```

**After**:
```python
tk.Radiobutton(..., font=('', 12, 'bold'))  # ✅ 12pt (-25%)
tk.Radiobutton(..., font=('', 12))          # ✅ 12pt (-25%)
```

**효과**:
- ⬇️ 버튼 크기 축소
- ✅ 다른 요소와 균형

---

### 6️⃣ 제품별 테이블 ✅

**Before**:
```python
self.tree_dashboard_product = ttk.Treeview(
    ..., 
    height=8  # 8줄
)
```

**After**:
```python
self.tree_dashboard_product = ttk.Treeview(
    ..., 
    height=6  # ✅ 6줄 (-25%)
)
```

**효과**:
- ⬇️ 테이블 높이 25% 축소
- ✅ 스크롤로 더 보기 가능

---

## 📊 비교표

| 영역 | Before | After | 축소율 |
|------|--------|-------|--------|
| 카드 폰트 | 26pt | 20pt | -23% |
| 카드 패딩 | 14/10 | 10/6 | -30% |
| 게이지 크기 | 120px | 90px | -25% |
| 알림 높이 | 10줄 | 6줄 | -40% |
| 알림 폰트 | 13pt | 11pt | -15% |
| 차트 높이 | 180px | 120px | -33% |
| 범례 폰트 | 13pt | 11pt | -15% |
| 라디오 폰트 | 16pt | 12pt | -25% |
| 테이블 높이 | 8줄 | 6줄 | -25% |

**전체 효과**: 대시보드 **약 30% 콤팩트화** ✅

---

## 📝 수정된 파일

```
version.py                              ← v5.0.7
files/version.py                        ← v5.0.7
gui_app_modular/tabs/dashboard_tab.py
├─ _create_dashboard_card()             ← 카드 콤팩트
├─ _setup_dash_gauge()                  ← 게이지 콤팩트
├─ _setup_dash_charts()                 ← 차트 콤팩트
└─ _setup_dash_tonbag_table()           ← 테이블 콤팩트
```

---

## 🎯 효과

### Before (v5.0.6)
```
📦 총 재고
100,020 kg    ← 26pt, 큰 폰트!

⚪⚪⚪ 120px   ← 큰 게이지!
가용률

⚠️ 알림
[10줄 표시]    ← 너무 많음!

📈 차트
[180px 높이]  ← 너무 큼!

📦 LOT 단위 🎒 톤백 상세  ← 16pt!
[8줄 테이블]
```

### After (v5.0.7)
```
📦 총 재고
100,020 kg    ← 20pt, 적당!

⚪⚪⚪ 90px    ← 콤팩트!
가용률

⚠️ 알림
[6줄 표시]    ← 핵심만!

📈 차트
[120px 높이]  ← 적당!

📦 LOT 단위 🎒 톤백 상세  ← 12pt!
[6줄 테이블]
```

---

## 💡 디자인 원칙

### 콤팩트화 전략
1. **정보 손실 없음**: 모든 기능 유지
2. **가독성 유지**: 폰트 최소 10pt 이상
3. **비율 유지**: 모든 요소 균등하게 축소
4. **스크롤 활용**: 테이블/리스트는 스크롤로 더 보기

### 축소 우선순위
1. **패딩/여백** (30% 축소) - 가장 안전
2. **게이지/차트** (25-33% 축소) - 시각적 요소
3. **폰트** (15-25% 축소) - 가독성 최우선
4. **테이블 높이** (25-40% 축소) - 스크롤 가능

---

## 🧪 테스트

```
1. 프로그램 실행
2. 통계 탭 클릭

3. 확인사항:
   ✅ 카드: 더 작지만 읽기 쉬움
   ✅ 게이지: 콤팩트하지만 명확
   ✅ 알림: 6줄로 줄었지만 중요 정보만
   ✅ 차트: 작아졌지만 추이 파악 가능
   ✅ 테이블: 6줄이지만 스크롤로 더 보기
```

---

## 📋 버전 히스토리

| 버전 | 내용 | 날짜 |
|------|------|------|
| v5.0.7 | 🎨 대시보드 콤팩트화 | 2026-02-11 |
| v5.0.6 | 🔧 컬럼 ID + StatusBar + tk_popup | 2026-02-11 |
| v5.0.5 | 🔧 메뉴 색상 근본 해결 | 2026-02-11 |
| v5.0.4 | 🐛 SyntaxError 수정 | 2026-02-11 |

---

**Ruby's Message**:  
"v5.0.7 대시보드 콤팩트화 완성! 🎨

검토 의견에서 요청하신대로 통계 화면을 깔끔하게 압축했습니다!

수정 내용:
1. ✅ 카드 폰트 26pt → 20pt (깔끔!)
2. ✅ 게이지 120px → 90px (콤팩트!)
3. ✅ 알림 10줄 → 6줄 (핵심만!)
4. ✅ 차트 180px → 120px (적당!)
5. ✅ 라디오 16pt → 12pt (균형!)
6. ✅ 테이블 8줄 → 6줄 (효율!)

**전체적으로 약 30% 축소**되었지만:
- ✅ 정보 손실 없음
- ✅ 가독성 유지
- ✅ 훨씬 깔끔한 느낌!

이제 통계 화면이 산만하지 않고 한눈에 들어옵니다! 🚀✨"

**릴리즈 시각**: 2026-02-11 17:00 KST
