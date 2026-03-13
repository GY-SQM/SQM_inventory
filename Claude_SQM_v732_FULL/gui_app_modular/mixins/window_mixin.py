# -*- coding: utf-8 -*-
"""
SQM Inventory - Window Management Mixin
=======================================

v2.9.91 - Extracted from gui_app.py

Window configuration, drag & drop, and UI utilities
"""

import os
import json
import logging
from ..utils.ui_constants import CustomMessageBox
from pathlib import Path

logger = logging.getLogger(__name__)


class WindowMixin:
    """
    Window management mixin
    
    Mixed into SQMInventoryApp class
    """
    
    def _load_window_config(self) -> None:
        """직전 사용한 창 크기/위치 복원. 없으면 기본 크게(1400x900)."""
        from ..utils.constants import WINDOW_CONFIG_FILE
        
        try:
            config_file = Path(WINDOW_CONFIG_FILE) if WINDOW_CONFIG_FILE else None
            if not config_file:
                config_file = Path(__file__).parent.parent.parent / "window_config.json"

            if config_file and config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 최소 크기 적용 (작게 저장된 값 방지)
                width = max(config.get('width', 1400), 1000)
                height = max(config.get('height', 900), 700)
                x = config.get('x')
                y = config.get('y')
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                if x is not None and y is not None:
                    if 0 <= x < screen_width - 100 and 0 <= y < screen_height - 100:
                        self.root.geometry(f"{width}x{height}+{x}+{y}")
                    else:
                        self.root.geometry(f"{width}x{height}")
                else:
                    self.root.geometry(f"{width}x{height}")
                logger.info(f"Window config loaded: {width}x{height}")
                return
        except (RuntimeError, ValueError, OSError) as e:
            logger.warning(f"Window config load failed: {e}")
        # 기본: 직전 크기가 없을 때 크게
        self.root.geometry("1400x900")
    
    def _save_window_config(self) -> None:
        """메인 창 크기/위치 저장. 기존 dialogs 등 다른 키는 유지."""
        from ..utils.constants import WINDOW_CONFIG_FILE
        try:
            from ..utils.ui_constants import load_all_geometry, save_geometry_config
            config_file = Path(WINDOW_CONFIG_FILE) if WINDOW_CONFIG_FILE else None
            if not config_file:
                config_file = Path(__file__).parent.parent.parent / "window_config.json"
            geometry = self.root.geometry()
            import re
            match = re.match(r'(\d+)x(\d+)\+(-?\d+)\+(-?\d+)', geometry)
            if match:
                config = load_all_geometry()
                config['width'] = int(match.group(1))
                config['height'] = int(match.group(2))
                config['x'] = int(match.group(3))
                config['y'] = int(match.group(4))
                save_geometry_config(config)
                logger.info(f"Window config saved: {config.get('width')}x{config.get('height')}")
        except (OSError, IOError, PermissionError, ImportError) as e:
            logger.warning(f"Window config save failed: {e}")
    
    def _setup_drag_drop(self) -> None:
        """Setup drag and drop file handling"""
        try:
            # Try tkinterdnd2
            try:
                from tkinterdnd2 import DND_FILES
                
                self.root.drop_target_register(DND_FILES)
                self.root.dnd_bind('<<Drop>>', self._on_file_drop)
                
                logger.info("Drag & drop enabled (tkinterdnd2)")
                return
            except ImportError as _e:
                logger.debug(f"[window_mixin] 무시: {_e}")
            
            # Fallback: Manual drop handling (Windows only)
            import platform
            if platform.system() == 'Windows':
                try:
                    self._setup_windows_drop()
                    logger.info("Drag & drop enabled (Windows native)")
                except (RuntimeError, ValueError) as e:
                    logger.warning(f"Windows drop setup failed: {e}")
            
        except (RuntimeError, ValueError) as e:
            logger.warning(f"Drag & drop setup failed: {e}")
    
    def _setup_windows_drop(self) -> None:
        """Setup Windows native drag and drop"""
        # Windows 네이티브 드래그&드롭 — windnd 패키지 필요
        logger.debug("Windows native drop: windnd 미설치, 파일 다이얼로그 폴백")
    
    def _on_file_drop(self, event) -> None:
        """Handle dropped files"""
        try:
            # Parse dropped files
            files = event.data
            
            # Handle different formats
            if isinstance(files, str):
                # May be space-separated or brace-enclosed
                if files.startswith('{') and files.endswith('}'):
                    # Brace-enclosed format: {path1} {path2}
                    import re
                    files = re.findall(r'\{([^}]+)\}', files)
                else:
                    files = files.split()
            
            if not files:
                return
            
            # Process each file
            for file_path in files:
                file_path = file_path.strip()
                if not file_path:
                    continue
                
                ext = os.path.splitext(file_path)[1].lower()
                
                if ext == '.pdf':
                    self._log(f"Dropped PDF: {os.path.basename(file_path)}")
                    self._process_inbound(file_path)
                elif ext in ('.xlsx', '.xls'):
                    self._log(f"Dropped Excel: {os.path.basename(file_path)}")
                    self._process_excel_inbound(file_path)
                else:
                    self._log(f"WARNING Unsupported file type: {ext}")
                    
        except (OSError, IOError, PermissionError) as e:
            logger.error(f"File drop error: {e}")
            self._log(f"X File drop error: {e}")
    

    def _on_closing(self) -> None:
        """Handle window close event"""

        
        # Save window config
        self._save_window_config()
        
        # Confirm exit
        if CustomMessageBox.askyesno(self.root, "Exit", "Exit application?"):
            # v3.6.2: 자동 새로고침 타이머 정리
            if hasattr(self, '_stop_auto_refresh'):
                try:
                    self._stop_auto_refresh()
                except (ValueError, TypeError, AttributeError) as e:
                    logger.debug(f"{type(e).__name__}: {e}")
            
            # ② v6.7.1: 프로그램 종료 시 PENDING_APPROVAL 자동 정리
            try:
                if hasattr(self, 'engine') and self.engine and                         hasattr(self.engine, 'clear_pending_allocation_on_exit'):
                    result = self.engine.clear_pending_allocation_on_exit()
                    cleared = result.get('cleared', 0) if isinstance(result, dict) else 0
                    if cleared:
                        logger.info(f"[_on_closing] PENDING_APPROVAL 자동정리: {cleared}건 REJECTED")
            except Exception as _e:
                logger.debug(f"[_on_closing] clear_pending 스킵: {_e}")

            # Cleanup
            # v6.3.5: close_all() 사용 — 모든 스레드 연결 + WAL checkpoint
            # (close()는 메인 스레드만 닫아 WAL 파일이 남을 수 있음)
            try:
                if hasattr(self, 'engine') and self.engine:
                    # 자동 백업 스케줄러 먼저 중지
                    if hasattr(self, 'auto_backup_scheduler') and self.auto_backup_scheduler:
                        try:
                            self.auto_backup_scheduler.stop()
                        except Exception as _e:
                            logger.debug(f"auto_backup stop: {_e}")
                    # close_all: 전체 스레드 연결 + WAL checkpoint(TRUNCATE)
                    if hasattr(self.engine, 'db') and hasattr(self.engine.db, 'close_all'):
                        self.engine.db.close_all()
                        logger.info("[_on_closing] DB close_all 완료")
                    else:
                        self.engine.close()  # fallback
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(f"Engine close error: {e}")
            
            self.root.destroy()
    

    def _show_from_tray(self) -> None:
        """Restore from system tray"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    # v3.6.2: _toggle_fullscreen 제거 (keybindings_mixin.py에서 정의)
    # MRO 충돌 방지
    
    def _setup_window_bindings(self) -> None:
        """Setup window-related key bindings"""
        # Fullscreen toggle (keybindings_mixin에서 F11 바인딩)
        # Close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
