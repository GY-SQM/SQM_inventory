# -*- coding: utf-8 -*-
"""
SQM Telegram 봇 v3 — 기존 v2 + 신규 기능
① 싱글톤 엔진 (응답 3초→0.5초)
② /만료 명령어 (Con Return 임박 LOT)
③ /비교 명령어 (어제 대비 재고 변동)
④ 로그 자동 로테이션 (10MB)
배치: scripts/sqm_bot.py (기존 덮어쓰기)
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

# ── 로그 로테이션 (10MB, 3개 보관) ──────────────────────────
_handler = logging.handlers.RotatingFileHandler(
    str(_ROOT / 'logs' / 'sqm_bot.log'),
    maxBytes=10*1024*1024, backupCount=3, encoding='utf-8'
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [sqm_bot] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(), _handler]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID   = os.getenv("CHAT_ID",   "")
POLL_SEC  = 3

# ── 싱글톤 엔진 (명령마다 새로 생성 → 1회 생성 재사용) ──────
_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
        _engine = SQMInventoryEngineV3()
        logger.info("엔진 싱글톤 생성")
    return _engine

# ── 2단계 인증 대기 ──────────────────────────────────────────
_pending: dict = {}
CONFIRM_TIMEOUT = 30


def send(text: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        return False
    try:
        import requests
        res = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        return res.status_code == 200
    except Exception as e:
        logger.warning(f"발송 실패: {e}")
        return False


def get_updates(offset=0):
    try:
        import requests
        res = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"offset": offset, "timeout": POLL_SEC},
            timeout=POLL_SEC + 5
        )
        if res.status_code == 200:
            return res.json().get("result", [])
    except Exception:
        pass
    return []


# ================================================================
# 조회 명령어
# ================================================================

def cmd_재고() -> str:
    try:
        from features.repositories.inventory_repository import InventoryRepository
        repo    = InventoryRepository(_get_engine().db)
        summary = repo.get_inventory_summary()
        by_prod = repo.get_inventory_by_product()
        avail   = round((summary.get('available_weight_kg',0) or 0)/1000, 2)
        picked  = round((summary.get('picked_weight_kg',0)   or 0)/1000, 2)
        lines   = [
            f"📦 <b>재고 현황</b>  {datetime.now().strftime('%m/%d %H:%M')}",
            f"",
            f"LOT: {summary.get('total_lots',0)}개  |  톤백: {summary.get('total_bags',0)}개",
            f"가용: {avail:.2f} MT  |  피킹: {picked:.2f} MT",
        ]
        if by_prod:
            lines += ["", "📊 <b>제품별:</b>"]
            for p in by_prod[:5]:
                nm = (p.get('product') or p.get('product_code') or '?')[:18]
                wt = round((p.get('total_weight_kg',0) or 0)/1000, 2)
                lines.append(f"  • {nm}: {wt:.2f} MT")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 재고 조회 실패\n{str(e)[:100]}"


def cmd_출고(days=0) -> str:
    try:
        engine = _get_engine()
        if days > 0:
            date_f = (datetime.now()-timedelta(days=days)).strftime('%Y-%m-%d')
            where  = f"DATE(sold_date) >= '{date_f}'"
            title  = f"최근 {days}일"
        else:
            today = datetime.now().strftime('%Y-%m-%d')
            where = f"DATE(sold_date) = '{today}'"
            title = f"오늘"
        rows = engine.db.fetchall(
            f"SELECT customer, COUNT(*) cnt, COALESCE(SUM(sold_qty_kg)/1000,0) mt "
            f"FROM sold_table WHERE {where} GROUP BY customer ORDER BY mt DESC"
        ) or []
        if not rows:
            return f"📤 <b>{title} 출고</b>\n내역 없음"
        tc = sum(int(r[1] if not hasattr(r,'keys') else r['cnt']) for r in rows)
        tm = sum(float(r[2] if not hasattr(r,'keys') else r['mt'] or 0) for r in rows)
        lines = [f"📤 <b>{title} 출고</b>", f"합계: {tc}톤백 / {tm:.3f} MT", "", "<b>고객별:</b>"]
        for r in rows[:8]:
            c,n,m = (r['customer'],r['cnt'],r['mt']) if hasattr(r,'keys') else (r[0],r[1],r[2] or 0)
            lines.append(f"  • {(c or '?')[:15]}: {n}개 / {float(m):.3f}MT")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 출고 조회 실패\n{str(e)[:100]}"


def cmd_대기() -> str:
    try:
        from features.repositories.outbound_query import OutboundQuery
        q        = OutboundQuery(_get_engine().db)
        reserved = q.load_reserved_plans()
        picked   = q.load_picked_tonbags()
        stale    = q.warn_stale_plans(reserved)
        r_lots   = len(set((r.get('lot_no') if hasattr(r,'keys') else r[1]) for r in reserved))
        p_lots   = len(set((r.get('lot_no') if hasattr(r,'keys') else r[1]) for r in picked))
        lines    = [
            f"⏳ <b>출고 대기</b>  {datetime.now().strftime('%m/%d %H:%M')}",
            f"",
            f"예약: {len(reserved)}건 / {r_lots}LOT",
            f"피킹: {len(picked)}건 / {p_lots}LOT",
        ]
        if stale:
            sl = list({p.get('lot_no') if hasattr(p,'keys') else p[1] for p in stale})[:3]
            lines += [f"", f"⚠️ 만료예약 {len(stale)}건: {', '.join(str(l) for l in sl)}"]
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 대기 조회 실패\n{str(e)[:100]}"


def cmd_lot(lot_no: str) -> str:
    try:
        from features.repositories.inventory_repository import InventoryRepository
        repo   = InventoryRepository(_get_engine().db)
        detail = repo.get_lot_detail(lot_no)
        if detail.get('error'):
            return f"❌ LOT 없음: {lot_no}"
        s  = detail.get('status','?')
        cw = round((detail.get('current_weight',0) or 0)/1000, 3)
        pw = round((detail.get('picked_weight',0)  or 0)/1000, 3)
        cr = detail.get('con_return','')
        STATUS_KO = {'AVAILABLE':'✅가용','RESERVED':'⏳예약','PICKED':'📦피킹',
                     'OUTBOUND':'📤출고','PARTIAL':'🟡일부','DEPLETED':'⬛소진'}
        lines = [
            f"🔍 <b>LOT: {lot_no}</b>",
            f"상태: {STATUS_KO.get(s,s)}",
            f"가용: {cw:.3f}MT  |  피킹: {pw:.3f}MT",
        ]
        if cr:
            days_left = (datetime.strptime(cr, '%Y-%m-%d').date() - datetime.now().date()).days
            emoji = "🚨" if days_left <= 3 else ("⚠️" if days_left <= 7 else "📅")
            lines.append(f"반납기한: {emoji} {cr} ({days_left}일 후)")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ LOT 조회 실패\n{str(e)[:100]}"


def cmd_만료() -> str:
    """Con Return 임박 LOT 목록"""
    try:
        engine  = _get_engine()
        today_s = datetime.now().strftime('%Y-%m-%d')
        warn_s  = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        rows = engine.db.fetchall(
            """SELECT lot_no, con_return, container_no, warehouse
               FROM inventory
               WHERE con_return IS NOT NULL AND con_return != ''
                 AND con_return >= ? AND con_return <= ?
                 AND status NOT IN ('OUTBOUND','SOLD','DEPLETED')
               ORDER BY con_return""",
            (today_s, warn_s)
        ) or []
        if not rows:
            return "📅 <b>Con Return 임박 LOT 없음</b>\n(7일 이내)"
        lines = [f"📅 <b>Con Return 임박 ({len(rows)}건)</b>", ""]
        for r in rows[:15]:
            lot = r.get('lot_no') if hasattr(r,'keys') else r[0]
            cr  = r.get('con_return') if hasattr(r,'keys') else r[1]
            cnt = (r.get('container_no') if hasattr(r,'keys') else r[2]) or '?'
            days_left = (datetime.strptime(cr,'%Y-%m-%d').date()-datetime.now().date()).days
            emoji = "🚨" if days_left <= 3 else "⚠️"
            lines.append(f"  {emoji} {lot} | {cr} ({days_left}일) | {cnt}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 만료 조회 실패\n{str(e)[:100]}"


def cmd_비교() -> str:
    """어제 대비 오늘 재고 변동"""
    try:
        engine  = _get_engine()
        today_s = datetime.now().strftime('%Y-%m-%d')
        yest_s  = (datetime.now()-timedelta(days=1)).strftime('%Y-%m-%d')

        # 오늘 출고 (OUTBOUND)
        sold_rows = engine.db.fetchall(
            "SELECT COUNT(*) cnt, COALESCE(SUM(sold_qty_kg)/1000,0) mt "
            "FROM sold_table WHERE DATE(sold_date)=?", (today_s,)
        ) or []
        sold_cnt = int(sold_rows[0][0] if sold_rows else 0)
        sold_mt  = round(float(sold_rows[0][1] if sold_rows else 0), 3)

        # 오늘 입고
        inb_rows = engine.db.fetchall(
            "SELECT COUNT(*) cnt FROM inventory WHERE DATE(inbound_date)=?", (today_s,)
        ) or []
        inb_cnt = int(inb_rows[0][0] if inb_rows else 0)

        # 현재 재고 총량
        inv_row = engine.db.fetchone(
            "SELECT COUNT(*) lot_cnt, COALESCE(SUM(current_weight)/1000,0) avail_mt "
            "FROM inventory WHERE status NOT IN ('OUTBOUND','SOLD','DEPLETED')"
        )
        lot_cnt  = int(inv_row[0] if inv_row else 0)
        avail_mt = round(float(inv_row[1] if inv_row else 0), 3)

        lines = [
            f"📊 <b>오늘 재고 변동</b>  {today_s}",
            f"",
            f"📥 입고: {inb_cnt}LOT",
            f"📤 출고: {sold_cnt}건 / {sold_mt:.3f}MT",
            f"",
            f"현재 가용: {avail_mt:.3f}MT / {lot_cnt}LOT",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 비교 조회 실패\n{str(e)[:100]}"


def cmd_정합성() -> str:
    try:
        send("🔍 점검 중...")
        engine = _get_engine()
        result = engine.fix_lot_status_integrity()
        fixed  = result.get('fixed',0)
        errors = result.get('errors',[])
        if fixed==0 and not errors:
            return f"✅ <b>정합성 이상 없음</b>  {datetime.now().strftime('%m/%d %H:%M')}"
        lines = [f"⚠️ <b>정합성 이상</b>  수정:{fixed}건 / 오류:{len(errors)}건"]
        for e in errors[:3]:
            lines.append(f"  • {str(e)[:60]}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 정합성 실패\n{str(e)[:100]}"


def cmd_백업() -> str:
    try:
        from utils.backup import force_backup
        send("💾 백업 중...")
        ok, msg = force_backup()
        return f"{'✅' if ok else '❌'} <b>백업 {'완료' if ok else '실패'}</b>\n{msg}"
    except Exception as e:
        return f"❌ 백업 실패\n{str(e)[:100]}"


def cmd_상태() -> str:
    try:
        import requests as req
        lines = [f"🖥️ <b>SQM 상태</b>  {datetime.now().strftime('%m/%d %H:%M')}", ""]
        try:
            r = req.get(
                f"http://{os.getenv('API_HOST','127.0.0.1')}:{os.getenv('API_PORT','8000')}/api/health",
                timeout=3
            )
            lines.append(f"API: {'✅ 정상' if r.status_code==200 else '⚠️ '+str(r.status_code)}")
        except Exception:
            lines.append("API: ❌ 응답 없음")
        try:
            engine  = _get_engine()
            db_path = Path(str(getattr(engine,'db_path','')))
            size    = db_path.stat().st_size/1024/1024 if db_path.exists() else 0
            lines.append(f"DB: ✅ 정상 ({size:.1f}MB)")
        except Exception as e:
            lines.append(f"DB: ❌ {str(e)[:40]}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 상태 확인 실패\n{str(e)[:100]}"


# ================================================================
# 실행 명령어 (2단계 인증)
# ================================================================

def cmd_확정_1단계(lot_no: str) -> str:
    if not lot_no:
        return "사용법: /확정 LOT번호"
    try:
        from features.repositories.inventory_repository import InventoryRepository
        repo   = InventoryRepository(_get_engine().db)
        detail = repo.get_lot_detail(lot_no)
        if detail.get('error'):
            return f"❌ LOT 없음: {lot_no}"
        _pending[CHAT_ID] = {"action":"확정","args":[lot_no],"expires":time.time()+CONFIRM_TIMEOUT}
        return (f"⚠️ <b>출고 확정 확인</b>\nLOT: <b>{lot_no}</b>\n상태: {detail.get('status','?')}\n"
                f"\n30초 내 /확인 입력")
    except Exception as e:
        return f"❌ 확정 준비 실패\n{str(e)[:100]}"


def cmd_취소_1단계(lot_no: str, sub_lt: str) -> str:
    if not lot_no:
        return "사용법: /취소 LOT번호 톤백번호"
    _pending[CHAT_ID] = {"action":"취소","args":[lot_no, int(sub_lt) if sub_lt else 0],"expires":time.time()+CONFIRM_TIMEOUT}
    return f"⚠️ <b>출고 취소 확인</b>\nLOT: <b>{lot_no}</b>\n\n30초 내 /확인 입력"


def cmd_예약취소_1단계(lot_no: str) -> str:
    if not lot_no:
        return "사용법: /예약취소 LOT번호"
    _pending[CHAT_ID] = {"action":"예약취소","args":[lot_no],"expires":time.time()+CONFIRM_TIMEOUT}
    return f"⚠️ <b>예약 취소 확인</b>\nLOT: <b>{lot_no}</b>\n\n30초 내 /확인 입력"


def cmd_확인_2단계() -> str:
    p = _pending.get(CHAT_ID)
    if not p:
        return "❌ 대기 중인 명령 없음"
    if time.time() > p["expires"]:
        del _pending[CHAT_ID]
        return "⏰ 시간 초과 (30초). 다시 입력하세요."
    action, args = p["action"], p["args"]
    del _pending[CHAT_ID]
    try:
        if action == "확정":
            from features.services.outbound_service import OutboundService
            svc = OutboundService(_get_engine().db)
            r   = svc.confirm_outbound(lot_no=args[0])
            return (f"✅ <b>출고 확정 완료</b>\nLOT: {args[0]}\n확정: {r['confirmed']}톤백"
                    if r["success"] else f"❌ 출고 확정 실패\n{'; '.join(r['errors'][:2])}")
        elif action == "취소":
            from features.services.outbound_service import OutboundService
            svc = OutboundService(_get_engine().db)
            r   = svc.revert_outbound_to_available(lot_no=args[0])
            return (f"✅ <b>출고 취소 완료</b>\nLOT: {args[0]}"
                    if r["success"] else f"❌ 출고 취소 실패")
        elif action == "예약취소":
            engine = _get_engine()
            rows   = engine.db.fetchall(
                "SELECT id FROM allocation_plan WHERE lot_no=? AND status='RESERVED'", (args[0],)
            ) or []
            if not rows:
                return f"❌ RESERVED 예약 없음: {args[0]}"
            plan_ids = [r[0] if not hasattr(r,'keys') else r['id'] for r in rows]
            from features.services.outbound_service import OutboundService
            svc = OutboundService(engine.db)
            r   = svc.cancel_reservation(plan_ids, "TELEGRAM")
            return f"✅ 예약 취소 완료 {r.get('cancelled',0)}건" if r.get('ok') else f"❌ 예약 취소 실패"
    except Exception as e:
        return f"❌ 실행 오류\n{str(e)[:100]}"


def cmd_취소확인() -> str:
    if CHAT_ID in _pending:
        del _pending[CHAT_ID]
        return "✅ 명령 취소됨"
    return "대기 중인 명령 없음"


# ================================================================
# 자동 리포트
# ================================================================

def send_weekly_report():
    try:
        engine   = _get_engine()
        week_ago = (datetime.now()-timedelta(days=7)).strftime('%Y-%m-%d')
        rows = engine.db.fetchall(
            f"SELECT DATE(sold_date) d, COUNT(*) cnt, COALESCE(SUM(sold_qty_kg)/1000,0) mt "
            f"FROM sold_table WHERE DATE(sold_date)>='{week_ago}' "
            f"GROUP BY DATE(sold_date) ORDER BY d"
        ) or []
        tc = sum(int(r[1] if not hasattr(r,'keys') else r['cnt']) for r in rows)
        tm = sum(float(r[2] if not hasattr(r,'keys') else r['mt'] or 0) for r in rows)
        lines = [f"📊 <b>주간 리포트</b>  {week_ago}~오늘", f"총: {tc}건 / {tm:.3f}MT", "", "<b>일별:</b>"]
        for r in rows:
            d,n,m = (r['d'],r['cnt'],r['mt']) if hasattr(r,'keys') else (r[0],r[1],r[2] or 0)
            lines.append(f"  {d}: {n}개/{float(m):.3f}MT")
        send("\n".join(lines))
    except Exception as e:
        logger.error(f"주간 리포트 오류: {e}")


def send_monthly_report():
    try:
        engine = _get_engine()
        now    = datetime.now()
        first  = now.replace(day=1)
        prev_first = first.replace(month=now.month-1) if now.month > 1 else first.replace(year=now.year-1, month=12)
        prev_last  = first - timedelta(days=1)
        rows = engine.db.fetchall(
            f"SELECT customer, COUNT(*) cnt, COALESCE(SUM(sold_qty_kg)/1000,0) mt "
            f"FROM sold_table WHERE DATE(sold_date) BETWEEN '{prev_first.strftime('%Y-%m-%d')}' AND '{prev_last.strftime('%Y-%m-%d')}' "
            f"GROUP BY customer ORDER BY mt DESC"
        ) or []
        tc = sum(int(r[1] if not hasattr(r,'keys') else r['cnt']) for r in rows)
        tm = sum(float(r[2] if not hasattr(r,'keys') else r['mt'] or 0) for r in rows)
        lines = [f"📅 <b>월간 리포트</b>  {prev_first.strftime('%Y년 %m월')}", f"총: {tc}건 / {tm:.3f}MT", "", "<b>고객별:</b>"]
        for r in rows:
            c,n,m = (r['customer'],r['cnt'],r['mt']) if hasattr(r,'keys') else (r[0],r[1],r[2] or 0)
            lines.append(f"  • {(c or '?')[:15]}: {n}개/{float(m):.3f}MT")
        send("\n".join(lines))
    except Exception as e:
        logger.error(f"월간 리포트 오류: {e}")


HELP_TEXT = """📋 <b>SQM 봇 v3 명령어</b>

<b>[조회]</b>
/재고         가용 재고 요약
/출고         오늘 출고
/출고 7       최근 7일 출고
/대기         RESERVED/PICKED 현황
/lot LOT번호  LOT 상세
/만료         Con Return 7일 이내 ★신규
/비교         오늘 재고 변동 ★신규
/정합성       정합성 점검
/백업         즉시 백업
/상태         서버+DB 상태

<b>[실행 — 2단계 인증]</b>
/확정 LOT번호      출고 확정
/취소 LOT번호 번호 출고 취소
/예약취소 LOT번호  예약 취소
/확인              실행 확정
/취소확인          명령 취소""".strip()


# ================================================================
# 자동 리포트 스케줄
# ================================================================

_last_weekly = None
_last_monthly = None


def check_auto_reports():
    global _last_weekly, _last_monthly
    now, today = datetime.now(), datetime.now().strftime('%Y-%m-%d')
    if now.weekday()==0 and now.hour==8 and now.minute<2 and _last_weekly!=today:
        _last_weekly = today; send_weekly_report()
    if now.day==1 and now.hour==8 and now.minute<2 and _last_monthly!=today:
        _last_monthly = today; send_monthly_report()


# ================================================================
# 라우터
# ================================================================

def route(text: str) -> str:
    parts = text.strip().split()
    cmd   = parts[0].lower() if parts else ''
    if cmd == '/확인':      return cmd_확인_2단계()
    if cmd == '/취소확인':  return cmd_취소확인()
    if cmd == '/확정':      return cmd_확정_1단계(parts[1] if len(parts)>1 else '')
    if cmd == '/취소' and len(parts)>=2 and '-' in (parts[1] if len(parts)>1 else ''):
        return cmd_취소_1단계(parts[1] if len(parts)>1 else '', parts[2] if len(parts)>2 else '0')
    if cmd == '/예약취소':  return cmd_예약취소_1단계(parts[1] if len(parts)>1 else '')
    if cmd == '/재고':      return cmd_재고()
    if cmd == '/출고':      return cmd_출고(int(parts[1]) if len(parts)>1 and parts[1].isdigit() else 0)
    if cmd == '/대기':      return cmd_대기()
    if cmd == '/lot':       return cmd_lot(parts[1] if len(parts)>1 else '')
    if cmd == '/만료':      return cmd_만료()
    if cmd == '/비교':      return cmd_비교()
    if cmd == '/정합성':    return cmd_정합성()
    if cmd == '/백업':      return cmd_백업()
    if cmd == '/상태':      return cmd_상태()
    if cmd in ('/도움말','/help','/start'): return HELP_TEXT
    return f"알 수 없는 명령어: {text}\n/도움말 확인"


# ================================================================
# 메인
# ================================================================

def main():
    if not BOT_TOKEN or not CHAT_ID:
        logger.error("BOT_TOKEN/CHAT_ID 미설정"); sys.exit(1)
    logger.info("SQM 봇 v3 시작")
    send(f"🤖 <b>SQM 봇 v3 시작</b>\n{datetime.now().strftime('%Y-%m-%d %H:%M')}\n/도움말 확인")

    offset, loop = 0, 0
    while True:
        try:
            if loop % 20 == 0:
                check_auto_reports()
            loop += 1
            for u in get_updates(offset):
                offset = u["update_id"] + 1
                msg    = u.get("message",{})
                text   = msg.get("text","").strip()
                sender = str(msg.get("chat",{}).get("id",""))
                if sender != str(CHAT_ID) or not text:
                    continue
                logger.info(f"명령: {text}")
                try:
                    send(route(text))
                except Exception as e:
                    logger.error(f"처리 오류: {e}", exc_info=True)
                    send(f"❌ 오류\n{str(e)[:100]}")
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("봇 종료"); send("🔴 SQM 봇 종료"); break
        except Exception as e:
            logger.error(f"폴링 오류: {e}", exc_info=True); time.sleep(10)


if __name__ == "__main__":
    main()
