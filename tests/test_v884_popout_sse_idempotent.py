# -*- coding: utf-8 -*-
"""[감사 #3-E] 분리창(popout) SSE 멱등성 회귀 테스트.

문제: d2m SSE 는 (재)구독 때마다 누적 이벤트를 통째로 재생했고, EventSource 는
  오류 시 자동 재연결한다. d2m 'action' 은 메인 창에서 eval 로 '한 번 실행'되는
  부수효과 명령이라, 재연결마다 삭제/확정 같은 액션이 중복 실행됐다.
수정: (1) 이벤트에 채널 단조증가 id 부여 + Last-Event-ID 이후만 재생(dedup),
      (2) 부수효과 명령(d2m action/close)은 재생 버퍼에 넣지 않음(at-most-once).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import backend.api.popout as popout


def _fresh(key):
    """테스트 격리를 위해 채널 초기화."""
    if key in popout._CHANNELS:
        del popout._CHANNELS[key]
    return popout._CHANNELS[key]


def test_side_effect_classification():
    assert popout._is_side_effect('d2m', {'type': 'action', 'expr': 'x()'}) is True
    assert popout._is_side_effect('d2m', {'type': 'close'}) is True
    # m2d 콘텐츠 업데이트는 부수효과 아님(재생 허용)
    assert popout._is_side_effect('m2d', {'type': 'update', 'html': '<b>x</b>'}) is False
    # 명시적 opt-out 플래그
    assert popout._is_side_effect('m2d', {'type': 'update', '_ephemeral': True}) is True
    assert popout._is_side_effect('m2d', {'type': 'update', '_replay': False}) is True


def test_d2m_action_not_buffered_for_replay():
    """핵심: d2m 'action' 은 재생 버퍼에 남지 않는다 → 재연결해도 재실행 안 됨."""
    key = 'K_ACTION'
    ch = _fresh(key)
    popout._push_event(key, 'd2m', {'type': 'action', 'expr': 'window.doDelete()'})
    # 재생 버퍼 비어 있음
    assert ch['d2m_events'] == []
    # 재연결(Last-Event-ID=0) 시 재생할 것 없음 → 중복 실행 방지
    assert popout._events_to_replay(ch, 'd2m', 0) == []


def test_close_not_buffered_for_replay():
    key = 'K_CLOSE'
    ch = _fresh(key)
    popout._push_event(key, 'd2m', {'type': 'close'})
    assert ch['d2m_events'] == []
    assert popout._events_to_replay(ch, 'd2m', 0) == []


def test_action_still_delivered_live_once():
    """재생은 막되, 현재 연결된 구독자에게는 라이브로 1회 전달된다."""
    import asyncio

    key = 'K_LIVE'
    ch = _fresh(key)
    q: asyncio.Queue = asyncio.Queue()
    ch['d2m_subs'].append(q)

    popout._push_event(key, 'd2m', {'type': 'action', 'expr': 'x()'})

    assert q.qsize() == 1
    env = q.get_nowait()
    assert env['event']['type'] == 'action'
    assert isinstance(env['id'], int) and env['id'] >= 1


def test_m2d_state_buffered_and_replayed_with_dedup():
    """m2d 상태 이벤트는 버퍼링·재생하되 Last-Event-ID 로 중복 제거."""
    key = 'K_STATE'
    ch = _fresh(key)
    popout._push_event(key, 'm2d', {'type': 'update', 'n': 1})
    popout._push_event(key, 'm2d', {'type': 'update', 'n': 2})

    ids = [env['id'] for env in ch['m2d_events']]
    assert len(ids) == 2 and ids[0] < ids[1], "단조 증가 id"

    # 신규 구독(Last-Event-ID 없음) → 둘 다 재생
    replay_all = popout._events_to_replay(ch, 'm2d', 0)
    assert [e['event']['n'] for e in replay_all] == [1, 2]

    # 첫 이벤트까지 봤다면(Last-Event-ID=ids[0]) → 두 번째만 재생
    replay_after = popout._events_to_replay(ch, 'm2d', ids[0])
    assert [e['event']['n'] for e in replay_after] == [2]


def test_reconnect_does_not_replay_side_effect_but_replays_state():
    """복합 시나리오: 재연결 시 상태는 이어받되 부수효과 명령은 재생되지 않음."""
    key = 'K_MIX'
    ch = _fresh(key)
    # m2d 상태 1건 + d2m 액션 1건이 순서대로 발생
    popout._push_event(key, 'm2d', {'type': 'update', 'html': 'A'})
    popout._push_event(key, 'd2m', {'type': 'action', 'expr': 'window.confirmOutbound()'})

    # 분리 창 재연결(m2d, Last-Event-ID=0) → 상태 A 는 재생됨
    m2d_replay = popout._events_to_replay(ch, 'm2d', 0)
    assert [e['event']['html'] for e in m2d_replay] == ['A']
    # 메인 재연결(d2m, Last-Event-ID=0) → 액션은 재생 안 됨(중복 확정 방지)
    d2m_replay = popout._events_to_replay(ch, 'd2m', 0)
    assert d2m_replay == []


def test_last_event_id_parsing():
    class _Req:
        def __init__(self, headers):
            self.headers = headers
    assert popout._parse_last_event_id(_Req({'last-event-id': '7'})) == 7
    assert popout._parse_last_event_id(_Req({})) == 0
    assert popout._parse_last_event_id(_Req({'last-event-id': ''})) == 0
    assert popout._parse_last_event_id(_Req({'last-event-id': 'bad'})) == 0
