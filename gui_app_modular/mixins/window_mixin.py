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
        """Load saved window size/position"""
        from ..utils.constants import WINDOW_CONFIG_FILE
        
        try:
            config_file = Path(WINDOW_CONFIG_FILE) if WINDOW_CONFIG_FILE else None
            
            if config_file and config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                width = max(config.get('width', 1200), 900)
                height = max(config.get('height', 800), 600)
                x = config.get('x')
                y = config.get('y')
                
                # Prevent off-screen
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
                
        except (RuntimeError, ValueError) as e:
            logger.warning(f"Window config load failed: {e}")
        
        # Default
        self.root.geometry("1200x800")
    
    def _save_window_config(self) -> None:
        """Save window size/position"""
        from ..utils.constants import WINDOW_CONFIG_FILE
        
        try:
            config_file = Path(WINDOW_CONFIG_FILE) if WINDOW_CONFIG_FILE else None
            
            if not config_file:
                config_file = Path(__file__).parent.parent.parent / "window_config.json"
            
            # Get current geometry
            geometry = self.root.geometry()
            
            # Parse geometry string (e.g., "1200x800+100+50")
            import re
            match = re.match(r'(\d+)x(\d+)\+(-?\d+)\+(-?\d+)', geometry)
            
            if match:
                config = {
                    'width': int(match.group(1)),
                    'height': int(match.group(2)),
                    'x': int(match.group(3)),
                    'y': int(match.group(4)),
                }
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Window config saved: {config}")
                
        except (OSError, IOError, PermissionError) as e:
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
    
    def _center_window(self, window=None) -> None:
        """Center window on screen"""
        target = window or self.root
        
        target.update_idletasks()
        
        width = target.winfo_width()
        height = target.winfo_height()
        screen_width = target.winfo_screenwidth()
        screen_height = target.winfo_screenheight()
        
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        target.geometry(f"+{x}+{y}")
    
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
            
            # Cleanup
            try:
                if hasattr(self, 'engine') and self.engine:
                    self.engine.close()
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(f"Engine close error: {e}")
            
            self.root.destroy()
    
    def _minimize_to_tray(self) -> None:
        """Minimize to system tray (if supported)"""
        try:
            pass
            
            # Create tray icon
            # This is a placeholder - full implementation needs icon file
            self.root.withdraw()
            
        except ImportError:
            # pystray not available, just minimize
            self.root.iconify()
    
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
