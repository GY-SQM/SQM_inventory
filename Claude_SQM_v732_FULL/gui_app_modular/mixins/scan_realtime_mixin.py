# -*- coding: utf-8 -*-
"""
SQM v7.3.2.1 — 실시간 스캔 대시보드 Mixin
=========================================
행 색상 적용, 알림 배너, 통계 패널, 실시간 업데이트.
"""
import logging
from ..utils.constants import tk
from ..utils.constants import ttk

from ..utils.ui_constants import ThemeColors, Spacing
from ..utils.db_helper import fetchone, fetchall

logger = logging.getLogger(__name__)

_STATUS_TAG_MAP = {
    'SCANNED':   ('scanned',   '#10b981'),
    'OK':        ('ok',        '#10b981'),
    'ERROR':     ('error',     '#ef4444'),
    'DUP':       ('dup',       '#f59e0b'),
    'PENDING':   ('pending',   '#94a3b8'),
    'PICKED':    ('picked',    '#8b5cf6'),
    'AVAILABLE': ('available', '#0ea5e9'),
}


class ScanRealtimeMixin:
    """실시간 스캔 대시보드: 행 색상, 배너, 통계 패널."""

    def _apply_scan_row_color(self, tree, iid, status) -> None:
        """Treeview 행에 상태별 색상 태그 적용."""
        try:
            status_upper = str(status).upper()
            tag_info = _STATUS_TAG_MAP.get(status_upper)
            if not tag_info:
                return
            tag_name, color = tag_info

            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly'))
            fg = '#ffffff' if is_dark else '#1e293b'

            # 태그 등록 (존재하면 덮어쓰기)
            try:
                tree.tag_configure(tag_name, foreground=color)
            except Exception:
                pass

            # 행에 태그 적용
            existing = list(tree.item(iid, 'tags') or ())
            if tag_name not in existing:
                existing.append(tag_name)
            tree.item(iid, tags=tuple(existing))

        except Exception as e:
            logger.debug(f"_apply_scan_row_color: {e}")

    def _show_scan_alert_banner(self, parent=None, msg="",
                                 level="error") -> None:
        """자동 제거 알림 배너 (5초)."""
        try:
            target = parent or getattr(self, 'root', None)
            if not target:
                return

            colors = {
                'error':   '#ef4444',
                'warn':    '#f59e0b',
                'success': '#10b981',
                'info':    '#0ea5e9',
            }
            bg = colors.get(level, '#ef4444')
            fg = '#ffffff'

            banner = tk.Frame(target, bg=bg, height=32)
            banner.pack(fill=tk.X, side=tk.TOP, padx=0, pady=0)
            banner.pack_propagate(False)

            tk.Label(banner, text=f"  {msg}", font=('맑은 고딕', 10, 'bold'),
                     fg=fg, bg=bg).pack(side=tk.LEFT, padx=Spacing.SM)

            close_lbl = tk.Label(banner, text="  X  ",
                                  font=('맑은 고딕', 9, 'bold'),
                                  fg=fg, bg=bg, cursor='hand2')
            close_lbl.pack(side=tk.RIGHT, padx=4)
            close_lbl.bind('<Button-1>', lambda e: banner.destroy())

            # 5초 후 자동 제거
            target.after(5000, lambda: banner.destroy()
                         if banner.winfo_exists() else None)

        except Exception as e:
            logger.debug(f"_show_scan_alert_banner: {e}")

    def _build_scan_realtime_panel(self, parent) -> dict:
        """실시간 통계 패널 빌드. 진행률 바 + 피드."""
        refs = {}
        try:
            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly'))
            bg = ThemeColors.get('bg_primary', is_dark)
            card_bg = ThemeColors.get('bg_card', is_dark)
            fg = ThemeColors.get('text_primary', is_dark)
            fg2 = ThemeColors.get('text_secondary', is_dark)
            accent = ThemeColors.get('primary', is_dark)

            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, padx=Spacing.SM, pady=Spacing.SM)

            # 통계 카드
            stats_f = tk.Frame(frame, bg=card_bg, relief='groove', bd=1,
                               padx=12, pady=8)
            stats_f.pack(fill=tk.X, pady=Spacing.XS)

            stat_labels = {}
            for idx, (key, label, default) in enumerate([
                ('total_scan', '총 스캔', '0'),
                ('ok_count', '성공', '0'),
                ('err_count', '오류', '0'),
                ('progress', '진행률', '0%'),
            ]):
                col_f = tk.Frame(stats_f, bg=card_bg)
                col_f.pack(side=tk.LEFT, expand=True, padx=8)
                tk.Label(col_f, text=label, font=('맑은 고딕', 9),
                         fg=fg2, bg=card_bg).pack()
                val_lbl = tk.Label(col_f, text=default,
                                    font=('맑은 고딕', 14, 'bold'),
                                    fg=fg, bg=card_bg)
                val_lbl.pack()
                stat_labels[key] = val_lbl

            refs['stat_labels'] = stat_labels

            # 진행률 바
            progress_bar = ttk.Progressbar(frame, maximum=100, value=0,
                                           length=300)
            progress_bar.pack(fill=tk.X, padx=Spacing.SM, pady=Spacing.XS)
            refs['progress_bar'] = progress_bar

            # 피드 (최근 스캔)
            feed_frame = ttk.Frame(frame)
            feed_frame.pack(fill=tk.X, pady=Spacing.XS)

            feed_cols = [
                ('time', '시간', 70, 'center'),
                ('barcode', '바코드', 120, 'center'),
                ('status', '결과', 80, 'center'),
            ]
            fcols = [c[0] for c in feed_cols]
            feed_tree = ttk.Treeview(feed_frame, columns=fcols,
                                      show='headings', height=5,
                                      selectmode='none')
            for col_id, label, width, anchor in feed_cols:
                feed_tree.heading(col_id, text=label)
                feed_tree.column(col_id, width=width, anchor=anchor)
            feed_tree.pack(fill=tk.X)

            feed_tree.tag_configure('ok', foreground='#10b981')
            feed_tree.tag_configure('err', foreground='#ef4444')
            refs['feed_tree'] = feed_tree

            refs['root'] = frame

        except Exception as e:
            logger.error(f"_build_scan_realtime_panel 오류: {e}")

        return refs

    def _update_scan_realtime(self, lot_no="") -> None:
        """DB에서 스캔 통계 업데이트."""
        try:
            refs = getattr(self, '_scan_realtime_refs', None)
            if not refs:
                return

            stat_labels = refs.get('stat_labels', {})
            progress_bar = refs.get('progress_bar')
            feed_tree = refs.get('feed_tree')

            # picking_table에서 대상 수 조회
            expected = 0
            if lot_no:
                row = fetchone(self,
                    "SELECT COUNT(*) AS cnt FROM picking_table "
                    "WHERE lot_no = ? AND status = 'ACTIVE'",
                    (lot_no,))
                expected = int(row['cnt']) if row else 0

            # outbound_scan_log에서 스캔 수 조회
            where = "WHERE lot_no = ?" if lot_no else ""
            params = (lot_no,) if lot_no else ()

            total_row = fetchone(self,
                f"SELECT COUNT(*) AS cnt FROM outbound_scan_log {where}",
                params)
            total_scan = int(total_row['cnt']) if total_row else 0

            ok_row = fetchone(self,
                f"SELECT COUNT(*) AS cnt FROM outbound_scan_log "
                f"{where + ' AND' if where else 'WHERE'} status = 'SCANNED'",
                params)
            ok_count = int(ok_row['cnt']) if ok_row else 0

            err_count = total_scan - ok_count
            pct = (ok_count / expected * 100) if expected > 0 else 0

            # 라벨 업데이트
            if 'total_scan' in stat_labels:
                stat_labels['total_scan'].config(text=str(total_scan))
            if 'ok_count' in stat_labels:
                stat_labels['ok_count'].config(text=str(ok_count))
            if 'err_count' in stat_labels:
                stat_labels['err_count'].config(text=str(err_count))
            if 'progress' in stat_labels:
                stat_labels['progress'].config(text=f"{pct:.0f}%")

            if progress_bar:
                progress_bar.config(value=min(pct, 100))

            # 피드 업데이트
            if feed_tree:
                for item in feed_tree.get_children(''):
                    feed_tree.delete(item)
                recent = fetchall(self,
                    f"SELECT scan_time, tonbag_uid, status "
                    f"FROM outbound_scan_log {where} "
                    f"ORDER BY scan_time DESC LIMIT 5",
                    params)
                for r in (recent or []):
                    tag = 'ok' if r.get('status') == 'SCANNED' else 'err'
                    t = str(r.get('scan_time', ''))[-8:]
                    feed_tree.insert('', 'end',
                                     values=(t, r.get('tonbag_uid', ''),
                                             r.get('status', '')),
                                     tags=(tag,))

        except Exception as e:
            logger.debug(f"_update_scan_realtime: {e}")
