# SQM Inventory UI 가시성 및 통일성 개선 가이드
## v3.3 UI/UX 표준화 분석 리포트

---

## 📊 1. 현재 상태 분석

### 발견된 불일치 항목

| 항목 | 현재 상태 | 문제점 |
|------|----------|--------|
| **창 크기** | 750x550, 400x500, 600x400 등 | 다이얼로그마다 다름 |
| **폰트 크기** | 9, 10, 11pt 혼용 | 일관성 없음 |
| **패딩** | 5, 10, 15, 20px 혼용 | 규칙 없음 |
| **버튼 크기** | width=8, 10, 12 혼용 | 표준 없음 |
| **컬럼 너비** | 60~150px 다양 | 내용 기준 없음 |
| **색상** | 하드코딩, 테마 혼용 | 다크모드 미대응 |

---

## 📐 2. 계산해야 할 핵심 요소

### 2.1 화면 해상도 기반 크기 계산

```python
# === 화면 비율 기반 창 크기 계산 ===

class UICalculator:
    """UI 크기 계산기 - 화면 해상도 기반"""
    
    def __init__(self, root):
        self.screen_width = root.winfo_screenwidth()
        self.screen_height = root.winfo_screenheight()
        self.dpi = root.winfo_fpixels('1i')  # DPI 감지
        
        # 기준 해상도 (1920x1080)
        self.base_width = 1920
        self.base_height = 1080
        self.base_dpi = 96
        
    @property
    def scale_factor(self) -> float:
        """화면 크기 기반 스케일 팩터"""
        width_scale = self.screen_width / self.base_width
        height_scale = self.screen_height / self.base_height
        return min(width_scale, height_scale)
    
    @property
    def dpi_scale(self) -> float:
        """DPI 기반 스케일 팩터 (고해상도 모니터 대응)"""
        return self.dpi / self.base_dpi
    
    def scaled(self, value: int) -> int:
        """값을 스케일링"""
        return int(value * self.scale_factor * self.dpi_scale)
```

### 2.2 창 크기 계산 공식

```python
# === 메인 윈도우 ===
# 화면의 70-80% 사용 권장
MAIN_WINDOW_WIDTH = int(screen_width * 0.75)   # 예: 1440px
MAIN_WINDOW_HEIGHT = int(screen_height * 0.80)  # 예: 864px

# 최소 크기 (가독성 보장)
MIN_WIDTH = max(1000, int(screen_width * 0.5))
MIN_HEIGHT = max(700, int(screen_height * 0.5))

# === 서브 윈도우 (다이얼로그) ===
DIALOG_SIZES = {
    # 소형 (알림, 확인)
    'small': {
        'width': 0.25,   # 메인 창의 25%
        'height': 0.20,
        'min': (350, 200),
        'max': (500, 350)
    },
    
    # 중형 (설정, 상세보기)
    'medium': {
        'width': 0.40,   # 메인 창의 40%
        'height': 0.50,
        'min': (500, 400),
        'max': (800, 600)
    },
    
    # 대형 (테이블, 미리보기)
    'large': {
        'width': 0.60,   # 메인 창의 60%
        'height': 0.70,
        'min': (700, 500),
        'max': (1200, 900)
    },
    
    # 전체 (리포트, 대시보드)
    'full': {
        'width': 0.85,
        'height': 0.85,
        'min': (1000, 700),
        'max': (1600, 1000)
    }
}
```

---

## 🔤 3. 폰트 크기 계산

### 3.1 DPI 기반 폰트 스케일링

```python
class FontScale:
    """DPI 인식 폰트 크기 계산"""
    
    # 기준 폰트 크기 (96 DPI 기준)
    BASE_SIZES = {
        'title':      16,   # 제목
        'subtitle':   14,   # 부제목
        'heading':    12,   # 섹션 헤딩
        'body':       10,   # 본문 (기본)
        'small':       9,   # 보조 텍스트
        'tiny':        8,   # 주석, 툴팁
        'mono':       10,   # 고정폭 (코드, LOT번호)
    }
    
    def __init__(self, dpi: float = 96):
        self.dpi = dpi
        self.scale = dpi / 96
    
    def get_size(self, style: str) -> int:
        """스케일링된 폰트 크기 반환"""
        base = self.BASE_SIZES.get(style, 10)
        scaled = int(base * self.scale)
        return max(scaled, 8)  # 최소 크기 보장
```

### 3.2 일관된 폰트 적용 위치

| 용도 | 스타일 | 크기 | Weight |
|------|--------|------|--------|
| 창 제목 | title | 16pt | bold |
| 탭 이름 | subtitle | 14pt | normal |
| LabelFrame 제목 | heading | 12pt | bold |
| 테이블 헤더 | body | 10pt | bold |
| 테이블 내용 | body | 10pt | normal |
| 버튼 텍스트 | body | 10pt | normal |
| 상태바 | small | 9pt | normal |
| 툴팁 | tiny | 8pt | normal |
| LOT/SAP 번호 | mono | 10pt | normal |

---

## 📏 4. 간격(Spacing) 계산

### 4.1 8px 그리드 시스템

```python
class Spacing:
    """일관된 간격 시스템 (8px 그리드)"""
    
    UNIT = 8  # 기본 단위 (px)
    
    XS = UNIT // 2      # 4px  - 최소 간격
    SM = UNIT           # 8px  - 작은 간격
    MD = UNIT * 2       # 16px - 중간 간격 (기본)
    LG = UNIT * 3       # 24px - 큰 간격
    XL = UNIT * 4       # 32px - 매우 큰 간격
    XXL = UNIT * 6      # 48px - 섹션 간격
    
    # 용도별 권장값
    PADDING = {
        'dialog':       MD,     # 16px
        'frame':        SM,     # 8px
        'labelframe':   MD,     # 16px
        'button_group': SM,     # 8px
        'section':      LG,     # 24px
    }
```

### 4.2 패딩 적용 기준

| 요소 | padx | pady | 설명 |
|------|------|------|------|
| 메인 프레임 | 16 | 16 | 창 가장자리 |
| LabelFrame | 16 | 8 | 내부 콘텐츠 |
| 버튼 그룹 | 8 | 4 | 버튼 사이 |
| 입력 필드 | 8 | 4 | 필드 내부 |
| 테이블 | 0 | 0 | 스크롤 영역 |
| 상태바 | 8 | 4 | 좌우 여백 |

---

## 📊 5. 테이블 컬럼 너비 계산

### 5.1 표준 컬럼 너비표

| 필드 | 최소 | 권장 | 최대 | 정렬 |
|------|------|------|------|------|
| LOT NO | 120 | 130 | 150 | center |
| SAP NO | 100 | 110 | 130 | center |
| B/L NO | 100 | 110 | 130 | center |
| 중량 | 80 | 90 | 110 | e (우측) |
| 수량 | 50 | 60 | 80 | center |
| 제품명 | 100 | 150 | 200 | w (좌측) |
| 고객사 | 120 | 180 | 250 | w (좌측) |
| 날짜 | 85 | 90 | 100 | center |
| 상태 | 70 | 80 | 100 | center |

### 5.2 컬럼 너비 계산 공식

```python
def calculate_column_width(char_count, char_type='mixed', font_size=10):
    """
    컬럼 너비 계산
    
    char_type: 'number'(8px), 'letter'(7px), 'korean'(14px), 'mixed'(10px)
    """
    CHAR_WIDTH = {'number': 8, 'letter': 7, 'korean': 14, 'mixed': 10}
    
    width = char_count * CHAR_WIDTH[char_type] * (font_size / 10)
    width += 20  # 헤더 패딩
    
    return int(width)
```

---

## 🎨 6. 색상 체계

### 6.1 테마 인식 색상

```python
class ThemeAwareColors:
    """다크모드 대응 색상 시스템"""
    
    LIGHT = {
        'success': '#28a745', 'warning': '#ffc107', 'danger': '#dc3545',
        'available': '#C6EFCE', 'picked': '#FFC7CE', 
        'reserved': '#FFEB9C', 'shipped': '#DDEBF7',
    }
    
    DARK = {
        'success': '#00bc8c', 'warning': '#f39c12', 'danger': '#e74c3c',
        'available': '#1a472a', 'picked': '#4a1a1a',
        'reserved': '#4a4a1a', 'shipped': '#1a3a4a',
    }
```

### 6.2 상태별 색상

| 상태 | 라이트 배경 | 다크 배경 |
|------|------------|-----------|
| AVAILABLE | #C6EFCE (연두) | #1a472a |
| PICKED | #FFC7CE (연분홍) | #4a1a1a |
| RESERVED | #FFEB9C (연노랑) | #4a4a1a |
| SHIPPED | #DDEBF7 (연파랑) | #1a3a4a |

---

## 🪟 7. 다이얼로그 위치 계산

### 7.1 부모 창 중앙 배치

```python
def center_dialog_on_parent(dialog, parent):
    """부모 창 중앙에 다이얼로그 배치"""
    dialog.update_idletasks()
    
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()
    
    dialog_width = dialog.winfo_width()
    dialog_height = dialog.winfo_height()
    
    # 중앙 좌표 계산
    x = parent_x + (parent_width - dialog_width) // 2
    y = parent_y + (parent_height - dialog_height) // 2
    
    # 화면 범위 내 유지
    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()
    
    x = max(0, min(x, screen_width - dialog_width))
    y = max(0, min(y, screen_height - dialog_height))
    
    dialog.geometry(f"+{x}+{y}")
```

---

## 📱 8. 반응형 레이아웃

### 8.1 브레이크포인트

```python
BREAKPOINTS = {
    'xs': 0,      # 0-599px
    'sm': 600,    # 600-899px
    'md': 900,    # 900-1199px
    'lg': 1200,   # 1200-1599px
    'xl': 1600,   # 1600+px
}

# 브레이크포인트별 컬럼 수
COLUMNS = {'xs': 1, 'sm': 2, 'md': 3, 'lg': 4, 'xl': 6}
```

---

## ✅ 9. 구현 체크리스트

### 즉시 적용
- [ ] UIConstants 클래스 생성
- [ ] FontScale 클래스 적용
- [ ] Spacing 상수 적용
- [ ] 다이얼로그 크기 표준화

### 단기 (1주)
- [ ] ThemeAwareColors 적용
- [ ] 컬럼 너비 자동 계산
- [ ] center_dialog_on_parent() 통일
- [ ] ESC 닫기 통일

### 중기 (2주)
- [ ] 반응형 레이아웃 구현
- [ ] 고해상도 모니터 테스트
- [ ] 다중 모니터 지원

---

**작성일:** 2026-01-27 | **버전:** v3.3
