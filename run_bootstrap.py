# -*- coding: utf-8 -*-
"""
SQM - 실행 부트스트랩 (P3: run.py 슬림화)
==========================================
진단, 백업, GUI/CLI 실행 진입 로직.
run.py는 이 모듈을 import하여 main()만 유지.
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

try:
    from version import __version__, APP_NAME
except ImportError:
    __version__ = "0.0.0"
    APP_NAME = "SQM 재고관리 시스템"


def run_self_diagnostic():
    """
    부팅 시 Self-Diagnostic.
    누락 모듈/설정/DB 경로/권한/모델 존재 여부 점검.
    """
    print("=" * 50)
    print(f"🔍 {APP_NAME} v{__version__} 시스템 점검")
    print("=" * 50)

    issues = []
    warnings = []

    print("\n1️⃣ 필수 모듈 확인...")
    required_modules = [
        ('pandas', 'pandas'),
        ('openpyxl', 'openpyxl'),
        ('fitz', 'pymupdf'),
        ('tkinter', 'tkinter (시스템)'),
        ('google.genai', 'google-genai (Gemini API) ★필수★'),
    ]
    for module, name in required_modules:
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError:
            print(f"   ❌ {name} - 미설치")
            issues.append(f"필수 모듈 누락: {name}")
            if module == 'google.genai':
                print("      → 자동 설치 시도 중...")
                try:
                    import subprocess
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'google-genai', '-q'])
                    __import__(module)
                    print(f"   ✅ {name} - 자동 설치 성공!")
                    issues.remove(f"필수 모듈 누락: {name}")
                except (ValueError, TypeError, KeyError) as e:
                    print(f"      ❌ 자동 설치 실패: {e}")
                    print("      → 수동 설치: pip install google-genai")

    print("\n2️⃣ 선택적 모듈 확인...")
    for module, name in [
        ('ttkbootstrap', 'ttkbootstrap (UI 테마)'),
        ('reportlab', 'reportlab (PDF 생성)'),
        ('docx', 'python-docx (Word 생성)'),
    ]:
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError:
            print(f"   ⚠️ {name} - 미설치 (선택적)")
            warnings.append(f"선택적 모듈 누락: {name}")

    print("\n3️⃣ 설정 파일 확인...")
    try:
        from config import SETTINGS_FILE, DB_PATH, GEMINI_API_KEY, API_KEY_SOURCE
        if SETTINGS_FILE.exists():
            print("   ✅ settings.ini 존재")
        else:
            print("   ⚠️ settings.ini 없음 (기본값 사용)")
            warnings.append("settings.ini 없음")
        if API_KEY_SOURCE == 'ENV':
            print("   ✅ API 키: 환경변수 (안전)")
        elif API_KEY_SOURCE == 'INI':
            print("   ⚠️ API 키: settings.ini (보안 주의)")
            warnings.append("API 키가 ini에 평문 저장됨")
        else:
            print("   ℹ️ API 키: 미설정")
    except (ValueError, TypeError, KeyError) as e:
        print(f"   ❌ 설정 로드 실패: {e}")
        issues.append(f"설정 로드 실패: {e}")

    print("\n4️⃣ 데이터베이스 확인...")
    try:
        from config import DB_PATH, DB_DIR
        if DB_DIR.exists():
            print(f"   ✅ DB 디렉토리 존재: {DB_DIR}")
        else:
            print(f"   ℹ️ DB 디렉토리 생성 예정: {DB_DIR}")
        if DB_PATH.exists():
            print(f"   ✅ DB 파일 존재: {DB_PATH.name}")
            if os.access(DB_PATH, os.W_OK):
                print("   ✅ DB 쓰기 권한 있음")
            else:
                print("   ❌ DB 쓰기 권한 없음")
                issues.append("DB 쓰기 권한 없음")
        else:
            print("   ℹ️ DB 파일 없음 (첫 실행 시 생성)")
    except (ValueError, TypeError, KeyError) as e:
        print(f"   ❌ DB 경로 확인 실패: {e}")
        issues.append(f"DB 경로 확인 실패: {e}")

    logger.debug("\n5️⃣ Gemini API 확인...")
    try:
        from config import GEMINI_API_KEY, GEMINI_MODEL
        if GEMINI_API_KEY and not GEMINI_API_KEY.startswith('your-'):
            print("   ✅ API 키 설정됨")
            print(f"   ℹ️ 모델: {GEMINI_MODEL}")
            try:
                from google import genai
                client = genai.Client(api_key=GEMINI_API_KEY)
                models = list(client.models.list())
                print(f"   ✅ Gemini 연결 성공 ({len(models)}개 모델 사용 가능)")
            except (ValueError, TypeError, KeyError) as api_e:
                print(f"   ⚠️ Gemini 연결 실패: {api_e}")
                warnings.append("Gemini API 연결 실패")
        else:
            print("   ℹ️ API 키 미설정 (정규식 파서 사용)")
    except ImportError:
        print("   ⚠️ google-genai 미설치")
    except (ValueError, TypeError, KeyError) as e:
        print(f"   ⚠️ Gemini 확인 실패: {e}")

    logger.debug("\n" + "=" * 50)
    if issues:
        print(f"❌ 심각한 문제 {len(issues)}개:")
        for issue in issues:
            logger.debug(f"   • {issue}")
    if warnings:
        print(f"⚠️ 경고 {len(warnings)}개:")
        for warn in warnings:
            logger.debug(f"   • {warn}")
    if not issues and not warnings:
        print("✅ 모든 점검 통과!")
    print("=" * 50)
    return len(issues) == 0


def check_dependencies():
    """필수 라이브러리 확인"""
    missing = []
    optional_missing = []
    try:
        __import__("pandas")
    except ImportError:
        missing.append("pandas")
    try:
        __import__("openpyxl")
    except ImportError:
        missing.append("openpyxl")
    try:
        import fitz  # noqa: F401
    except ImportError:
        optional_missing.append("pymupdf")
    try:
        __import__("tkinter")
    except ImportError:
        missing.append("tkinter")
    if optional_missing:
        print(f"  ⚠️ 선택 라이브러리 미설치: {', '.join(optional_missing)}")
        print(f"     → PDF 파싱 기능 제한. pip install {' '.join(optional_missing)}")
    if missing:
        print("필수 라이브러리가 설치되지 않았습니다:")
        for lib in missing:
            print(f"   - {lib}")
        print("\n설치 명령어:")
        print(f"   pip install {' '.join(missing)}")
        return False
    return True


def run_auto_backup():
    """프로그램 시작 시 자동 백업"""
    try:
        from utils.backup import auto_backup_on_startup
        success, msg = auto_backup_on_startup()
        if success:
            print(f"📦 {msg}")
        else:
            print(f"⚠️ 백업: {msg}")
        return success
    except (ValueError, TypeError, KeyError) as e:
        print(f"⚠️ 백업 모듈 로드 실패: {e}")
        return False


def run_gui():
    """GUI 모드 실행"""
    try:
        run_auto_backup()
        try:
            print("✅ ttkbootstrap 테마 사용")
        except ImportError:
            print("ℹ️ 기본 ttk 테마 사용 (ttkbootstrap 미설치)")
        try:
            from config import GEMINI_API_KEY
            if GEMINI_API_KEY and len(GEMINI_API_KEY) > 10:
                print(f"✅ Gemini API 키 로드됨 ({GEMINI_API_KEY[:10]}...)")
            else:
                print("ℹ️ Gemini API 키 미설정 (settings.ini 확인)")
        except ImportError:
            print("ℹ️ Gemini API 설정 없음")
        from gui_app_modular import SQMInventoryApp
        logger.debug("🚀 SQM 재고관리 시스템 GUI 시작...")
        app = SQMInventoryApp()
        app.run()
    except (ValueError, TypeError, KeyError) as e:
        print(f"❌ GUI 실행 오류: {str(e)}")
        import traceback
        traceback.print_exc()


def run_backup_only():
    """백업만 실행"""
    try:
        from utils.backup import force_backup, list_backups
        print("\n📦 강제 백업 실행 중...")
        success, msg = force_backup()
        logger.debug(f"   결과: {msg}")
        print("\n📋 백업 목록:")
        for backup in list_backups():
            logger.debug(f"   - {backup['filename']} ({backup['size_str']}) - {backup['created_str']}")
    except (ValueError, TypeError, KeyError) as e:
        print(f"❌ 백업 오류: {e}")


def run_cli():
    """CLI 테스트 모드"""
    try:
        from dev_tools.test_real_files import test_real_files
        test_real_files()
    except ImportError:
        print("❌ test_real_files 모듈을 찾을 수 없습니다.")


def run_self_check():
    """
    프로그램 시작 전 환경 점검.
    DB 경로/권한, 공유폴더, 백업/출력 폴더 권한, 필수 라이브러리.
    """
    from pathlib import Path
    results = {'passed': True, 'checks': [], 'warnings': [], 'errors': []}
    try:
        from config import DB_PATH, BACKUP_DIR, OUTPUT_DIR
    except ImportError:
        results['errors'].append("config.py를 찾을 수 없습니다")
        results['passed'] = False
        return results

    db_path = Path(DB_PATH)
    db_dir = db_path.parent
    if db_dir.exists():
        results['checks'].append(f"✅ DB 디렉토리 존재: {db_dir}")
    else:
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
            results['checks'].append(f"✅ DB 디렉토리 생성됨: {db_dir}")
        except (OSError, IOError, PermissionError) as e:
            results['errors'].append(f"❌ DB 디렉토리 생성 실패: {e}")
            results['passed'] = False

    db_str = str(DB_PATH)
    is_network = db_str.startswith('\\\\') or db_str.startswith('//')
    if not is_network and sys.platform == 'win32' and len(db_str) >= 2 and db_str[1] == ':':
        try:
            import ctypes
            drive = db_str[0].upper() + ':'
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive + '\\')
            if drive_type == 4:
                is_network = True
        except (ValueError, TypeError, AttributeError) as e:
            logger.debug(f"Suppressed: Windows drive type check: {e}")
    if is_network:
        results['warnings'].append("⚠️ 공유폴더 감지됨 - DELETE 모드로 동작합니다")
        results['warnings'].append("⚠️ 동시 사용자가 있으면 DB 쓰기 대기 발생 가능")
        try:
            __import__("filelock")
            results['checks'].append("✅ filelock 라이브러리 설치됨 (락 관리 가능)")
        except ImportError:
            results['warnings'].append("⚠️ filelock 미설치 - pip install filelock 권장")
    else:
        results['checks'].append("✅ 로컬 경로 - WAL 모드 사용 가능")

    try:
        test_db = db_dir / ".write_test.tmp"
        test_db.write_text("test")
        test_db.unlink()
        results['checks'].append("✅ DB 폴더 쓰기 권한 확인")
    except (OSError, IOError, PermissionError) as e:
        results['errors'].append(f"❌ DB 폴더 쓰기 권한 없음: {e}")
        results['passed'] = False

    backup_dir = Path(BACKUP_DIR)
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        test_file = backup_dir / ".write_test.tmp"
        test_file.write_text("test")
        test_file.unlink()
        results['checks'].append(f"✅ 백업 폴더 쓰기 권한 확인: {backup_dir}")
    except (OSError, IOError, PermissionError) as e:
        results['warnings'].append(f"⚠️ 백업 폴더 쓰기 실패: {e}")

    output_dir = Path(OUTPUT_DIR)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        results['checks'].append(f"✅ 출력 폴더 준비됨: {output_dir}")
    except (OSError, IOError, PermissionError) as e:
        results['warnings'].append(f"⚠️ 출력 폴더 생성 실패: {e}")

    return results


def print_self_check_report(results: dict) -> None:
    """Self-Check 결과 출력"""
    print("=" * 60)
    print(f"  SQM 환경 점검 (v{__version__})")
    print("=" * 60)
    for check in results['checks']:
        print(f"  {check}")
    for warning in results['warnings']:
        print(f"  {warning}")
    for error in results['errors']:
        print(f"  {error}")
    print("-" * 60)
    if results['passed']:
        print("  환경 점검 통과 - 프로그램 시작")
    else:
        print("  환경 점검 실패 - 위 오류를 해결해 주세요")
    print("=" * 60)
