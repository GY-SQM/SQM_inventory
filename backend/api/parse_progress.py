"""
parse_progress.py — OneStop 파싱 진행 상황 SSE pub/sub
─────────────────────────────────────────────────────────
백엔드 동기 파싱 중간중간에 emit_event(...) 를 호출해서
프론트의 EventSource 가 실시간으로 받아볼 수 있게 한다.

사용 패턴
─────────
백엔드(동기 파싱):
    pp.register_job(job_id)
    pp.emit_event(job_id, "step", {"stage": "pl_parse_start", "filename": pl.filename})
    ... 파싱 ...
    pp.emit_event(job_id, "step", {"stage": "pl_parse_done", "rows": len(...)})
    ...
    pp.finish_job(job_id)

엔드포인트:
    GET /api/onestop/parse-stream/{job_id}
    → text/event-stream 으로 위 이벤트들을 그대로 push.

설계 결정
─────────
- 메모리 dict (`_jobs`) 사용. 단일 프로세스/PyWebView 환경에 충분.
- 스레드 안전 (threading.Lock).
- 파싱은 별도 스레드 없이 동기 호출 그대로. emit 만 list append (블록 없음).
- SSE 컨슈머는 async generator + asyncio.sleep 폴링 (0.15s) 방식 — 백엔드 파싱이
  메인 스레드를 점유해도 별 영향 없음. (FastAPI 는 sync def 엔드포인트도
  threadpool 으로 돌리므로 SSE async 와 병행 가능)
- 완료 후 60초 뒤 자동 GC.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sqm.parse_progress")

_jobs: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

# 완료된 job 자동 정리 임계값 (초)
_GC_AFTER_SEC = 60


def register_job(job_id: str) -> None:
    """파싱 시작 직전 한 번만 호출. job_id 는 프론트에서 생성한 임의 문자열."""
    if not job_id:
        return
    with _lock:
        _jobs[job_id] = {
            "events": [],
            "done": False,
            "started_at": time.time(),
            "finished_at": 0.0,
        }
    logger.info(f"[parse_progress] register {job_id}")


def emit_event(job_id: str, event: str, data: Optional[dict] = None) -> None:
    """파싱 도중 진행 이벤트 1건 추가.
    event: 'step' | 'warn' | 'error' | 'info' | 'done' | 'result'
    data:  임의 dict (JSON 직렬화 가능해야 함)
    """
    if not job_id:
        return
    payload = {
        "event": event,
        "data": data or {},
        "ts": time.time(),
    }
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            # register 안 된 job — 누락 emit 은 조용히 무시
            return
        job["events"].append(payload)


def finish_job(job_id: str, summary: Optional[dict] = None) -> None:
    """파싱 완료/실패 시 호출. done 이벤트를 자동 추가."""
    if not job_id:
        return
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        if summary is not None:
            job["events"].append({"event": "summary", "data": summary, "ts": time.time()})
        job["events"].append({"event": "done", "data": {}, "ts": time.time()})
        job["done"] = True
        job["finished_at"] = time.time()
    _gc()
    logger.info(f"[parse_progress] finish {job_id}")


def _gc() -> None:
    """완료된 지 _GC_AFTER_SEC 초 지난 job 들 제거."""
    now = time.time()
    with _lock:
        to_del = [
            jid for jid, j in _jobs.items()
            if j["done"] and (now - j["finished_at"]) > _GC_AFTER_SEC
        ]
        for jid in to_del:
            _jobs.pop(jid, None)


def get_events_since(job_id: str, sent_count: int) -> tuple[list, bool, bool]:
    """job_id 의 events[sent_count:] 와 (done, exists) 반환. 스레드 safe."""
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return [], False, False
        events = job["events"][sent_count:]
        return list(events), bool(job["done"]), True


def format_sse(payload: dict) -> str:
    """SSE 텍스트 직렬화. event 라인 + data 라인."""
    try:
        data_json = json.dumps(payload.get("data") or {}, ensure_ascii=False)
    except Exception:
        data_json = "{}"
    ev = payload.get("event") or "message"
    # SSE 스펙: 각 라인은 \n, 메시지 구분은 \n\n
    return f"event: {ev}\ndata: {data_json}\n\n"
