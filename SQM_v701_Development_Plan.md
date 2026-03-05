# SQM v7.0.1 테마 가시성 근본 해결 — 최종 개발 계획서

**작성일**: 2026-02-22 22:03 KST  
**작성자**: Ruby (AI Assistant)  
**대상 버전**: SQM v7.0.0 → v7.0.1  
**목적**: 화이트/다크 테마(총 10개 내외) 전환 시 글자가 안 보이는 문제를 근본 해결

---

## 목차

1. [문제 정의](#1-문제-정의)
2. [근본 원인 분석 (10가지)](#2-근본-원인-분석)
3. [해결 아키텍처 개요](#3-해결-아키텍처-개요)
4. [Phase 1: 긴급 버그 수정 (즉시 효과)](#4-phase-1-긴급-버그-수정)
5. [Phase 2: 전체 Treeview 자동 스캔 엔진](#5-phase-2-전체-treeview-자동-스캔-엔진)
6. [Phase 3: Style.lookup 기반 동적 색상 시스템](#6-phase-3-stylelookup-기반-동적-색상-시스템)
7. [Phase 4: 네이티브 위젯(tk.Text/Label) 동기화](#7-phase-4-네이티브-위젯-동기화)
8. [Phase 5: 다이얼로그 생성 시점 동기화](#8-phase-5-다이얼로그-생성-시점-동기화)
9. [Phase 6: 2차 적용 보험 + 디버그 도구](#9-phase-6-2차-적용-보험--디버그-도구)
10. [수정 파일 총괄표](#10-수정-파일-총괄표)
11. [테스트 체크리스트](#11-테스트-체크리스트)
12. [위험 요소 및 롤백 계획](#12-위험-요소-및-롤백-계획)

---

## 1. 문제 정의

### 1.1 현상
- 화이트 테마에서 다크 테마로 전환하면, 일부 Treeview 행의 **글자가 검정색으로 남아** 어두운 배경에서 안 보임
- 다크 테마에서 화이트 테마로 전환하면, 일부 Treeview 행의 **글자가 흰색으로 남아** 밝은 배경에서 안 보임
- 행을 선택(selected)했을 때 **선택 행 글자가 배경과 같은 색**이 되어 안 보이는 경우도 있음
- 현상이 **간헐적**으로 발생하여 재현이 어려움

### 1.2 영향 범위
- **Treeview (표)**: 재고탭, 톤백탭, 화물현황탭, 픽드탭, 솔드탭, 로그탭, 통계탭, 각종 프리뷰 다이얼로그
- **tk.Text (텍스트)**: 로그 뷰어, 가이드, SQL 결과, 출고 LOT 텍스트
- **tk.Label (라벨)**: 설정 다이얼로그, LOT 상세, 각종 정보 표시
- **tk.Listbox**: 테마 선택 다이얼로그

### 1.3 테마 환경
- 라이트 테마 ~6개: cosmo, flatly, litera, minty, lumen, sandstone, yeti, pulse, united, morph, journal, simplex, cerculean
- 다크 테마 ~5개: darkly, cyborg, superhero, solar, vapor
- **테마명에 의존하지 않는 동적 해결**이 필수

---

## 2. 근본 원인 분석

### 원인 #1: `ReadableStyle.apply()`에서 Treeview 기본 foreground 미설정
- **파일**: `gui_app_modular/utils/ui_constants.py` (598~614행)
- **문제**: `style.configure('Treeview', ...)`에 `foreground`, `background`, `fieldbackground`가 없음
- **결과**: ttkbootstrap 테마 내부 기본값에 의존 → 일부 테마에서 배경색과 글자색이 동일해짐

### 원인 #2: `style.map`에서 `('!selected', fg_color)` 조건 누락
- **파일**: `gui_app_modular/utils/ui_constants.py` (610~614행)
- **문제**: `style.map('Treeview', foreground=[('selected', ...)])` 만 있고, `('!selected', ...)` 없음
- **결과**: 행 선택 후 해제하면 foreground가 원래 값으로 원복되지 않아 글자가 사라짐

### 원인 #3: `global_tree_style.py`에서 `import tkinter as tk` 누락
- **파일**: `fixes/global_tree_style.py` (24행, 42행)
- **문제**: `from tkinter import ttk`만 있고 `import tkinter as tk` 없음. 그런데 42행에서 `tk.TclError` 사용
- **결과**: TclError 발생 시 except 블록이 NameError를 발생시켜 다크 테마 감지 실패 → 라이트 색상이 다크 배경에 적용

### 원인 #4: `inventory_tab.py`에서 `style.map` 중복 호출 + 잘못된 색상 키
- **파일**: `gui_app_modular/tabs/inventory_tab.py` (208~213행)
- **문제**: `style.map('Inv.Treeview', ...)`가 2번 연속 호출. 두 번째가 첫 번째를 덮어씀. 또한 `ThemeColors.get('tree_select_fg')`를 background에 사용
- **결과**: 선택 행의 배경색이 글자색이 되는 버그

### 원인 #5: 테마 변경 시 일부 Treeview(2개)만 갱신
- **파일**: `gui_app_modular/mixins/theme_mixin.py` (_update_theme_colors)
- **문제**: `tree_inventory`, `tree_sublot` 만 갱신. picked/sold/log/statistics/프리뷰 다이얼로그의 Treeview는 갱신 안 됨
- **결과**: 갱신 안 된 Treeview의 태그(odd/even) foreground가 이전 테마 값으로 남음

### 원인 #6: 커스텀 스타일명(`Inv.Treeview` 등)이 전역 `"Treeview"` map에서 제외
- **파일**: 여러 탭 파일 (inventory_tab.py, tonbag_tab.py, cargo_overview_tab.py)
- **문제**: 각 탭이 `Inv.Treeview`, `Tb.Treeview`, `Cargo.Treeview` 등 독자 스타일 사용. 전역 `style.map("Treeview", ...)` 갱신은 이 커스텀 스타일에 적용 안 됨
- **결과**: 전역 스타일만 갱신해도 개별 탭 Treeview는 그대로

### 원인 #7: 전역 Treeview 스타일(`global_tree_style`)이 테마 변경 시 재호출 안 됨
- **파일**: `fixes/global_tree_style.py`
- **문제**: 앱 초기화 시 1회만 호출. 테마 변경 훅에서 재호출이 보장되지 않음
- **결과**: 초기 테마 기준 색상이 테마 변경 후에도 그대로 남음

### 원인 #8: tk.Text / tk.Label 등 네이티브 위젯이 ttkbootstrap 테마 영향 안 받음
- **파일**: 다이얼로그 전반 (settings_dialog.py, lot_detail_dialog.py, log_tab.py 등)
- **문제**: tkinter 네이티브 위젯은 ttkbootstrap 테마 전환 시 자동으로 색상이 바뀌지 않음
- **결과**: 다크 모드로 전환해도 tk.Label의 fg='black'이 그대로 → 안 보임

### 원인 #9: 다이얼로그가 테마 변경 후 새로 열릴 때 이전 색상으로 생성
- **파일**: 다이얼로그 전반
- **문제**: 다이얼로그 생성 시점에 ThemeColors를 조회하지만, 해당 시점의 테마가 올바르게 반영되지 않는 경우 있음
- **결과**: 새로 열린 다이얼로그에서도 글자 안 보임

### 원인 #10: `Style.lookup()` 반환값이 시스템 색상명일 경우 예측 불가
- **파일**: 해당 사항 없음 (신규 도입 시 발생 가능)
- **문제**: 일부 OS에서 `style.lookup("Treeview", "foreground")`가 `"systemWindowText"` 같은 시스템 색상명 반환
- **결과**: tag_configure에 전달 시 예상과 다른 색상이 적용될 수 있음

---

## 3. 해결 아키텍처 개요

```
테마 변경 (_change_theme)
    │
    ├── ① ttkbootstrap 테마 전환 (기존)
    │
    ├── ② ReadableStyle.apply() 재호출 — foreground/background 명시 [Phase 1]
    │
    ├── ③ global_tree_style 재호출 [Phase 1]
    │
    ├── ④ 전체 위젯 스캔 엔진 실행 [Phase 2]
    │       ├── 모든 ttk.Treeview 발견
    │       │     ├── Style.lookup()으로 현재 테마 색상 조회 [Phase 3]
    │       │     ├── 해당 Treeview의 실제 스타일명 조회 (cget('style'))
    │       │     ├── configure_tags() 재적용
    │       │     └── update_grid_style_for_theme() 재적용
    │       │
    │       ├── 모든 tk.Text 발견 → fg/bg 동기화 [Phase 4]
    │       ├── 모든 tk.Label(bg 하드코딩) 발견 → fg/bg 동기화 [Phase 4]
    │       └── 모든 tk.Listbox 발견 → fg/bg 동기화 [Phase 4]
    │
    ├── ⑤ 주요 탭 리프레시 (기존 + 확장)
    │
    ├── ⑥ 메뉴바/툴바 색상 갱신 (기존)
    │
    └── ⑦ after(50ms) 2차 적용 [Phase 6]
            └── ④~⑥ 한 번 더 실행 (간헐적 타이밍 이슈 보험)
```

---

## 4. Phase 1: 긴급 버그 수정 (즉시 효과)

> **목표**: 코드 레벨 버그 3개를 즉시 수정. 이것만으로도 체감 개선 큼.

### 4.1 수정 ①: `global_tree_style.py` — `tk` import 추가

**파일**: `fixes/global_tree_style.py`  
**위치**: 24행  
**작업**: `import tkinter as tk` 1줄 추가

```python
# ===== 수정 전 =====
from tkinter import ttk

# ===== 수정 후 =====
import tkinter as tk      # v7.0.1: tk.TclError 사용을 위해 추가
from tkinter import ttk
```

**검증**: 다크 테마 전환 후 `is_dark` 변수가 `True`인지 로그 확인

---

### 4.2 수정 ②: `ui_constants.py` — ReadableStyle.apply()에 foreground/background 명시

**파일**: `gui_app_modular/utils/ui_constants.py`  
**위치**: ReadableStyle.apply() 메서드 내 Treeview 섹션 (약 597~614행)

```python
# ===== 수정 전 =====
# ─── Treeview ───
style.configure(
    'Treeview',
    rowheight=cls.ROW_HEIGHT,
    font=(cls.FONT_FAMILY, cls.FONT_SIZE),
    borderwidth=0,
    relief='flat',
)
style.configure(
    'Treeview.Heading',
    font=(cls.FONT_FAMILY, cls.HEADING_SIZE, 'bold'),
    padding=(8, 6),
    relief='flat',
)
style.map(
    'Treeview',
    background=[('selected', p['tree_select_bg'])],
    foreground=[('selected', p['tree_select_fg'])],
)

# ===== 수정 후 =====
# ─── Treeview ─── (v7.0.1: foreground/background 명시)
style.configure(
    'Treeview',
    rowheight=cls.ROW_HEIGHT,
    font=(cls.FONT_FAMILY, cls.FONT_SIZE),
    borderwidth=0,
    relief='flat',
    foreground=p['text_primary'],       # ★ 추가
    background=p['bg_card'],            # ★ 추가
    fieldbackground=p['bg_card'],       # ★ 추가
)
style.configure(
    'Treeview.Heading',
    font=(cls.FONT_FAMILY, cls.HEADING_SIZE, 'bold'),
    padding=(8, 6),
    relief='flat',
    foreground=p['text_primary'],       # ★ 추가
    background=p['bg_secondary'],       # ★ 추가
)
style.map(
    'Treeview',
    background=[('selected', p['tree_select_bg'])],
    foreground=[
        ('selected', p['tree_select_fg']),
        ('!selected', p['text_primary']),  # ★ 핵심 추가
    ],
)
```

**검증**: 라이트/다크 전환 후 Treeview 행 글자가 보이는지 확인

---

### 4.3 수정 ③: `inventory_tab.py` — style.map 중복 제거 + 올바른 색상

**파일**: `gui_app_modular/tabs/inventory_tab.py`  
**위치**: 약 208~213행

```python
# ===== 수정 전 =====
# v4.0.0 Q7: 선택 행 하이라이트 강화
_style.map('Inv.Treeview',
           background=[('selected', ThemeColors.get('info'))],
           foreground=[('selected', ThemeColors.get('bg_card'))])
_style.map('Inv.Treeview',
           background=[('selected', ThemeColors.get('tree_select_fg'))],  # ← 버그: fg를 bg에
           foreground=[('selected', ThemeColors.get('bg_card'))])

# ===== 수정 후 =====
# v7.0.1: 선택/비선택 행 foreground 명시 + 중복 제거
_style.map('Inv.Treeview',
           background=[('selected', ThemeColors.get('tree_select_bg', _is_dark_tv))],
           foreground=[
               ('selected', ThemeColors.get('tree_select_fg', _is_dark_tv)),
               ('!selected', _tv_fg),   # ★ 비선택 시 foreground 보장
           ])
```

**검증**: 재고탭에서 행 선택/해제 후 글자 가시성 확인

---

### 4.4 수정 ④: `tonbag_tab.py` — !selected foreground 추가

**파일**: `gui_app_modular/tabs/tonbag_tab.py`  
**위치**: 약 145~148행

```python
# ===== 수정 전 =====
_style.map('Tb.Treeview',
           background=[('selected', ThemeColors.get('tree_select_fg'))],
           foreground=[('selected', ThemeColors.get('bg_card'))])

# ===== 수정 후 =====
# v7.0.1: 선택/비선택 행 foreground 명시
_style.map('Tb.Treeview',
           background=[('selected', ThemeColors.get('tree_select_bg', _is_dark_tb))],
           foreground=[
               ('selected', ThemeColors.get('tree_select_fg', _is_dark_tb)),
               ('!selected', _tb_fg),   # ★ 비선택 시 foreground 보장
           ])
```

---

### 4.5 수정 ⑤: `cargo_overview_tab.py` — !selected foreground 추가

**파일**: `gui_app_modular/tabs/cargo_overview_tab.py`  
**위치**: 약 125행

```python
# ===== 수정 전 =====
_style.map('Cargo.Treeview',
           background=[('selected', ThemeColors.get('info'))],
           foreground=[('selected', ThemeColors.get('bg_card'))])

# ===== 수정 후 =====
# v7.0.1: 선택/비선택 행 foreground 명시
_style.map('Cargo.Treeview',
           background=[('selected', ThemeColors.get('tree_select_bg', _is_dark))],
           foreground=[
               ('selected', ThemeColors.get('tree_select_fg', _is_dark)),
               ('!selected', _tv_fg),   # ★ 비선택 시 foreground 보장
           ])
```

---

## 5. Phase 2: 전체 Treeview 자동 스캔 엔진

> **목표**: 테마 변경 시 "특정 Treeview 2개만 갱신"하는 구조를 없애고, 화면에 존재하는 **모든 Treeview를 자동 탐색하여 일괄 갱신**

### 5.1 신규 유틸리티 함수 작성

**파일**: `gui_app_modular/utils/theme_refresh.py` (신규 생성)

```python
# -*- coding: utf-8 -*-
"""
SQM v7.0.1 - 테마 변경 시 전체 위젯 자동 갱신 엔진
====================================================

테마 토글 때 화면에 존재하는 모든 Treeview(+ 네이티브 위젯)를
자동 탐색하여 색상을 일괄 재적용합니다.

사용법:
    from gui_app_modular.utils.theme_refresh import refresh_all_widgets_for_theme
    refresh_all_widgets_for_theme(self)  # self = SQMInventoryApp 인스턴스
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 1. 위젯 트리 탐색기
# ═══════════════════════════════════════════════════════════════

def _walk_widgets(root_widget):
    """
    루트 위젯부터 모든 자식 위젯을 재귀 탐색하는 제너레이터.
    Toplevel(다이얼로그) 포함.
    
    Args:
        root_widget: 탐색 시작 위젯 (보통 app.root)
    
    Yields:
        tkinter 위젯 인스턴스
    """
    stack = [root_widget]
    while stack:
        w = stack.pop()
        yield w
        try:
            children = w.winfo_children()
            stack.extend(children)
        except (tk.TclError, RuntimeError):
            pass
    
    # Toplevel 윈도우도 탐색 (다이얼로그 포함)
    try:
        for toplevel in root_widget.winfo_children():
            if isinstance(toplevel, tk.Toplevel):
                for child in _walk_toplevel(toplevel):
                    yield child
    except (tk.TclError, RuntimeError):
        pass


def _walk_toplevel(toplevel):
    """Toplevel 내부 위젯 탐색"""
    stack = [toplevel]
    while stack:
        w = stack.pop()
        yield w
        try:
            stack.extend(w.winfo_children())
        except (tk.TclError, RuntimeError):
            pass


# ═══════════════════════════════════════════════════════════════
# 2. Style.lookup 기반 안전한 색상 조회
# ═══════════════════════════════════════════════════════════════

def _safe_lookup(style: ttk.Style, widget_class: str, option: str, fallback: str) -> str:
    """
    ttk.Style.lookup()을 안전하게 호출.
    빈 문자열, None, 시스템 색상명을 처리.
    
    Args:
        style: ttk.Style 인스턴스
        widget_class: 조회할 위젯 클래스 (예: "Treeview")
        option: 조회할 옵션 (예: "foreground")
        fallback: lookup 실패 시 반환할 기본값
    
    Returns:
        색상 문자열 (예: "#2c3e50")
    """
    try:
        value = style.lookup(widget_class, option)
        if not value or value.strip() == '':
            return fallback
        
        # 시스템 색상명(예: "systemWindowText")을 RGB로 변환 시도
        if not value.startswith('#') and not value.startswith('rgb'):
            try:
                # tkinter의 winfo_rgb로 변환 시도
                # 이 시점에서는 root가 없으므로 fallback 사용
                # (Phase 3에서 root 전달 시 변환 가능)
                return value  # 대부분의 경우 tkinter가 시스템 색상명을 처리 가능
            except Exception:
                return fallback
        
        return value
    except (tk.TclError, RuntimeError, ValueError):
        return fallback


def get_theme_colors_from_style() -> dict:
    """
    현재 적용된 ttk.Style에서 Treeview 관련 색상을 동적으로 조회.
    테마가 몇 개든 "현재 테마의 실제 색상"을 반환.
    
    Returns:
        dict: {
            'fg': str,          # Treeview 기본 글자색
            'bg': str,          # Treeview 기본 배경색
            'field_bg': str,    # Treeview 필드 배경색
            'sel_fg': str,      # 선택 행 글자색
            'sel_bg': str,      # 선택 행 배경색
            'heading_fg': str,  # 헤더 글자색
            'heading_bg': str,  # 헤더 배경색
            'is_dark': bool,    # 다크 테마 여부 (명도 기반 자동 판별)
        }
    """
    style = ttk.Style()
    
    fg = _safe_lookup(style, "Treeview", "foreground", "#000000")
    bg = _safe_lookup(style, "Treeview", "background", "#ffffff")
    field_bg = _safe_lookup(style, "Treeview", "fieldbackground", bg)
    
    # 선택 색상 (style.map에서 직접 조회는 어려우므로 lookup + fallback)
    sel_bg = _safe_lookup(style, "Treeview", "selectbackground", "#0078D7")
    sel_fg = _safe_lookup(style, "Treeview", "selectforeground", "#ffffff")
    
    # fallback: style.lookup이 빈 값일 때 일반 위젯에서 조회
    if fg in ('#000000', 'black', ''):
        fg = _safe_lookup(style, ".", "foreground", "#000000")
    if bg in ('#ffffff', 'white', ''):
        bg = _safe_lookup(style, ".", "background", "#ffffff")
    
    heading_fg = _safe_lookup(style, "Treeview.Heading", "foreground", fg)
    heading_bg = _safe_lookup(style, "Treeview.Heading", "background", bg)
    
    # 명도 기반 다크/라이트 자동 판별
    is_dark = _is_dark_color(bg)
    
    return {
        'fg': fg,
        'bg': bg,
        'field_bg': field_bg,
        'sel_fg': sel_fg,
        'sel_bg': sel_bg,
        'heading_fg': heading_fg,
        'heading_bg': heading_bg,
        'is_dark': is_dark,
    }


def _is_dark_color(color_str: str) -> bool:
    """
    색상 문자열의 명도(brightness)를 계산하여 다크 여부 판별.
    
    Args:
        color_str: 색상 문자열 (예: "#2c3e50", "white")
    
    Returns:
        True = 어두운 색 (다크 테마), False = 밝은 색 (라이트 테마)
    """
    try:
        # hex 색상 파싱
        if color_str.startswith('#'):
            hex_color = color_str.lstrip('#')
            if len(hex_color) == 3:
                hex_color = ''.join([c*2 for c in hex_color])
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        elif color_str.lower() in ('white', '#ffffff'):
            return False
        elif color_str.lower() in ('black', '#000000'):
            return True
        else:
            return False  # 판별 불가 시 라이트로 간주
        
        # ITU-R BT.601 명도 계산
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        return brightness < 128  # 128 미만이면 다크
        
    except (ValueError, IndexError):
        return False


# ═══════════════════════════════════════════════════════════════
# 3. Treeview 일괄 갱신
# ═══════════════════════════════════════════════════════════════

def _refresh_single_treeview(tree: ttk.Treeview, colors: dict, style: ttk.Style) -> None:
    """
    단일 Treeview의 태그 + 스타일을 현재 테마에 맞게 갱신.
    
    Args:
        tree: 갱신할 Treeview 위젯
        colors: get_theme_colors_from_style() 반환값
        style: ttk.Style 인스턴스
    """
    fg = colors['fg']
    bg = colors['bg']
    is_dark = colors['is_dark']
    sel_fg = colors['sel_fg']
    sel_bg = colors['sel_bg']
    
    # ─── A) 태그 foreground 갱신 (odd/even/stripe) ───
    for tag_name in ('odd', 'even', 'stripe', 'oddrow', 'evenrow'):
        try:
            # 기존 태그가 있으면 foreground만 갱신 (배경은 기존 정책 유지)
            existing = tree.tag_configure(tag_name)
            if existing:  # 태그가 존재하면
                tree.tag_configure(tag_name, foreground=fg)
        except (tk.TclError, ValueError):
            pass
    
    # ─── B) 상태 태그 foreground 갱신 (available/picked/reserved/shipped/depleted) ───
    try:
        from gui_app_modular.utils.ui_constants import ThemeColors
        ThemeColors.configure_tags(tree, is_dark)
    except (ImportError, Exception) as e:
        logger.debug(f"ThemeColors.configure_tags skip: {e}")
        # fallback: 상태 태그도 기본 fg로 설정
        for tag_name in ('available', 'picked', 'reserved', 'shipped', 'depleted'):
            try:
                tree.tag_configure(tag_name, foreground=fg)
            except (tk.TclError, ValueError):
                pass
    
    # ─── C) 해당 Treeview의 커스텀 스타일 갱신 ───
    try:
        style_name = tree.cget('style') or 'Treeview'
        
        # configure: 기본 foreground/background
        style.configure(style_name,
                       foreground=fg,
                       background=bg,
                       fieldbackground=colors['field_bg'])
        
        # map: selected + !selected
        style.map(style_name,
                 foreground=[
                     ('selected', sel_fg),
                     ('!selected', fg),
                 ],
                 background=[
                     ('selected', sel_bg),
                 ])
        
        # Heading도 갱신
        heading_style = f"{style_name}.Heading" if style_name != 'Treeview' else 'Treeview.Heading'
        style.configure(heading_style,
                       foreground=colors['heading_fg'],
                       background=colors['heading_bg'])
        
    except (tk.TclError, ValueError, RuntimeError) as e:
        logger.debug(f"Treeview style update skip ({style_name}): {e}")
    
    # ─── D) Grid/RowHeight 스타일도 갱신 ───
    try:
        from gui_app_modular.utils.table_styler import TableStyler
        TableStyler.update_grid_style_for_theme(tree, is_dark)
    except (ImportError, Exception) as e:
        logger.debug(f"TableStyler update skip: {e}")


# ═══════════════════════════════════════════════════════════════
# 4. 네이티브 위젯(tk.Text/Label/Listbox) 동기화
# ═══════════════════════════════════════════════════════════════

def _refresh_native_widget(widget, colors: dict) -> None:
    """
    tk.Text, tk.Label, tk.Listbox 등 네이티브 위젯의 fg/bg를 테마에 맞게 동기화.
    
    주의: 모든 네이티브 위젯을 무차별 변경하면 의도된 커스텀 색상까지 덮어쓸 수 있으므로,
    "명백히 테마와 충돌하는 경우"만 수정합니다.
    
    판별 기준:
    - 다크 테마인데 fg가 검정 계열 → 안 보임 → fg를 밝은 색으로
    - 라이트 테마인데 fg가 흰색 계열 → 안 보임 → fg를 어두운 색으로
    """
    is_dark = colors['is_dark']
    theme_fg = colors['fg']
    theme_bg = colors['bg']
    
    try:
        current_fg = str(widget.cget('fg') if hasattr(widget, 'cget') else '')
        current_bg = str(widget.cget('bg') if hasattr(widget, 'cget') else '')
    except (tk.TclError, RuntimeError):
        return
    
    # 충돌 판별
    fg_is_dark = _is_dark_color(current_fg) if current_fg and current_fg.startswith('#') else (current_fg.lower() in ('black', '#000000', ''))
    fg_is_light = not fg_is_dark
    
    needs_fix = False
    if is_dark and fg_is_dark:
        # 다크 배경 + 어두운 글자 → 안 보임
        needs_fix = True
    elif not is_dark and fg_is_light and current_fg.lower() not in ('', 'black', '#000000'):
        # 라이트 배경 + 밝은 글자 → 안 보임
        needs_fix = True
    
    if needs_fix:
        try:
            widget.configure(fg=theme_fg)
            # bg도 함께 맞추는 게 안전 (단, 의도된 배경색이 있을 수 있으므로 조건부)
            if current_bg.lower() in ('white', '#ffffff', 'black', '#000000', ''):
                widget.configure(bg=theme_bg)
            # Text 위젯의 커서 색상도 동기화
            if isinstance(widget, tk.Text):
                widget.configure(insertbackground=theme_fg)
        except (tk.TclError, RuntimeError):
            pass


# ═══════════════════════════════════════════════════════════════
# 5. 메인 갱신 함수 (이것을 _change_theme에서 호출)
# ═══════════════════════════════════════════════════════════════

def refresh_all_widgets_for_theme(app) -> dict:
    """
    테마 변경 시 화면에 존재하는 모든 위젯을 자동 탐색하여 색상 일괄 갱신.
    
    이 함수를 ThemeMixin._change_theme() 끝에서 호출하면 됩니다.
    
    Args:
        app: SQMInventoryApp 인스턴스 (app.root 필요)
    
    Returns:
        dict: 갱신 통계 {'treeviews': int, 'native_widgets': int, 'is_dark': bool}
    
    사용법:
        # theme_mixin.py의 _change_theme() 끝에서:
        from ..utils.theme_refresh import refresh_all_widgets_for_theme
        stats = refresh_all_widgets_for_theme(self)
        logger.debug(f"Theme refresh: {stats}")
    """
    stats = {'treeviews': 0, 'native_widgets': 0, 'is_dark': False}
    
    try:
        # ─── Step 1: 전역 스타일 재적용 ───
        try:
            from fixes.global_tree_style import apply_global_tree_style
            apply_global_tree_style()
        except (ImportError, Exception) as e:
            logger.debug(f"global_tree_style 재적용 skip: {e}")
        
        # ─── Step 2: 현재 테마 색상 조회 ───
        colors = get_theme_colors_from_style()
        stats['is_dark'] = colors['is_dark']
        style = ttk.Style()
        
        # ─── Step 3: 전체 위젯 스캔 ───
        for w in _walk_widgets(app.root):
            # Treeview 갱신
            if isinstance(w, ttk.Treeview):
                _refresh_single_treeview(w, colors, style)
                stats['treeviews'] += 1
            
            # 네이티브 위젯 갱신 (tk.Text, tk.Label with explicit bg, tk.Listbox)
            elif isinstance(w, (tk.Text, tk.Listbox)):
                _refresh_native_widget(w, colors)
                stats['native_widgets'] += 1
            elif isinstance(w, tk.Label):
                # tk.Label만 (ttk.Label은 자동으로 테마를 따름)
                # ttk.Label이 아닌 경우만 처리
                if not isinstance(w, ttk.Label):
                    _refresh_native_widget(w, colors)
                    stats['native_widgets'] += 1
        
        logger.info(f"[v7.0.1] Theme refresh 완료: "
                    f"Treeview={stats['treeviews']}, "
                    f"Native={stats['native_widgets']}, "
                    f"dark={stats['is_dark']}")
        
    except Exception as e:
        logger.error(f"[v7.0.1] Theme refresh 실패: {e}")
    
    return stats


# ═══════════════════════════════════════════════════════════════
# 6. 디버그 유틸리티
# ═══════════════════════════════════════════════════════════════

def debug_dump_widget_theme_status(app) -> str:
    """
    현재 화면의 모든 Treeview/네이티브 위젯의 테마 상태를 덤프.
    디버그 메뉴에서 호출하여 문제 위젯을 즉시 특정할 수 있음.
    
    Returns:
        str: 위젯별 상태 텍스트 (로그/다이얼로그에 출력용)
    """
    lines = []
    lines.append("=" * 70)
    lines.append("SQM v7.0.1 Widget Theme Status Dump")
    lines.append("=" * 70)
    
    colors = get_theme_colors_from_style()
    lines.append(f"Current theme colors: fg={colors['fg']}, bg={colors['bg']}, dark={colors['is_dark']}")
    lines.append("")
    
    tree_count = 0
    native_count = 0
    problems = []
    
    for w in _walk_widgets(app.root):
        if isinstance(w, ttk.Treeview):
            tree_count += 1
            style_name = w.cget('style') or 'Treeview'
            
            # 태그 상태 확인
            tag_info = []
            for tag in ('odd', 'even', 'available', 'picked', 'reserved'):
                try:
                    cfg = w.tag_configure(tag)
                    if cfg:
                        tag_fg = cfg.get('foreground', [''])[0] if isinstance(cfg.get('foreground'), (list, tuple)) else cfg.get('foreground', '')
                        tag_info.append(f"{tag}:fg={tag_fg}")
                except Exception:
                    pass
            
            line = f"  [Treeview #{tree_count}] style={style_name} | tags: {', '.join(tag_info) if tag_info else 'none'}"
            lines.append(line)
            
            # 문제 감지
            for tag in ('odd', 'even'):
                try:
                    cfg = w.tag_configure(tag)
                    tag_fg = str(cfg.get('foreground', ''))
                    if colors['is_dark'] and tag_fg.lower() in ('black', '#000000', ''):
                        problems.append(f"⚠️ Treeview #{tree_count} ({style_name}): tag '{tag}' fg='{tag_fg}' on dark theme!")
                    elif not colors['is_dark'] and tag_fg.lower() in ('white', '#ffffff'):
                        problems.append(f"⚠️ Treeview #{tree_count} ({style_name}): tag '{tag}' fg='{tag_fg}' on light theme!")
                except Exception:
                    pass
        
        elif isinstance(w, (tk.Text, tk.Listbox)):
            native_count += 1
        elif isinstance(w, tk.Label) and not isinstance(w, ttk.Label):
            native_count += 1
    
    lines.append("")
    lines.append(f"Total: Treeview={tree_count}, Native={native_count}")
    
    if problems:
        lines.append("")
        lines.append("─── PROBLEMS DETECTED ───")
        for p in problems:
            lines.append(f"  {p}")
    else:
        lines.append("✅ No visibility problems detected")
    
    lines.append("=" * 70)
    return "\n".join(lines)
```

---

## 6. Phase 3: Style.lookup 기반 동적 색상 시스템

> **목표**: `ThemeColors.configure_tags()`를 하드코딩 의존에서 `Style.lookup` 기반으로 전환

### 6.1 `ui_constants.py` — ThemeColors.configure_tags() 개선

**파일**: `gui_app_modular/utils/ui_constants.py`  
**위치**: ThemeColors 클래스의 configure_tags 메서드

```python
# ===== 수정 전 =====
@classmethod
def configure_tags(cls, tree, is_dark: bool = False):
    """트리뷰 상태 태그 설정 (v3.8.4)"""
    p = cls.DARK if is_dark else cls.LIGHT
    fg = '#f0f0f0' if is_dark else '#1a1a1a'
    for status in ['available', 'picked', 'reserved', 'shipped']:
        tree.tag_configure(status, background=p[status], foreground=fg)
    tree.tag_configure('depleted', background='#f0f0f0' if not is_dark else '#2a2a2a',
                      foreground='#aaaaaa' if not is_dark else '#888888')
    tree.tag_configure('stripe', background=p['tree_stripe'], foreground=fg)

# ===== 수정 후 =====
@classmethod
def configure_tags(cls, tree, is_dark: bool = None):
    """
    v7.0.1: 트리뷰 상태 태그 설정.
    is_dark가 None이면 Style.lookup으로 자동 판별.
    """
    # Style.lookup 기반 자동 판별 (is_dark가 명시되지 않으면)
    if is_dark is None:
        try:
            from gui_app_modular.utils.theme_refresh import get_theme_colors_from_style
            colors = get_theme_colors_from_style()
            is_dark = colors['is_dark']
        except (ImportError, Exception):
            is_dark = False
    
    p = cls.DARK if is_dark else cls.LIGHT
    
    # v7.0.1: Style.lookup으로 기본 fg 조회 (하드코딩 제거)
    try:
        style = ttk.Style()
        base_fg = style.lookup("Treeview", "foreground") or ''
        if not base_fg or base_fg.strip() == '':
            base_fg = '#f0f0f0' if is_dark else '#1a1a1a'
    except Exception:
        base_fg = '#f0f0f0' if is_dark else '#1a1a1a'
    
    fg = base_fg
    
    for status in ['available', 'picked', 'reserved', 'shipped']:
        try:
            tree.tag_configure(status, background=p[status], foreground=fg)
        except Exception:
            pass
    
    try:
        tree.tag_configure('depleted',
                          background='#2a2a2a' if is_dark else '#f0f0f0',
                          foreground='#888888' if is_dark else '#aaaaaa')
    except Exception:
        pass
    
    try:
        tree.tag_configure('stripe', background=p['tree_stripe'], foreground=fg)
    except Exception:
        pass
    
    # v7.0.1: odd/even 태그도 fg 동기화
    try:
        tree.tag_configure('odd', foreground=fg)
        tree.tag_configure('even', foreground=fg)
    except Exception:
        pass
```

---

## 7. Phase 4: 네이티브 위젯 동기화

> **목표**: tk.Text, tk.Label, tk.Listbox 등 네이티브 위젯도 테마 전환 시 색상 동기화
> **구현**: Phase 2의 `theme_refresh.py` 내 `_refresh_native_widget()` 함수에 이미 포함

### 7.1 추가 작업: 주요 다이얼로그의 하드코딩 색상 점검

아래 파일들에서 `fg='black'`, `fg='white'`, `bg='white'`, `bg='black'` 같은 하드코딩을 찾아 ThemeColors 기반으로 교체합니다.

**점검 대상 파일 목록**:

| 파일 | 하드코딩 위치 | 수정 방향 |
|------|-------------|----------|
| `dialogs/settings_dialog.py` | `tk.Label(..., bg=_bg, fg=_fg)` | ✅ 이미 ThemeColors 사용 (양호) |
| `dialogs/lot_detail_dialog.py` | `tk.Frame(bg=header_bg)`, `tk.Label(fg=fg)` | ✅ 이미 ThemeColors 사용 (양호, 단 생성 시점 고정 → Phase 5에서 해결) |
| `dialogs/auto_backup.py` | `foreground='gray'` | ⚠️ ThemeColors.get('text_muted', is_dark)로 교체 |
| `dialogs/picking_list_preview_dialog.py` | `foreground="darkred"` | ⚠️ ThemeColors.get('danger', is_dark)로 교체 |
| `dialogs/column_mapper_dialog.py` | `foreground='gray'` | ⚠️ ThemeColors.get('text_muted', is_dark)로 교체 |
| `tabs/log_tab.py` | `tk.Text(...)` — fg/bg 없음 | ⚠️ 생성 시 ThemeColors 기반 fg/bg 추가 |
| `mixins/custom_menubar.py` | `tk.Text(...)` — fg/bg 없음 | ⚠️ 생성 시 ThemeColors 기반 fg/bg 추가 |

**수정 예시** (`log_tab.py`):

```python
# ===== 수정 전 =====
self.log_text = tk.Text(log_frame, wrap='word', height=20, state='disabled', font=fonts.mono())

# ===== 수정 후 =====
_is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
_log_fg = ThemeColors.get('text_primary', _is_dark)
_log_bg = ThemeColors.get('bg_card', _is_dark)
self.log_text = tk.Text(
    log_frame, wrap='word', height=20, state='disabled', font=fonts.mono(),
    fg=_log_fg, bg=_log_bg, insertbackground=_log_fg,    # ★ v7.0.1
)
```

---

## 8. Phase 5: 다이얼로그 생성 시점 동기화

> **목표**: 테마 변경 후 새로 열리는 다이얼로그가 올바른 색상으로 생성되도록 보장

### 8.1 `ui_constants.py` — `setup_dialog_defaults()` 함수에 테마 동기화 추가

**파일**: `gui_app_modular/utils/ui_constants.py`  
**위치**: `setup_dialog_defaults()` 함수 (약 682행)

```python
# ===== 수정 전 =====
def setup_dialog_defaults(dialog, parent, title: str, size_type: str = 'medium'):
    """다이얼로그 기본 설정"""
    dialog.title(title)
    geometry = DialogSize.get_geometry(parent, size_type)
    dialog.geometry(geometry)
    apply_modal_window_options(dialog)
    dialog.transient(parent)
    dialog.grab_set()
    center_dialog(dialog, parent)
    dialog.bind('<Escape>', lambda e: dialog.destroy())
    return dialog

# ===== 수정 후 =====
def setup_dialog_defaults(dialog, parent, title: str, size_type: str = 'medium'):
    """다이얼로그 기본 설정 (v7.0.1: 생성 시 테마 동기화 포함)"""
    dialog.title(title)
    geometry = DialogSize.get_geometry(parent, size_type)
    dialog.geometry(geometry)
    apply_modal_window_options(dialog)
    dialog.transient(parent)
    dialog.grab_set()
    center_dialog(dialog, parent)
    dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    # ★ v7.0.1: 다이얼로그 생성 시 내부 Treeview/네이티브 위젯 테마 동기화
    #   after(100ms)로 위젯이 모두 생성된 후 적용
    try:
        def _sync_dialog_theme():
            try:
                from gui_app_modular.utils.theme_refresh import (
                    _walk_widgets, get_theme_colors_from_style,
                    _refresh_single_treeview, _refresh_native_widget
                )
                import tkinter as _tk
                from tkinter import ttk as _ttk
                
                colors = get_theme_colors_from_style()
                style = _ttk.Style()
                
                for w in _walk_widgets(dialog):
                    if isinstance(w, _ttk.Treeview):
                        _refresh_single_treeview(w, colors, style)
                    elif isinstance(w, (_tk.Text, _tk.Listbox)):
                        _refresh_native_widget(w, colors)
                    elif isinstance(w, _tk.Label) and not isinstance(w, _ttk.Label):
                        _refresh_native_widget(w, colors)
            except Exception:
                pass
        
        dialog.after(100, _sync_dialog_theme)
    except Exception:
        pass
    
    return dialog
```

---

## 9. Phase 6: 2차 적용 보험 + 디버그 도구

> **목표**: 간헐적 타이밍 이슈 방지 + 문제 위젯 즉시 특정

### 9.1 `theme_mixin.py` — `_change_theme()` 전면 개편

**파일**: `gui_app_modular/mixins/theme_mixin.py`  
**위치**: `_change_theme()` 메서드 + `_update_theme_colors()` 메서드

```python
# ===== _change_theme() 수정 후 (전체) =====
def _change_theme(self, theme_name: str) -> None:
    """Change application theme — v7.0.1: 전역 스타일·전체 위젯 일괄 갱신"""
    from ..utils.constants import HAS_TTKBOOTSTRAP
    
    if not HAS_TTKBOOTSTRAP:
        CustomMessageBox.showinfo(self.root, "Info", "Theme change requires ttkbootstrap")
        return
    
    try:
        # Step 1: ttkbootstrap 테마 전환
        if hasattr(self.root, 'style'):
            self.root.style.theme_use(theme_name)
        
        self.current_theme = theme_name
        self._save_theme_preference(theme_name)
        
        # Step 2: ReadableStyle 재적용 (foreground/background 명시 포함)
        try:
            from ..utils.ui_constants import ReadableStyle
            ReadableStyle.apply(self.root, theme_name)
        except (ImportError, Exception) as e:
            logger.debug(f"ReadableStyle 재적용 무시: {e}")
        
        # Step 3: 전체 위젯 갱신 (1차)
        self._update_theme_colors()
        
        # Step 4: 메뉴바 테마 갱신
        try:
            if hasattr(self, 'custom_menubar') and getattr(self.custom_menubar, 'refresh_theme_colors', None):
                self.custom_menubar.refresh_theme_colors()
        except (ValueError, TypeError, AttributeError) as _e:
            logger.debug(f"메뉴바 테마 갱신 무시: {_e}")
        
        # Step 5: 주요 탭 리프레시
        try:
            if hasattr(self, '_refresh_inventory'):
                self._refresh_inventory()
            if hasattr(self, '_refresh_tonbag'):
                self._refresh_tonbag()
        except (ValueError, TypeError, AttributeError) as _e:
            logger.debug(f"탭 리프레시 무시: {_e}")
        
        # Step 6: update_idletasks 후 2차 적용 (50ms 보험)
        try:
            self.root.update_idletasks()
            self.root.after(50, self._update_theme_colors)    # ★ v7.0.1 보험
        except Exception as _e:
            logger.debug(f"2차 적용 무시: {_e}")
        
        self._log(f"Theme changed: {theme_name}")
        
    except (ValueError, TypeError, AttributeError) as e:
        CustomMessageBox.showerror(self.root, "Error", f"Theme change failed:\n{e}")


# ===== _update_theme_colors() 수정 후 (전체) =====
def _update_theme_colors(self) -> None:
    """v7.0.1: 테마 변경 시 전체 위젯 자동 스캔 + 일괄 갱신"""
    try:
        from ..utils.theme_refresh import refresh_all_widgets_for_theme
        stats = refresh_all_widgets_for_theme(self)
        logger.debug(f"[v7.0.1] _update_theme_colors: {stats}")
    except (ImportError, Exception) as e:
        logger.error(f"[v7.0.1] theme_refresh import 실패, fallback 사용: {e}")
        # fallback: 기존 로직 (최소한의 갱신)
        self._update_theme_colors_fallback()


def _update_theme_colors_fallback(self) -> None:
    """v7.0.1: theme_refresh 모듈 사용 불가 시 기존 방식으로 최소 갱신"""
    from ..utils.ui_constants import ThemeColors
    
    is_dark = ThemeColors.is_dark_theme(self.current_theme)
    
    if hasattr(self, 'tree_inventory'):
        ThemeColors.configure_tags(self.tree_inventory, is_dark)
        try:
            from ..utils.table_styler import TableStyler
            TableStyler.update_grid_style_for_theme(self.tree_inventory, is_dark)
        except (ImportError, Exception):
            pass
    
    if hasattr(self, 'tree_sublot'):
        ThemeColors.configure_tags(self.tree_sublot, is_dark)
        try:
            from ..utils.table_styler import TableStyler
            TableStyler.update_grid_style_for_theme(self.tree_sublot, is_dark)
        except (ImportError, Exception):
            pass
    
    try:
        if hasattr(self, '_refresh_toolbar_theme'):
            self._refresh_toolbar_theme()
    except Exception:
        pass
```

---

### 9.2 디버그 메뉴에 위젯 테마 상태 점검 버튼 추가

**파일**: 디버그 메뉴가 정의된 곳 (예: `gui_app_modular/mixins/diagnostics_mixin.py` 또는 메뉴 설정부)

```python
# 디버그 메뉴에 추가할 항목
def _debug_theme_status(self):
    """디버그: 현재 화면 위젯의 테마 상태 점검"""
    try:
        from gui_app_modular.utils.theme_refresh import debug_dump_widget_theme_status
        result = debug_dump_widget_theme_status(self)
        
        # 결과를 다이얼로그로 표시
        import tkinter as tk
        from tkinter import scrolledtext
        
        dialog = tk.Toplevel(self.root)
        dialog.title("🔍 Widget Theme Status")
        dialog.geometry("700x500")
        dialog.transient(self.root)
        
        text = scrolledtext.ScrolledText(dialog, font=('Consolas', 9))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert('1.0', result)
        text.configure(state='disabled')
        
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    except Exception as e:
        logger.error(f"Theme status dump 실패: {e}")
```

---

## 10. 수정 파일 총괄표

| # | 파일 경로 | Phase | 작업 내용 | 신규/수정 |
|---|----------|-------|----------|----------|
| 1 | `fixes/global_tree_style.py` | P1 | `import tkinter as tk` 1줄 추가 | 수정 |
| 2 | `gui_app_modular/utils/ui_constants.py` | P1+P3 | ReadableStyle.apply() fg/bg 명시 + ThemeColors.configure_tags() lookup 기반 개선 | 수정 |
| 3 | `gui_app_modular/tabs/inventory_tab.py` | P1 | style.map 중복 제거 + !selected fg 추가 | 수정 |
| 4 | `gui_app_modular/tabs/tonbag_tab.py` | P1 | !selected fg 추가 | 수정 |
| 5 | `gui_app_modular/tabs/cargo_overview_tab.py` | P1 | !selected fg 추가 | 수정 |
| 6 | `gui_app_modular/utils/theme_refresh.py` | P2+P4+P6 | 전체 위젯 스캔 엔진 + 네이티브 위젯 동기화 + 디버그 도구 | **신규** |
| 7 | `gui_app_modular/mixins/theme_mixin.py` | P1+P6 | _change_theme() 전면 개편 + _update_theme_colors() 전체 스캔 방식 교체 + fallback + after(50ms) | 수정 |
| 8 | `gui_app_modular/utils/ui_constants.py` | P5 | setup_dialog_defaults()에 테마 동기화 추가 | 수정 |
| 9 | `gui_app_modular/tabs/log_tab.py` | P4 | tk.Text 생성 시 fg/bg 추가 | 수정 |
| 10 | `gui_app_modular/mixins/diagnostics_mixin.py` | P6 | 디버그 메뉴에 위젯 테마 상태 점검 버튼 추가 | 수정 |

---

## 11. 테스트 체크리스트

### 11.1 기본 테스트 (모든 Phase 완료 후)

| # | 테스트 항목 | 예상 결과 | Pass/Fail |
|---|-----------|----------|-----------|
| T1 | flatly → darkly 전환 후 재고탭 Treeview 글자 | 밝은 글자 보임 | |
| T2 | darkly → flatly 전환 후 재고탭 Treeview 글자 | 어두운 글자 보임 | |
| T3 | 테마 전환 후 톤백탭 Treeview 글자 | 보임 | |
| T4 | 테마 전환 후 화물현황탭 Treeview 글자 | 보임 | |
| T5 | 테마 전환 후 솔드탭 Treeview 글자 | 보임 | |
| T6 | 테마 전환 후 로그탭 Text 글자 | 보임 | |
| T7 | 테마 전환 후 Treeview 행 선택/해제 | 선택 시 보임, 해제 시 보임 | |
| T8 | 다크 테마에서 출고 프리뷰 다이얼로그 열기 | 글자 보임 | |
| T9 | 라이트 테마에서 설정 다이얼로그 열기 | 글자 보임 | |
| T10 | LOT 상세 다이얼로그 열기 | 글자 보임 | |

### 11.2 다수 테마 테스트

| # | 테마 전환 경로 | 결과 |
|---|--------------|------|
| T11 | flatly → cyborg → cosmo | 매 전환마다 글자 보임 |
| T12 | darkly → minty → superhero | 매 전환마다 글자 보임 |
| T13 | solar → flatly → vapor | 매 전환마다 글자 보임 |
| T14 | 테마 3회 연속 빠르게 전환 | 글자 깨짐 없음 |

### 11.3 엣지 케이스 테스트

| # | 테스트 항목 | 예상 결과 |
|---|-----------|----------|
| T15 | 테마 전환 직후 다이얼로그 즉시 열기 | 글자 보임 |
| T16 | 테마 전환 중 탭 전환 | 글자 보임 |
| T17 | 앱 시작 시 저장된 다크 테마 로드 | 글자 보임 |
| T18 | 디버그 메뉴 > 위젯 테마 상태 점검 | 문제 없음 표시 |

---

## 12. 위험 요소 및 롤백 계획

### 12.1 위험 요소

| 위험 | 확률 | 대응 |
|------|------|------|
| `_walk_widgets`가 대량 위젯 탐색 시 성능 저하 | 낮음 (위젯 수백 개 수준) | 탐색 시간 측정, 500ms 초과 시 경고 로그 |
| 네이티브 위젯 fg/bg 강제 변경이 의도된 커스텀 색상을 덮어씀 | 중간 | `_refresh_native_widget()`의 충돌 판별 로직으로 방어. "명백히 안 보이는 경우"만 수정 |
| `Style.lookup()`이 특정 OS/테마에서 빈 값 반환 | 낮음 | `_safe_lookup()` fallback 로직으로 방어 |
| `after(50ms)` 2차 적용이 화면 깜빡임 유발 | 매우 낮음 | 실제 테스트 후 문제 시 100ms로 조정 또는 제거 |

### 12.2 롤백 계획

1. **`theme_refresh.py`는 신규 파일**이므로, 삭제만 하면 원복
2. **`_update_theme_colors()`에 fallback 메서드** 포함 → `theme_refresh` import 실패 시 기존 로직 자동 사용
3. 모든 수정 파일은 **`# v7.0.1`** 주석 태그 → `grep -rn "v7.0.1"` 으로 전체 변경점 즉시 확인 가능

---

**끝. 이 계획서대로 구현하면 테마가 몇 개든 "글자가 안 보이는" 문제가 근본적으로 해결됩니다.**
