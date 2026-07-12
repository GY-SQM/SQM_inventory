# -*- coding: utf-8 -*-
"""
SQM Location Map API — v8.7.0
================================
위치재고조회 엑셀(신형식 G{동}-{칸}-{열}-{층} [N]) import 기능.

엔드포인트:
  POST /api/location-map/preview  — 업로드 파싱 + 검증 + 직전 batch diff (저장 전)
  POST /api/location-map/commit   — 검증 통과분 LOT 위치 후보 스냅샷 저장
  GET  /api/location-map/batches  — import 이력 목록
  GET  /api/location-map/latest   — 최신 batch 매핑 조회

DB 테이블 (최초 호출 시 자동 생성):
  lot_location_import_batch — import 1회 = 1 batch
  lot_location_map          — batch별 (LOT, 셀, 톤백수) 행

검증 규칙:
  - 치명적(errors, commit 차단): 위치 형식오류 / 셀 중복 / LOT 중복 / [N] 누락
  - 입고 누락(inbound_short): 신규 LOT인데 톤백 합 ≠ 10 → 경고 + 누락 셀 지목
                              (commit 시 force=true 아니면 차단)
  - diff: 직전 batch와 비교 — 신규/삭제/위치변경/수량변경 LOT 분류

작성자: Ruby (남기동)  /  버전: v8.7.0 (2026-05-19)
"""
import logging
import os
import sqlite3
import tempfile
from datetime import datetime

from fastapi import APIRouter, File, Query, UploadFile

from backend.common.errors import ok_response, err_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/location-map', tags=['location-map'])


def _error_help(code: str, causes: list | None = None,
                actions: list | None = None, details: list | None = None) -> dict:
    """사용자에게 보여줄 에러 원인/해결 안내를 표준 구조로 만든다."""
    return {
        'code': code,
        'causes': causes or [],
        'actions': actions or [],
        'details': details or [],
    }


# ─────────────────────────────────────────────────────────────────────
# DB
# ─────────────────────────────────────────────────────────────────────
def _db() -> sqlite3.Connection:
    from config import DB_PATH
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA busy_timeout=5000')
    return con


def _ensure_tables(con: sqlite3.Connection) -> None:
    """lot_location_* 테이블 자동 생성 (최초 1회)."""
    con.executescript("""
        CREATE TABLE IF NOT EXISTS lot_location_import_batch (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file   TEXT    DEFAULT '',
            imported_at   TEXT    NOT NULL,
            total_lots    INTEGER DEFAULT 0,
            total_cells   INTEGER DEFAULT 0,
            total_tonbags INTEGER DEFAULT 0,
            warning_count INTEGER DEFAULT 0,
            note          TEXT    DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS lot_location_map (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id     INTEGER NOT NULL,
            lot_no       TEXT    NOT NULL,
            location     TEXT    NOT NULL,
            dong         INTEGER,
            rack         INTEGER,
            col          INTEGER,
            level        INTEGER,
            tonbag_count INTEGER NOT NULL DEFAULT 0,
            product      TEXT    DEFAULT '',
            shipper      TEXT    DEFAULT '',
            sap_no       TEXT    DEFAULT '',
            created_at   TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_llm_batch ON lot_location_map(batch_id);
        CREATE INDEX IF NOT EXISTS idx_llm_lot   ON lot_location_map(lot_no);
        CREATE INDEX IF NOT EXISTS idx_llm_loc   ON lot_location_map(location);
    """)
    con.commit()


def _load_latest_batch(con: sqlite3.Connection):
    """직전(최신) batch id + {lot_no: {location: tonbag_count}} 반환."""
    row = con.execute(
        'SELECT id FROM lot_location_import_batch ORDER BY id DESC LIMIT 1'
    ).fetchone()
    if not row:
        return None, {}
    batch_id = row['id']
    prev: dict = {}
    for r in con.execute(
        'SELECT lot_no, location, tonbag_count FROM lot_location_map WHERE batch_id=?',
        (batch_id,),
    ):
        prev.setdefault(r['lot_no'], {})[r['location']] = r['tonbag_count']
    return batch_id, prev


# ─────────────────────────────────────────────────────────────────────
# 분석 (diff + 입고 검증)
# ─────────────────────────────────────────────────────────────────────
def _new_map_from_lots(lots: list) -> dict:
    """파싱 lots → {lot_no: {location: tonbag_count}} (유효 셀만)."""
    out: dict = {}
    for lot in lots:
        out[lot['lot_no']] = {
            c['location']: c['tonbag_count']
            for c in lot['cells'] if c.get('valid')
        }
    return out


def _compute_diff(prev_map: dict, new_map: dict) -> dict:
    """직전 batch와 신규 파일 비교 → 신규/삭제/위치변경/수량변경 분류."""
    prev_ids, new_ids = set(prev_map), set(new_map)
    new_lots = sorted(new_ids - prev_ids)
    removed_lots = sorted(prev_ids - new_ids)
    location_changed, count_changed = [], []
    unchanged = 0
    for lot in sorted(new_ids & prev_ids):
        pv, nv = prev_map[lot], new_map[lot]
        if set(pv) != set(nv):
            location_changed.append({
                'lot_no': lot,
                'before': sorted(pv), 'after': sorted(nv),
            })
        elif pv != nv:
            count_changed.append({
                'lot_no': lot,
                'before': pv, 'after': nv,
            })
        else:
            unchanged += 1
    return {
        'new_lots':         new_lots,
        'removed_lots':     removed_lots,
        'location_changed': location_changed,
        'count_changed':    count_changed,
        'unchanged_count':  unchanged,
    }


def _inbound_short_check(lots: list, new_lot_ids: set) -> list:
    """신규(입고) LOT 중 톤백 합 ≠ 10 인 건 → 누락 셀 지목."""
    from features.parsers.location_inventory_parser import (
        EXPECTED_TONBAGS_PER_LOT, find_missing_cells,
    )
    short = []
    for lot in lots:
        if lot['lot_no'] not in new_lot_ids:
            continue  # 기존 LOT은 입고 검증 대상 아님 (출고 감소는 정상)
        if lot['tonbag_sum'] == EXPECTED_TONBAGS_PER_LOT:
            continue
        short.append({
            'lot_no':        lot['lot_no'],
            'row_num':       lot['row_num'],
            'tonbag_sum':    lot['tonbag_sum'],
            'expected':      EXPECTED_TONBAGS_PER_LOT,
            'short_count':   lot['short_count'],
            'missing_cells': find_missing_cells(lot),
        })
    return short


def _active_inventory_lot_warnings(con: sqlite3.Connection, lot_ids: set) -> list:
    """
    엑셀 LOT가 현재 재고 DB의 AVAILABLE/PENDING 톤백 LOT에 없으면 경고한다.

    이 검사는 저장을 막지 않는다. 위치재고 엑셀은 LOT 위치 후보 스냅샷이므로,
    실제 톤백별 위치 확정은 출고 바코드 스캔 시점에 맡긴다.
    """
    if not lot_ids:
        return []
    table = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='inventory_tonbag'"
    ).fetchone()
    if not table:
        return []

    placeholders = ",".join("?" for _ in lot_ids)
    rows = con.execute(
        f"""
        SELECT DISTINCT lot_no
          FROM inventory_tonbag
         WHERE lot_no IN ({placeholders})
           AND UPPER(COALESCE(status, '')) IN ('AVAILABLE', 'PENDING')
           AND COALESCE(is_sample, 0) = 0
        """,
        tuple(lot_ids),
    ).fetchall()
    active_lots = {r['lot_no'] for r in rows}
    missing = sorted(lot_ids - active_lots)
    if not missing:
        return []
    shown = ", ".join(missing[:30])
    more = f" 외 {len(missing) - 30}건" if len(missing) > 30 else ""
    return [
        "현재 재고 DB의 AVAILABLE/PENDING LOT에 없는 위치재고 LOT: "
        f"{shown}{more} — 위치 후보로는 저장 가능하지만, 출고 전 입고/상태 확인이 필요합니다"
    ]


def _build_report(doc: dict, con: sqlite3.Connection) -> dict:
    """파싱 doc + DB → preview/commit 공용 분석 리포트."""
    prev_batch_id, prev_map = _load_latest_batch(con)
    new_map = _new_map_from_lots(doc['lots'])
    diff = _compute_diff(prev_map, new_map)
    inbound_short = _inbound_short_check(doc['lots'], set(diff['new_lots']))
    db_lot_warnings = _active_inventory_lot_warnings(con, set(new_map))

    fatal = list(doc['errors'])              # 형식/셀중복/LOT중복 — commit 차단
    can_commit = (len(fatal) == 0 and len(doc['lots']) > 0)

    return {
        'source_file':   doc['source_file'],
        'stats':         doc['stats'],
        'errors':        fatal,
        'warnings':      list(doc['warnings']) + db_lot_warnings,
        'inbound_short': inbound_short,
        'diff': {
            'prev_batch_id': prev_batch_id,
            **diff,
        },
        'can_commit':       can_commit,
        'has_inbound_short': len(inbound_short) > 0,
    }


def _save_upload(file: UploadFile) -> str:
    """업로드 파일 → 임시 .xlsx 경로."""
    ext = os.path.splitext(file.filename or '')[1].lower()
    if ext not in ('.xlsx', '.xls'):
        raise ValueError(f'Excel 파일만 지원 (.xlsx/.xls). 받은 파일: {file.filename}')
    content = file.file.read()
    if not content:
        raise ValueError('빈 파일입니다')
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        return tmp.name


# ─────────────────────────────────────────────────────────────────────
# POST /api/location-map/preview
# ─────────────────────────────────────────────────────────────────────
@router.post('/preview', summary='📋 위치 매핑 엑셀 미리보기 (검증 + diff, DB 미반영)')
def preview_location_map(file: UploadFile = File(...)):
    """업로드 엑셀을 파싱·검증하고 직전 batch와 diff 만 반환 (DB 안 건드림)."""
    from features.parsers.location_inventory_parser import parse_location_inventory_excel

    tmp_path = None
    try:
        tmp_path = _save_upload(file)
        doc = parse_location_inventory_excel(tmp_path)
        con = _db()
        try:
            _ensure_tables(con)
            report = _build_report(doc, con)
        finally:
            con.close()
        report['filename'] = file.filename
        return ok_response(report)
    except ValueError as ve:
        return err_response(
            str(ve),
            _error_help(
                'UPLOAD_FILE_INVALID',
                causes=[str(ve)],
                actions=[
                    '파일 확장자가 .xlsx 또는 .xls 인지 확인하세요.',
                    '파일이 비어 있거나 손상되었다면 Excel에서 다시 저장한 뒤 업로드하세요.',
                    '위치재고조회 원본 양식인지 확인하세요. 필수 컬럼은 위치와 LOT입니다.',
                ],
            ),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception('[location-map/preview] error: %s', e)
        return err_response(
            f'미리보기 실패: {e}',
            _error_help(
                'PREVIEW_FAILED',
                causes=[
                    '엑셀 파일을 읽거나 위치재고 형식으로 해석하는 중 오류가 발생했습니다.',
                    str(e),
                ],
                actions=[
                    '엑셀에 위치 컬럼과 LOT 컬럼이 있는지 확인하세요.',
                    '위치 값은 예: G6-08-13-01 [2] 형식이어야 합니다.',
                    '같은 셀이 서로 다른 LOT에 중복 배정되어 있지 않은지 확인하세요.',
                    '문제가 계속되면 해당 엑셀 파일명과 오류 메시지를 관리자에게 전달하세요.',
                ],
            ),
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ─────────────────────────────────────────────────────────────────────
# POST /api/location-map/commit
# ─────────────────────────────────────────────────────────────────────
@router.post('/commit', summary='💾 위치 매핑 엑셀 LOT 위치 후보 스냅샷 저장')
def commit_location_map(
    file: UploadFile = File(...),
    force: bool = Query(False, description='입고 누락(10개 미만) 경고를 무시하고 강제 저장'),
    apply_tonbag: bool = Query(False, description='True면 LOT 셀 매핑을 톤백 위치까지 즉시 확정(inventory_tonbag.location 갱신)'),
):
    """
    검증 통과분을 lot_location_map 에 새 batch 로 저장.
    기본은 inventory_tonbag.location 을 변경하지 않는다(LOT 후보 스냅샷).
    [v8.7.4] apply_tonbag=True 면 각 LOT 의 셀(위치+톤백수)을 가용 톤백에 개수만큼
    분배하여 inventory_tonbag.location 까지 즉시 확정 — '톤백 위치 매핑' 통합 기능.
    - 치명적 에러(형식/셀중복/LOT중복) 있으면 항상 차단
    - 입고 누락(신규 LOT 10개 미만)은 force=true 가 아니면 차단
    """
    from features.parsers.location_inventory_parser import parse_location_inventory_excel

    tmp_path = None
    try:
        tmp_path = _save_upload(file)
        doc = parse_location_inventory_excel(tmp_path)
        con = _db()
        try:
            _ensure_tables(con)
            report = _build_report(doc, con)

            # 1) 치명적 에러 → 항상 차단
            if not report['can_commit']:
                return {
                    'ok': False,
                    'error': '검증 실패 — 치명적 에러가 있어 저장할 수 없습니다',
                    'error_code': 'VALIDATION_FAILED',
                    'detail': _error_help(
                        'VALIDATION_FAILED',
                        causes=[
                            '엑셀 안에 저장을 막는 치명적 검증 오류가 있습니다.',
                            '대표 원인: 위치 형식 오류, [N] 톤백수 누락, 같은 셀 중복, 같은 LOT 중복.',
                        ],
                        actions=[
                            '화면의 치명적 에러 목록에서 행 번호와 LOT를 확인하세요.',
                            '위치 값은 예: G6-08-13-01 [2] 형식으로 수정하세요.',
                            '같은 창고 셀이 두 LOT에 동시에 들어가 있으면 하나를 수정하세요.',
                            '같은 LOT가 여러 행에 반복되어 있으면 한 행으로 정리하세요.',
                            '수정한 엑셀을 다시 업로드해서 검증 통과 여부를 확인하세요.',
                        ],
                        details=report['errors'][:50],
                    ),
                    'data': report,
                }
            # 2) 입고 누락 → force 아니면 차단
            if report['has_inbound_short'] and not force:
                return {
                    'ok': False,
                    'error': (
                        '신규 입고 LOT 중 톤백이 10개가 안 되는 건이 있습니다 — '
                        '바코드 스캔 누락일 수 있으니 현장 확인 후 수정하거나, '
                        '확인했다면 강제 저장(force)으로 진행하세요'
                    ),
                    'error_code': 'INBOUND_SHORT',
                    'detail': _error_help(
                        'INBOUND_SHORT',
                        causes=[
                            '직전 위치재고 스냅샷에 없던 신규 LOT인데 톤백 합계가 10개가 아닙니다.',
                            '현장 바코드 스캔 누락, 엑셀 위치 [N] 수량 누락, 일부 셀 누락 가능성이 있습니다.',
                        ],
                        actions=[
                            '화면의 입고 누락 의심 목록에서 LOT와 부족 셀을 확인하세요.',
                            '현장에서 해당 LOT의 실제 톤백 수와 위치를 확인하세요.',
                            '엑셀이 틀렸다면 위치 [N] 수량을 수정한 뒤 다시 업로드하세요.',
                            '현장 확인 결과 그대로 저장해도 된다면 강제 저장을 체크하고 진행하세요.',
                        ],
                    ),
                    'data': report,
                }

            # 3) LOT 위치 후보 스냅샷 저장
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            st = doc['stats']
            cur = con.execute(
                'INSERT INTO lot_location_import_batch '
                '(source_file, imported_at, total_lots, total_cells, '
                ' total_tonbags, warning_count, note) VALUES (?,?,?,?,?,?,?)',
                (file.filename or doc['source_file'], now,
                 st['total_lots'], st['total_cells'], st['total_tonbags'],
                 st['warning_count'],
                 'force' if force else ''),
            )
            batch_id = cur.lastrowid
            rows = 0
            for lot in doc['lots']:
                for c in lot['cells']:
                    if not c.get('valid'):
                        continue
                    con.execute(
                        'INSERT INTO lot_location_map '
                        '(batch_id, lot_no, location, dong, rack, col, level, '
                        ' tonbag_count, product, shipper, sap_no, created_at) '
                        'VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                        (batch_id, lot['lot_no'], c['location'],
                         c['dong'], c['rack'], c['col'], c['level'],
                         c['tonbag_count'], lot['product'], lot['shipper'],
                         lot['sap_no'], now),
                    )
                    rows += 1

            # [v8.7.4] 옵션: 톤백 위치까지 즉시 확정 (셀 매핑 → 가용 톤백에 개수만큼 분배)
            applied_tonbags = 0
            apply_shortfalls = []
            if apply_tonbag:
                for lot in doc['lots']:
                    cells = [c for c in lot['cells'] if c.get('valid')]
                    if not cells:
                        continue
                    tb_ids = [r[0] for r in con.execute(
                        "SELECT id FROM inventory_tonbag "
                        "WHERE lot_no=? AND status='AVAILABLE' AND COALESCE(is_sample,0)=0 "
                        "ORDER BY sub_lt", (lot['lot_no'],)).fetchall()]
                    mapped_total = sum(int(c.get('tonbag_count') or 0) for c in cells)
                    idx = 0
                    for c in cells:
                        for _ in range(int(c.get('tonbag_count') or 0)):
                            if idx >= len(tb_ids):
                                break
                            con.execute(
                                "UPDATE inventory_tonbag SET location=?, "
                                "location_updated_at=?, updated_at=? WHERE id=?",
                                (c['location'], now, now, tb_ids[idx]))
                            idx += 1
                            applied_tonbags += 1
                    if mapped_total > len(tb_ids):
                        apply_shortfalls.append(
                            f"{lot['lot_no']}: 매핑 {mapped_total}개 > 가용 {len(tb_ids)}개 (가용분만 반영)")

            con.commit()
        finally:
            con.close()

        logger.info('[location-map/commit] batch=%s rows=%s file=%s force=%s apply_tonbag=%s applied=%s',
                    batch_id, rows, file.filename, force, apply_tonbag, applied_tonbags)
        report['batch_id'] = batch_id
        report['committed_rows'] = rows
        report['apply_tonbag'] = apply_tonbag
        report['applied_tonbags'] = applied_tonbags
        if apply_shortfalls:
            report['apply_shortfalls'] = apply_shortfalls
        _msg = f'배치 #{batch_id} 위치 후보 저장 완료 — {rows}개 셀 매핑 저장'
        if apply_tonbag:
            _msg += f' · 톤백 위치 확정 {applied_tonbags}개'
            if apply_shortfalls:
                _msg += f' (가용부족 {len(apply_shortfalls)}건)'
        return ok_response(report, message=_msg)
    except ValueError as ve:
        return err_response(
            str(ve),
            _error_help(
                'UPLOAD_FILE_INVALID',
                causes=[str(ve)],
                actions=[
                    '파일 확장자가 .xlsx 또는 .xls 인지 확인하세요.',
                    '파일이 비어 있거나 손상되었다면 Excel에서 다시 저장한 뒤 업로드하세요.',
                    '위치재고조회 원본 양식인지 확인하세요. 필수 컬럼은 위치와 LOT입니다.',
                ],
            ),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception('[location-map/commit] error: %s', e)
        return err_response(
            f'저장 실패: {e}',
            _error_help(
                'COMMIT_FAILED',
                causes=[
                    '검증 이후 위치 후보 스냅샷을 DB에 저장하는 중 오류가 발생했습니다.',
                    str(e),
                ],
                actions=[
                    '프로그램을 새로고침한 뒤 같은 파일을 다시 시도하세요.',
                    '다른 사용자가 동시에 저장 중이면 잠시 후 다시 시도하세요.',
                    'DB 파일 접근 권한 또는 디스크 여유 공간을 확인하세요.',
                    '문제가 계속되면 오류 메시지와 파일명을 관리자에게 전달하세요.',
                ],
            ),
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ─────────────────────────────────────────────────────────────────────
# GET /api/location-map/batches
# ─────────────────────────────────────────────────────────────────────
@router.get('/batches', summary='📚 위치 매핑 import 이력')
def list_batches(limit: int = Query(50, ge=1, le=500)):
    """import batch 목록 (최신순)."""
    try:
        con = _db()
        try:
            _ensure_tables(con)
            rows = con.execute(
                'SELECT id, source_file, imported_at, total_lots, total_cells, '
                '       total_tonbags, warning_count, note '
                'FROM lot_location_import_batch ORDER BY id DESC LIMIT ?',
                (limit,),
            ).fetchall()
        finally:
            con.close()
        return ok_response({
            'batches': [dict(r) for r in rows],
            'count': len(rows),
        })
    except Exception as e:  # noqa: BLE001
        logger.exception('[location-map/batches] error: %s', e)
        return err_response(str(e))


# ─────────────────────────────────────────────────────────────────────
# GET /api/location-map/latest
# ─────────────────────────────────────────────────────────────────────
@router.get('/latest', summary='📍 최신 batch 위치 매핑')
def latest_map(batch_id: int = Query(None, description='지정 시 해당 batch, 미지정 시 최신')):
    """최신(또는 지정) batch 의 LOT↔셀 매핑 전체 반환."""
    try:
        con = _db()
        try:
            _ensure_tables(con)
            if batch_id is None:
                row = con.execute(
                    'SELECT id FROM lot_location_import_batch ORDER BY id DESC LIMIT 1'
                ).fetchone()
                if not row:
                    return ok_response({'batch_id': None, 'lots': [], 'count': 0})
                batch_id = row['id']
            rows = con.execute(
                'SELECT lot_no, location, dong, rack, col, level, tonbag_count, '
                '       product, shipper, sap_no '
                'FROM lot_location_map WHERE batch_id=? ORDER BY lot_no, location',
                (batch_id,),
            ).fetchall()
        finally:
            con.close()
        # LOT별로 묶기
        lots: dict = {}
        for r in rows:
            d = lots.setdefault(r['lot_no'], {
                'lot_no': r['lot_no'], 'product': r['product'],
                'shipper': r['shipper'], 'sap_no': r['sap_no'],
                'cells': [], 'tonbag_sum': 0,
            })
            d['cells'].append({
                'location': r['location'], 'dong': r['dong'], 'rack': r['rack'],
                'col': r['col'], 'level': r['level'],
                'tonbag_count': r['tonbag_count'],
            })
            d['tonbag_sum'] += r['tonbag_count']
        return ok_response({
            'batch_id': batch_id,
            'lots': list(lots.values()),
            'count': len(lots),
        })
    except Exception as e:  # noqa: BLE001
        logger.exception('[location-map/latest] error: %s', e)
        return err_response(str(e))


# ─────────────────────────────────────────────────────────────────────
# DELETE /api/location-map/batch/{batch_id}  (v8.7.0 롤백 A)
# ─────────────────────────────────────────────────────────────────────
@router.delete('/batch/{batch_id}', summary='🗑️ 위치 매핑 batch 삭제 (롤백)')
def delete_batch(batch_id: int):
    """잘못 임포트한 batch 삭제. lot_location_map + lot_location_import_batch에서 제거."""
    try:
        con = _db()
        try:
            _ensure_tables(con)
            row = con.execute(
                'SELECT id FROM lot_location_import_batch WHERE id=?',
                (batch_id,),
            ).fetchone()
            if not row:
                return err_response(f'batch #{batch_id} 를 찾을 수 없습니다', code='NOT_FOUND')
            lot_rows = con.execute(
                'SELECT DISTINCT lot_no FROM lot_location_map WHERE batch_id=?',
                (batch_id,),
            ).fetchall()
            lot_nos = [r['lot_no'] for r in lot_rows]
            con.execute('DELETE FROM lot_location_map WHERE batch_id=?', (batch_id,))
            con.execute('DELETE FROM lot_location_import_batch WHERE id=?', (batch_id,))
            con.commit()
            new_latest = con.execute(
                'SELECT id FROM lot_location_import_batch ORDER BY id DESC LIMIT 1'
            ).fetchone()
            new_batch_id = new_latest['id'] if new_latest else None
        finally:
            con.close()
        logger.info('[location-map/delete-batch] batch_id=%s lot_count=%s', batch_id, len(lot_nos))
        return ok_response({
            'deleted_batch_id': batch_id,
            'lot_nos': lot_nos,
            'lot_count': len(lot_nos),
            'new_latest_batch_id': new_batch_id,
            'message': f'배치 #{batch_id} 삭제 완료 ({len(lot_nos)}개 LOT 위치 후보 제거)',
        })
    except Exception as e:
        logger.exception('[location-map/delete-batch] error: %s', e)
        return err_response(str(e))
