# -*- coding: utf-8 -*-
r"""
tools/inspect_pc.py
===================
SQM v9.0.7 — PC 인스펙터 CLI

사용법:
    # 인스펙터 실행 (registry 자동 감지, 환경변수 PC_GUARD_REGISTRY)
    python tools/inspect_pc.py

    # registry 명시
    python tools/inspect_pc.py --registry D:\program-kdn\Network\allowed_pcs.json

    # 현재 PC의 GUID를 registry에 등록
    python tools/inspect_pc.py --register

출력: JSON 한 줄 (pretty-printed)

Exit code:
    0 — FULL_AUTH 또는 DISABLED (registry 미설정, 비활성)
    1 — PARTIAL_AUTH, NOT_REGISTERED, REGISTRY_MISSING, PARSE_ERROR
"""
import argparse
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Windows cp949 회피 — stdout을 utf-8로 강제
if hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

from core.pc_guard import inspect, register, get_registry_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SQM Inventory - PC 인스펙터 (v9.0.7)"
    )
    parser.add_argument(
        "--register", action="store_true",
        help="현재 PC의 GUID를 registry에 등록"
    )
    parser.add_argument(
        "--registry", type=Path, default=None,
        help="registry 경로 (기본: PC_GUARD_REGISTRY 환경변수)"
    )
    args = parser.parse_args()

    registry = args.registry or get_registry_path()

    if args.register:
        result = register(registry)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1

    # inspect
    report = inspect(registry)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    code = report.get("보안판정", {}).get("판정코드", "")
    if code in ("FULL_AUTH", "DISABLED"):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
