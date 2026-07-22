# -*- coding: utf-8 -*-
r"""
core/pc_guard.py
================
SQM v9.0.7 — PC Guard (허가된 PC에서만 SQM_inventory 동작)

GY_PC_Manager의 allowed_pcs.json을 registry로 사용.
PC 핑거프린트 (호스트명, MAC, MachineGuid)를 수집해
allowed_pcs.json에 등록된 PC인지 확인.

비활성 (기본):
    - PC_GUARD_REGISTRY 환경변수 미설정 시 비활성
    - is_allowed() → True (backward compat, SQM_inventory 기존 동작 유지)

활성:
    - PC_GUARD_REGISTRY=D:\program-kdn\Network\allowed_pcs.json
    - 미등록/부분 인증 PC → is_allowed() False, 호출자가 차단

registry 형식 (allowed_pcs.json):
    {
      "allowed_pcs": [
        {
          "name": "대흥남기동2025",
          "macs": ["E8:62:BE:90:6B:F9", ...],
          "machine_guid": "62a420c7-..."
        }
      ]
    }

판정 코드:
    - FULL_AUTH: hostname + mac + guid 모두 일치 → 허용
    - PARTIAL_AUTH: mac 일치 + guid 미등록 → 거부 (--register 권장)
    - NOT_REGISTERED: 미등록 PC → 거부
    - DISABLED: registry 미설정 → 허용 (비활성)
    - REGISTRY_MISSING: registry 파일 없음 → 거부
    - REGISTRY_PARSE_ERROR: registry JSON 깨짐 → 거부

Windows registry 경로 (참고):
    HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid

Windows 전용 (winreg, getmac). Linux/Mac에서는 fingerprint가 빈 값.
"""
import json
import os
import re
import shutil
import socket
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

IS_WINDOWS = os.name == "nt"


# ── registry 경로 ───────────────────────────────────────

def get_registry_path() -> Optional[Path]:
    """PC_GUARD_REGISTRY 환경변수에서 registry 경로. 미설정 시 None."""
    p = os.environ.get("PC_GUARD_REGISTRY", "").strip()
    if not p:
        return None
    return Path(p)


# ── 핑거프린트 수집 ─────────────────────────────────────

def collect_fingerprint() -> dict:
    """
    현재 PC의 핑거프린트 수집.

    Returns:
        {
            "hostname": str,
            "user": str,
            "machine_guid": str,  # Windows registry MachineGuid
            "macs": list[str],    # 모든 NIC MAC, 대문자, ':' 구분자
        }
    """
    return {
        "hostname": _get_hostname(),
        "user": _get_user(),
        "machine_guid": _get_machine_guid(),
        "macs": _get_mac_addresses(),
    }


def _get_hostname() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return ""


def _get_user() -> str:
    try:
        return os.getlogin()
    except Exception:
        return os.environ.get("USERNAME", os.environ.get("USER", "unknown"))


def _get_machine_guid() -> str:
    """Windows registry의 MachineGuid (HKLM\\SOFTWARE\\Microsoft\\Cryptography)."""
    if not IS_WINDOWS:
        return ""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        )
        try:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value)
        finally:
            winreg.CloseKey(key)
    except Exception:
        return ""


_MAC_RE = re.compile(
    r"^[0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}$"
)


def _get_mac_addresses() -> list[str]:
    """
    Windows getmac으로 모든 NIC의 MAC 주소 수집 (deduped, uppercase, ':' 구분자).

    Bluetooth/virtual adapter는 비활성인 경우도 있어서 결과가 비어있을 수 있음.
    """
    if not IS_WINDOWS:
        return []
    try:
        out = subprocess.run(
            ["getmac", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
            encoding="cp949",
            errors="replace",
        )
    except Exception:
        return []
    macs: list[str] = []
    seen: set[str] = set()
    for line in out.stdout.splitlines():
        parts = line.split(",")
        if not parts:
            continue
        mac = parts[0].strip().strip('"').replace("-", ":").upper()
        if _MAC_RE.match(mac) and mac not in seen:
            seen.add(mac)
            macs.append(mac)
    return macs


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── 인스펙터 (전체 리포트) ───────────────────────────────

def inspect(registry_path: Optional[Path] = None) -> dict:
    """
    PC 인스펙터 (SQM v9.0.7 slim 버전).

    Returns:
        {
            "관리정보": {"리포트제목", "수집시각", "호스트명", "사용자"},
            "하드웨어식별": {"MachineGuid", "전체MAC"},
            "보안판정": {"호스트명", "매칭PC"?, "MAC일치", "GUID일치",
                         "판정", "판정코드", "상세"?}
        }
    """
    if registry_path is None:
        registry_path = get_registry_path()
    fp = collect_fingerprint()
    return {
        "관리정보": {
            "리포트제목": "SQM Inventory - PC 인스펙터 (v9.0.7)",
            "수집시각": _now_str(),
            "호스트명": fp["hostname"],
            "사용자": fp["user"],
        },
        "하드웨어식별": {
            "MachineGuid": fp["machine_guid"],
            "전체MAC": fp["macs"],
        },
        "보안판정": _judge(fp, registry_path),
    }


# ── 판정 로직 ────────────────────────────────────────────

def _judge(fp: dict, registry_path: Optional[Path]) -> dict:
    """fingerprint + registry_path → 판정 dict."""
    if registry_path is None:
        return {
            "호스트명": fp["hostname"],
            "MAC일치": False,
            "GUID일치": False,
            "판정": "비활성 (PC_GUARD_REGISTRY 미설정)",
            "판정코드": "DISABLED",
        }
    if not registry_path.exists():
        return {
            "호스트명": fp["hostname"],
            "MAC일치": False,
            "GUID일치": False,
            "판정": f"⚠️ registry 없음: {registry_path}",
            "판정코드": "REGISTRY_MISSING",
        }
    try:
        raw = registry_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        allowed = data.get("allowed_pcs", [])
    except Exception as e:
        return {
            "호스트명": fp["hostname"],
            "MAC일치": False,
            "GUID일치": False,
            "판정": f"⚠️ registry 파싱 실패: {e}",
            "판정코드": "REGISTRY_PARSE_ERROR",
        }

    fp_macs = set(fp["macs"])
    for pc in allowed:
        name = pc.get("name", "")
        registered_macs = {m.upper() for m in pc.get("macs", [])}
        registered_guid = pc.get("machine_guid", "").strip()

        mac_match = bool(registered_macs & fp_macs)
        guid_match = bool(registered_guid) and (registered_guid == fp["machine_guid"])
        name_match = (name == fp["hostname"])

        if name_match and mac_match and guid_match:
            return {
                "호스트명": fp["hostname"],
                "매칭PC": name,
                "MAC일치": True,
                "GUID일치": True,
                "판정": "✅ 완전 인증",
                "판정코드": "FULL_AUTH",
            }
        if mac_match and not guid_match and name_match:
            matching_mac = sorted(registered_macs & fp_macs)[0]
            return {
                "호스트명": fp["hostname"],
                "매칭PC": name,
                "매칭MAC": matching_mac,
                "MAC일치": True,
                "GUID일치": False,
                "판정": "⚠️ 부분 인증: MAC 일치, GUID 미등록",
                "판정코드": "PARTIAL_AUTH",
                "상세": "GUID 미등록. --register로 GUID 등록 권장",
            }
    return {
        "호스트명": fp["hostname"],
        "MAC일치": False,
        "GUID일치": False,
        "판정": "❌ 미등록 PC",
        "판정코드": "NOT_REGISTERED",
    }


# ── is_allowed (시작 가드용) ───────────────────────────

def is_allowed(registry_path: Optional[Path] = None) -> tuple[bool, str]:
    """
    허용된 PC인지 확인. 메인 가드 진입점.

    Returns:
        (allowed, reason) — allowed=True면 SQM_inventory 정상 기동.
        FULL_AUTH, DISABLED → True
        PARTIAL_AUTH, NOT_REGISTERED, REGISTRY_* → False
    """
    if registry_path is None:
        registry_path = get_registry_path()
    fp = collect_fingerprint()
    judgment = _judge(fp, registry_path)
    code = judgment.get("판정코드", "")
    reason = judgment.get("판정", "")
    if code in ("FULL_AUTH", "DISABLED"):
        return True, reason
    return False, reason


# ── register (현재 PC GUID 등록) ────────────────────────

def register(registry_path: Optional[Path] = None) -> dict:
    """
    현재 PC의 GUID를 registry의 hostname 매칭 항목에 등록.

    Args:
        registry_path: 미설정 시 PC_GUARD_REGISTRY 환경변수 사용

    Returns:
        {"ok": bool, "registered"?: str, "guid"?: str,
         "backup"?: str, "error"?: str}
    """
    if registry_path is None:
        registry_path = get_registry_path()
    if registry_path is None:
        return {"ok": False, "error": "PC_GUARD_REGISTRY 미설정"}
    if not registry_path.exists():
        return {"ok": False, "error": f"registry 없음: {registry_path}"}

    fp = collect_fingerprint()
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": f"registry 파싱 실패: {e}"}

    allowed = data.get("allowed_pcs", [])
    for pc in allowed:
        if pc.get("name") == fp["hostname"]:
            old_guid = pc.get("machine_guid", "")
            pc["machine_guid"] = fp["machine_guid"]
            try:
                # 백업 (.json.bak.YYYYMMDD_HHMMSS)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                bak = registry_path.with_suffix(f".json.bak.{ts}")
                shutil.copy2(registry_path, bak)
                # 저장
                registry_path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                return {
                    "ok": True,
                    "registered": fp["hostname"],
                    "guid": fp["machine_guid"],
                    "old_guid": old_guid,
                    "backup": str(bak),
                }
            except Exception as e:
                return {"ok": False, "error": f"저장 실패: {e}"}

    return {
        "ok": False,
        "error": f"호스트명 '{fp['hostname']}' 미등록 (registry에 PC 이름 먼저 추가 필요)",
    }
