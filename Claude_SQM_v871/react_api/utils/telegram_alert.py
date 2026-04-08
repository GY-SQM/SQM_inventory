# -*- coding: utf-8 -*-
"""
SQM Telegram Alert — API 에러 + 시스템 이벤트 실시간 알림
생성일: 2026-04-08 | SQM v8.7.1

배치 위치: react_api/utils/telegram_alert.py

기존 scripts/telegram_notify.py 와의 차이:
  - 비동기(async) 지원 — FastAPI와 완벽 호환
  - 에러 레벨별 이모지 자동 적용
  - 중복 알림 방지 (1분 내 동일 에러 재발송 차단)
  - BOT_TOKEN / CHAT_ID .env 자동 로드
"""
import asyncio
import hashlib
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ================================================================
# 설정 — .env 에서 자동 로드
# ================================================================
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
CHAT_ID:   str = os.getenv("CHAT_ID",   "")

# 중복 알림 방지 — 같은 에러 60초 내 재발송 차단
_sent_cache: dict[str, float] = {}
DEDUP_SECONDS = 60


# ================================================================
# 핵심 발송 함수
# ================================================================

async def send_alert(
    message: str,
    level: str = "INFO",
    dedup: bool = True
) -> bool:
    """
    Telegram 알림 비동기 발송

    Args:
        message: 발송할 메시지
        level:   INFO / WARNING / ERROR / CRITICAL
        dedup:   True면 60초 내 동일 메시지 중복 차단

    Returns: 발송 성공 여부
    """
    if not BOT_TOKEN or not CHAT_ID:
        logger.debug("Telegram 미설정 — 알림 스킵 (BOT_TOKEN/CHAT_ID 없음)")
        return False

    # 중복 차단
    if dedup:
        key = hashlib.md5(message.encode()).hexdigest()
        now = time.time()
        if key in _sent_cache and now - _sent_cache[key] < DEDUP_SECONDS:
            logger.debug(f"Telegram 중복 차단 ({DEDUP_SECONDS}초): {message[:40]}")
            return False
        _sent_cache[key] = now
        # 캐시 정리 (1000개 초과 시)
        if len(_sent_cache) > 1000:
            oldest = sorted(_sent_cache.items(), key=lambda x: x[1])
            for k, _ in oldest[:500]:
                del _sent_cache[k]

    # 레벨별 이모지
    emoji = {
        "INFO":     "ℹ️",
        "WARNING":  "️",
        "ERROR":    "",
        "CRITICAL": "",
    }.get(level.upper(), "")

    full_msg = f"{emoji} <b>[SQM {level}]</b>\n{message}"

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id":    CHAT_ID,
                    "text":       full_msg,
                    "parse_mode": "HTML"
                }
            )
            ok = res.status_code == 200
            if not ok:
                logger.warning(f"Telegram 발송 실패: HTTP {res.status_code}")
            return ok
    except Exception as e:
        logger.warning(f"Telegram 발송 예외: {e}")
        return False


def send_alert_sync(message: str, level: str = "INFO") -> bool:
    """
    동기 방식 발송 (스케줄러, 백그라운드 태스크용)
    """
    if not BOT_TOKEN or not CHAT_ID:
        return False
    try:
        import requests
        emoji = {"INFO": "ℹ️", "WARNING": "️", "ERROR": "", "CRITICAL": ""}.get(
            level.upper(), ""
        )
        res = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id":    CHAT_ID,
                "text":       f"{emoji} <b>[SQM {level}]</b>\n{message}",
                "parse_mode": "HTML"
            },
            timeout=10
        )
        return res.status_code == 200
    except Exception as e:
        logger.warning(f"Telegram 동기 발송 예외: {e}")
        return False


# ================================================================
# 편의 함수
# ================================================================

async def alert_error(context: str, error: Exception) -> bool:
    """API 500 에러 알림"""
    msg = (
        f"<b>엔드포인트:</b> {context}\n"
        f"<b>에러:</b> {type(error).__name__}\n"
        f"<b>메시지:</b> {str(error)[:200]}"
    )
    return await send_alert(msg, level="ERROR")


async def alert_critical(context: str, detail: str) -> bool:
    """DB 연결 실패 / 엔진 초기화 실패 등 치명적 오류"""
    msg = f"<b>치명적 오류 — {context}</b>\n{detail[:300]}"
    return await send_alert(msg, level="CRITICAL", dedup=False)


async def alert_warning(context: str, detail: str) -> bool:
    """중량 불일치 / 만료 예약 등 경고"""
    msg = f"<b>{context}</b>\n{detail[:300]}"
    return await send_alert(msg, level="WARNING")


async def alert_info(message: str) -> bool:
    """서버 시작/종료 등 일반 정보"""
    return await send_alert(message, level="INFO", dedup=False)
