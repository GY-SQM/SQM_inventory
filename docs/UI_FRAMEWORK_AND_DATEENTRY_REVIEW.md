# UI 프레임워크 및 DateEntry 통일 검토

## 1. 현재 프로그램 UI 프레임워크 구조 (검증됨)

### 1.1 기본 구조: ttkbootstrap (1차) + tkinter (폴백)

- **gui_bootstrap.py** 한 곳에서 로드하며, 다른 모듈은 이 부트스트랩을 import해 사용하는 구조가 맞습니다.

### 1.2 ttkbootstrap 설치 시

| 용도 | 사용처 |
|------|--------|
| `import ttkbootstrap as ttk` | ttk.Button, ttk.Frame, ttk.Label 등 |
| `ttkbootstrap.Window` | 메인 윈도우 (tk.Tk 대체) |
| `ttkbootstrap.Style` | 테마 엔진 |
| `ttkbootstrap.scrolled.ScrolledFrame` | 스크롤 가능 프레임 |
| `ttkbootstrap.tableview.Tableview` | 테이블 뷰 (재고 목록 등) |
| `ttkbootstrap.tooltip.ToolTip` | 툴팁 |
| `ttkbootstrap.widgets.DateEntry` | 날짜 입력 (내장) |
| `ttkbootstrap.widgets.Meter` | 미터/게이지 |
| `ttkbootstrap.widgets.Floodgauge` | 진행바 |
| `tkinter as tk` | Canvas, Menu 등 기본 위젯 |

- **HAS_DATEENTRY**: `gui_bootstrap.py` 76행에서 `DateEntry is not None`으로 설정됨.

### 1.3 ttkbootstrap 미설치 시 (폴백)

- `tkinter as tk` + `tkinter.ttk`
- `Window = tk.Tk`, `DateEntry = None`, `ScrolledFrame = None`, `Tableview = None` 등
- HAS_DATEENTRY = False

### 1.4 테마

- 기본: `flatly`
- 라이트: cosmo, flatly, journal, litera, lumen, minty, pulse, sandstone, united, yeti
- 다크: darkly, superhero, cyborg, vapor, solar

---

## 2. DateEntry 사용 현황

### 2.1 gui_bootstrap

- **DateEntry**: `from ttkbootstrap.widgets import DateEntry` (31행), 실패 시 `DateEntry = None`
- **HAS_DATEENTRY**: 76행에서 플래그 설정

### 2.2 onestop_inbound.py (수정 전)

- **직접 import**: `from tkcalendar import DateEntry` (26행)
- **로컬 플래그**: `HAS_DATEPICKER` (tkcalendar import 성공 여부)
- **_ask_missing_dates()**: tkcalendar 전제로 `date_pattern='yyyy-mm-dd'`, `set_date()`, `textvariable=var` 사용

### 2.3 정리

- 날짜 입력은 **gui_bootstrap 한 곳**에서만 관리하는 편이 유지보수·의존성 관리에 유리합니다.
- tkcalendar을 별도 설치하지 않고, ttkbootstrap만 있으면 DateEntry를 쓰는 구성이 가능합니다.
- Ruby 의견대로 **import 경로와 플래그를 gui_bootstrap에 통일**하는 것이 좋습니다.

---

## 3. API 차이 (tkcalendar vs ttkbootstrap DateEntry)

| 항목 | tkcalendar.DateEntry | ttkbootstrap.widgets.DateEntry |
|------|----------------------|--------------------------------|
| 날짜 형식 | `date_pattern='yyyy-mm-dd'` | `dateformat='%Y-%m-%d'` (strftime) |
| 초기값 | `textvariable` + `set_date(date)` | `startdate=date` 또는 `set_date(date)` |
| 값 읽기 | `textvariable.get()` | `entry.get()` 또는 `get_date().strftime('%Y-%m-%d')` |
| set_date | 있음 | 있음 |

- ttkbootstrap은 **textvariable**을 생성자에서 받지 않으므로, 값 읽기/쓰기는 위젯의 `.entry.get()` / `set_date()` 로 맞추면 됩니다.

---

## 4. 권장 수정 사항

1. **onestop_inbound.py**
   - `from tkcalendar import DateEntry` 제거.
   - `gui_app_modular.utils.gui_bootstrap`에서 `DateEntry`, `HAS_DATEENTRY` import.
   - `HAS_DATEPICKER` → `HAS_DATEENTRY` 사용.
   - `_ask_missing_dates()` 내 날짜 필드:
     - DateEntry 생성: `dateformat='%Y-%m-%d'`, `startdate=prefill 파싱값 또는 None`.
     - 값 읽기: DateEntry면 `.entry.get()` (또는 `get_date().strftime('%Y-%m-%d')`), 폴백이면 기존처럼 `StringVar.get()`.
2. **requirements.txt**
   - tkcalendar 의존성은 ttkbootstrap에 포함되므로, 별도 명시하지 않아도 됨 (이미 그렇게 되어 있으면 유지해도 무방).

---

## 5. 결론

- **UI 프레임워크 설명(ttkbootstrap + tk 폴백, 위젯 목록, 테마)** 은 코드 기준으로 맞습니다.
- **DateEntry는 gui_bootstrap 한 곳으로 통일**하고, onestop_inbound는 **HAS_DATEENTRY와 ttkbootstrap DateEntry API**에 맞춰 수정하는 것이 좋습니다.
