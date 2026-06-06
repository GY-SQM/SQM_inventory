"""
SQM v8.7.1 — 분리 창 (Popout) Pub/Sub 라우터.

목적
----
PyWebView 메인 창의 떠다니는 패널(parse-result, parse-log, gemini-compare 등)을
OS 레벨 별도 창으로 "팝아웃" 할 수 있도록 하는 메시지 버스.

데이터 흐름
-----------
1. 메인 창이 패널 outerHTML 을 캡처해 POST /api/popout/snapshot/{key} 로 저장
2. 메인 창이 pywebview.api.open_detached_window(...) 호출 → 새 OS 창 생성
3. 새 창은 /popout.html?key={key} 를 로드, GET snapshot 으로 초기 HTML 주입
4. 메인 → 분리 창 라이브 업데이트: POST /api/popout/m2d/{key} → SSE 푸시
5. 분리 창 → 메인 액션(onclick 등): POST /api/popout/d2m/{key} → SSE 푸시
6. 분리 창 닫힐 때 d2m 으로 {type:'close'} 전송 → 메인이 원본 패널 복원

채널은 메모리 only (재시작 시 소실 OK — 휘발성 UI 상태).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/popout", tags=["popout"])
log = logging.getLogger(__name__)


# ── In-memory 채널 상태 ────────────────────────────────────────────────
# 각 key 마다: { 'snapshot': str, 'm2d_events': [...], 'd2m_events': [...],
#               'm2d_subs': [Queue], 'd2m_subs': [Queue], 'updated': float }
_CHANNELS: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
    'snapshot': '',
    'm2d_events': [],
    'd2m_events': [],
    'm2d_subs': [],
    'd2m_subs': [],
    'updated': time.time(),
})

# 최대 보관 이벤트 (메모리 보호)
_MAX_BUFFERED_EVENTS = 500


def _push_event(key: str, direction: str, event: Dict[str, Any]) -> None:
    """direction in {'m2d','d2m'} — 채널에 이벤트 추가 + 모든 구독자 큐에 전달."""
    ch = _CHANNELS[key]
    events_key = f'{direction}_events'
    subs_key = f'{direction}_subs'

    ch[events_key].append(event)
    # 버퍼 크기 제한
    if len(ch[events_key]) > _MAX_BUFFERED_EVENTS:
        ch[events_key] = ch[events_key][-_MAX_BUFFERED_EVENTS:]
    ch['updated'] = time.time()

    # 살아있는 구독자에게만 전달, dead 큐는 제거
    dead = []
    for q in ch[subs_key]:
        try:
            q.put_nowait(event)
        except Exception:
            dead.append(q)
    for q in dead:
        try:
            ch[subs_key].remove(q)
        except ValueError:
            pass


# ── Snapshot (초기 HTML) ──────────────────────────────────────────────
@router.post("/snapshot/{key}", summary="분리 창 초기 HTML 저장")
async def set_snapshot(key: str, payload: dict = Body(...)):
    html = (payload or {}).get('html', '')
    if not isinstance(html, str):
        raise HTTPException(400, "html must be string")
    # snapshot 갱신 시 기존 이벤트 큐를 비워 새 라이프사이클 시작
    ch = _CHANNELS[key]
    ch['snapshot'] = html
    ch['m2d_events'] = []
    ch['d2m_events'] = []
    ch['updated'] = time.time()
    return {'ok': True, 'key': key, 'size': len(html)}


@router.get("/snapshot/{key}", summary="분리 창 초기 HTML 조회")
async def get_snapshot(key: str):
    ch = _CHANNELS.get(key)
    if not ch or not ch.get('snapshot'):
        raise HTTPException(404, f"no snapshot for key={key}")
    return {'ok': True, 'key': key, 'html': ch['snapshot']}


# ── M2D (메인 → 분리 창) ───────────────────────────────────────────────
@router.post("/m2d/{key}", summary="메인 → 분리 창 이벤트")
async def post_m2d(key: str, payload: dict = Body(...)):
    if not isinstance(payload, dict):
        raise HTTPException(400, "event must be json object")
    _push_event(key, 'm2d', payload)
    return {'ok': True}


@router.get("/m2d/{key}/stream", summary="분리 창 구독 (SSE)")
async def stream_m2d(key: str, request: Request):
    """분리 창이 메인에서 보낸 이벤트를 구독."""
    q: asyncio.Queue = asyncio.Queue()
    ch = _CHANNELS[key]
    ch['m2d_subs'].append(q)

    # 누적 이벤트 즉시 재생 (재연결 대응)
    for ev in ch['m2d_events']:
        await q.put(ev)

    async def gen():
        try:
            # 연결 초기 핸드셰이크
            yield "event: ready\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"event: message\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            try:
                ch['m2d_subs'].remove(q)
            except ValueError:
                pass

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── D2M (분리 창 → 메인) ───────────────────────────────────────────────
@router.post("/d2m/{key}", summary="분리 창 → 메인 이벤트")
async def post_d2m(key: str, payload: dict = Body(...)):
    if not isinstance(payload, dict):
        raise HTTPException(400, "event must be json object")
    _push_event(key, 'd2m', payload)
    return {'ok': True}


@router.get("/d2m/{key}/stream", summary="메인 구독 (SSE)")
async def stream_d2m(key: str, request: Request):
    """메인 창이 분리 창에서 보낸 이벤트(close/action 등)를 구독."""
    q: asyncio.Queue = asyncio.Queue()
    ch = _CHANNELS[key]
    ch['d2m_subs'].append(q)

    for ev in ch['d2m_events']:
        await q.put(ev)

    async def gen():
        try:
            yield "event: ready\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"event: message\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            try:
                ch['d2m_subs'].remove(q)
            except ValueError:
                pass

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── Cleanup ────────────────────────────────────────────────────────────
@router.post("/clear/{key}", summary="채널 클리어 (메인이 팝인 후 호출)")
async def clear_channel(key: str):
    if key in _CHANNELS:
        del _CHANNELS[key]
    return {'ok': True, 'key': key}


@router.get("/status/{key}", summary="채널 상태 조회")
async def status(key: str):
    ch = _CHANNELS.get(key)
    if not ch:
        return {'exists': False, 'key': key}
    return {
        'exists': True,
        'key': key,
        'has_snapshot': bool(ch.get('snapshot')),
        'm2d_events': len(ch.get('m2d_events', [])),
        'd2m_events': len(ch.get('d2m_events', [])),
        'm2d_subs': len(ch.get('m2d_subs', [])),
        'd2m_subs': len(ch.get('d2m_subs', [])),
        'updated': ch.get('updated', 0),
    }
