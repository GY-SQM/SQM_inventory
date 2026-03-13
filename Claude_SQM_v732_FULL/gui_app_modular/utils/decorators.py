# -*- coding: utf-8 -*-
"""
SQM v7.3.2 — 공통 데코레이터
================================
· safe_call    : 예외를 logger.error로 잡고 None 반환
· db_operation : DB 작업용 예외 핸들러 + 로깅
· ui_action    : UI 동작용 예외 핸들러 (messagebox fallback)

사용법:
  from gui_app_modular.utils.decorators import safe_call, db_operation, ui_action

  @safe_call
  def _update_status_label(self):
      ...

  @db_operation
  def _save_to_db(self, data):
      ...

  @ui_action("입고 오류")
  def _on_inbound_click(self):
      ...
"""
import functools
import logging
import tkinter.messagebox as _mb

logger = logging.getLogger(__name__)


def safe_call(func):
    """예외를 조용히 잡고 None 반환. 내부 헬퍼 함수에 사용."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.error(f"{func.__qualname__} 오류: {exc}", exc_info=True)
            return None
    return wrapper


def db_operation(func):
    """DB 작업: 오류 시 logger.error + False 반환."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.error(f"[DB] {func.__qualname__}: {exc}", exc_info=True)
            return False
    return wrapper


def ui_action(title: str = "오류"):
    """UI 동작: 오류 시 messagebox.showerror + None 반환."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:
                logger.error(f"[UI] {func.__qualname__}: {exc}", exc_info=True)
                try:
                    root = getattr(self, "root", None)
                    _mb.showerror(
                        title,
                        f"예기치 않은 오류가 발생했습니다.\n{exc}",
                        parent=root,
                    )
                except Exception:
                    pass
                return None
        return wrapper
    return decorator
