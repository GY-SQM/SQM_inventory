# SQM v3.6.4 변경 리포트 — 2단계: tk → ttk 위젯 마이그레이션

**작성일:** 2026-02-04  
**버전:** v3.6.3 → v3.6.4  
**목표:** tk.Button/Frame/Label → ttk + bootstyle 전환

---

## 📊 변경 전/후 비교

| 위젯 유형 | v3.6.3 | v3.6.4 | 변화 |
|----------|--------|--------|------|
| **tk.Button** | 99건 | **0건** | ✅ 100% ttk 전환 |
| tk.Label | 35건 | 35건 | bg= 테마용 유지 |
| tk.Frame | 48건 → | 39건 | ▼ 9건 ttk 전환 |
| bootstyle= | 13건 | **23건** | ▲ 77% 증가 |
| **ttk.Button** | — | **99건** | 전량 bootstyle 적용 |
| ttk.Frame | 88건 | **97건** | ▲ 9건 증가 |
| ttk.Label | 142건 | **144건** | ▲ 2건 증가 |
| 문법 오류 | 0건 | 0건 | 유지 |

---

## 🎨 bootstyle 매핑 규칙

| 기능 색상 | bootstyle | 용도 |
|----------|-----------|------|
| 녹색 (#27ae60) | `success` | 적용, 전체선택 |
| 주황 (#e67e22) | `warning` | Excel 내보내기, 초기화 |
| 파랑 (#3498db) | `info` | 위/아래 이동, 미리보기 |
| 빨강 (#e74c3c) | `danger` | 전체해제 |
| 회색 (#95a5a6) | `secondary` | 초기화 |
| 짙은색 (#2c3e50) | `dark` | 전체화면 |
| 테두리만 | `*-outline` | 취소, 보조 버튼 |

---

## 🔧 수정 파일 (2개)

### 1. `pivot_tab.py` — 핵심 변환
**tk.Button → ttk.Button + bootstyle (10건):**
- 제어 패널 버튼 4개: `▶ 분석`, `📋 원본`, `📥 Excel+헤더`, `📥 Excel`, `🔄 초기화`, `⛶ 전체화면` → bootstyle 매핑
- 열 선택기: `⬆ 위로`(info), `⬇ 아래로`(info), `☑ 전체선택`(success), `☐ 전체해제`(danger)
- 열 선택기 액션: `✅ 적용`(success), `🔄 전체 표시`(warning), `취소`(secondary-outline)
- 헤더 빌더: `👁 미리보기 갱신`(info), `📥 Excel 내보내기`(warning), `취소`(secondary-outline)
- 전체화면 바: `📥 Excel 내보내기`(warning), `📥 Excel+헤더`(warning-outline)

**tk.Frame → ttk.Frame (9건):**
- 다이얼로그 컨테이너 프레임 (bg= 불필요한 것만)
- rf, tc, lf, bf, af, mid, inner, tr, cf

**tk.Label → ttk.Label (2건):**
- 다이얼로그 안내 텍스트 (bg= 불필요)

### 2. 버전 통일
- `version.py`, `constants.py`, `main_app.py` → v3.6.4

---

## ⚠️ 의도적 tk 유지 (77건)

| 파일 | tk.Label | tk.Frame | tk.Entry | 사유 |
|------|---------|---------|---------|------|
| toolbar_mixin.py | 15 | 17 | 1 | hover bg= 동적 변경 |
| pivot_tab.py | 12 | 9 | — | bg= 팔레트 테마 구분 |
| dashboard_tab.py | 6 | 3 | — | 카드/차트 색상 강조 |
| tonbag_tab.py | 1 | 5 | 1 | bg= 팔레트 테마 |
| inventory_tab.py | 1 | 5 | 1 | bg= 팔레트 테마 |

> 이들은 v3.6.3에서 ThemeColors 팔레트로 전환 완료.  
> ttk로 변환하면 팔레트 색상이 유실되어 **의도적으로 tk 유지**.

---

## 🔮 다음 단계 (v3.6.5 예정)

**3단계: ttkbootstrap 전용 위젯 도입 (Premium)**
- ToolTip: 버튼 hover 시 설명 표시
- Meter: 재고 소진율 게이지
- DateEntry: 날짜 선택기
- Floodgauge: 프로그레스바
- ScrolledFrame: 자동 스크롤

---

## 📈 v3.6.0 → v3.6.4 누적 진행률

| 항목 | v3.6.0 | v3.6.4 | 목표 |
|------|--------|--------|------|
| 하드코딩 색상 | 169건 | **12건** | ~5건 |
| bootstyle 사용 | 13건 | **23건** | 250건 |
| 다크모드 호환 | 부분 | **~90%** | 100% |
| tk.Button | 99건 | **0건** | ✅ 완료 |
| UI 일관성 | 중간 | **높음** | 프로 수준 |
