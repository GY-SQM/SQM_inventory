# -*- coding: utf-8 -*-
"""
SQM Inventory - Ops Center KPI Dashboard Mixin
================================================

v7.3.2 - Real-time KPI card panels for operational overview.

Provides three horizontally arranged metric cards:
  1. 재고 현황  (Inventory status — AVAILABLE / RESERVED / PICKED counts)
  2. 출고 흐름  (Outbound flow — SOLD / today's outbound / total outbound)
  3. 위치 관리  (Location mgmt — assigned / unassigned / coverage %)

Plus a bottleneck alert label that warns when PICKED or RESERVED
counts exceed thresholds.

Usage:
    class SQMInventoryApp(OpsCenterMixin, ...):
        def _setup_dashboard_tab(self):
            self._build_ops_center(self.tab_dashboard)
            ...
        def _refresh_dashboard(self):
            self._refresh_ops_center()
"""

import logging
import tkinter as tk
from tkinter import ttk

from ..utils.ui_constants import ThemeColors, Spacing
from ..utils.db_helper import fetchall

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Card accent colors
# ─────────────────────────────────────────────────────────────
_CARD_ACCENTS = {
    'inventory': {True: '#f59e0b', False: '#d97706'},   # amber
    'outbound':  {True: '#10b981', False: '#059669'},    # green
    'location':  {True: '#8b5cf6', False: '#7c3aed'},    # purple
}


class OpsCenterMixin:
    """KPI dashboard card panels mixin.

    Mixed into ``SQMInventoryApp``.  Call ``_build_ops_center(parent)``
    during dashboard tab setup, then ``_refresh_ops_center()`` whenever
    data should be refreshed.

    Attributes written
    ------------------
    _ops_refs : dict
        Nested dict of label widget references for each metric.
        Structure::

            {
                'inv_available': tk.Label,
                'inv_reserved':  tk.Label,
                'inv_picked':    tk.Label,
                'out_sold':      tk.Label,
                'out_today':     tk.Label,
                'out_total':     tk.Label,
                'loc_assigned':  tk.Label,
                'loc_none':      tk.Label,
                'loc_coverage':  tk.Label,
            }

    _ops_bottleneck_lbl : tk.Label
        Alert label shown below the cards.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _build_ops_center(self, parent) -> None:
        """Create three KPI card panels arranged horizontally.

        Parameters
        ----------
        parent : tk.Widget
            Parent frame (typically ``self.tab_dashboard``).
        """
        try:
            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly')
            )
            palette = ThemeColors.get_palette(is_dark)
            self._ops_refs = {}

            # Outer container
            ops_frame = tk.Frame(parent, bg=palette['bg_primary'])
            ops_frame.pack(fill='x', padx=Spacing.MD, pady=(Spacing.MD, Spacing.SM))

            # Three equal-width columns
            ops_frame.columnconfigure(0, weight=1)
            ops_frame.columnconfigure(1, weight=1)
            ops_frame.columnconfigure(2, weight=1)

            # --- Card 1: 재고 현황 (amber) ---
            self._build_kpi_card(
                ops_frame,
                col=0,
                title="재고 현황",
                accent_key='inventory',
                metrics=[
                    ('inv_available', '판매가능 (AVAILABLE)'),
                    ('inv_reserved',  '판매배정 (RESERVED)'),
                    ('inv_picked',    '화물결정 (PICKED)'),
                ],
                palette=palette,
                is_dark=is_dark,
            )

            # --- Card 2: 출고 흐름 (green) ---
            self._build_kpi_card(
                ops_frame,
                col=1,
                title="출고 흐름",
                accent_key='outbound',
                metrics=[
                    ('out_sold',  '출고완료 (SOLD)'),
                    ('out_today', '금일 출고'),
                    ('out_total', '누적 출고'),
                ],
                palette=palette,
                is_dark=is_dark,
            )

            # --- Card 3: 위치 관리 (purple) ---
            self._build_kpi_card(
                ops_frame,
                col=2,
                title="위치 관리",
                accent_key='location',
                metrics=[
                    ('loc_assigned', '위치 지정'),
                    ('loc_none',     '미지정'),
                    ('loc_coverage', '커버리지'),
                ],
                palette=palette,
                is_dark=is_dark,
            )

            # --- Bottleneck alert ---
            self._ops_bottleneck_lbl = tk.Label(
                parent,
                text="",
                font=('맑은 고딕', 10),
                fg=palette.get('warning', '#f59e0b'),
                bg=palette['bg_primary'],
                anchor='w',
            )
            self._ops_bottleneck_lbl.pack(
                fill='x', padx=Spacing.MD, pady=(0, Spacing.SM)
            )

            logger.info("[ops_center] KPI 카드 빌드 완료")

        except Exception as exc:
            logger.error(f"[ops_center] _build_ops_center 실패: {exc}", exc_info=True)

    # ------------------------------------------------------------------
    # Internal: card builder
    # ------------------------------------------------------------------

    def _build_kpi_card(
        self,
        parent,
        col: int,
        title: str,
        accent_key: str,
        metrics: list,
        palette: dict,
        is_dark: bool,
    ) -> None:
        """Build a single KPI card with an accent top bar and metric rows.

        Parameters
        ----------
        parent : tk.Frame
            Grid parent.
        col : int
            Column index in parent grid.
        title : str
            Card title (Korean).
        accent_key : str
            Key into ``_CARD_ACCENTS`` dict.
        metrics : list[tuple[str, str]]
            List of ``(ref_key, display_label)`` for each metric row.
        palette : dict
            ThemeColors palette.
        is_dark : bool
            Current theme darkness flag.
        """
        try:
            accent_color = _CARD_ACCENTS.get(accent_key, {}).get(is_dark, '#10b981')
            card_bg = palette.get('bg_card', '#ffffff' if not is_dark else '#1e293b')
            border_color = palette.get('border', '#e2e8f0')

            # Card outer (with border effect)
            card_outer = tk.Frame(
                parent,
                bg=border_color,
                padx=1,
                pady=1,
            )
            card_outer.grid(
                row=0, column=col, sticky='nsew',
                padx=(0 if col == 0 else Spacing.SM, 0),
            )

            card = tk.Frame(card_outer, bg=card_bg)
            card.pack(fill='both', expand=True)

            # Accent top bar (4px)
            accent_bar = tk.Frame(card, bg=accent_color, height=4)
            accent_bar.pack(fill='x')
            accent_bar.pack_propagate(False)

            # Title
            title_lbl = tk.Label(
                card,
                text=title,
                font=('맑은 고딕', 12, 'bold'),
                fg=palette.get('text_primary', '#1e293b'),
                bg=card_bg,
                anchor='w',
            )
            title_lbl.pack(fill='x', padx=Spacing.MD, pady=(Spacing.SM, Spacing.XS))

            # Separator under title
            tk.Frame(card, bg=border_color, height=1).pack(
                fill='x', padx=Spacing.SM
            )

            # Metric rows
            for ref_key, display_label in metrics:
                row_frame = tk.Frame(card, bg=card_bg)
                row_frame.pack(fill='x', padx=Spacing.MD, pady=(Spacing.XS, 0))

                # Label (left)
                tk.Label(
                    row_frame,
                    text=display_label,
                    font=('맑은 고딕', 9),
                    fg=palette.get('text_secondary', '#64748b'),
                    bg=card_bg,
                    anchor='w',
                ).pack(side='left')

                # Value (right, large bold)
                value_lbl = tk.Label(
                    row_frame,
                    text="--",
                    font=('맑은 고딕', 16, 'bold'),
                    fg=palette.get('text_primary', '#1e293b'),
                    bg=card_bg,
                    anchor='e',
                )
                value_lbl.pack(side='right')

                self._ops_refs[ref_key] = value_lbl

            # Bottom padding
            tk.Frame(card, bg=card_bg, height=Spacing.SM).pack(fill='x')

        except Exception as exc:
            logger.error(
                f"[ops_center] _build_kpi_card 실패 ({title}): {exc}",
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------

    def _refresh_ops_center(self) -> None:
        """Query inventory table and update all KPI labels.

        Uses ``GROUP BY status`` for efficient single-pass counting.
        Also computes location coverage and sets bottleneck alerts.
        """
        try:
            if not hasattr(self, '_ops_refs') or not self._ops_refs:
                return

            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly')
            )
            palette = ThemeColors.get_palette(is_dark)

            # ── 1. Status counts (inventory_tonbag) ──
            status_counts = {'AVAILABLE': 0, 'RESERVED': 0, 'PICKED': 0, 'SOLD': 0, 'OUTBOUND': 0}
            try:
                rows = fetchall(
                    self,
                    """
                    SELECT UPPER(TRIM(status)) AS st, COUNT(*) AS cnt
                    FROM inventory_tonbag
                    WHERE COALESCE(is_sample, 0) = 0
                    GROUP BY UPPER(TRIM(status))
                    """,
                )
                for row in rows:
                    st = (row.get('st') or '').upper()
                    cnt = int(row.get('cnt') or 0)
                    if st in status_counts:
                        status_counts[st] += cnt
            except Exception as exc:
                logger.warning(f"[ops_center] status count 조회 실패: {exc}")

            # Card 1 values
            avail_count = status_counts.get('AVAILABLE', 0)
            reserved_count = status_counts.get('RESERVED', 0)
            picked_count = status_counts.get('PICKED', 0)

            self._ops_set_value('inv_available', f"{avail_count:,}")
            self._ops_set_value('inv_reserved', f"{reserved_count:,}")
            self._ops_set_value('inv_picked', f"{picked_count:,}")

            # ── 2. Outbound flow ──
            sold_count = status_counts.get('SOLD', 0) + status_counts.get('OUTBOUND', 0)
            self._ops_set_value('out_sold', f"{sold_count:,}")

            # Today's outbound
            today_out = 0
            try:
                row = fetchall(
                    self,
                    """
                    SELECT COUNT(*) AS cnt
                    FROM inventory_tonbag
                    WHERE UPPER(TRIM(status)) IN ('SOLD', 'OUTBOUND')
                      AND DATE(updated_at) = DATE('now', 'localtime')
                    """,
                )
                if row and len(row) > 0:
                    today_out = int(row[0].get('cnt', 0))
            except Exception as exc:
                logger.debug(f"[ops_center] 금일 출고 조회: {exc}")

            self._ops_set_value('out_today', f"{today_out:,}")

            # Total outbound (all time)
            total_out = sold_count
            self._ops_set_value('out_total', f"{total_out:,}")

            # ── 3. Location management ──
            loc_assigned = 0
            loc_none = 0
            try:
                loc_rows = fetchall(
                    self,
                    """
                    SELECT
                        SUM(CASE WHEN COALESCE(TRIM(location), '') != '' THEN 1 ELSE 0 END) AS assigned,
                        SUM(CASE WHEN COALESCE(TRIM(location), '') = '' THEN 1 ELSE 0 END) AS unassigned
                    FROM inventory_tonbag
                    WHERE COALESCE(is_sample, 0) = 0
                      AND UPPER(TRIM(status)) IN ('AVAILABLE', 'RESERVED', 'PICKED')
                    """,
                )
                if loc_rows and len(loc_rows) > 0:
                    loc_assigned = int(loc_rows[0].get('assigned') or 0)
                    loc_none = int(loc_rows[0].get('unassigned') or 0)
            except Exception as exc:
                logger.debug(f"[ops_center] 위치 조회: {exc}")

            self._ops_set_value('loc_assigned', f"{loc_assigned:,}")
            self._ops_set_value('loc_none', f"{loc_none:,}")

            # Coverage %
            total_loc = loc_assigned + loc_none
            if total_loc > 0:
                coverage_pct = (loc_assigned / total_loc) * 100
                self._ops_set_value('loc_coverage', f"{coverage_pct:.1f}%")
            else:
                self._ops_set_value('loc_coverage', "N/A")

            # ── 4. Bottleneck alert ──
            self._update_ops_bottleneck(picked_count, reserved_count, palette)

            logger.debug(
                f"[ops_center] 새로고침 완료: AVAIL={avail_count}, "
                f"RESERVED={reserved_count}, PICKED={picked_count}, SOLD={sold_count}"
            )

        except Exception as exc:
            logger.error(f"[ops_center] _refresh_ops_center 실패: {exc}", exc_info=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ops_set_value(self, ref_key: str, text: str) -> None:
        """Safely set a KPI label's text.

        Parameters
        ----------
        ref_key : str
            Key in ``self._ops_refs``.
        text : str
            Display value.
        """
        try:
            lbl = self._ops_refs.get(ref_key)
            if lbl is not None:
                lbl.configure(text=text)
        except (tk.TclError, AttributeError) as exc:
            logger.debug(f"[ops_center] _ops_set_value({ref_key}): {exc}")

    def _update_ops_bottleneck(
        self, picked: int, reserved: int, palette: dict
    ) -> None:
        """Update the bottleneck alert label based on threshold rules.

        Rules:
        - PICKED > 5  : warning (amber)  -- "화물결정 적체 주의"
        - RESERVED > 10: info (blue)      -- "배정 대기 많음"
        - Otherwise    : clear

        Parameters
        ----------
        picked : int
            Current PICKED count.
        reserved : int
            Current RESERVED count.
        palette : dict
            ThemeColors palette.
        """
        try:
            if not hasattr(self, '_ops_bottleneck_lbl') or self._ops_bottleneck_lbl is None:
                return

            if picked > 5:
                self._ops_bottleneck_lbl.configure(
                    text=f"\u26a0  화물결정 적체 주의: PICKED {picked:,}건 (기준 5건 초과)",
                    fg=palette.get('warning', '#f59e0b'),
                )
            elif reserved > 10:
                self._ops_bottleneck_lbl.configure(
                    text=f"\u2139  배정 대기 많음: RESERVED {reserved:,}건 (기준 10건 초과)",
                    fg=palette.get('info', '#0ea5e9'),
                )
            else:
                self._ops_bottleneck_lbl.configure(text="", fg=palette.get('text_muted', '#94a3b8'))

        except (tk.TclError, AttributeError) as exc:
            logger.debug(f"[ops_center] _update_ops_bottleneck: {exc}")
