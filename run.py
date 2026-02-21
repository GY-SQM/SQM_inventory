#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 메인 실행 파일 (★ 유일한 엔트리 포인트 ★)

★★★ v2.8.0: 이 파일이 프로그램의 유일한 진입점입니다 ★★★
★★★ python -m gui_app_modular 도 이 main()으로 위임됩니다. ★★★

사용법:
    python run.py              # GUI 실행 (기본)
    python -m gui_app_modular   # 위와 동일 (run.main() 호출)
    python run.py --cli        # CLI 테스트 모드
    python run.py --backup     # 백업만 실행
    python run.py --check      # 시스템 점검만 실행
    python run.py --version    # 버전 정보

P3: 진단·백업·GUI/CLI 로직은 run_bootstrap.py 로 분리.
"""

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, OSError) as e:
        logger.debug(f"Suppressed: {e}")

try:
    from version import __version__, APP_NAME
except ImportError:
    __version__ = "0.0.0"
    APP_NAME = "SQM 재고관리 시스템"


def main():
    """메인 함수 — run_bootstrap 위임"""
    from run_bootstrap import (
        run_self_diagnostic,
        run_self_check,
        print_self_check_report,
        check_dependencies,
        run_cli,
        run_backup_only,
        run_gui,
    )

    if "--version" in sys.argv:
        print(f"{APP_NAME} v{__version__}")
        sys.exit(0)
    if "--check" in sys.argv:
        ok = run_self_diagnostic()
        sys.exit(0 if ok else 1)

    # MAC/GUID(PC Guard) 체크: 기본 비활성화. 필요 시 --mac-check 로만 검사 수행
    if "--mac-check" in sys.argv:
        try:
            from security.mac_guard import verify_pc
            if not verify_pc(show_gui_error=True):
                print("[PC Guard] 이 PC에서는 실행이 차단되었습니다.")
                sys.exit(99)
        except ImportError as _e:
            logger.debug(f"[run] 무시: {_e}")

    print("=" * 60)
    print(f"  {APP_NAME} v{__version__}")
    print("  개발: Ruby")
    print("=" * 60)

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


if __name__ == "__main__":
    main()
