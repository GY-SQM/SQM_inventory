# -*- coding: utf-8 -*-
"""[감사] OneStop 파싱 진행 SSE 무한 스핀/누수 방지 회귀 테스트.

문제:
  - /api/onestop/parse-stream/{job_id} 가 Request 를 안 받아 창이 닫혀도 코루틴이
    계속 돌았고(누수), 등록만 되고 finish_job 이 영영 안 오면(업로드 취소·job_id
    불일치) while True 가 무한 keepalive 로 스핀 → 진행바가 영영 안 끝남.
  - parse_progress._jobs 는 done=False 인 orphan job 을 GC 하지 못해 무한 축적.
수정:
  - is_disconnected() 로 즉시 종료 + 유휴 타임아웃(STREAM_IDLE_TIMEOUT_SEC) 후 error 종료.
  - _gc() 가 방치된 orphan job(_STALE_AFTER_SEC 초과)도 정리 + register 마다 호출.
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import backend.api as bapi
import backend.api.parse_progress as pp


def _drain(resp, overall_timeout=5.0):
    """StreamingResponse 를 끝까지 소비해 (문자열 청크 목록) 반환. 자체 타임아웃 보호."""
    async def run():
        chunks = []
        async for c in resp.body_iterator:
            chunks.append(c.decode() if isinstance(c, (bytes, bytearray)) else c)
            if len(chunks) > 500:   # 안전장치: 무한 스핀이면 여기서 끊고 실패시킴
                break
        return chunks
    return asyncio.run(asyncio.wait_for(run(), timeout=overall_timeout))


class _Req:
    def __init__(self, disconnected=False):
        self._d = disconnected

    async def is_disconnected(self):
        return self._d


def test_stream_stops_immediately_when_disconnected():
    """창이 닫히면(=is_disconnected True) 스트림이 즉시 종료(무한 루프 아님)."""
    pp._jobs.clear()
    pp.register_job("JD")
    pp.emit_event("JD", "step", {"stage": "x"})   # done 은 영영 안 옴

    resp = asyncio.run(bapi.onestop_parse_stream("JD", _Req(disconnected=True)))
    chunks = _drain(resp, overall_timeout=5.0)
    # 즉시 종료 → 청크 거의 없음(무한 keepalive 아님)
    assert len(chunks) < 500


def test_stream_idle_timeout_ends_stream(monkeypatch):
    """등록만 되고 done/새 이벤트가 없으면 유휴 타임아웃 error 로 종료(무한 스핀 방지)."""
    pp._jobs.clear()
    pp.register_job("JT")   # exists=True, done 은 영영 안 옴, 이벤트도 없음
    monkeypatch.setattr(pp, "STREAM_IDLE_TIMEOUT_SEC", 0.3)
    monkeypatch.setattr(pp, "STREAM_POLL_INTERVAL_SEC", 0.05)

    resp = asyncio.run(bapi.onestop_parse_stream("JT", _Req(disconnected=False)))
    chunks = _drain(resp, overall_timeout=5.0)
    joined = "".join(chunks)
    assert "stream_idle_timeout" in joined, joined[:200]


def test_stream_completes_normally_on_done(monkeypatch):
    """정상 경로: 이벤트 후 finish_job(done) 이 오면 그 이벤트들을 흘리고 종료."""
    pp._jobs.clear()
    pp.register_job("JN")
    pp.emit_event("JN", "step", {"stage": "pl_parse_start"})
    pp.emit_event("JN", "step", {"stage": "pl_parse_done"})
    pp.finish_job("JN", summary={"rows": 3})
    monkeypatch.setattr(pp, "STREAM_IDLE_TIMEOUT_SEC", 5.0)

    resp = asyncio.run(bapi.onestop_parse_stream("JN", _Req(disconnected=False)))
    chunks = _drain(resp, overall_timeout=5.0)
    joined = "".join(chunks)
    assert "pl_parse_start" in joined and "pl_parse_done" in joined
    assert "event: done" in joined
    assert "stream_idle_timeout" not in joined


def test_job_not_found_error_when_never_registered(monkeypatch):
    """등록조차 안 된 job → register 대기 후 job_not_found error 로 종료."""
    pp._jobs.clear()
    monkeypatch.setattr(pp, "STREAM_REGISTER_WAIT_SEC", 0.2)

    resp = asyncio.run(bapi.onestop_parse_stream("NOPE", _Req(disconnected=False)))
    chunks = _drain(resp, overall_timeout=5.0)
    assert "job_not_found" in "".join(chunks)


def test_gc_reaps_stale_unfinished_orphan_jobs():
    """done 되지 못한 채 방치된 orphan job 도 GC 대상."""
    pp._jobs.clear()
    pp.register_job("ORPHAN")
    # started_at 을 stale 임계값 이전으로 되돌림
    pp._jobs["ORPHAN"]["started_at"] = time.time() - pp._STALE_AFTER_SEC - 10
    pp._gc()
    assert "ORPHAN" not in pp._jobs


def test_gc_keeps_recent_unfinished_job():
    """방금 등록된(진행 중) job 은 GC 하지 않음 — 오탐 방지."""
    pp._jobs.clear()
    pp.register_job("FRESH")
    pp._gc()
    assert "FRESH" in pp._jobs
