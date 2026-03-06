# -*- coding: utf-8 -*-
"""
SQM PREMIUM UI v7 (Prototype)
- ttkbootstrap 기반 "프리미엄 다크/라이트" UI 샘플
- 목표: ERP/Terminal 급 '절제된 고급감' + 테이블 가독성 + 일관된 팔레트

실행:
  pip install ttkbootstrap
  python SQM_PREMIUM_UI_v7.py
"""

from __future__ import annotations

import random
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# ============================================================
# 1) Ruby Premium Palettes (세련된 2단 명도 + 절제된 포인트)
# ============================================================
PALETTE_DARK = {
    "bg":        "#0B0F17",
    "panel":     "#0F1623",
    "card":      "#121C2B",
    "card2":     "#162238",
    "border":    "#22314D",
    "text":      "#E6EDF6",
    "muted":     "#A8B3C7",
    "accent":    "#7C5CFF",   # 버튼/포커스 등 '아주 제한'
    "select_bg": "#1B2A44",

    # 상태(부드럽게) — 과한 네온 금지
    "st_available": "#12314A",
    "st_reserved":  "#2A2152",
    "st_picked":    "#1E3A2F",
    "st_shipped":   "#2F2F2F",
}

PALETTE_LIGHT = {
    "bg":        "#F6F8FC",
    "panel":     "#EEF2F8",
    "card":      "#FFFFFF",
    "card2":     "#F7FAFF",
    "border":    "#D7DFEC",
    "text":      "#0B1220",
    "muted":     "#53627A",
    "accent":    "#4F46E5",
    "select_bg": "#DCE7FF",

    "st_available": "#E6F2FF",
    "st_reserved":  "#F1E9FF",
    "st_picked":    "#E8FFF1",
    "st_shipped":   "#F2F4F7",
}

STATUS_TAGS = ("available", "reserved", "picked", "shipped")


# ============================================================
# 2) Theme Engine (단일 소스 + 덮어쓰기 최소화)
# ============================================================
class PremiumTheme:
    def __init__(self, style: tb.Style, start_mode: str = "dark"):
        self.style = style
        self.mode = start_mode  # "dark" | "light"

    @property
    def P(self):
        return PALETTE_DARK if self.mode == "dark" else PALETTE_LIGHT

    def apply(self):
        P = self.P
        s = self.style

        # 전역 컨테이너/라벨
        s.configure("TFrame", background=P["bg"])
        s.configure("TLabel", background=P["bg"], foreground=P["text"])
        s.configure("Muted.TLabel", background=P["bg"], foreground=P["muted"])
        s.configure("Card.TFrame", background=P["card"], borderwidth=0)
        s.configure("Card2.TFrame", background=P["card2"], borderwidth=0)

        # 엔트리/콤보 (업무용 가독성)
        s.configure("TEntry", foreground=P["text"], fieldbackground=P["card"])
        s.configure("TCombobox", foreground=P["text"], fieldbackground=P["card"])

        # 버튼: 기본 중립, 중요 액션만 Accent
        s.configure("TButton", padding=(10, 6))
        s.configure("Accent.TButton", background=P["accent"], foreground=P["text"])
        s.map("Accent.TButton",
              background=[("active", P["accent"]), ("pressed", P["accent"])],
              foreground=[("active", P["text"]), ("pressed", P["text"])])

        # Notebook (탭바 panel, 선택 탭 card)
        s.configure("TNotebook", background=P["panel"], borderwidth=0)
        s.configure("TNotebook.Tab",
                    padding=(12, 8),
                    background=P["panel"],
                    foreground=P["muted"])
        s.map("TNotebook.Tab",
              background=[("selected", P["card"])],
              foreground=[("selected", P["text"])])

        # Treeview (핵심)
        s.configure("Treeview",
                    background=P["card2"],
                    fieldbackground=P["card2"],
                    foreground=P["text"],
                    bordercolor=P["border"],
                    lightcolor=P["border"],
                    darkcolor=P["border"],
                    rowheight=26)
        s.configure("Treeview.Heading",
                    background=P["card"],
                    foreground=P["muted"],
                    relief="flat")

        # 선택색은 절제
        s.map("Treeview",
              background=[("selected", P["select_bg"])],
              foreground=[("selected", P["text"])])

    def toggle(self):
        self.mode = "light" if self.mode == "dark" else "dark"
        self.apply()


# ============================================================
# 3) UI Widgets
# ============================================================
class TopBar(ttk.Frame):
    def __init__(self, parent, theme: PremiumTheme, on_toggle_theme):
        super().__init__(parent, padding=(12, 10))
        self.theme = theme
        self.on_toggle_theme = on_toggle_theme
        self._build()

    def _build(self):
        left = ttk.Frame(self)
        left.pack(side=LEFT, fill=X, expand=True)

        ttk.Label(left, text="SQM PREMIUM UI v7", font=("Malgun Gothic", 12, "bold")).pack(side=LEFT)
        ttk.Label(left, text="(Prototype)", style="Muted.TLabel").pack(side=LEFT, padx=(10, 0))

        right = ttk.Frame(self)
        right.pack(side=RIGHT)

        ttk.Button(right, text="테마 전환", command=self.on_toggle_theme).pack(side=LEFT, padx=(0, 8))
        ttk.Button(right, text="중요 실행", style="Accent.TButton", command=lambda: None).pack(side=LEFT)


class SideBar(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=(10, 10))
        self._build()

    def _build(self):
        ttk.Label(self, text="MENU", font=("Malgun Gothic", 10, "bold")).pack(anchor=W, pady=(0, 8))
        for name in ["입고", "재고", "출고", "반품", "리포트", "설정"]:
            ttk.Button(self, text=name).pack(fill=X, pady=4)


class FilterBar(ttk.Frame):
    def __init__(self, parent, on_apply, on_reset):
        super().__init__(parent, padding=(10, 8))
        self.on_apply = on_apply
        self.on_reset = on_reset

        self.var_lot = tk.StringVar(value="전체")
        self.var_status = tk.StringVar(value="전체")
        self.var_kw = tk.StringVar(value="")
        self._build()

    def _build(self):
        row = ttk.Frame(self)
        row.pack(fill=X)

        ttk.Label(row, text="LOT", style="Muted.TLabel").pack(side=LEFT, padx=(0, 6))
        ttk.Combobox(row, textvariable=self.var_lot, values=["전체", "1125072147", "1125072150", "1125072199"], width=14).pack(side=LEFT, padx=(0, 10))

        ttk.Label(row, text="STATUS", style="Muted.TLabel").pack(side=LEFT, padx=(0, 6))
        ttk.Combobox(row, textvariable=self.var_status, values=["전체", "available", "reserved", "picked", "shipped"], width=14).pack(side=LEFT, padx=(0, 10))

        ttk.Label(row, text="키워드", style="Muted.TLabel").pack(side=LEFT, padx=(0, 6))
        ttk.Entry(row, textvariable=self.var_kw, width=24).pack(side=LEFT, padx=(0, 10))

        ttk.Button(row, text="적용", style="Accent.TButton", command=self.on_apply).pack(side=RIGHT)
        ttk.Button(row, text="초기화", command=self.on_reset).pack(side=RIGHT, padx=(0, 8))


class MainTable(ttk.Frame):
    def __init__(self, parent, theme: PremiumTheme):
        super().__init__(parent, padding=10)
        self.theme = theme

        self._all_rows = []
        self._build()
        self._seed_data()
        self.refresh()

    def _build(self):
        # 카드 컨테이너
        self.card = ttk.Frame(self, style="Card.TFrame", padding=10)
        self.card.pack(fill=BOTH, expand=True)

        cols = ("LOT_NO", "SAP_NO", "PRODUCT", "QTY_MT", "CUSTOMER", "STATUS", "WH", "UPDATED")
        self.tree = ttk.Treeview(self.card, columns=cols, show="headings")
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)

        vs = ttk.Scrollbar(self.card, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        vs.pack(side=RIGHT, fill=Y)

        headings = {
            "LOT_NO": "LOT NO",
            "SAP_NO": "SAP NO",
            "PRODUCT": "PRODUCT",
            "QTY_MT": "QTY (MT)",
            "CUSTOMER": "CUSTOMER",
            "STATUS": "STATUS",
            "WH": "WH",
            "UPDATED": "UPDATED",
        }
        widths = {
            "LOT_NO": 140, "SAP_NO": 120, "PRODUCT": 220, "QTY_MT": 90,
            "CUSTOMER": 220, "STATUS": 110, "WH": 80, "UPDATED": 140
        }

        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor=W)

        self.apply_tags()

    def apply_tags(self):
        P = self.theme.P
        t = self.tree

        # 상태별 배경(부드럽게)
        t.tag_configure("available", background=P["st_available"], foreground=P["text"])
        t.tag_configure("reserved",  background=P["st_reserved"],  foreground=P["text"])
        t.tag_configure("picked",    background=P["st_picked"],    foreground=P["text"])
        t.tag_configure("shipped",   background=P["st_shipped"],   foreground=P["text"])

    def _seed_data(self):
        products = ["PT LBM 300MT", "SQM Li2CO3", "HY Clean Metal", "LiOH (Battery Grade)"]
        customers = ["GY Logistics", "ABC Trading", "Seoul Client", "Export Partner", "FTZ Client"]
        whs = ["GW", "SL", "FTZ"]
        saps = ["SAP-100221", "SAP-100238", "SAP-100251", "SAP-100299"]

        self._all_rows = []
        for _ in range(60):
            lot = random.choice(["1125072147", "1125072150", "1125072199"])
            sap = random.choice(saps)
            prod = random.choice(products)
            qty = round(random.choice([10, 20, 40, 60, 80]) + random.random(), 3)
            cust = random.choice(customers)
            st = random.choice(STATUS_TAGS)
            wh = random.choice(whs)
            updated = random.choice(["2026-03-02", "2026-03-03", "2026-03-04"])
            self._all_rows.append((lot, sap, prod, qty, cust, st, wh, updated))

    def set_filter(self, lot: str, status: str, kw: str):
        lot = (lot or "전체").strip()
        status = (status or "전체").strip()
        kw = (kw or "").strip().lower()

        def ok(r):
            r_lot, r_sap, r_prod, r_qty, r_cust, r_st, r_wh, r_upd = r
            if lot != "전체" and r_lot != lot:
                return False
            if status != "전체" and r_st != status:
                return False
            if kw:
                blob = f"{r_lot} {r_sap} {r_prod} {r_cust} {r_st} {r_wh} {r_upd}".lower()
                if kw not in blob:
                    return False
            return True

        self._filtered = [r for r in self._all_rows if ok(r)]
        self.refresh()

    def refresh(self):
        # 테마 변경 시 태그 재적용
        self.apply_tags()

        for iid in self.tree.get_children(""):
            self.tree.delete(iid)

        rows = getattr(self, "_filtered", self._all_rows)
        for r in rows:
            lot, sap, prod, qty, cust, st, wh, upd = r
            self.tree.insert("", "end", values=(lot, sap, prod, qty, cust, st, wh, upd), tags=(st,))


class App:
    def __init__(self):
        # 베이스 테마: 다크는 darkly, 라이트는 flatly로 토글
        self.style = tb.Style(theme="darkly")
        self.theme = PremiumTheme(self.style, start_mode="dark")
        self.theme.apply()

        self.root = self.style.master
        self.root.title("SQM PREMIUM UI v7 (Prototype) - Ruby")
        self.root.geometry("1400x800")
        self.root.configure(bg=self.theme.P["bg"])

        self._build()

    def _build(self):
        # Top
        self.top = TopBar(self.root, self.theme, on_toggle_theme=self.toggle_theme)
        self.top.pack(fill=X)

        # Body layout: sidebar + content
        body = ttk.Frame(self.root)
        body.pack(fill=BOTH, expand=True)

        self.sidebar = SideBar(body)
        self.sidebar.pack(side=LEFT, fill=Y)

        content = ttk.Frame(body)
        content.pack(side=LEFT, fill=BOTH, expand=True)

        # Notebook
        nb = ttk.Notebook(content)
        nb.pack(fill=BOTH, expand=True, padx=8, pady=8)

        tab_inv = ttk.Frame(nb)
        tab_dash = ttk.Frame(nb)
        nb.add(tab_inv, text="재고(메인)")
        nb.add(tab_dash, text="대시보드")

        # Inventory tab: filter + table
        self.filterbar = FilterBar(
            tab_inv,
            on_apply=self.on_apply_filter,
            on_reset=self.on_reset_filter
        )
        self.filterbar.pack(fill=X)

        self.table = MainTable(tab_inv, self.theme)
        self.table.pack(fill=BOTH, expand=True)

        # Dashboard tab: 카드 샘플
        dash = ttk.Frame(tab_dash, padding=16)
        dash.pack(fill=BOTH, expand=True)
        ttk.Label(dash, text="대시보드 (샘플)", font=("Malgun Gothic", 14, "bold")).pack(anchor=W)
        ttk.Label(dash, text="• KPI 카드/알림/작업 큐를 card 톤으로 배치하면 고급스럽게 나옵니다.",
                  style="Muted.TLabel").pack(anchor=W, pady=(8, 0))

        cards = ttk.Frame(dash)
        cards.pack(fill=X, pady=12)
        for title, val in [("판매가능", "1,240 MT"), ("판매배정", "620 MT"), ("출고대기", "180 MT"), ("오늘 처리", "42 건")]:
            c = ttk.Frame(cards, style="Card.TFrame", padding=14)
            c.pack(side=LEFT, padx=8)
            ttk.Label(c, text=title, style="Muted.TLabel").pack(anchor=W)
            ttk.Label(c, text=val, font=("Malgun Gothic", 16, "bold")).pack(anchor=W, pady=(6, 0))

    def on_apply_filter(self):
        lot = self.filterbar.var_lot.get()
        st = self.filterbar.var_status.get()
        kw = self.filterbar.var_kw.get()
        self.table.set_filter(lot, st, kw)

    def on_reset_filter(self):
        self.filterbar.var_lot.set("전체")
        self.filterbar.var_status.set("전체")
        self.filterbar.var_kw.set("")
        self.table.set_filter("전체", "전체", "")

    def toggle_theme(self):
        # ttkbootstrap theme 전환 (기본 스타일 엔진)
        if self.theme.mode == "dark":
            self.style.theme_use("flatly")
        else:
            self.style.theme_use("darkly")

        self.theme.toggle()
        self.root.configure(bg=self.theme.P["bg"])

        # 하위 위젯도 배경이 자연스럽게 보이도록 태그/스타일 재적용
        self.table.apply_tags()
        self.table.refresh()

    def run(self):
        self.root.mainloop()


def main():
    App().run()


if __name__ == "__main__":
    main()
