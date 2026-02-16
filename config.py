# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 설정 모듈
================================

v3.6.0: Docstring 보강

모듈 개요:
    시스템 전역 설정을 관리합니다. 경로, 데이터베이스, API, UI, 
    로깅 등 모든 설정이 이 모듈에서 정의됩니다.

주요 설정:
    - DB_TYPE: 데이터베이스 유형 ('sqlite' 또는 'postgresql')
    - DB_PATH: SQLite 데이터베이스 파일 경로
    - PG_*: PostgreSQL 연결 설정
    - GEMINI_API_KEY: Gemini API 키
    - UI_THEME: ttkbootstrap 테마

주요 함수:
    - validate_api_key(): API 키 유효성 검사
    - validate_api_key_with_gui(): GUI 경고창 포함 검증
    - safe_file_backup(): 안전한 파일 백업
    - smart_path_recovery(): 경로 자동 복구
    - sql_*(): SQL 호환 함수들

사용 예시:
    >>> from config import DB_PATH, DB_TYPE, GEMINI_API_KEY
    >>> 
    >>> # API 키 검증
    >>> valid, error = validate_api_key()
    >>> 
    >>> # 안전한 백업
    >>> success, path = safe_file_backup('data.db')
    >>> 
    >>> # SQL 호환 함수
    >>> query = f"SELECT {sql_group_concat('lot_no')} FROM inventory"

환경변수:
    - SQM_DB_TYPE: 데이터베이스 유형 (기본: sqlite)
    - SQM_PG_HOST: PostgreSQL 호스트
    - SQM_PG_PORT: PostgreSQL 포트
    - SQM_PG_DATABASE: PostgreSQL 데이터베이스명
    - SQM_PG_USER: PostgreSQL 사용자
    - SQM_PG_PASSWORD: PostgreSQL 비밀번호
    - GEMINI_API_KEY: Gemini API 키

작성자: Ruby (남기동)
버전: v3.6.0
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# 프로젝트 정보 (★ v2.5.4: 버전 단일화)
# =============================================================================

try:
    from version import __version__, APP_NAME, APP_NAME_EN
except ImportError:
    __version__ = "0.0.0"
    APP_NAME = "SQM 재고관리 시스템"
    APP_NAME_EN = "SQM Inventory Management System"

APP_VERSION = __version__  # 하위 호환성 유지

# =============================================================================
# 경로 설정
# =============================================================================

# 기본 디렉토리 (실행 파일 위치 기준)
BASE_DIR = Path(__file__).parent.absolute()

# 데이터 디렉토리
DATA_DIR = BASE_DIR / "data"
DB_DIR = DATA_DIR / "db"
OUTPUT_DIR = BASE_DIR / "output"
BACKUP_DIR = BASE_DIR / "backup"
LOG_DIR = BASE_DIR / "logs"
TEMP_DIR = BASE_DIR / "temp"

# 디렉토리 자동 생성
for dir_path in [DATA_DIR, DB_DIR, OUTPUT_DIR, BACKUP_DIR, LOG_DIR, TEMP_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# =============================================================================
# 데이터베이스 설정
# =============================================================================

# ★★★ v3.6.0: PostgreSQL 지원 (기본값: SQLite) ★★★
# DB_TYPE: 'sqlite' 또는 'postgresql'
DB_TYPE = os.environ.get('SQM_DB_TYPE', 'sqlite')  # 기본값: sqlite (나중에 postgresql 전환 용이)

# SQLite 설정 (DB_TYPE='sqlite' 일 때 사용)
DB_PATH = DB_DIR / "sqm_inventory.db"
DB_TIMEOUT = 30.0  # 초
DB_WAL_MODE = True  # WAL 모드 활성화

# PostgreSQL 설정 (DB_TYPE='postgresql' 일 때 사용)
PG_HOST = os.environ.get('SQM_PG_HOST', 'localhost')
PG_PORT = int(os.environ.get('SQM_PG_PORT', '5432'))
PG_DATABASE = os.environ.get('SQM_PG_DATABASE', 'sqm_inventory')
PG_USER = os.environ.get('SQM_PG_USER', 'postgres')
PG_PASSWORD = os.environ.get('SQM_PG_PASSWORD', 'postgres')

# PostgreSQL 연결 풀 설정
PG_MIN_CONNECTIONS = int(os.environ.get('SQM_PG_MIN_CONN', '2'))
PG_MAX_CONNECTIONS = int(os.environ.get('SQM_PG_MAX_CONN', '10'))

def get_pg_connection_string():
    """PostgreSQL 연결 문자열 반환"""
    return f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"

def get_db_info():
    """현재 DB 설정 정보 반환"""
    if DB_TYPE == 'postgresql':
        return {
            'type': 'PostgreSQL',
            'host': PG_HOST,
            'port': PG_PORT,
            'database': PG_DATABASE,
            'user': PG_USER,
        }
    else:
        return {
            'type': 'SQLite',
            'path': str(DB_PATH),
        }

# =============================================================================
# 백업 설정 (개선 #1)
# =============================================================================

BACKUP_ENABLED = True
BACKUP_MAX_COUNT = 5  # 최대 백업 파일 수
BACKUP_BEFORE_IMPORT = True  # 가져오기 전 자동 백업
BACKUP_BEFORE_DELETE = True  # 삭제 전 자동 백업
BACKUP_INTERVAL_HOURS = 24  # 최소 백업 간격 (시간)

# =============================================================================
# API 설정 (v2.8.0: 환경변수 우선, settings.ini 폴백)
# =============================================================================

import configparser

# settings.ini 파일 경로
SETTINGS_FILE = BASE_DIR / "settings.ini"

def _load_settings():
    """
    settings.ini 파일에서 설정 읽기
    
    ★★★ v3.9.7: 보안 강화 ★★★
    1. 환경변수 우선 (GEMINI_API_KEY)
    2. keyring (OS 자격증명 관리자) 2순위
    3. settings.ini는 폴백용 + 자동 마이그레이션
    """
    config = configparser.ConfigParser()

    # 기본값
    defaults = {
        'api_key': '',
        'model': 'gemini-2.5-flash',
        'use_gemini': 'true',
        'theme': 'flatly',
        'openai_api_key': '',
        'openai_model': 'gpt-4o',
        'save_raw_gemini_response': False,   # v5.5.2: 디버깅 시 Gemini 원문을 logs/에 저장 (ON/OFF)
        'disable_openai_fallback': False,     # v5.5.2: True면 OpenAI 폴백 비활성 (Gemini-only)
    }
    
    # ★★★ 1순위: 환경변수 ★★★
    env_api_key = os.environ.get('GEMINI_API_KEY', '')
    env_model = os.environ.get('GEMINI_MODEL', '')
    env_db_path = os.environ.get('SQM_DB_PATH', '')
    env_openai_key = os.environ.get('OPENAI_API_KEY', '')
    env_openai_model = os.environ.get('OPENAI_MODEL', '')
    env_save_raw = os.environ.get('SQM_SAVE_RAW_GEMINI_RESPONSE', '')
    
    result = defaults.copy()
    
    if env_api_key:
        result['api_key'] = env_api_key
        result['api_key_source'] = 'ENV'
    
    if env_model:
        result['model'] = env_model
    
    if env_openai_key:
        result['openai_api_key'] = env_openai_key
    if env_openai_model:
        result['openai_model'] = env_openai_model
    if env_save_raw and str(env_save_raw).strip().lower() in ('1', 'true', 'yes'):
        result['save_raw_gemini_response'] = True

    # ★★★ 2순위: keyring (OS 자격증명 관리자) ★★★
    if not result.get('api_key'):
        try:
            import keyring
            kr_key = keyring.get_password('SQM_Inventory', 'GEMINI_API_KEY')
            if kr_key:
                result['api_key'] = kr_key
                result['api_key_source'] = 'KEYRING'
        except (ImportError, Exception) as e:
            logger.debug(f"Suppressed: keyring 미설치 또는 오류 — 건너뜀: {e}")

    if SETTINGS_FILE.exists():
        try:
            config.read(SETTINGS_FILE, encoding='utf-8')
            
            # ★★★ 3순위: ini 파일 (+ 자동 마이그레이션) ★★★
            if not result.get('api_key') or result.get('api_key_source') is None:
                ini_key = config.get('Gemini', 'api_key', fallback='')
                if ini_key and not ini_key.startswith('your-'):
                    result['api_key'] = ini_key
                    result['api_key_source'] = 'INI'
                    print("⚠️ [보안경고] API 키가 settings.ini에 평문 저장되어 있습니다!")
                    print("   자동으로 OS 자격증명에 이관을 시도합니다...")
                    # v3.9.7: keyring으로 자동 이관 시도
                    _migrate_api_key_to_keyring(ini_key, config)
            
            result['model'] = config.get('Gemini', 'model', fallback=result['model'])
            result['use_gemini'] = config.getboolean('Parser', 'use_gemini', fallback=True)
            result['theme'] = config.get('UI', 'theme', fallback=defaults['theme'])
            if config.has_section('OpenAI'):
                result['openai_api_key'] = config.get('OpenAI', 'api_key', fallback=result.get('openai_api_key', ''))
                result['openai_model'] = config.get('OpenAI', 'model', fallback=result.get('openai_model', 'gpt-4o'))
            if config.has_section('Debug'):
                result['save_raw_gemini_response'] = config.getboolean('Debug', 'save_raw_gemini_response', fallback=result.get('save_raw_gemini_response', False))
            if config.has_section('Parser'):
                result['disable_openai_fallback'] = config.getboolean('Parser', 'disable_openai_fallback', fallback=result.get('disable_openai_fallback', False))
            
        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"⚠️ settings.ini 읽기 오류: {e}")

    return result


def _migrate_api_key_to_keyring(api_key: str, config: configparser.ConfigParser) -> bool:
    """v3.9.7: API 키를 settings.ini → keyring(OS 자격증명)으로 이관"""
    try:
        import keyring
        keyring.set_password('SQM_Inventory', 'GEMINI_API_KEY', api_key)
        
        # ini에서 키 제거 (주석으로 대체)
        config.set('Gemini', 'api_key', '# MIGRATED_TO_KEYRING')
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
        
        print("   ✅ API 키가 OS 자격증명 관리자로 안전하게 이관되었습니다.")
        return True
    except ImportError:
        print("   ℹ️ keyring 미설치. pip install keyring 으로 설치하면 자동 이관됩니다.")
        return False
    except (OSError, IOError, PermissionError) as e:
        print(f"   ⚠️ keyring 이관 실패: {e}")
        return False


def save_api_key_secure(api_key: str) -> str:
    """v3.9.7: API 키를 가장 안전한 방법으로 저장 (GUI에서 호출)"""
    # 1순위: keyring
    try:
        import keyring
        keyring.set_password('SQM_Inventory', 'GEMINI_API_KEY', api_key)
        return 'KEYRING'
    except (ImportError, Exception) as _e:
        logger.debug(f"Suppressed: {_e}")
    
    # 2순위: 환경변수 안내
    # (실제 환경변수 설정은 사용자가 해야 하므로 ini에 저장)
    try:
        config = configparser.ConfigParser()
        if SETTINGS_FILE.exists():
            config.read(SETTINGS_FILE, encoding='utf-8')
        if not config.has_section('Gemini'):
            config.add_section('Gemini')
        config.set('Gemini', 'api_key', api_key)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
        return 'INI'
    except (OSError, IOError, PermissionError):
        return 'FAILED'


def save_gemini_model(model: str) -> bool:
    """Gemini 모델을 settings.ini [Gemini] model에 저장. 다음 실행부터 적용."""
    if not model or not model.strip():
        return False
    try:
        config = configparser.ConfigParser()
        if SETTINGS_FILE.exists():
            config.read(SETTINGS_FILE, encoding='utf-8')
        if not config.has_section('Gemini'):
            config.add_section('Gemini')
        config.set('Gemini', 'model', model.strip())
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
        return True
    except (OSError, IOError, PermissionError):
        return False


# 설정 로드
_settings = _load_settings()

# Gemini API 설정
GEMINI_API_KEY = _settings['api_key']
GEMINI_MODEL = _settings['model']
USE_GEMINI_DEFAULT = _settings.get('use_gemini', True)
API_KEY_SOURCE = _settings.get('api_key_source', 'NONE')  # v2.8.0: 키 출처 추적

# OpenAI API 설정 (Gemini 실패 시 폴백용, 선택)
OPENAI_API_KEY = _settings.get('openai_api_key', '')
OPENAI_MODEL = _settings.get('openai_model', 'gpt-4o')

# v5.5.2: 디버깅/정책 옵션
SAVE_RAW_GEMINI_RESPONSE = _settings.get('save_raw_gemini_response', False)  # True면 logs/raw_pl_response.txt 등 저장
DISABLE_OPENAI_FALLBACK = _settings.get('disable_openai_fallback', False)    # True면 Gemini만 사용

# API 키 검증
def validate_api_key():
    """API 키 유효성 검사"""
    if not GEMINI_API_KEY or GEMINI_API_KEY.startswith('your-'):
        return False, "GEMINI_API_KEY가 설정되지 않았습니다. 환경변수 또는 settings.ini를 확인하세요."
    return True, ""

def get_api_key_warning():
    """v2.8.0: API 키 보안 경고 메시지 반환"""
    if API_KEY_SOURCE == 'INI':
        return ("⚠️ API 키가 settings.ini에 평문 저장됨\n"
                "환경변수 GEMINI_API_KEY 사용을 권장합니다.")
    return None

# =============================================================================
# UI 설정
# =============================================================================

UI_THEME = "flatly"  # v3.0: 고급스러운 기본 테마  # ttkbootstrap 테마
UI_DARK_MODE = False
WINDOW_SIZE = "1200x800"
WINDOW_MIN_SIZE = (900, 600)

# =============================================================================
# 비즈니스 설정
# =============================================================================

# 제품 코드
PRODUCT_CODES = {
    "MIC9000": "LITHIUM CARBONATE 99.5%",
    "MIC9100": "LITHIUM CARBONATE 99.5% BG",
    "LC": "LITHIUM CARBONATE",
    "LH": "LITHIUM HYDROXIDE",
}

# 포장 단위
PACKING_UNITS = {
    "MX500": "MX 500 Kg (In Wooden Pallet)",
    "MX1000": "MX 1000 Kg (In Wooden Pallet)",
}

# 입력 검증 설정 (개선 #3)
VALIDATION = {
    'LOT_NO_MIN_LENGTH': 5,
    'LOT_NO_MAX_LENGTH': 20,
    'LOT_NO_PATTERN': r'^\d{10}$',  # 10자리 숫자 (권장)
    'WEIGHT_MIN': 0,
    'WEIGHT_MAX': 50000,  # 50톤
    'SAP_NO_PATTERN': r'^\d{10}$',  # 10자리 숫자
}

# =============================================================================
# 로깅 설정 (개선 #4 - 로그 로테이션)
# =============================================================================

LOG_LEVEL = os.environ.get('SQM_LOG_LEVEL', 'INFO')
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 로그 로테이션 설정
LOG_MAX_SIZE_MB = 10  # 최대 로그 파일 크기 (MB)
LOG_BACKUP_COUNT = 5  # 백업 로그 파일 수
LOG_KEEP_DAYS = 30  # 로그 보관 일수

# 로그 파일 경로
LOG_FILE = LOG_DIR / "sqm_inventory.log"

# =============================================================================
# 로깅 초기화 함수
# =============================================================================

def setup_logging():
    """
    로깅 설정 초기화 (로테이션 포함)

    Returns:
        logger: 설정된 로거 객체
    """
    import logging
    from logging.handlers import RotatingFileHandler

    # 루트 로거 설정
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL))

    # 기존 핸들러 제거
    logger.handlers.clear()

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(console_handler)

    # 파일 핸들러 (로테이션)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_SIZE_MB * 1024 * 1024,  # MB → bytes
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        logger.warning(f"파일 로깅 설정 실패: {e}")

    return logger

# =============================================================================
# 설정 유효성 검사
# =============================================================================

def validate_config():
    """
    전체 설정 유효성 검사

    Returns:
        (success, errors): 성공 여부 및 오류 목록
    """
    errors = []

    # 디렉토리 확인
    for dir_name, dir_path in [
        ('DATA_DIR', DATA_DIR),
        ('DB_DIR', DB_DIR),
        ('LOG_DIR', LOG_DIR),
    ]:
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except (ConnectionError, TimeoutError, ValueError) as e:
                errors.append(f"{dir_name} 생성 실패: {e}")

    # API 키 확인
    api_valid, api_error = validate_api_key()
    if not api_valid:
        errors.append(api_error)

    return len(errors) == 0, errors


# =============================================================================
# v3.6.0: API 키 GUI 검증 (안정성 강화)
# =============================================================================

def validate_api_key_with_gui(parent=None):
    """
    v3.6.0: GUI 실행 전 API 키 검증 및 경고창 표시
    
    Args:
        parent: 부모 윈도우 (None이면 루트 생성)
    
    Returns:
        bool: 계속 실행 여부 (True: 진행, False: 중단)
    """
    api_valid, api_error = validate_api_key()
    
    if not api_valid:
        try:
            import tkinter as tk
            from gui_app_modular.utils.custom_messagebox import CustomMessageBox

            # 임시 루트 윈도우 (숨김)
            if parent is None:
                temp_root = tk.Tk()
                temp_root.withdraw()
            
            CustomMessageBox.warning(None, 
                "⚠️ API 설정 필요",
                "Gemini API 키가 설정되지 않았습니다.\n\n"
                "PDF 파싱 기능을 사용하려면:\n"
                "1. 메뉴 > 도구 > Gemini > 설정\n"
                "2. 또는 환경변수 GEMINI_API_KEY 설정\n\n"
                "API 키 없이도 기본 기능은 사용 가능합니다."
            )
            
            if parent is None:
                temp_root.destroy()
                
        except (RuntimeError, ValueError) as e:
            print(f"⚠️ API 키 미설정: {api_error}")
    
    return True  # 실행은 허용 (경고만 표시)


# =============================================================================
# v3.6.0: 스마트 경로 자동 매핑 (편의성 향상)
# =============================================================================

def smart_path_recovery(invalid_path: str, file_extension: str = None) -> str:
    """
    v3.6.0: 유효하지 않은 경로에서 유사한 파일 자동 검색
    
    Args:
        invalid_path: 유효하지 않은 파일 경로
        file_extension: 찾을 파일 확장자 (예: '.xlsx', '.pdf')
    
    Returns:
        str: 복구된 경로 또는 빈 문자열
    """
    import os
    from pathlib import Path
    
    if not invalid_path:
        return ""
    
    invalid_path = Path(invalid_path)
    
    # 1. 파일이 존재하면 그대로 반환
    if invalid_path.exists():
        return str(invalid_path)
    
    # 2. 디렉토리 추출
    parent_dir = invalid_path.parent
    if not parent_dir.exists():
        # 상위 폴더도 없으면 기본 경로에서 검색
        parent_dir = BASE_DIR
    
    # 3. 확장자 결정
    if file_extension is None:
        file_extension = invalid_path.suffix or '.*'
    
    # 4. 유사한 파일 검색
    try:
        pattern = f"*{file_extension}" if file_extension != '.*' else "*"
        candidates = list(parent_dir.glob(pattern))
        
        if not candidates:
            return ""
        
        # 5. 원본 파일명과 가장 유사한 파일 찾기
        original_name = invalid_path.stem.lower()
        
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            if candidate.is_file():
                candidate_name = candidate.stem.lower()
                # 간단한 유사도 계산 (공통 문자 수)
                common = sum(1 for c in original_name if c in candidate_name)
                score = common / max(len(original_name), len(candidate_name), 1)
                
                if score > best_score:
                    best_score = score
                    best_match = candidate
        
        # 유사도 30% 이상이면 반환
        if best_match and best_score >= 0.3:
            return str(best_match)
        
        # 유사한 파일이 없으면 가장 최근 수정된 파일 반환
        candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return str(candidates[0]) if candidates else ""
        
    except (ValueError, TypeError, AttributeError) as e:
        print(f"경로 복구 오류: {e}")
        return ""


def get_recent_files(directory: str = None, extension: str = None, limit: int = 10) -> list:
    """
    v3.6.0: 최근 파일 목록 반환
    
    Args:
        directory: 검색할 디렉토리 (None이면 OUTPUT_DIR)
        extension: 파일 확장자 필터
        limit: 반환할 최대 파일 수
    
    Returns:
        list: 최근 파일 경로 목록
    """
    from pathlib import Path
    
    search_dir = Path(directory) if directory else OUTPUT_DIR
    
    if not search_dir.exists():
        return []
    
    try:
        pattern = f"*{extension}" if extension else "*"
        files = [f for f in search_dir.glob(pattern) if f.is_file()]
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return [str(f) for f in files[:limit]]
    except (OSError, IOError, PermissionError):
        return []


# =============================================================================
# v3.6.0: 안전한 백업 함수 (PermissionError 방지)
# =============================================================================

def safe_file_backup(source_path: str, backup_dir: str = None) -> tuple:
    """
    v3.6.0: PermissionError를 방지하는 안전한 파일 백업
    
    Args:
        source_path: 백업할 파일 경로
        backup_dir: 백업 디렉토리 (None이면 BACKUP_DIR)
    
    Returns:
        (success, backup_path or error_message)
    """
    import shutil
    import time
    from pathlib import Path
    
    source = Path(source_path)
    
    if not source.exists():
        return False, f"파일 없음: {source_path}"
    
    backup_directory = Path(backup_dir) if backup_dir else BACKUP_DIR
    backup_directory.mkdir(parents=True, exist_ok=True)
    
    # 백업 파일명 생성
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"{source.stem}_{timestamp}{source.suffix}"
    backup_path = backup_directory / backup_name
    
    # 파일 핸들 점검 및 재시도 로직
    max_retries = 3
    retry_delay = 0.5  # 초
    
    for attempt in range(max_retries):
        try:
            # 파일이 사용 중인지 확인 (Windows)
            try:
                with open(source, 'rb') as f:
                    pass  # 읽기 가능하면 OK
            except PermissionError:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return False, f"파일 사용 중: {source_path}"
            
            # 백업 실행
            shutil.copy2(source, backup_path)
            return True, str(backup_path)
            
        except PermissionError as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return False, f"권한 오류: {e}"
        except (OSError, IOError, PermissionError) as e:
            return False, f"백업 오류: {e}"
    
    return False, "백업 실패 (최대 재시도 초과)"


# =============================================================================
# v5.7.8: SQL 호환 함수 — config_sql에서 구현, 하위 호환용 래퍼 (출고/리포트 참조)
# =============================================================================
from config_sql import (
    sql_auto_increment as _sql_auto_increment_impl,
    sql_date_format as _sql_date_format_impl,
    sql_group_concat as _sql_group_concat_impl,
    sql_ifnull,
    sql_current_timestamp,
)


def sql_group_concat(column: str, separator: str = ',') -> str:
    """DB 타입에 따른 문자열 집계. SQLite: GROUP_CONCAT, PostgreSQL: STRING_AGG"""
    return _sql_group_concat_impl(DB_TYPE, column, separator)


def sql_date_format(column: str, format_str: str) -> str:
    """DB 타입에 따른 날짜 포맷. SQLite: strftime, PostgreSQL: to_char"""
    return _sql_date_format_impl(DB_TYPE, column, format_str)


def sql_auto_increment() -> str:
    """자동 증가 컬럼 타입. SQLite: INTEGER PRIMARY KEY AUTOINCREMENT, PG: SERIAL PRIMARY KEY"""
    return _sql_auto_increment_impl(DB_TYPE)


# 모듈 로드 시 로깅 초기화
_logger = setup_logging()
