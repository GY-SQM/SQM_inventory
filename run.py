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
        logger.info(f"{APP_NAME} v{__version__}")
        sys.exit(0)
    if "--check" in sys.argv:
        ok = run_self_diagnostic()
        sys.exit(0 if ok else 1)

    # 허용 PC 등록 (기본: 기존 목록 유지 + 현재 PC 추가/갱신)
    if "--register-pc" in sys.argv:
        try:
            from security.mac_guard import register_current_pc
            replace_mode = "--replace-pc-list" in sys.argv
            ok, msg = register_current_pc(replace=replace_mode)
            logger.info(f"[PC Guard] {msg}")
            sys.exit(0 if ok else 1)
        except ImportError as e:
            logger.error(f"[PC Guard] 등록 실패: {e}")
            sys.exit(1)

    # PC 잠금(라이선스): 허가된 PC 외 실행 차단. --no-license 또는 SQM_SKIP_LICENSE=1 이면 스킵
    skip_license = "--no-license" in sys.argv or os.environ.get("SQM_SKIP_LICENSE", "").strip() in ("1", "true", "yes")
    if not skip_license:
        try:
            from security.mac_guard import verify_pc
            if not verify_pc(show_gui_error=True):
                logger.error("[PC Guard] 이 PC는 인가되지 않았습니다. 프로그램을 종료합니다.")
                sys.exit(99)
        except ImportError as _e:
            logger.debug(f"[run] PC Guard 미로드: {_e}")

    logger.info("=" * 60)
    logger.info(f"  {APP_NAME} v{__version__}")
    logger.info("  개발: Ruby")
    logger.info("=" * 60)

    if "--no-check" not in sys.argv:
        results = run_self_check()
        print_self_check_report(results)
        if not results['passed']:
            logger.error("환경 점검 실패로 프로그램을 종료합니다.")
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
