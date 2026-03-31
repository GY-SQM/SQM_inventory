"""
run_bootstrap.py — SQM v8.1.0
==============================

run.py의 진단·백업·GUI/CLI 로직 분리 모듈.
run.py에서 import하여 사용.

필수 함수:
  check_dependencies()       — 필수 패키지 존재 확인
  print_self_check_report()  — 점검 결과 출력
  run_backup_only()          — 백업만 실행
  run_cli()                  — CLI 테스트 모드
  run_gui()                  — GUI 실행 (메인)
  run_self_check()           — 환경 점검
  run_self_diagnostic()      — 상세 진단

[수정이력]
  2026-03-20  v8.1.0  신규 생성 (run.py에서 분리)
"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# 1. 의존성 확인
# ─────────────────────────────────────────────────────────────

REQUIRED_PACKAGES = [
    ("tkinter",       "tkinter"),
    ("ttkbootstrap",  "ttkbootstrap"),
    ("sqlite3",       "sqlite3"),
]

OPTIONAL_PACKAGES = [
    ("pandas",        "pandas"),
    ("openpyxl",      "openpyxl"),
    ("pdfplumber",    "pdfplumber"),
    ("fitz",          "PyMuPDF"),
    ("PIL",           "Pillow"),
]


def check_dependencies() -> bool:
    """필수 패키지 존재 여부 확인. 하나라도 없으면 False."""
    all_ok = True
    for mod_name, pkg_name in REQUIRED_PACKAGES:
        try:
            __import__(mod_name)
        except ImportError:
            logger.error(f"[의존성] 필수 패키지 없음: {pkg_name}  →  pip install {pkg_name}")
            all_ok = False
    return all_ok


# ─────────────────────────────────────────────────────────────
# 2. 자가 점검
# ─────────────────────────────────────────────────────────────

def run_self_check() -> dict:
    """환경 점검 — DB 경로, 패키지, 폴더 구조 확인."""
    results = {
        "passed": True,
        "checks": [],
    }

    def _add(name: str, ok: bool, msg: str = ""):
        results["checks"].append({"name": name, "ok": ok, "msg": msg})
        if not ok:
            results["passed"] = False

    # Python 버전
    major, minor = sys.version_info[:2]
    _add("Python 버전", major >= 3 and minor >= 9,
         f"Python {major}.{minor} (권장: 3.9+)")

    # 필수 패키지
    for mod_name, pkg_name in REQUIRED_PACKAGES:
        try:
            __import__(mod_name)
            _add(f"패키지 {pkg_name}", True)
        except ImportError:
            _add(f"패키지 {pkg_name}", False, f"pip install {pkg_name}")

    # 선택 패키지 (경고만)
    for mod_name, pkg_name in OPTIONAL_PACKAGES:
        try:
            __import__(mod_name)
            _add(f"선택 {pkg_name}", True)
        except ImportError:
            # 선택 패키지 없어도 passed=True 유지
            logger.debug(f"[점검] 선택 패키지 없음: {pkg_name}")

    # data/db 폴더
    db_dir = Path("data") / "db"
    if not db_dir.exists():
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
            _add("DB 폴더", True, f"{db_dir} 생성됨")
        except Exception as e:
            _add("DB 폴더", False, str(e))
    else:
        _add("DB 폴더", True, str(db_dir))

    return results


def print_self_check_report(results: dict) -> None:
    """점검 결과 로그 출력."""
    logger.info("─" * 40)
    logger.info("[환경 점검 결과]")
    for c in results.get("checks", []):
        mark = "✅" if c["ok"] else "❌"
        msg  = f"  {c['msg']}" if c.get("msg") else ""
        logger.info(f"  {mark} {c['name']}{msg}")
    status = "통과" if results["passed"] else "실패"
    logger.info(f"[환경 점검] {status}")
    logger.info("─" * 40)


def run_self_diagnostic() -> bool:
    """상세 진단 모드 (--check 옵션)."""
    logger.info("[진단 모드] 시작")
    results = run_self_check()
    print_self_check_report(results)

    # 선택 패키지 상세 출력
    for mod_name, pkg_name in OPTIONAL_PACKAGES:
        try:
            m = __import__(mod_name)
            ver = getattr(m, "__version__", "?")
            logger.info(f"  ℹ️  {pkg_name} {ver}")
        except ImportError:
            logger.info(f"  ⚠️  {pkg_name} 미설치 (선택 패키지)")

    logger.info("[진단 모드] 완료")
    return results["passed"]


# ─────────────────────────────────────────────────────────────
# 3. 백업
# ─────────────────────────────────────────────────────────────

def run_backup_only() -> None:
    """--backup 옵션: DB 백업만 실행 후 종료."""
    logger.info("[백업 모드] 시작")
    try:
        from utils.backup import run_backup
        ok = run_backup()
        logger.info(f"[백업 모드] {'완료' if ok else '실패'}")
    except ImportError:
        # utils/backup.py 없으면 sqlite3로 직접 백업
        import shutil, sqlite3
        from datetime import datetime
        db_path = Path("data") / "db" / "sqm_inventory.db"
        if db_path.exists():
            ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
            dst = db_path.parent / f"sqm_inventory_backup_{ts}.db"
            shutil.copy2(db_path, dst)
            logger.info(f"[백업 모드] {dst}")
        else:
            logger.warning(f"[백업 모드] DB 없음: {db_path}")
    except Exception as e:
        logger.error(f"[백업 모드] 오류: {e}")


# ─────────────────────────────────────────────────────────────
# 4. CLI 모드
# ─────────────────────────────────────────────────────────────

def run_cli() -> None:
    """--cli 옵션: CLI 테스트 모드."""
    logger.info("[CLI 모드] 시작")
    try:
        from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
        db_path = str(Path("data") / "db" / "sqm_inventory.db")
        engine  = SQMInventoryEngineV3(db_path)
        logger.info(f"[CLI 모드] Engine OK: {db_path}")

        # 간단 상태 조회
        try:
            rows = engine.db.fetchall(
                "SELECT status, COUNT(*) as cnt FROM inventory_tonbag GROUP BY status"
            )
            for r in rows:
                logger.info(f"  {r.get('status','?')}: {r.get('cnt',0)}개")
        except Exception as qe:
            logger.debug(f"[CLI] 조회 무시: {qe}")

    except Exception as e:
        logger.error(f"[CLI 모드] 오류: {e}")
    logger.info("[CLI 모드] 종료")


# ─────────────────────────────────────────────────────────────
# 5. GUI 실행 (메인)
# ─────────────────────────────────────────────────────────────

def run_gui() -> None:
    """메인 GUI 실행."""
    logger.info("[GUI] 시작")
    try:
        from gui_app_modular.main_app import SQMInventoryAppFull

        app = SQMInventoryAppFull()

        has_root = hasattr(app, "root") and app.root is not None
        logger.info(
            "[GUI] 인스턴스 점검: type=%s has_run=%s has_mainloop=%s has_root=%s",
            type(app).__name__,
            hasattr(app, "run") and callable(getattr(app, "run")),
            hasattr(app, "mainloop") and callable(getattr(app, "mainloop")),
            has_root,
        )
        if has_root:
            logger.info("[GUI] root type=%s", type(app.root).__name__)

        if hasattr(app, "run") and callable(getattr(app, "run")):
            app.run()
        elif hasattr(app, "mainloop") and callable(getattr(app, "mainloop")):
            app.mainloop()
        elif has_root and hasattr(app.root, "mainloop"):
            app.root.mainloop()
        else:
            raise RuntimeError(
                "GUI 실행 실패: app.run / app.mainloop / app.root.mainloop 을 사용할 수 없습니다."
            )
    except Exception as e:
        logger.critical(f"[GUI] 치명적 오류: {e}", exc_info=True)
        raise
    finally:
        logger.info("[GUI] 종료")
