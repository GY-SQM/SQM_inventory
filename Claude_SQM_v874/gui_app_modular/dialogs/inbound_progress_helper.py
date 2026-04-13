"""Inbound progress helper mixin extracted from onestop_inbound."""

import logging
import time
import tkinter as tk


logger = logging.getLogger(__name__)
PROGRESS_POPUP_CLOSE_DELAY_MS = 1600


class InboundProgressHelper:
    """진행 표시 헬퍼 클래스 — Mixin"""

    def _build_inbound_progress_frame(self, main) -> None:
        """진행 상태 프레임 (⏱ 파싱 진행 표시)."""
        self._build_inbound_progress_frame_impl(main)

    def _build_inbound_progress_frame_impl(self, main) -> None:
        """진행 프레임 본문은 기존 create_dialog 흐름에서 구성됨."""
        pass

    def _show_progress_inline(self) -> None:
        """진행 상태를 미리보기 위 인라인 영역에만 표시 (팝업 없음)."""
        ph = getattr(self, '_progress_inline_placeholder', None)
        fr = getattr(self, '_progress_inline_frame', None)
        if ph and ph.winfo_ismapped():
            ph.pack_forget()
        if fr:
            fr.pack(fill=tk.X)
        self._progress_start_time = time.time()
        if getattr(self, '_progress_inline_bar', None):
            self._progress_inline_bar['value'] = 0
        if getattr(self, '_progress_inline_msg', None):
            self._progress_inline_msg.config(text="준비 중...")
        if getattr(self, '_progress_inline_pct_elapsed', None):
            self._progress_inline_pct_elapsed.config(text="0%  ·  경과: 0:00")
        if getattr(self, '_progress_inline_busy', None):
            self._progress_inline_busy.config(text="진행 중 ●")
            self._progress_inline_busy.place(relx=0, rely=0.5, anchor='w')
        self._start_progress_elapsed_tick()
        self._start_progress_busy_animation()

    def _hide_progress_inline(self) -> None:
        """진행 완료 후 인라인 영역을 플레이스홀더로 복귀."""
        fr = getattr(self, '_progress_inline_frame', None)
        ph = getattr(self, '_progress_inline_placeholder', None)
        if fr and fr.winfo_ismapped():
            fr.pack_forget()
        if ph:
            ph.pack(anchor='w')

    def _show_progress_popup(self) -> None:
        """작업진행 전용 창 사용 안 함 — 인라인 진행만 사용."""

    def _progress_elapsed_tick(self) -> None:
        """경과 시간 표시 업데이트 (1초 간격)."""
        start = getattr(self, '_progress_start_time', None)
        if start is None:
            self._progress_elapsed_job = self.dialog.after(1000, self._progress_elapsed_tick) if self.dialog and self.dialog.winfo_exists() else None
            return
        secs = int(time.time() - start)
        if secs >= 3600:
            h, r = divmod(secs, 3600)
            m, s = divmod(r, 60)
            elapsed_text = f"경과: {h}:{m:02d}:{s:02d}"
        else:
            m, s = divmod(secs, 60)
            elapsed_text = f"경과: {m}:{s:02d}"
        pct_elapsed = getattr(self, '_progress_inline_pct_elapsed', None)
        if pct_elapsed and pct_elapsed.winfo_ismapped():
            pct = getattr(self, 'progress_var', None)
            pct_val = int(pct.get()) if pct else 0
            pct_elapsed.config(text=f"{pct_val}%  ·  {elapsed_text}")
        self._progress_elapsed_job = self.dialog.after(1000, self._progress_elapsed_tick) if self.dialog and self.dialog.winfo_exists() else None

    def _start_progress_elapsed_tick(self) -> None:
        """경과 시간 타이머 시작."""
        self._progress_elapsed_job = None
        if self.dialog and self.dialog.winfo_exists():
            self._progress_elapsed_job = self.dialog.after(1000, self._progress_elapsed_tick)

    def _stop_progress_elapsed_tick(self) -> None:
        """경과 시간 타이머 중지."""
        if getattr(self, '_progress_elapsed_job', None):
            try:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after_cancel(self._progress_elapsed_job)
            except (tk.TclError, ValueError) as e:
                logger.debug(f"Suppressed: {e}")
        self._progress_elapsed_job = None

    def _progress_busy_tick(self) -> None:
        """진행 중 움직임 표시 — 인라인 진행 상태에만 표시."""
        phase = getattr(self, '_progress_busy_phase', 0) % 4
        self._progress_busy_phase = phase + 1
        texts = ['진행 중 ●  ', '진행 중 ●● ', '진행 중 ●●●', '진행 중 ●● ']
        inline_busy = getattr(self, '_progress_inline_busy', None)
        if inline_busy and inline_busy.winfo_ismapped():
            inline_busy.config(text=texts[phase])
        self._progress_busy_job = self.dialog.after(400, self._progress_busy_tick) if self.dialog and self.dialog.winfo_exists() else None

    def _start_progress_busy_animation(self) -> None:
        self._progress_busy_phase = 0
        if self.dialog and self.dialog.winfo_exists():
            self._progress_busy_job = self.dialog.after(400, self._progress_busy_tick)

    def _stop_progress_busy_animation(self) -> None:
        if getattr(self, '_progress_busy_job', None):
            try:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after_cancel(self._progress_busy_job)
            except (tk.TclError, ValueError):
                logger.debug("[SUPPRESSED] exception in inbound_progress_helper.py")
        self._progress_busy_job = None

    def _hide_progress_popup(self) -> None:
        """진행률 팝업 닫기."""
        self._stop_progress_busy_animation()
        self._stop_progress_elapsed_tick()
        try:
            if getattr(self, '_progress_popup', None) and self._progress_popup.winfo_exists():
                self._progress_popup.destroy()
        except Exception as e:
            logger.debug(f"Suppressed: {e}")
        self._progress_popup = None
        self._progress_popup_label = None
        self._progress_popup_bar = None
        self._progress_popup_pct = None
        self._progress_popup_busy = None
        self._progress_popup_elapsed = None

    def _update_progress(self, pct: int, message: str):
        """프로그레스 바 업데이트 (스레드 안전)."""

        def _update():
            self.progress_var.set(pct)
            self.status_var.set(message)
            if message.strip() and getattr(self, '_log', None):
                try:
                    self._log(message)
                except (RuntimeError, ValueError):
                    logger.info(message)
            bar = getattr(self, '_progress_popup_bar', None)
            if bar and bar.winfo_exists():
                bar['value'] = max(0, min(100, pct))
                if self._progress_popup_label:
                    self._progress_popup_label.config(text=message)
                if getattr(self, '_progress_popup_pct', None):
                    self._progress_popup_pct.config(text=f"{pct}%" if pct >= 0 else "—")
            inline_bar = getattr(self, '_progress_inline_bar', None)
            inline_msg = getattr(self, '_progress_inline_msg', None)
            inline_busy = getattr(self, '_progress_inline_busy', None)
            if inline_bar and inline_bar.winfo_ismapped():
                inline_bar['value'] = max(0, min(100, pct))
            if inline_busy and inline_busy.winfo_ismapped():
                relx = max(0, min(1.0, pct / 100.0))
                if relx > 0.92:
                    relx = 0.92
                inline_busy.place(relx=relx, rely=0.5, anchor='w')
            if inline_msg and inline_msg.winfo_ismapped():
                inline_msg.config(text=message)
            if pct >= 100 or (pct == 0 and message.strip().startswith("❌")):
                self._stop_progress_busy_animation()
                if inline_busy and inline_busy.winfo_ismapped():
                    inline_busy.config(text="완료" if pct >= 100 else "오류")
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after(PROGRESS_POPUP_CLOSE_DELAY_MS, self._hide_progress_popup)
                    self.dialog.after(PROGRESS_POPUP_CLOSE_DELAY_MS + 100, self._hide_progress_inline)

        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, _update)
