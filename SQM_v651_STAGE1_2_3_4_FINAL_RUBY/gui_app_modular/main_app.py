# -*- coding: utf-8 -*-
from .utils.custom_messagebox import CustomMessageBox
"""
SQM Inventory - Main Application Class
======================================

v2.9.91 - Modular GUI Application

This module combines all mixins and tabs to create the main application.
"""

import os
import sqlite3
import sys
import logging
from pathlib import Path
from typing import Optional
import configparser  # v5.3.3

# Setup logging
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class SQMInventoryApp:
    """
    Main SQM Inventory Application
    
    Combines all GUI components through mixins:
    - MenuMixin: Menu bar setup
    - ToolbarMixin: Toolbar buttons
    - RefreshMixin: Data refresh functions
    - WindowMixin: Window management
    - ValidationMixin: Data validation
    - KeyBindingsMixin: Keyboard shortcuts
    - ContextMenuMixin: Right-click menus
    - FeaturesV2Mixin: Extended features (v2.7+)
    """
    
    def __init__(self, root=None, db_path: Optional[str] = None):
        """
        Initialize application
        
        Args:
            root: Tkinter root window (created if None)
            db_path: Database path (uses default if None)
        """
        # Import GUI libraries
        from .utils.constants import tk, ttk, HAS_TTKBOOTSTRAP
        
        # Create or use provided root
        if root is None:
            if HAS_TTKBOOTSTRAP:
                import ttkbootstrap as ttk_bs
                theme = self._load_theme_preference()
                # ★ v6.3.2-v5: ttkbootstrap primary 색상 소스 수정
                # Window 생성 전에 STANDARD_THEMES를 수정하면
                # 모든 위젯에 자동으로 새 색상이 적용됨
                try:
                    from ttkbootstrap.themes.standard import STANDARD_THEMES
                    _gy_colors = {
                        'primary':   '#10B981',   # 딥 에메랄드 (세련된 녹색)
                        'secondary': '#64748b',   # 슬레이트
                        'success':   '#10b981',   # 에메랄드
                        'info':      '#0ea5e9',   # 스카이 블루
                        'warning':   '#f59e0b',   # 앰버
                        'danger':    '#ef4444',   # 레드
                        'light':     '#cbd5e1',
                        'dark':      '#0f172a',   # 딥 네이비
                        'bg':        '#0b1120',   # 딥 네이비 블랙
                        'fg':        '#e2e8f0',   # 밝은 슬레이트
                        'selectbg':  '#1d4ed8',   # 다크 블루
                        'selectfg':  '#ffffff',
                        'border':    '#1e3a5f',   # 네이비 보더
                        'inputfg':   '#ffffff',
                        'inputbg':   '#111827',   # 네이비 입력 배경
                        'active':    '#1e293b',   # 네이비 액티브
                    }
                    if theme in STANDARD_THEMES:
                        STANDARD_THEMES[theme]['colors'].update(_gy_colors)
                except Exception as _e:
                    import logging
                    logging.getLogger(__name__).debug(f"Theme color override: {_e}")
                self.root = ttk_bs.Window(themename=theme)
            else:
                self.root = tk.Tk()
        else:
            self.root = root
        
        # v4.0.0 Q10: 창 제목에 버전 + 회사명
        try:
            from version import __version__, APP_NAME
            self.root.title(f"(주)지와이로지스 — {APP_NAME} v{__version__}")
        except ImportError:
            self.root.title("(주)지와이로지스 — SQM 재고관리 v4.0.0")
        
        # Store references
        self.tk = tk
        self.ttk = ttk
        self.db_path = db_path
        
        # Initialize state variables
        self._init_state()
        
        # v3.6.5: 가독성 스타일 적용 (테마 인식)
        try:
            from .utils.ui_constants import ReadableStyle, apply_contrast_scrollbar_style, init_ui_system
            init_ui_system(self.root)
            ReadableStyle.apply(self.root, self.current_theme)
            apply_contrast_scrollbar_style(self.root, self.current_theme)
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.debug(f"ReadableStyle init: {e}")
        
        # v4.19.1: 전역 Treeview 스타일 적용
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from fixes.global_tree_style import apply_global_tree_style
            apply_global_tree_style()
            logger.info("✅ 전역 Treeview 스타일 적용 완료")
        except ImportError as e:
            logger.debug(f"전역 스타일 로딩 실패 (무시): {e}")
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
            logger.warning(f"전역 스타일 적용 실패: {e}")
        
        # Initialize engine
        self._init_engine()
        
        # v5.0.3: 시작 시 DB 검증 및 자동 복구
        try:
            from utils.backup_validator import AutoRecovery
            
            backup_dir = os.path.join('data', 'db', 'backups')
            auto_recovery = AutoRecovery(self.db_path or 'data/db/sqm_inventory.db', backup_dir)
            
            recovered, message = auto_recovery.check_and_recover()
            
            if recovered:
                logger.warning(f"🔧 자동 복구 실행됨: {message}")
                # 복구 후 엔진 재초기화
                self._init_engine()
        except ImportError:
            logger.debug("자동 복구 모듈 없음 (무시)")
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
            logger.error(f"자동 복구 오류: {e}")
        
        # Setup UI
        self._setup_ui()
        # 전역 자동 툴팁: 메뉴/팝업/버튼에 120자 이내 안내 자동 부착
        try:
            from .utils.auto_tooltip import install_global_auto_tooltips
            install_global_auto_tooltips(self.root)
            logger.info("✅ 전역 자동 툴팁 적용 완료")
        except ImportError as e:
            logger.debug(f"전역 자동 툴팁 로딩 실패 (무시): {e}")
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
            logger.warning(f"전역 자동 툴팁 적용 실패: {e}")

        # v6.2.3: 전역 Editable Treeview 바인딩 (Ctrl+C/X/V, Delete, 더블클릭 편집)
        try:
            from .utils.global_editable_tree import install_global_editable_tree
            install_global_editable_tree(self.root)
            logger.info("✅ 전역 Editable Treeview 적용 완료")
        except ImportError as e:
            logger.debug(f"전역 Editable Treeview 로딩 실패 (무시): {e}")
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
            logger.warning(f"전역 Editable Treeview 적용 실패: {e}")

        # 전역 순번 열: 모든 표(Treeview)에 '순번' 자동 표시
        try:
            from .utils.global_row_number_tree import install_global_row_number_tree
            install_global_row_number_tree(self.root)
            logger.info("✅ 전역 순번 열 적용 완료")
        except (ImportError, ValueError, TypeError, KeyError, AttributeError, OSError) as e:
            logger.warning(f"전역 순번 열 적용 실패: {e}")
        
        # Load data
        self._load_initial_data()
        
        # v5.0.0: 모든 Treeview에 통일 스타일 자동 적용
        try:
            from fixes.auto_style_applier import apply_styles_to_all_trees
            # UI 생성 완료 후 실행 (after 사용)
            self.root.after(1000, lambda: apply_styles_to_all_trees(self.root))
            # ★ v6.3.2-colorful: 최종 오버라이드 (ttkbootstrap 강제 + 상태색)
            try:
                from fixes.theme_colorful_override import apply_colorful_overrides
                self.root.after(1500, lambda: apply_colorful_overrides(self))
            except ImportError:
                pass
            logger.info("✅ v5.0.0: 자동 스타일 적용 예약 완료")
        except ImportError as e:
            logger.debug(f"자동 스타일 적용기 로딩 실패 (무시): {e}")
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
            logger.warning(f"자동 스타일 적용 예약 실패: {e}")
        
        logger.info("SQM Inventory App initialized")
        self._ensure_resources_templates()   # v6.3.3 RUBI

    def _ensure_resources_templates(self) -> None:
        """
        v6.3.3 RUBI: resources/templates/ 폴더 자동 생성.

        Allocation 양식 미리보기 다이얼로그(AllocationTemplateDialog)가
        이 폴더에서 Song/Woo 양식 파일을 읽습니다.
        폴더가 없으면 실행 파일 기준 경로에 자동 생성합니다.

        배치 방법:
            resources/templates/allocation_template_song.xlsx  ← Song 양식
            resources/templates/allocation_template_woo.xlsx   ← Woo  양식
        """
        import os
        from pathlib import Path

        # SQM 실행 파일 기준 경로 (gui_app_modular 상위 = 프로젝트 루트)
        try:
            base = Path(__file__).parent.parent
        except Exception:
            base = Path(os.getcwd())

        templates_dir = base / 'resources' / 'templates'
        try:
            templates_dir.mkdir(parents=True, exist_ok=True)
            # README 파일 생성 (최초 1회)
            readme = templates_dir / 'README.txt'
            if not readme.exists():
                readme.write_text(
                    "SQM Allocation 양식 템플릿 폴더\n"
                    "================================\n\n"
                    "이 폴더에 아래 파일을 배치하면 '📄 Allocation 양식 미리보기' 메뉴에서\n"
                    "실제 양식 파일을 미리보기 및 다운로드할 수 있습니다.\n\n"
                    "  allocation_template_song.xlsx  : Song 양식 (250MT 기준)\n"
                    "  allocation_template_woo.xlsx   : Woo  양식 (550MT 기준)\n\n"
                    "파일이 없으면 내장 샘플 데이터로 대신 표시됩니다.\n",
                    encoding='utf-8',
                )
            logger.info(f"[v6.3.3] resources/templates 폴더 준비: {templates_dir}")
        except OSError as e:
            logger.warning(f"[v6.3.3] resources/templates 폴더 생성 실패 (무시): {e}")
    
    def _init_state(self) -> None:
        """Initialize application state variables"""
        # Selection state
        self.selected_tonbags = set()
        self.selected_search_items = set()
        
        # Sort state
        self._sort_column = None
        self._sort_reverse = False
        
        # Feature flags
        self.use_gemini = False
        self.gemini_required_warning_shown = False
        self._is_fullscreen = False
        
        # Filter presets
        self.filter_presets = {}
        
        # Recent files
        self.recent_files = []
        
        # Theme
        # ★ v6.3.2-fix: 실제 사용 중인 테마로 동기화 (flatly 하드코딩 제거)
        try:
            from tkinter import ttk as _ttk_detect
            self.current_theme = _ttk_detect.Style().theme_use() or 'darkly'
        except Exception:
            self.current_theme = 'darkly'
        
        # v3.0: UI 운영 헬퍼 초기화
        self.ui_helper = None  # _setup_ui에서 초기화

        # 전역 중복 검사 가드
        self._dup_guard_last_signature = ""
        self._dup_guard_interval_ms = 60000
    
    def _init_engine(self) -> None:
        """Initialize database engine"""
        try:
            from engine_modules.inventory import SQMInventoryEngine
            
            self.engine = SQMInventoryEngine(db_path=self.db_path)
            logger.info("Engine initialized")
            
        except ImportError as e:
            logger.warning(f"Engine import failed: {e}")
            # Try alternate import
            try:
                from engine import Engine
                self.engine = Engine(db_path=self.db_path)
            except ImportError:
                logger.error("No engine module found")
                self.engine = None
    
    def _setup_ui(self) -> None:
        """Setup main UI components"""
        from .utils.constants import ttk, BOTH, YES, X
        
        # Load window configuration
        self._load_window_config()
        
        # v3.8.4: 통합 메뉴바 (메인메뉴+액션+탭을 1줄로)
        self._setup_toolbar()
        # v5.4.1: 시작 직후 1회 툴바/드롭다운 팔레트 재동기화(화이트 모드 변색 방지)
        try:
            self._refresh_toolbar_theme()
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as _e:
            logger.debug(f"Suppressed: {_e}")
        
        # v5.0.6: main_frame 생성 (StatusBar를 위해 필요)
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        # Setup main notebook (tabs)
        self.notebook = ttk.Notebook(self.main_frame)  # ✅ main_frame 안에 배치
        self.notebook.pack(fill=BOTH, expand=YES)
        
        # v3.8.4: notebook 탭 헤더 숨김 (toolbar에 탭 버튼 있음)
        self._enforce_main_notebook_hidden_tabs()
        
        # Create tab frames (v7.0 1단계: 4개 메인 + 대시보드 + 로그)
        self.tab_dashboard = ttk.Frame(self.notebook)
        self.tab_cargo_overview = ttk.Frame(self.notebook)  # 6단계까지 유지(참조용)
        self.tab_inventory = ttk.Frame(self.notebook)
        self.tab_outbound_scheduled = ttk.Frame(self.notebook)  # 6단계까지 유지(참조용)
        self.tab_tonbag = ttk.Frame(self.notebook)  # 6단계에서 제거 예정, 지금은 유지
        self.tab_log = ttk.Frame(self.notebook)
        # v7.0 1단계: 4개 메인 탭용 신규 프레임
        self.tab_allocation = ttk.Frame(self.notebook)
        self.tab_picked = ttk.Frame(self.notebook)
        self.tab_sold = ttk.Frame(self.notebook)
        
        # 호환성: tab_inventory = AVAILABLE
        self.tab_available = self.tab_inventory
        self.tab_search = self.tab_inventory  # 검색은 재고 탭에 통합
        self.tab_summary = self.tab_dashboard  # 통계는 대시보드에 통합
        self.tab_pivot = ttk.Frame(self.notebook)  # 호환성 (사용 안 함)
        
        # v7.0: 4개 메인(한글) + 총괄 재고 리스트 + 통계 + 로그
        self.notebook.add(self.tab_inventory, text="  📦 판매가능  ")
        self.notebook.add(self.tab_allocation, text="  📋 판매배정  ")
        self.notebook.add(self.tab_picked, text="  🚛 판매화물 결정  ")
        self.notebook.add(self.tab_sold, text="  ✅ 출고  ")
        self.notebook.add(self.tab_cargo_overview, text="  📋 총괄 재고 리스트  ")
        self.notebook.add(self.tab_dashboard, text="  📊 통계  ")
        self.notebook.add(self.tab_log, text="  📝 로그  ")
        
        # Setup individual tabs (4개 메인 + 총괄 + 대시보드 + 로그)
        for tab_name, setup_fn in [
            ('Inventory', self._setup_inventory_tab),
            ('Allocation', self._setup_allocation_tab),
            ('Picked', self._setup_picked_tab),
            ('Sold', self._setup_sold_tab),
            ('CargoOverview', self._setup_cargo_overview_tab),
            ('Dashboard', self._setup_dashboard_tab),
            ('Log', self._setup_log_tab),
        ]:
            try:
                setup_fn()
            except (AttributeError, RuntimeError) as e:
                logger.error(f"탭 초기화 실패 [{tab_name}]: {e}")
                import traceback
                traceback.print_exc()
        
        # v3.8.8: 검색 탭 삭제 (팝업 검색으로 통일)
        if hasattr(self, '_setup_summary_tab_content'):
            self._setup_summary_tab_content()
        
        # v7.0: 시작 시 첫 탭 (0번 = AVAILABLE)
        try:
            self.notebook.select(0)  # index 0 = AVAILABLE (LOT 리스트)
        except (ValueError, TypeError, AttributeError) as _e:
            logger.debug(f"{type(_e).__name__}: {_e}")
        except (ValueError, TypeError, AttributeError) as _e:
            logger.debug(f"main_app: {_e}")
        
        # v3.8.4: notebook 탭 변경 시 툴바 탭 버튼 연동
        def _on_notebook_tab_changed(event):
            try:
                idx = self.notebook.index(self.notebook.select())
                # 0=판매가능, 1=판매배정, 2=판매화물 결정, 3=출고, 4=총괄 재고 리스트, 5=통계, 6=로그
                idx_to_key = {0: 'inventory', 1: 'allocation', 2: 'picked', 3: 'sold', 4: 'cargo_overview', 5: 'dashboard', 6: 'log'}
                key = idx_to_key.get(idx)
                if key and hasattr(self, '_active_tab_key'):
                    self._active_tab_key = key
                    self._highlight_active_tab()
                
                # 탭 전환 시 자동 새로고침
                if key == 'inventory' and hasattr(self, '_refresh_inventory'):
                    self._refresh_inventory()
                elif key == 'allocation' and hasattr(self, '_refresh_allocation'):
                    self._refresh_allocation()
                elif key == 'picked' and hasattr(self, '_refresh_picked'):
                    self._refresh_picked()
                elif key == 'sold' and hasattr(self, '_refresh_sold'):
                    self._refresh_sold()
                elif key == 'cargo_overview' and hasattr(self, '_refresh_cargo_overview'):
                    self._refresh_cargo_overview()
                elif key == 'dashboard':
                    if hasattr(self, '_refresh_dashboard') and callable(self._refresh_dashboard):
                        self._refresh_dashboard()
                    elif hasattr(self, '_refresh_summary'):
                        self._refresh_summary()
                
                # v3.9.4: 탭 전환 시 상태바 + 하단 통계 갱신
                if hasattr(self, '_update_statusbar_summary'):
                    self._update_statusbar_summary()
                
                # v3.8.8: 탭 전환 시 전용 툴바 활성화/비활성화
                self._toggle_tab_toolbars(key)
            except (AttributeError, RuntimeError) as _e:
                logger.debug(f"{type(_e).__name__}: {_e}")
            except (ValueError, TypeError, AttributeError) as _e:
                logger.debug(f"main_app: {_e}")
        
        self.notebook.bind('<<NotebookTabChanged>>', _on_notebook_tab_changed)
        
        # v3.6.5: 인프라 초기화 개별 예외 처리
        for infra_name, infra_fn in [
            ('StatusBar', self._setup_status_bar),
            ('KeyBindings', self._setup_keybindings),
            ('ContextMenus', self._setup_context_menus),
            ('WindowBindings', self._setup_window_bindings),
            ('DragDrop', self._setup_drag_drop),
            ('UIHelper', self._setup_ui_helper),
        ]:
            try:
                infra_fn()
            except (ValueError, TypeError, AttributeError) as e:
                logger.error(f"초기화 실패 [{infra_name}]: {e}")

    def _enforce_main_notebook_hidden_tabs(self) -> None:
        """메인 노트북 탭 헤더를 항상 숨김(중복 줄 표시 방지)."""
        try:
            style = self.ttk.Style()
            # 전역 TNotebook.Tab을 건드리지 않고 메인 전용 스타일만 숨김
            style.layout('MainHidden.TNotebook.Tab', [])
            if hasattr(self, 'notebook') and self.notebook:
                self.notebook.configure(style='MainHidden.TNotebook')
        except (RuntimeError, ValueError, AttributeError) as _e:
            logger.debug(f"_enforce_main_notebook_hidden_tabs: {_e}")
    
    def _setup_ui_helper(self) -> None:
        """v3.0: UI 운영 헬퍼 초기화"""
        try:
            from .utils.ui_ops_helper import UIOperationsHelper
            
            # 상태바에서 진행률 바와 레이블 가져오기
            progressbar = getattr(self, 'progress_bar', None)
            progress_label = getattr(self, 'status_label', None)
            
            # UI 헬퍼 초기화
            self.ui_helper = UIOperationsHelper(
                self.root, 
                progressbar=progressbar,
                progress_label=progress_label
            )
            
            # 미완료 작업 확인 (앱 시작 시)
            self.root.after(1000, self._check_work_recovery)
            
            # v3.9.4: 앱 시작 시 상태바 + 하단 통계 자동 갱신
            self.root.after(1500, self._startup_stats_refresh)
            
            # v3.8.4: 자동 백업 스케줄러 시작
            self.root.after(2000, self._start_auto_backup_safe)
            
            logger.info("[v3.0] UI 운영 헬퍼 초기화 완료")
            
        except ImportError as e:
            logger.warning(f"[v3.0] UI 헬퍼 로드 실패: {e}")
            self.ui_helper = None
    
    def _check_work_recovery(self) -> None:
        """미완료 작업 복구 확인"""
        if not self.ui_helper:
            return
    
    def _startup_stats_refresh(self) -> None:
        """v3.9.4: 앱 시작 시 통계 자동 갱신 (하단바 + 상태바)"""
        try:
            # 재고리스트 새로고침 → 하단 통계 자동 채움
            if hasattr(self, '_refresh_inventory'):
                self._refresh_inventory()
            # 상태바 요약
            if hasattr(self, '_update_statusbar_summary'):
                self._update_statusbar_summary()
            logger.info("[v3.9.4] 시작 시 통계 자동 갱신 완료")
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"startup_stats_refresh: {e}")
    
    def _start_auto_backup_safe(self) -> None:
        """v3.8.4: 자동 백업 안전 시작"""
        try:
            if hasattr(self, '_start_auto_backup'):
                self._start_auto_backup()
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"자동 백업 시작 오류: {e}")
        
        def on_recover(work):
            """복구 콜백"""
            self._log(f"작업 복구: {work.work_type} (진행률: {work.progress:.0%})")
            # 작업 유형에 따른 복구 로직
            if work.work_type == "INBOUND":
                self._log("입고 작업 복구 시도")
            elif work.work_type == "OUTBOUND":
                self._log("출고 작업 복구 시도")
            else:
                self._log(f"기타 작업 복구: {work.work_type}")
        
        def on_discard():
            """무시 콜백"""
            self._log("미완료 작업 무시됨")
        
        try:
            self.ui_helper.check_recovery(on_recover, on_discard)
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"작업 복구 확인 실패: {e}")
    
    def _load_initial_data(self) -> None:
        """Load initial data into UI"""
        try:
            # v3.8.4: 시작 시 정합성 검사
            self._startup_integrity_check()
            
            # v3.8.4 A6: 일별 스냅샷 저장
            self._save_startup_snapshot()
            
            self._refresh_inventory()
            self._refresh_tonbag()
            if hasattr(self, '_refresh_summary'):
                self._refresh_summary()
            self._start_duplicate_guard()
            self._log("Data loaded")
        except (AttributeError, RuntimeError) as e:
            logger.error(f"Initial data load error: {e}")
            self._log(f"X Data load error: {e}")

    def _start_duplicate_guard(self) -> None:
        """전역 중복 검사 자동 루프 시작."""
        try:
            self.root.after(2500, self._run_duplicate_guard_once)
        except (ValueError, TypeError, AttributeError) as e:
            logger.debug(f"duplicate guard start skip: {e}")

    def _run_duplicate_guard_once(self) -> None:
        """전역 식별 키 중복 검사 1회 실행 후 재예약."""
        try:
            if not self.engine or not hasattr(self.engine, "db"):
                return
            from .utils.duplicate_guard import scan_duplicate_keys

            findings = scan_duplicate_keys(self.engine.db)
            signature = "\n".join(findings)
            if findings:
                self._set_status(f"⚠️ 중복 감지 {len(findings)}건")
                if signature != self._dup_guard_last_signature:
                    self._log("⚠️ 전역 중복 검사 결과:")
                    for line in findings[:10]:
                        self._log(f"   - {line}")
                    if len(findings) > 10:
                        self._log(f"   ... 외 {len(findings) - 10}건")
                    popup_lines = findings[:5]
                    popup_msg = "중복 데이터가 감지되었습니다.\n\n"
                    popup_msg += "\n".join([f"• {x}" for x in popup_lines])
                    if len(findings) > 5:
                        popup_msg += f"\n\n... 외 {len(findings) - 5}건"
                    # v6.3.5: 기본은 팝업 생략(논블로킹), SQM_DUP_POPUP=1 일 때만 모달 표시
                    _dup_popup = (os.environ.get("SQM_DUP_POPUP", "").strip() == "1")
                    if _dup_popup:
                        CustomMessageBox.showwarning(
                            self.root,
                            "중복 데이터 경고",
                            popup_msg
                        )
                    else:
                        self._log("⚠️ 중복 데이터 경고: 팝업은 생략했습니다. (SQM_DUP_POPUP=1 이면 팝업 표시)")
                self._dup_guard_last_signature = signature
            else:
                self._dup_guard_last_signature = ""
        except (ImportError, ModuleNotFoundError, ValueError, TypeError, AttributeError) as e:
            logger.debug(f"duplicate guard run skip: {e}")
        finally:
            try:
                self.root.after(self._dup_guard_interval_ms, self._run_duplicate_guard_once)
            except (ValueError, TypeError, AttributeError) as e:
                logger.debug(f"duplicate guard reschedule skip: {e}")

    def _save_startup_snapshot(self) -> None:
        """v3.8.4 A6: 프로그램 시작 시 일별 재고 스냅샷 저장"""
        try:
            from core.validators import InventoryValidator
            validator = InventoryValidator(db=self.engine.db)
            result = validator.save_daily_snapshot()
            if result.get('success'):
                logger.info(f"[스냅샷] {result['date']}: {result['total_lots']}개 LOT, {result['total_weight_kg']:,.0f}kg")
        except (OSError, RuntimeError) as e:
            logger.debug(f"스냅샷 저장 실패 (무시): {e}")

    def _startup_integrity_check(self) -> None:
        """v3.8.4: 시작 시 데이터 정합성 검사. 경고/에러 시 발생 위치·작업을 로그에 명시."""
        _where, _what = "시작 시 정합성 검사", "데이터 정합성 검사"
        try:
            if not self.engine or not hasattr(self.engine, 'db'):
                return

            from core.validators import InventoryValidator
            validator = InventoryValidator(db=self.engine.db)
            result = validator.check_data_integrity()

            issues = []
            if result.errors:
                for e in result.errors:
                    issues.append(f"🔴 {e}")
                    self._log(f"🔴 정합성 오류: {e}", level="error", where=_where, what=_what)
            if result.warnings:
                for w in result.warnings:
                    issues.append(f"🟡 {w}")
                    self._log(f"🟡 정합성 경고: {w}", level="warning", where=_where, what=_what)

            if issues:
                from .utils.custom_messagebox import CustomMessageBox
                msg = "시작 시 데이터 정합성 검사 결과:\n\n"
                msg += "\n".join(issues[:10])
                if len(issues) > 10:
                    msg += f"\n\n... 외 {len(issues) - 10}건"

                if result.errors:
                    msg += "\n\n[설정/도구 → 정합성 복구]에서 자동 수정할 수 있습니다."
                    CustomMessageBox.showwarning(self.root, "⚠️ 정합성 검사", msg)
                else:
                    self._log("경미한 경고 발견 (위 항목 참고).", level="warning", where=_where, what=_what)
            else:
                self._log("데이터 정합성 검사 통과", level="info", where=_where, what=_what)

        except (ImportError, ModuleNotFoundError) as e:
            logger.debug(f"정합성 검사 스킵: {e}")
    
    def run(self) -> None:
        """Start the application main loop"""
        self._log("Application started")
        self.root.mainloop()
    
    def _toggle_tab_toolbars(self, active_tab: str) -> None:
        """v3.8.8: 탭 전환 시 해당 탭 전용 툴바만 표시
        
        각 탭이 초기화될 때 self._tab_toolbars dict에 등록하면,
        탭 전환 시 자동으로 show/hide 처리됨.
        
        등록 예: self._tab_toolbars['tonbag'] = [action_bar_widget]
        """
        if not hasattr(self, '_tab_toolbars'):
            return
        
        try:
            for tab_key, widgets in self._tab_toolbars.items():
                for w in widgets:
                    try:
                        if tab_key == active_tab:
                            # 활성 탭의 툴바 표시
                            if not w.winfo_ismapped():
                                w.pack(fill='x')
                        else:
                            # 비활성 탭의 툴바 숨김
                            if w.winfo_ismapped():
                                w.pack_forget()
                    except (RuntimeError, ValueError) as _e:
                        logger.debug(f"{type(_e).__name__}: {_e}")
        except (RuntimeError, ValueError) as _e:
            logger.debug(f"{type(_e).__name__}: {_e}")
        except (RuntimeError, ValueError) as _e:
            logger.debug(f"_toggle_tab_toolbars: {_e}")
    
    # =========================================================================
    # Placeholder methods - These are implemented by mixins
    # =========================================================================
    
    def _log_fallback(self, message: str, level: str = 'info') -> None:
        """Log message - fallback when LogTabMixin not available"""
        logger.debug(f"[{level.upper()}] {message}")
    
    def _set_status_fallback(self, message: str) -> None:
        """Set status bar - fallback when StatusBarMixin not available"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message)
    
    def _run_background(self, work_fn, on_success=None, on_error=None) -> None:
        """v3.6.5: Background task runner (동기 fallback)
        
        gui/mixins/base_mixin에 비동기 구현이 있지만
        gui_app_modular에서는 간단한 동기 실행으로 대체
        """
        try:
            result = work_fn()
            if on_success:
                on_success(result)
        except (RuntimeError, ValueError) as e:
            logger.error(f"Background task error: {e}")
            if on_error:
                on_error(e)
            elif hasattr(self, '_log'):
                self._log(f"❌ 작업 오류: {e}")
    
    # v3.6.5: _load_theme_preference 제거 (theme_mixin.py에서 정의)
    # MRO 충돌 방지


# Import and mix in all mixin classes
from .mixins import (
    MenuMixin,
    RefreshMixin,
    FeaturesV2Mixin,
    WindowMixin,
    ValidationMixin,
    KeyBindingsMixin,
    ContextMenuMixin,
    ToolbarMixin,
    StatusBarMixin,
    DatabaseMixin,
    DragDropMixin,
    ThemeMixin,
    AdvancedFeaturesMixin,
)

from .tabs import (
    AllocationTabMixin,
    CargoOverviewTabMixin,
    DashboardTabMixin,
    InventoryTabMixin,
    OutboundScheduledTabMixin,
    PickedTabMixin,
    SoldTabMixin,
    TonbagTabMixin,
    LogTabMixin,
    SummaryTabMixin,
)
# v5.5.3 P8: PivotLogicMixin 제거 (죽은 코드)
from .tabs.dashboard_data_mixin import DashboardDataMixin

from .handlers import (
    ImportHandlersMixin,
    OutboundHandlersMixin,
    BackupHandlersMixin,
    PDFHandlersMixin,
    ExportHandlersMixin,
    InboundProcessorMixin,
    StatusImportHandlersMixin,
    SimpleOutboundHandlerMixin,
)
from .handlers.pdf_report_handler import PDFReportMixin
from .handlers.inbound_update_mixin import InboundUpdateMixin
from .handlers.outbound_template_mixin import OutboundTemplateMixin
from .handlers.product_handlers import ProductManagementMixin
from .handlers.simple_excel_outbound import SimpleExcelOutboundMixin

from .dialogs import (
    LotDetailDialogMixin,
    SettingsDialogMixin,
    InfoDialogsMixin,
    OutboundPreviewDialogMixin,
)


# Create combined application class with all mixins
class SQMInventoryAppFull(
    SQMInventoryApp,
    # Mixins
    MenuMixin,
    RefreshMixin,
    FeaturesV2Mixin,
    WindowMixin,
    ValidationMixin,
    KeyBindingsMixin,
    ContextMenuMixin,
    ToolbarMixin,
    StatusBarMixin,
    DatabaseMixin,
    DragDropMixin,
    ThemeMixin,
    AdvancedFeaturesMixin,
    # Tabs
    CargoOverviewTabMixin,
    AllocationTabMixin,
    DashboardTabMixin,
    DashboardDataMixin,
    InventoryTabMixin,
    OutboundScheduledTabMixin,
    PickedTabMixin,
    SoldTabMixin,
    TonbagTabMixin,
    LogTabMixin,
    SummaryTabMixin,
    # Handlers
    ImportHandlersMixin,
    OutboundHandlersMixin,
    BackupHandlersMixin,
    PDFHandlersMixin,
    ExportHandlersMixin,
    InboundProcessorMixin,
    InboundUpdateMixin,
    StatusImportHandlersMixin,
    SimpleOutboundHandlerMixin,
    OutboundTemplateMixin,
    PDFReportMixin,
    ProductManagementMixin,
    SimpleExcelOutboundMixin,
    # Dialogs
    LotDetailDialogMixin,
    SettingsDialogMixin,
    InfoDialogsMixin,
    OutboundPreviewDialogMixin,
):
    """
    Full SQM Inventory Application with all features
    
    This class combines the base application with all mixins
    to provide the complete functionality.
    """

    def _safe_progress(self, value: int, message: str = '', detail: str = ''):
        """안전한 진행률 업데이트 (어디서든 호출 가능)"""
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar['value'] = value
            if message:
                self._log(message)
            if hasattr(self, '_set_status') and (detail or message):
                self._set_status(detail or message)
            if hasattr(self, 'root'):
                self.root.update_idletasks()
        except (AttributeError, RuntimeError) as _e:
            logger.debug(f"{type(_e).__name__}: {_e}")
        except (ValueError, TypeError, AttributeError) as _e:
            logger.debug(f"main_app: {_e}")

    def _update_progress(self, value: int, message: str = '', detail: str = ''):
        """호환성 래퍼"""
        self._safe_progress(value, message, detail)
    
    def _run_integrity_check(self) -> None:
        """
        데이터 정합성 검사 실행
        
        v4.19.1: 정합성 검사 에러 수정
        메뉴: 설정 및 도구 → 데이터 정합성 검사
        """
        try:
            from utils.integrity_check import run_integrity_check
            from .utils.constants import tk
            
            # 검사 실행
            report = run_integrity_check(self.engine.db)
            
            # 결과 다이얼로그
            if report.is_valid:
                tk.CustomMessageBox.info(None, 
                    "✅ 정합성 검사 완료",
                    f"모든 데이터가 정상입니다!\n\n"
                    f"검사 LOT 수: {report.total_lots}개\n"
                    f"정상: {report.valid_lots}개\n"
                    f"경고: {report.warning_lots}개"
                )
            else:
                error_msg = "\n".join([
                    f"- {err['lot_no']}: {err['message']}"
                    for err in report.errors[:5]
                ])
                
                tk.CustomMessageBox.warning(None, 
                    "⚠️ 정합성 문제 발견",
                    f"일부 데이터에 문제가 있습니다.\n\n"
                    f"오류 LOT: {len(report.errors)}개\n\n"
                    f"{error_msg}\n\n"
                    f"전체 보고서는 로그를 확인하세요."
                )
        
        except ImportError as e:
            from .utils.constants import tk
            tk.CustomMessageBox.error(None, 
                "기능 로딩 실패",
                f"정합성 검사 모듈을 불러올 수 없습니다.\n\n{e}"
            )
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
            logger.exception("정합성 검사 실패")
            from .utils.constants import tk
            tk.CustomMessageBox.error(None, 
                "검사 실행 실패",
                f"정합성 검사 중 오류가 발생했습니다.\n\n{e}"
            )


def main():
    """GUI 전용 진입 (부트스트랩 없음). 정식 실행은 run.py 또는 python -m gui_app_modular 사용."""
    import argparse

    parser = argparse.ArgumentParser(description='SQM Inventory Management System')
    parser.add_argument('--db', type=str, help='Database path')
    parser.add_argument('--theme', type=str, default='flatly', help='UI theme (default: flatly)')
    args = parser.parse_args()

    app = SQMInventoryAppFull(db_path=args.db)
    app.run()


# 개발/테스트용: 이 파일 직접 실행 시 환경 점검·MAC Guard·자동 백업 생략
if __name__ == '__main__':
    main()


    # --------------------------
    # v5.3.1: Manual DB Migration (v5.3.0)
    # --------------------------
    def _on_run_v530_migration(self):
        """Manual migration trigger: v5.3.0 audit columns + mapping history."""
        try:
            # engine may expose migration mixin via self.engine.db or similar; best-effort call
            mig = None
            if hasattr(self, "engine") and hasattr(self.engine, "db_migration"):
                mig = self.engine.db_migration
            elif hasattr(self, "engine") and hasattr(self.engine, "db"):
                mig = getattr(self.engine.db, "migration", None)
            elif hasattr(self, "engine"):
                mig = getattr(self.engine, "migration", None)

            if mig is None and hasattr(self, "engine"):
                # fallback: try attribute name
                mig = getattr(self.engine, "db_migration_mixin", None)

            if mig is None:
                raise RuntimeError("Migration runner not found on engine.")
            if hasattr(mig, "run_v530_migration_manual"):
                mig.run_v530_migration_manual()
            else:
                raise RuntimeError("run_v530_migration_manual() not found.")
            CustomMessageBox.info(None, "DB Migration", "v5.3.0 migration completed successfully.")
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
            CustomMessageBox.error(None, "DB Migration (HARD STOP)", f"Migration failed: {e}")

    # --------------------------
    # v5.3.3: Menu Theme Fix (white theme background issue) - best effort
    # --------------------------
    def _read_ui_settings(self):
        base = os.getcwd()
        cfg = configparser.ConfigParser()
        try:
            cfg.read(os.path.join(base, 'settings.ini'), encoding='utf-8')
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as _e:
            logger.debug(f"Suppressed: {_e}")
        menu_fix = cfg.getint('ui', 'menu_fix_enabled', fallback=1)
        return {"menu_fix_enabled": menu_fix}


    def _show_product_inventory_report(self):
        """도구 > 제품별 재고 현황 리포트."""
        try:
            from .dialogs.product_inventory_report import show_product_inventory_report
            show_product_inventory_report(self)
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                from tkinter import messagebox
                messagebox.showerror("오류", f"제품별 리포트 열기 실패:\n{e}")
            except Exception:
                pass

    # v6.2.7: 제품 마스터 관리
    def _show_product_master(self):
        """도구 > 제품 마스터 관리 다이얼로그."""
        try:
            from .dialogs.product_master_dialog import show_product_master_dialog
            show_product_master_dialog(self)
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                from tkinter import messagebox
                messagebox.showerror("오류", f"제품 마스터 열기 실패:\n{e}")
            except Exception:
                pass

    # v5.3.4: Tools Menu Ensure (100% 연결 목표)
    # --------------------------
