# -*- coding: utf-8 -*-
"""
SQM 재고관리 - GUI 상수 및 설정
================================

v2.9.91 - gui_app.py에서 분리

상수, 설정, 폴백 정의
"""

import logging
from pathlib import Path

# 모듈 로거
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# GUI 라이브러리 로드
# ═══════════════════════════════════════════════════════════════

try:
    import ttkbootstrap as ttk
    from ttkbootstrap import Window, Style
    from ttkbootstrap.scrolled import ScrolledFrame
    from ttkbootstrap.tableview import Tableview
    from ttkbootstrap.tooltip import ToolTip
    import tkinter as tk
    from tkinter import filedialog, messagebox
    
    # v3.6.5: ttkbootstrap 전용 위젯 (안전 import)
    try:
        from ttkbootstrap.widgets import Meter, DateEntry, Floodgauge
    except ImportError:
        Meter = None
        DateEntry = None
        Floodgauge = None
    
    # ttkbootstrap에 LabelFrame이 없으면 tkinter.ttk에서 가져옴
    if not hasattr(ttk, 'LabelFrame'):
        from tkinter.ttk import LabelFrame
        ttk.LabelFrame = LabelFrame
    
    # tkinter 상수 (ttkbootstrap에서 재정의되지 않으므로 직접 정의)
    LEFT = tk.LEFT
    RIGHT = tk.RIGHT
    TOP = tk.TOP
    BOTTOM = tk.BOTTOM
    BOTH = tk.BOTH
    X = tk.X
    Y = tk.Y
    YES = True
    NO = False
    VERTICAL = tk.VERTICAL
    HORIZONTAL = tk.HORIZONTAL
    END = tk.END
    WORD = tk.WORD
    DISABLED = tk.DISABLED
    NORMAL = tk.NORMAL
    SUNKEN = tk.SUNKEN
    RAISED = tk.RAISED
    FLAT = tk.FLAT
    GROOVE = tk.GROOVE
    RIDGE = tk.RIDGE
    W = tk.W
    E = tk.E
    N = tk.N
    S = tk.S
    NW = tk.NW
    NE = tk.NE
    SW = tk.SW
    SE = tk.SE
    CENTER = tk.CENTER
    Menu = tk.Menu
    
    HAS_TTKBOOTSTRAP = True
    HAS_TOOLTIP = True
    HAS_METER = Meter is not None
    HAS_DATEENTRY = DateEntry is not None
    HAS_FLOODGAUGE = Floodgauge is not None
    logger.info("✅ ttkbootstrap 로드됨")
except ImportError:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import filedialog, messagebox
    HAS_TTKBOOTSTRAP = False
    HAS_TOOLTIP = False
    HAS_METER = False
    HAS_DATEENTRY = False
    HAS_FLOODGAUGE = False
    ToolTip = None
    Meter = None
    DateEntry = None
    Floodgauge = None
    ScrolledFrame = None
    Tableview = None
    
    # ttkbootstrap 상수 폴백 정의
    LEFT = tk.LEFT
    RIGHT = tk.RIGHT
    TOP = tk.TOP
    BOTTOM = tk.BOTTOM
    BOTH = tk.BOTH
    X = tk.X
    Y = tk.Y
    YES = True
    NO = False
    VERTICAL = tk.VERTICAL
    HORIZONTAL = tk.HORIZONTAL
    END = tk.END
    WORD = tk.WORD
    DISABLED = tk.DISABLED
    NORMAL = tk.NORMAL
    SUNKEN = tk.SUNKEN
    RAISED = tk.RAISED
    FLAT = tk.FLAT
    GROOVE = tk.GROOVE
    RIDGE = tk.RIDGE
    W = tk.W
    E = tk.E
    N = tk.N
    S = tk.S
    NW = tk.NW
    NE = tk.NE
    SW = tk.SW
    SE = tk.SE
    CENTER = tk.CENTER
    Menu = tk.Menu
    
    Window = tk.Tk
    Style = None
    ScrolledFrame = None
    Tableview = None
    
    logger.warning("⚠️ ttkbootstrap 미설치 - 기본 UI 사용")

# ═══════════════════════════════════════════════════════════════
# pandas
# ═══════════════════════════════════════════════════════════════

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None
    logger.warning("⚠️ pandas 미설치")

# ═══════════════════════════════════════════════════════════════
# 설정 파일 경로
# ═══════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent.parent
WINDOW_CONFIG_FILE = BASE_DIR / "window_config.json"
THEME_CONFIG_FILE = BASE_DIR / "theme_preference.json"
RECENT_FILES_FILE = BASE_DIR / "recent_files.json"

# ═══════════════════════════════════════════════════════════════
# 버전 정보
# ═══════════════════════════════════════════════════════════════

try:
    from version import __version__, APP_NAME
except ImportError:
    __version__ = "0.0.0"
    APP_NAME = "SQM 재고관리 시스템"

# ═══════════════════════════════════════════════════════════════
# 선택적 모듈 플래그
# ═══════════════════════════════════════════════════════════════

# Column Aliases
try:
    from column_aliases import ColumnMapper, COLUMN_ALIASES
    HAS_COLUMN_ALIASES = True
except ImportError:
    ColumnMapper = None
    COLUMN_ALIASES = {}
    HAS_COLUMN_ALIASES = False

# Validators
try:
    from validators import DataValidator
    HAS_VALIDATOR = True
except ImportError:
    HAS_VALIDATOR = False
    DataValidator = None

# DB Protection
try:
    from db_protection import DBProtection, ActionLogger
    HAS_DB_PROTECTION = True
except ImportError:
    HAS_DB_PROTECTION = False
    DBProtection = None
    ActionLogger = None

# Error Handler
try:
    from error_handler import (
        ErrorDialog, safe_execute,
        add_tooltip
    )
    HAS_ERROR_HANDLER = True
except ImportError:
    HAS_ERROR_HANDLER = False
    ErrorDialog = None
    safe_execute = lambda f: f
    add_tooltip = lambda w, t: None

# Preflight
try:
    from preflight import PreflightValidator, PreflightError
    HAS_PREFLIGHT = True
except ImportError:
    HAS_PREFLIGHT = False
    PreflightValidator = None
    PreflightError = None

# Features
try:
    from features import FeatureManager
    HAS_FEATURES = True
except ImportError:
    HAS_FEATURES = False
    FeatureManager = None

# Features V2
try:
    from features_v2 import FeaturesV2Manager
    HAS_FEATURES_V2 = True
except ImportError:
    HAS_FEATURES_V2 = False
    FeaturesV2Manager = None

# Comprehensive Backup
try:
    from comprehensive_backup import (
        ComprehensiveBackupSystem
    )
    HAS_COMPREHENSIVE_BACKUP = True
except ImportError:
    HAS_COMPREHENSIVE_BACKUP = False
    ComprehensiveBackupSystem = None

# Upload Guard
try:
    from upload_guard import UploadGuard
    HAS_UPLOAD_GUARD = True
except ImportError:
    HAS_UPLOAD_GUARD = False
    UploadGuard = None

# Document Parser V2
try:
    from parsers.document_parser_v2 import DocumentParserV2
    HAS_PARSER_V2 = True
except ImportError:
    HAS_PARSER_V2 = False
    DocumentParserV2 = None

# PDF Parser (Legacy)
try:
    from parsers.pdf_parser import PDFParser, parse_pdf
except ImportError:
    try:
        from parsers import PDFParser, parse_pdf
    except ImportError:
        PDFParser = None
        parse_pdf = None

# Gemini API
try:
    from config import GEMINI_API_KEY
    HAS_GEMINI = bool(GEMINI_API_KEY and GEMINI_API_KEY != 'your-api-key-here')
except ImportError:
    HAS_GEMINI = False
    GEMINI_API_KEY = None

# Progress Dialog
try:
    from improvements import TkProgressDialog, ProgressInfo
    HAS_PROGRESS = True
except ImportError:
    HAS_PROGRESS = False
    TkProgressDialog = None
    ProgressInfo = None

# ═══════════════════════════════════════════════════════════════
# UI 상수
# ═══════════════════════════════════════════════════════════════

# 기본 창 크기
DEFAULT_WINDOW_WIDTH = 1400
DEFAULT_WINDOW_HEIGHT = 900
MIN_WINDOW_WIDTH = 1000
MIN_WINDOW_HEIGHT = 700

# 기본 테마
DEFAULT_THEME = "flatly"  # v3.0: 고급스러운 기본 테마
DARK_THEMES = ["darkly", "superhero", "cyborg", "vapor", "solar"]
LIGHT_THEMES = ["cosmo", "flatly", "journal", "litera", "lumen", "minty", "pulse", "sandstone", "united", "yeti"]

# 상태 코드
STATUS_AVAILABLE = "AVAILABLE"
STATUS_RESERVED = "RESERVED"
STATUS_PICKED = "PICKED"
STATUS_SHIPPED = "SHIPPED"

# 색상
COLORS = {
    'success': '#28a745',
    'warning': '#ffc107',
    'danger': '#dc3545',
    'info': '#17a2b8',
    'primary': '#007bff',
}

# 최근 파일 최대 개수
MAX_RECENT_FILES = 10

# 캐시 만료 시간 (초)
CACHE_EXPIRE_SECONDS = 300

# ═══════════════════════════════════════════════════════════════
# SQM 비즈니스 기본값 (v3.8.8)
# ═══════════════════════════════════════════════════════════════
DEFAULT_WAREHOUSE = '광양'
DEFAULT_PRODUCT = 'LITHIUM CARBONATE'
DEFAULT_TONBAG_COUNT = 10
WEIGHT_TOLERANCE_KG = 0.5  # 무게 허용 오차 (kg)
