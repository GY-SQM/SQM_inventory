#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 메인 실행 파일 (★ 유일한 진입점 ★)

★★★ v2.8.0: 이 파일이 프로그램의 유일한 진입점입니다 ★★★

사용법:
    python run_app.py              # GUI 실행 (기본)
    python run_app.py --cli        # CLI 테스트 모드
    python run_app.py --backup     # 백업만 실행
    python run_app.py --check      # 시스템 점검만 실행
    python run_app.py --version    # 버전 정보

다른 파일 설명:
    - main.py: 레거시 (run_app.py 사용 권장)
    - gui_app.py: GUI 클래스 정의 (직접 실행 비권장)

Author: Ruby
"""

import os
import sys
import logging

# 패키지 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows 콘솔 cp949에서 이모지/한글 출력 오류 방지 (v5.6.1)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

logger = logging.getLogger(__name__)

# ★ v2.5.4: 버전 단일화
try:
    from version import __version__, APP_NAME
except ImportError:
    __version__ = "3.9.4"
    APP_NAME = "SQM 재고관리 시스템"


def run_self_diagnostic():
    """
    v2.8.0: 부팅 시 Self-Diagnostic
    누락 모듈/설정/DB 경로/권한/모델 존재 여부를 점검
    """
    print("=" * 50)
    print(f"🔍 {APP_NAME} v{__version__} 시스템 점검")
    print("=" * 50)
    
    issues = []
    warnings = []
    
    # 1. 필수 모듈 확인
    print("\n1️⃣ 필수 모듈 확인...")
    required_modules = [
        ('pandas', 'pandas'),
        ('openpyxl', 'openpyxl'),
        ('fitz', 'pymupdf'),
        ('tkinter', 'tkinter (시스템)'),
        ('google.genai', 'google-genai (Gemini API) ★필수★'),  # v2.9.13: 필수로 변경
    ]
    
    for module, name in required_modules:
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError:
            print(f"   ❌ {name} - 미설치")
            issues.append(f"필수 모듈 누락: {name}")
            
            # ★★★ v2.9.13: google-genai 자동 설치 시도 ★★★
            if module == 'google.genai':
                print(f"      → 자동 설치 시도 중...")
                try:
                    import subprocess
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'google-genai', '-q'])
                    __import__(module)
                    print(f"   ✅ {name} - 자동 설치 성공!")
                    issues.remove(f"필수 모듈 누락: {name}")
                except (ValueError, TypeError, KeyError) as e:
                    print(f"      ❌ 자동 설치 실패: {e}")
                    print(f"      → 수동 설치: pip install google-genai")
    
    # 2. 선택적 모듈 확인
    print("\n2️⃣ 선택적 모듈 확인...")
    optional_modules = [
        ('ttkbootstrap', 'ttkbootstrap (UI 테마)'),
        ('reportlab', 'reportlab (PDF 생성)'),
        ('docx', 'python-docx (Word 생성)'),
    ]
    
    for module, name in optional_modules:
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError:
            print(f"   ⚠️ {name} - 미설치 (선택적)")
            warnings.append(f"선택적 모듈 누락: {name}")
    
    # 3. 설정 파일 확인
    print("\n3️⃣ 설정 파일 확인...")
    try:
        from config import SETTINGS_FILE, DB_PATH, GEMINI_API_KEY, API_KEY_SOURCE
        
        if SETTINGS_FILE.exists():
            print(f"   ✅ settings.ini 존재")
        else:
            print(f"   ⚠️ settings.ini 없음 (기본값 사용)")
            warnings.append("settings.ini 없음")
        
        # API 키 출처 확인
        if API_KEY_SOURCE == 'ENV':
            print(f"   ✅ API 키: 환경변수 (안전)")
        elif API_KEY_SOURCE == 'INI':
            print(f"   ⚠️ API 키: settings.ini (보안 주의)")
            warnings.append("API 키가 ini에 평문 저장됨")
        else:
            print(f"   ℹ️ API 키: 미설정")
            
    except (ValueError, TypeError, KeyError) as e:
        print(f"   ❌ 설정 로드 실패: {e}")
        issues.append(f"설정 로드 실패: {e}")
    
    # 4. DB 경로/권한 확인
    print("\n4️⃣ 데이터베이스 확인...")
    try:
        from config import DB_PATH, DB_DIR
        
        if DB_DIR.exists():
            print(f"   ✅ DB 디렉토리 존재: {DB_DIR}")
        else:
            print(f"   ℹ️ DB 디렉토리 생성 예정: {DB_DIR}")
        
        if DB_PATH.exists():
            print(f"   ✅ DB 파일 존재: {DB_PATH.name}")
            # 쓰기 권한 확인
            if os.access(DB_PATH, os.W_OK):
                print(f"   ✅ DB 쓰기 권한 있음")
            else:
                print(f"   ❌ DB 쓰기 권한 없음")
                issues.append("DB 쓰기 권한 없음")
        else:
            print(f"   ℹ️ DB 파일 없음 (첫 실행 시 생성)")
            
    except (ValueError, TypeError, KeyError) as e:
        print(f"   ❌ DB 경로 확인 실패: {e}")
        issues.append(f"DB 경로 확인 실패: {e}")
    
    # 5. Gemini 모델 확인 (API 키가 있을 때만)
    logger.debug("\n5️⃣ Gemini API 확인...")
    try:
        from config import GEMINI_API_KEY, GEMINI_MODEL
        
        if GEMINI_API_KEY and not GEMINI_API_KEY.startswith('your-'):
            print(f"   ✅ API 키 설정됨")
            print(f"   ℹ️ 모델: {GEMINI_MODEL}")
            
            # 모델 존재 확인 (선택적)
            try:
                from google import genai
                client = genai.Client(api_key=GEMINI_API_KEY)
                models = list(client.models.list())
                print(f"   ✅ Gemini 연결 성공 ({len(models)}개 모델 사용 가능)")
            except (ValueError, TypeError, KeyError) as api_e:
                print(f"   ⚠️ Gemini 연결 실패: {api_e}")
                warnings.append(f"Gemini API 연결 실패")
        else:
            print(f"   ℹ️ API 키 미설정 (정규식 파서 사용)")
            
    except ImportError:
        print(f"   ⚠️ google-genai 미설치")
    except (ValueError, TypeError, KeyError) as e:
        print(f"   ⚠️ Gemini 확인 실패: {e}")
    
    # 결과 요약
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
        import fitz  # noqa: F401 - PyMuPDF
    except ImportError:
        optional_missing.append("pymupdf")  # v5.6.0: 선택적 (PDF 파싱에만 필요)

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
        print(f"\n설치 명령어:")
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
        # ★ 자동 백업 실행 (v2.5.4)
        run_auto_backup()

        # ttkbootstrap 시도
        try:
            print("✅ ttkbootstrap 테마 사용")
        except ImportError:
            print("ℹ️ 기본 ttk 테마 사용 (ttkbootstrap 미설치)")

        # Gemini API 상태 확인
        try:
            from config import GEMINI_API_KEY
            if GEMINI_API_KEY and len(GEMINI_API_KEY) > 10:
                print(f"✅ Gemini API 키 로드됨 ({GEMINI_API_KEY[:10]}...)")
            else:
                print("ℹ️ Gemini API 키 미설정 (settings.ini 확인)")
        except ImportError:  # v2.5.4 수정
            print("ℹ️ Gemini API 설정 없음")

        # ★★★ v2.9.99: 모듈화 버전으로 전환 ★★★
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


def main():
    """메인 함수"""
    # ★ --version / --check 는 환경 점검·이모지 출력 전에 처리 (cp949 콘솔 오류 방지)
    if "--version" in sys.argv:
        logger.debug(f"{APP_NAME} v{__version__}")
        sys.exit(0)
    if "--check" in sys.argv:
        ok = run_self_diagnostic()
        sys.exit(0 if ok else 1)

    # ★ v5.6.0: MAC + MachineGuid 2중 PC 잠금 (--no-mac-check로 비활성화 가능)
    if "--no-mac-check" not in sys.argv:
        try:
            from security.mac_guard import verify_pc
            if not verify_pc(show_gui_error=True):
                print("[PC Guard] 이 PC에서는 실행이 차단되었습니다.")
                sys.exit(99)
        except ImportError as _e:
            logger.debug(f"[run_app] 무시: {_e}")

    print("=" * 60)
    print(f"  {APP_NAME} v{__version__}")
    print("  개발: Ruby")
    print("=" * 60)

    # ★ v2.5.4: 환경 점검
    if "--no-check" not in sys.argv:
        results = run_self_check()
        print_self_check_report(results)
        if not results['passed']:
            print("환경 점검 실패로 프로그램을 종료합니다.")
            sys.exit(1)

    if not check_dependencies():
        sys.exit(1)

    if "--cli" in sys.argv:
        run_cli()
    elif "--backup" in sys.argv:
        run_backup_only()
    else:
        run_gui()


# main() 호출은 파일 맨 끝에서 실행됨 (아래 참조)


# =============================================================================
# ★ v2.5.4: 시작 시 Self-Check 리포트
# =============================================================================

def run_self_check() -> dict:
    """
    프로그램 시작 전 환경 점검 (v2.5.4)
    
    점검 항목:
    - DB 경로 및 쓰기 권한
    - 공유폴더 여부
    - 백업 폴더 권한
    - 출력 폴더 권한
    - 필수 라이브러리
    
    Returns:
        dict: 점검 결과
    """
    from pathlib import Path
    
    results = {
        'passed': True,
        'checks': [],
        'warnings': [],
        'errors': []
    }
    
    try:
        from config import DB_PATH, BACKUP_DIR, OUTPUT_DIR
    except ImportError:
        results['errors'].append("config.py를 찾을 수 없습니다")
        results['passed'] = False
        return results
    
    # 1. DB 경로 확인
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
    
    # 2. 공유폴더 감지 (상세)
    db_str = str(DB_PATH)
    is_network = db_str.startswith('\\\\') or db_str.startswith('//')
    
    # Windows 네트워크 드라이브 추가 감지
    if not is_network and sys.platform == 'win32' and len(db_str) >= 2 and db_str[1] == ':':
        try:
            import ctypes
            drive = db_str[0].upper() + ':'
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive + '\\')
            if drive_type == 4:  # DRIVE_REMOTE
                is_network = True
        except (ValueError, TypeError, AttributeError) as e:
            logger.debug(f"Suppressed: Windows drive type check (Linux/Mac or API error): {e}")
    
    if is_network:
        results['warnings'].append(f"⚠️ 공유폴더 감지됨 - DELETE 모드로 동작합니다")
        results['warnings'].append(f"⚠️ 동시 사용자가 있으면 DB 쓰기 대기 발생 가능")
        
        # filelock 라이브러리 확인
        try:
            __import__("filelock")
            results['checks'].append(f"✅ filelock 라이브러리 설치됨 (락 관리 가능)")
        except ImportError:
            results['warnings'].append(f"⚠️ filelock 미설치 - pip install filelock 권장")
    else:
        results['checks'].append(f"✅ 로컬 경로 - WAL 모드 사용 가능")
    
    # 3. DB 쓰기 테스트
    try:
        test_db = db_dir / ".write_test.tmp"
        test_db.write_text("test")
        test_db.unlink()
        results['checks'].append(f"✅ DB 폴더 쓰기 권한 확인")
    except (OSError, IOError, PermissionError) as e:
        results['errors'].append(f"❌ DB 폴더 쓰기 권한 없음: {e}")
        results['passed'] = False
    
    # 4. 백업 폴더 확인
    backup_dir = Path(BACKUP_DIR)
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        test_file = backup_dir / ".write_test.tmp"
        test_file.write_text("test")
        test_file.unlink()
        results['checks'].append(f"✅ 백업 폴더 쓰기 권한 확인: {backup_dir}")
    except (OSError, IOError, PermissionError) as e:
        results['warnings'].append(f"⚠️ 백업 폴더 쓰기 실패: {e}")
    
    # 5. 출력 폴더 확인
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


# =============================================================================
# 프로그램 실행
# =============================================================================
if __name__ == "__main__":
    main()
