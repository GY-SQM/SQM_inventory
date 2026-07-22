# -*- coding: utf-8 -*-
"""
tools/cleanup_audit_job.py
==========================
SQM v9.0.6 — audit_log 자동 정리 작업 (Windows 스케줄러에서 호출)

v9.0.5에서 추가된 cleanup_audit() 함수를 운영 자동화한다.
v8.8.5에서 "윈도우 스케줄러 자동 디스크 청소 주기 등록"이 description만
남아있고 실제 schtasks 명령은 레포에 없었던 작업을 v9.0.6에서 보완.

사용법:
    python tools/cleanup_audit_job.py [DAYS]
        DAYS: 보관 기간 (default 30, 1~365 권장)

스케줄러 등록:
    powershell -ExecutionPolicy Bypass -File tools/install_cleanup_scheduler.ps1

출력 (JSON, 한 줄):
    {"ok": true,  "data": {"deleted": N, "days": 30}}
    {"ok": false, "error": "...", "data": {"deleted": 0, "days": 30}}

설계 결정:
    - 항상 exit 0 (silent failure: cleanup은 best-effort, 운영 critical 아님)
    - JSON 한 줄 출력 → 스케줄러 로그/모니터링 파싱 용이
    - DB 없거나 실패 시 deleted=0 + error 메시지
    - DB 경로는 core.db_allowed._get_default_db_path() 위임
      (config.DB_PATH 또는 환경변수; 테스트 환경에서 None이면 즉시 종료)
"""
import json
import sys
from pathlib import Path

# 프로젝트 루트 추가 (tools/ 단독 실행 대비)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def run_cleanup(days: int = 30) -> dict:
    """
    cleanup_audit() 호출 + 결과 dict 반환.

    Returns:
        {"ok": bool, "data": {"deleted": int, "days": int}, "error"?: str}
    """
    try:
        from core.db_allowed import cleanup_audit
        deleted = cleanup_audit(days=days)
        return {"ok": True, "data": {"deleted": int(deleted), "days": days}}
    except Exception as e:
        # silent failure — 스케줄러는 매주 반복되므로 일시 실패는 noise
        return {
            "ok": False,
            "error": str(e)[:200],
            "data": {"deleted": 0, "days": days},
        }


def main() -> int:
    days = 30
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print(json.dumps({"ok": False, "error": f"days 인자 파싱 실패: {sys.argv[1]!r}"}))
            return 0

    # days <= 0이면 run_cleanup()이 no-op (cleanup_audit 내부 가드) → deleted=0
    # 그래도 JSON 한 줄은 출력 (스케줄러 로그 파싱 일관성)
    result = run_cleanup(days=days)
    print(json.dumps(result, ensure_ascii=False))
    return 0  # 항상 0 (best-effort)


if __name__ == "__main__":
    sys.exit(main())
