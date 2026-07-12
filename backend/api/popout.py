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
#               'm2d_subs': [Queue], 'd2m_subs': [Queue], 'updated': float,
#               '_seq': int }
# 버퍼 이벤트는 {'id': int, 'event': dict} 봉투(envelope)로 보관한다.
_CHANNELS: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
    'snapshot': '',
    'm2d_events': [],
    'd2m_events': [],
    'm2d_subs': [],
    'd2m_subs': [],
    'updated': time.time(),
    '_seq': 0,
})

# 최대 보관 이벤트 (메모리 보호)
_MAX_BUFFERED_EVENTS = 500

# [감사 #3-E] 재생(replay) 금지 대상 = '부수효과 명령' 이벤트.
#   SSE 자동 재연결 시 서버가 누적 이벤트를 재생하는데, 아래 타입은 상태가 아니라
#   메인 창에서 eval 등으로 '한 번 실행'되는 명령이다. 재생하면 삭제/확정 같은
#   부수효과가 중복 실행된다. → 라이브로만 1회 전달하고 버퍼(재생 대상)엔 넣지 않음
#   (at-most-once: 유실은 재클릭으로 복구 가능, 중복 실행이 훨씬 위험).
_SIDE_EFFECT_TYPES: Dict[str, set] = {
    'd2m': {'action', 'close'},
    'm2d': set(),
}


def _is_side_effect(direction: str, event: Dict[str, Any]) -> bool:
    """이 이벤트가 재생 금지 대상(부수효과 명령)인지."""
    if not isinstance(event, dict):
        return False
    if event.get('_ephemeral') is True or event.get('_replay') is False:
        return True
    return event.get('type') in _SIDE_EFFECT_TYPES.get(direction, set())


def _events_to_replay(ch: Dict[str, Any], direction: str, last_event_id: int) -> List[dict]:
    """(재)구독 시 재생할 봉투 목록 — last_event_id 보다 큰 것만."""
    return [env for env in ch[f'{direction}_events'] if env['id'] > last_event_id]


def _parse_last_event_id(request) -> int:
    """SSE 재연결 시 브라우저가 보내는 Last-Event-ID 헤더(정수) 파싱. 없으면 0."""
    try:
        raw = request.headers.get('last-event-id')
        return int(raw) if raw is not None and str(raw).strip() != '' else 0
    except (TypeError, ValueError):
        return 0


def _push_event(key: str, direction: str, event: Dict[str, Any]) -> None:
    """direction in {'m2d','d2m'} — 채널에 이벤트 추가 + 모든 구독자 큐에 전달.

    [감사 #3-E] 각 이벤트에 채널 단조 증가 id 를 부여한다(SSE `id:` 필드로 노출 →
    브라우저가 Last-Event-ID 로 되돌려줌). 부수효과 명령(_is_side_effect)은 재생
    버퍼에 넣지 않아 재연결 시 재실행되지 않는다(라이브 1회 전달만).
    """
    ch = _CHANNELS[key]
    events_key = f'{direction}_events'
    subs_key = f'{direction}_subs'

    ch['_seq'] += 1
    env = {'id': ch['_seq'], 'event': event}

    if not _is_side_effect(direction, event):
        ch[events_key].append(env)
        # 버퍼 크기 제한
        if len(ch[events_key]) > _MAX_BUFFERED_EVENTS:
            ch[events_key] = ch[events_key][-_MAX_BUFFERED_EVENTS:]
    ch['updated'] = time.time()

    # 살아있는 구독자에게만 (봉투 그대로) 전달, dead 큐는 제거
    dead = []
    for q in ch[subs_key]:
        try:
            q.put_nowait(env)
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


def _sse_stream(key: str, direction: str, request: Request) -> StreamingResponse:
    """m2d/d2m 공통 SSE 스트림.

    [감사 #3-E] 재연결 시 Last-Event-ID 이후의, 그리고 부수효과가 아닌(버퍼에 남은)
    이벤트만 재생한다. 각 프레임에 `id:` 를 실어 브라우저가 다음 재연결에 이어붙일
    수 있게 한다.
    """
    q: asyncio.Queue = asyncio.Queue()
    ch = _CHANNELS[key]
    ch[f'{direction}_subs'].append(q)

    last_id = _parse_last_event_id(request)
    # 누적(재생 대상) 이벤트 중 아직 못 본 것만 재생 (재연결 대응)
    for env in _events_to_replay(ch, direction, last_id):
        q.put_nowait(env)

    async def gen():
        try:
            # 연결 초기 핸드셰이크
            yield "event: ready\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    env = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield (
                        f"id: {env['id']}\n"
                        f"event: message\n"
                        f"data: {json.dumps(env['event'], ensure_ascii=False)}\n\n"
                    )
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            try:
                ch[f'{direction}_subs'].remove(q)
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


@router.get("/m2d/{key}/stream", summary="분리 창 구독 (SSE)")
async def stream_m2d(key: str, request: Request):
    """분리 창이 메인에서 보낸 이벤트를 구독."""
    return _sse_stream(key, 'm2d', request)


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
    return _sse_stream(key, 'd2m', request)


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
