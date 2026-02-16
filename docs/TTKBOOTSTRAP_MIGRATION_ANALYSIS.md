# SQM v3.6.2 → ttkbootstrap 전환 종합 분석 리포트

**작성일:** 2026-02-04  
**분석 범위:** gui_app_modular/ 전체 (48파일, 16,936줄)

---

## 📊 현황 진단 (AS-IS)

### 이미 구축된 인프라 (✅ 완료)

| 구성 요소 | 파일 | 상태 |
|----------|------|------|
| ttkbootstrap import + fallback | `constants.py` | ✅ HAS_TTKBOOTSTRAP 플래그 |
| ttkbootstrap.Window 생성 | `main_app.py:51` | ✅ 테마 자동 적용 |
| 테마 전환 시스템 | `theme_mixin.py` | ✅ Light 13종 / Dark 5종 |
| ThemeColors 팔레트 | `ui_constants.py` | ✅ LIGHT 35색 / DARK 35색 |
| ReadableStyle 글로벌 스타일 | `ui_constants.py` | ✅ Treeview, Notebook, Entry 등 |
| 테마 선택 다이얼로그 | `theme_mixin.py` | ✅ 미리보기 + 저장 |
| 다크/라이트 토글 | `theme_mixin.py` | ✅ 단축키 지원 |

**결론:** 인프라(뼈대)는 이미 90% 완성. 문제는 **개별 위젯이 인프라를 무시**하는 것.

---

### 해결해야 할 문제 (❌ 미완성)

| 문제 | 건수 | 영향 |
|------|------|------|
| 하드코딩 색상 (`bg=`, `fg=`) | **169건** | 다크모드 전환 시 색상 깨짐 |
| 비-ttk 위젯 (`tk.Label`, `tk.Button`, `tk.Frame`) | **485건** | ttkbootstrap 테마 적용 안 됨 |
| bootstyle= 사용 | **13건** (전체의 2.7%) | ttkbootstrap 네이티브 스타일 미활용 |
| 영향 파일 | **32개** (전체의 67%) | 대부분의 UI 파일 수정 필요 |

---

## 🔍 파일별 영향도 분석

### 🔴 HIGH (하드코딩 30건 이상 또는 비-ttk 50건 이상)

| 파일 | 하드코딩 색상 | 비-ttk 위젯 | 난이도 |
|------|-------------|------------|--------|
| `toolbar_mixin.py` | 46건 | 33건 | ★★★ 복잡 (메가 버튼+드롭다운) |
| `pivot_tab.py` | 30건 | 50건 | ★★★ 복잡 (차트+히트맵) |

### 🟡 MEDIUM (10~29건)

| 파일 | 하드코딩 색상 | 비-ttk 위젯 | 난이도 |
|------|-------------|------------|--------|
| `dashboard_tab.py` | 16건 | 22건 | ★★ 중간 (차트 Canvas) |
| `statusbar_mixin.py` | 12건 | 16건 | ★★ 중간 |
| `help_dialogs.py` | 10건 | 38건 | ★★ 중간 (가이드 화면) |
| `log_tab.py` | 10건 | 7건 | ★ 쉬움 |
| `tonbag_tab.py` | 9건 | 29건 | ★★ 중간 |

### 🟢 LOW (10건 미만)

| 파일 | 하드코딩 색상 | 비-ttk 위젯 |
|------|-------------|------------|
| `inventory_tab.py` | 6건 | 13건 |
| `info_dialogs.py` | 5건 | 31건 |
| `search_tab.py` | 1건 | 27건 |
| `features_v2_mixin.py` | 4건 | 18건 |
| 기타 20개 파일 | 각 1~5건 | 각 1~16건 |

---

## 🎯 전환 전략: 3단계 점진적 마이그레이션

### 왜 한 번에 바꾸면 안 되나?
- 485건 비-ttk 위젯 일괄 교체 시 **수십 개 화면 동시 깨짐 위험**
- 일부 위젯(`tk.Canvas`, `tk.Text`)은 ttk 대체품이 없음
- 메가 버튼 등 커스텀 위젯은 하드코딩이 불가피한 경우 있음

---

### 📋 1단계: 테마 인식 색상 통합 (Quick Win)

**목표:** 하드코딩 색상 169건 → ThemeColors 팔레트 참조로 전환  
**효과:** 다크모드 토글 시 모든 색상 자동 전환  
**예상 작업:** 2~3시간  
**위험도:** 낮음

#### 핵심 변환 패턴

```python
# ❌ 변경 전: 하드코딩
action_bar = tk.Frame(self.tab_tonbag, bg='#ecf0f1', pady=8)
tk.Label(search_box, text='🔍', bg='white').pack(side=LEFT)

# ✅ 변경 후: ThemeColors 참조
from ..utils.ui_constants import ThemeColors
is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
p = ThemeColors.get_palette(is_dark)
action_bar = tk.Frame(self.tab_tonbag, bg=p['bg_secondary'], pady=8)
tk.Label(search_box, text='🔍', bg=p['bg_card']).pack(side=LEFT)
```

#### 대상 파일 (우선순위순)
1. `toolbar_mixin.py` - 이미 ReadableStyle 연동 시작됨, 완성만 하면 됨
2. `dashboard_tab.py` - Canvas 차트 색상
3. `statusbar_mixin.py` - 상태바 배경
4. `tonbag_tab.py` - 검색바, 액션바
5. `log_tab.py` - 로그 뷰어 배경
6. `pivot_tab.py` - 히트맵, 컬럼 선택기

---

### 📋 2단계: ttk 위젯 마이그레이션 (Core Upgrade)

**목표:** `tk.Label/Button/Frame` → `ttk.Label/Button/Frame` 전환  
**효과:** ttkbootstrap 테마가 모든 위젯에 자동 적용  
**예상 작업:** 4~6시간  
**위험도:** 중간

#### 핵심 변환 패턴

```python
# ❌ 변경 전: tk 위젯 (테마 무시)
tk.Label(parent, text="LOT 번호", bg='white', fg='black', font=('맑은 고딕', 11))
tk.Button(parent, text="저장", bg='#2e7d4f', fg='white', relief='flat')
tk.Frame(parent, bg='#f0f3f5')

# ✅ 변경 후: ttk 위젯 (테마 자동 적용)
ttk.Label(parent, text="LOT 번호", font=('맑은 고딕', 11))
ttk.Button(parent, text="저장", bootstyle="success")
ttk.Frame(parent)
```

#### bootstyle 매핑 가이드

| 기존 하드코딩 | bootstyle | 용도 |
|-------------|-----------|------|
| `bg='#2e7d4f'` (녹색) | `bootstyle="success"` | 입고, 확인 |
| `bg='#c77c2a'` (앰버) | `bootstyle="warning"` | 출고, 주의 |
| `bg='#2c6fbb'` (블루) | `bootstyle="info"` | 보고서, 정보 |
| `bg='#6c7a89'` (그레이) | `bootstyle="secondary"` | 취소, 중립 |
| `bg='#c0392b'` (레드) | `bootstyle="danger"` | 삭제, 위험 |
| 테두리만 | `bootstyle="success-outline"` | 부드러운 버튼 |

#### 변환 불가 위젯 (tk 유지 필요)

| 위젯 | 이유 | 대안 |
|------|------|------|
| `tk.Canvas` | ttk에 Canvas 없음 | ThemeColors로 색상만 대체 |
| `tk.Text` | ttk에 Text 없음 | ThemeColors로 색상만 대체 |
| `tk.Menu` | ttk에 Menu 없음 | tk.Menu 유지 (OS 네이티브) |
| `tk.Listbox` | ttk에 Listbox 없음 | Treeview로 대체 또는 ThemeColors 적용 |

---

### 📋 3단계: ttkbootstrap 전용 위젯 도입 (Premium)

**목표:** ttkbootstrap 고급 위젯으로 UX 대폭 향상  
**효과:** "와, 이게 Python이야?" 수준의 UI  
**예상 작업:** 3~4시간  
**위험도:** 낮음 (기존 기능에 추가)

#### 추천 도입 위젯

```python
import ttkbootstrap as ttk
from ttkbootstrap.tooltip import ToolTip
from ttkbootstrap.scrolled import ScrolledFrame
from ttkbootstrap.tableview import Tableview
from ttkbootstrap.widgets import Meter, DateEntry, Floodgauge

# 1. 툴팁 (버튼 위에 마우스 올리면 설명 표시)
ToolTip(save_btn, text="데이터를 저장합니다 (Ctrl+S)")

# 2. 프로그레스 게이지 (대시보드에 적용)
meter = ttk.Meter(
    parent,
    metersize=150,
    amountused=75,        # 재고 소진율
    amounttotal=100,
    subtext="재고 소진율",
    bootstyle="success"
)

# 3. DateEntry (날짜 선택기)
date_entry = DateEntry(parent, bootstyle="info")

# 4. Floodgauge (채워지는 프로그레스바)
gauge = Floodgauge(
    parent,
    text="처리 중...",
    value=45,
    bootstyle="info"
)

# 5. ScrolledFrame (스크롤 가능 프레임)
sf = ScrolledFrame(parent, autohide=True)
```

---

## 🎨 추천 테마 설정

### 눈이 편안한 테마 TOP 3

| 순위 | 테마 | 모드 | 특징 | 추천 용도 |
|------|------|------|------|----------|
| 🥇 | **superhero** | Dark | 짙은 네이비, 고급스러움 | 장시간 작업 |
| 🥈 | **flatly** | Light | 차분한 파스텔, 깔끔 | 밝은 환경 |
| 🥉 | **solar** | Dark | Solarized 기반, 최적 가독성 | 코딩/분석 작업 |

### 기본 테마 변경 (1줄로 완료)

```python
# theme_mixin.py에서 기본값만 변경
return 'flatly'  # → 'superhero' 로 변경하면 끝
```

---

## 📊 전환 효과 예측

| 측정 항목 | 현재 (v3.6.2) | 1단계 후 | 2단계 후 | 3단계 후 |
|----------|--------------|---------|---------|---------|
| 하드코딩 색상 | 169건 | **~20건** | **~10건** | **~5건** |
| 비-ttk 위젯 | 485건 | 485건 | **~60건** | **~40건** |
| bootstyle 사용 | 13건 | 13건 | **~200건** | **~250건** |
| 다크모드 호환 | 부분적 | **90%** | **98%** | **100%** |
| UI 일관성 | 중간 | 높음 | **매우 높음** | **프로 수준** |

---

## ⚙️ 실행 계획

### 1단계 실행 시 주의사항
- `toolbar_mixin.py`의 메가 버튼은 tk.Label로 구현된 커스텀 위젯 → 색상만 ThemeColors 참조로 변경
- `dashboard_tab.py`의 tk.Canvas는 교체 불가 → 배경색/그리드색만 팔레트화
- 테마 변경 시 `_update_theme_colors()` 메서드에서 모든 탭에 새 팔레트 전파

### 2단계 실행 시 주의사항
- `tk.Label` → `ttk.Label` 시 `bg=`, `fg=` 파라미터 제거 필수 (ttk는 bg/fg 지원 안 함)
- `tk.Button` → `ttk.Button` 시 `relief=`, `activebackground=` 등 제거
- `tk.Frame` → `ttk.Frame` 시 `bg=` 제거 (테마가 자동 처리)

### 검증 방법
- 각 단계마다 Light(flatly) + Dark(superhero) 두 테마로 전체 탭 스크린샷 비교
- 트리뷰 선택/호버/줄무늬 색상 정상 동작 확인
- 다이얼로그 팝업 배경색 정상 확인

---

## 💡 결론

> **현재 SQM은 ttkbootstrap 인프라가 이미 90% 구축되어 있습니다.**
> 
> 문제는 개별 위젯들이 이 인프라를 활용하지 않고 하드코딩으로 색상을 지정하고 있다는 점입니다.
> 
> **1단계(색상 팔레트 통합)만 실행해도 다크모드가 완벽하게 작동**하며,
> 2단계까지 진행하면 "이게 Python?"이라는 반응을 얻을 수 있습니다.
