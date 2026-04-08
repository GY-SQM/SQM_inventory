# -*- coding: utf-8 -*-
"""
SQM 자동 스케줄러 v2 — 4가지 통합
① 매일 09:00 DB 자동 백업
② 매일 09:00 재고 정합성 점검
③ 매일 09:00 Con Return 만료 경고
④ 로그 자동 로테이션 (10MB)
배치: scripts/backup_scheduler.py
생성일: 2026-04-08
"""
import logging, logging.handlers, os, sys, time
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

_env = _ROOT / '.env'
if _env.exists():
    with open(_env, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

(_ROOT / 'logs').mkdir(exist_ok=True)
_handler = logging.handlers.RotatingFileHandler(
    str(_ROOT / 'logs' / 'backup_scheduler.log'),
    maxBytes=10*1024*1024, backupCount=3, encoding='utf-8'
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [scheduler] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(), _handler]
)
logger = logging.getLogger(__name__)

SCHEDULE_HOUR   = int(os.getenv("BACKUP_SCHEDULE_HOUR", "9"))
CON_RETURN_WARN = int(os.getenv("CON_RETURN_WARN_DAYS", "7"))
CON_RETURN_CRIT = int(os.getenv("CON_RETURN_CRIT_DAYS", "3"))


def _send(msg):
    try:
        from scripts.telegram_notify import send
        send(msg)
    except Exception as e:
        logger.warning(f"Telegram 발송 실패: {e}")


def run_backup() -> bool:
    from utils.backup import force_backup
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    try:
        ok, msg = force_backup()
        _send(f"{'✅' if ok else '❌'} <b>SQM 자동 백업 {'완료' if ok else '실패'}</b>\n{now_str}\n{msg}")
        return ok
    except Exception as e:
        logger.error(f"백업 예외: {e}", exc_info=True)
        _send(f"🚨 <b>백업 예외</b>\n{str(e)[:200]}")
        return False


def run_integrity() -> None:
    try:
        from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
        engine = SQMInventoryEngineV3()
        result = engine.fix_lot_status_integrity()
        engine.close()
        fixed, errors = result.get('fixed',0), result.get('errors',[])
        if fixed > 0 or errors:
            msg = f"⚠️ <b>정합성 이상</b>\n수정: {fixed}건 / 오류: {len(errors)}건"
            if errors:
                msg += "\n" + "\n".join(f"  • {e}" for e in errors[:3])
            _send(msg)
        else:
            logger.info("정합성 이상 없음")
    except Exception as e:
        logger.warning(f"정합성 예외: {e}")


def run_con_return_check() -> None:
    """Con Return 만료 임박 LOT → Telegram 경고"""
    try:
        from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
        engine = SQMInventoryEngineV3()
        today   = datetime.now().date()
        today_s = today.strftime('%Y-%m-%d')
        crit_s  = (today + timedelta(days=CON_RETURN_CRIT)).strftime('%Y-%m-%d')
        warn_s  = (today + timedelta(days=CON_RETURN_WARN)).strftime('%Y-%m-%d')

        rows = engine.db.fetchall(
            """SELECT lot_no, bl_no, con_return, container_no, warehouse
               FROM inventory
               WHERE con_return IS NOT NULL AND con_return != ''
                 AND con_return >= ? AND con_return <= ?
                 AND status NOT IN ('OUTBOUND','SOLD','DEPLETED')
               ORDER BY con_return""",
            (today_s, warn_s)
        ) or []
        engine.close()

        if not rows:
            logger.info("Con Return 임박 없음")
            return

        def _get(r, i, k):
            return r.get(k) if hasattr(r,'keys') else (r[i] if len(r)>i else '?')

        def _fmt(r):
            return (f"  • {_get(r,0,'lot_no')} | "
                    f"반납:{_get(r,2,'con_return')} | "
                    f"{_get(r,3,'container_no')} | "
                    f"{_get(r,4,'warehouse')}")

        crit = [r for r in rows if _get(r,2,'con_return') <= crit_s]
        warn = [r for r in rows if _get(r,2,'con_return') > crit_s]

        if crit:
            _send(
                f"🚨 <b>컨테이너 반납 긴급 ({CON_RETURN_CRIT}일 이내) — {len(crit)}건</b>\n"
                f"기준: {today_s}\n\n"
                + "\n".join(_fmt(r) for r in crit[:10])
            )
            logger.warning(f"Con Return 긴급 {len(crit)}건")

        if warn:
            _send(
                f"⚠️ <b>컨테이너 반납 주의 ({CON_RETURN_WARN}일 이내) — {len(warn)}건</b>\n"
                + "\n".join(_fmt(r) for r in warn[:10])
            )
            logger.info(f"Con Return 경고 {len(warn)}건")

    except Exception as e:
        logger.warning(f"Con Return 예외: {e}")


def main():
    logger.info(f"스케줄러 v2 시작 | {SCHEDULE_HOUR:02d}:00 | Con Return 경고 {CON_RETURN_WARN}일")
    _send(f"⏰ <b>SQM 스케줄러 v2</b>\n매일 {SCHEDULE_HOUR:02d}:00 자동 실행")

    last_run = None
    while True:
        try:
            now, today = datetime.now(), datetime.now().strftime('%Y-%m-%d')
            if now.hour == SCHEDULE_HOUR and now.minute < 2 and last_run != today:
                logger.info(f"실행: {today}")
                run_backup()
                run_integrity()
                run_con_return_check()
                last_run = today
            time.sleep(60)
        except KeyboardInterrupt:
            logger.info("종료")
            break
        except Exception as e:
            logger.error(f"루프 예외: {e}", exc_info=True)
            time.sleep(300)


if __name__ == "__main__":
    if '--now' in sys.argv:
        run_backup(); run_integrity(); run_con_return_check()
    else:
        main()
