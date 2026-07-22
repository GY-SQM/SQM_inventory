# -*- coding: utf-8 -*-
"""
tests/test_pc_guard.py
======================
SQM v9.0.7 — PC Guard 모듈 회귀 테스트

검증:
    - collect_fingerprint: 필수 키 4개 + 형식
    - get_registry_path: env unset/set
    - _judge: DISABLED / REGISTRY_MISSING / FULL_AUTH / PARTIAL_AUTH /
              NOT_REGISTERED / REGISTRY_PARSE_ERROR
    - register: hostname 매칭 / 매칭 없음 / registry 없음
    - is_allowed: True/False 분기
    - inspect: 3 섹션 (관리정보/하드웨어식별/보안판정)
    - CLI: inspect_pc.py 실행 가능
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import pc_guard  # noqa: E402


# ── collect_fingerprint ──────────────────────────────────

def test_pc01_fingerprint_has_required_keys():
    """collect_fingerprint 결과에 필수 키 4개."""
    fp = pc_guard.collect_fingerprint()
    for key in ("hostname", "user", "machine_guid", "macs"):
        assert key in fp, f"필수 키 누락: {key}"


def test_pc02_macs_is_list():
    """macs는 list[str]."""
    fp = pc_guard.collect_fingerprint()
    assert isinstance(fp["macs"], list)
    for m in fp["macs"]:
        assert isinstance(m, str)


def test_pc03_macs_uppercase_colon():
    """macs는 대문자 + ':' 구분자."""
    fp = pc_guard.collect_fingerprint()
    for m in fp["macs"]:
        assert m == m.upper(), f"대문자 아님: {m}"
        assert ":" in m, f"':' 구분자 없음: {m}"


# ── get_registry_path ────────────────────────────────────

def test_pc10_registry_env_unset(monkeypatch):
    """환경변수 미설정 시 None."""
    monkeypatch.delenv("PC_GUARD_REGISTRY", raising=False)
    assert pc_guard.get_registry_path() is None


def test_pc11_registry_env_set(monkeypatch):
    """환경변수 설정 시 Path 반환."""
    monkeypatch.setenv("PC_GUARD_REGISTRY", "D:/test/reg.json")
    p = pc_guard.get_registry_path()
    assert p is not None
    assert str(p).replace("\\", "/") == "D:/test/reg.json"


# ── _judge 판정 ──────────────────────────────────────────

def test_pc20_judge_disabled():
    """registry None → DISABLED."""
    fp = {"hostname": "x", "machine_guid": "g", "macs": []}
    result = pc_guard._judge(fp, None)
    assert result["판정코드"] == "DISABLED"
    assert "비활성" in result["판정"]


def test_pc20b_judge_dict_registry_full_auth():
    """dict registry (config_local fallback) → FULL_AUTH."""
    fp = {
        "hostname": "test-pc",
        "machine_guid": "guid-1",
        "macs": ["AA:BB:CC:DD:EE:FF"],
    }
    data = {"allowed_pcs": [{
        "name": "test-pc",
        "macs": ["AA:BB:CC:DD:EE:FF"],
        "machine_guid": "guid-1",
    }]}
    result = pc_guard._judge(fp, data)
    assert result["판정코드"] == "FULL_AUTH"


def test_pc20c_judge_dict_registry_partial_auth():
    """dict registry, guid 미등록 → PARTIAL_AUTH."""
    fp = {
        "hostname": "test-pc",
        "machine_guid": "guid-1",
        "macs": ["AA:BB:CC:DD:EE:FF"],
    }
    data = {"allowed_pcs": [{
        "name": "test-pc",
        "macs": ["AA:BB:CC:DD:EE:FF"],
        "machine_guid": "",  # 미등록
    }]}
    result = pc_guard._judge(fp, data)
    assert result["판정코드"] == "PARTIAL_AUTH"


def test_pc20d_judge_unknown_type():
    """registry가 Path/dict/None이 아니면 REGISTRY_PARSE_ERROR."""
    fp = {"hostname": "x", "machine_guid": "g", "macs": []}
    result = pc_guard._judge(fp, 42)  # int (invalid type)
    assert result["판정코드"] == "REGISTRY_PARSE_ERROR"


def test_pc21_judge_registry_missing(tmp_path):
    """registry 파일 없음 → REGISTRY_MISSING."""
    fp = {"hostname": "x", "machine_guid": "g", "macs": []}
    result = pc_guard._judge(fp, tmp_path / "missing.json")
    assert result["판정코드"] == "REGISTRY_MISSING"


def test_pc22_judge_full_auth(tmp_path):
    """hostname + mac + guid 모두 일치 → FULL_AUTH."""
    registry = tmp_path / "reg.json"
    registry.write_text(json.dumps({
        "allowed_pcs": [{
            "name": "test-pc",
            "macs": ["AA:BB:CC:DD:EE:FF"],
            "machine_guid": "guid-1",
        }]
    }), encoding="utf-8")
    fp = {
        "hostname": "test-pc",
        "machine_guid": "guid-1",
        "macs": ["AA:BB:CC:DD:EE:FF"],
    }
    result = pc_guard._judge(fp, registry)
    assert result["판정코드"] == "FULL_AUTH"
    assert result["MAC일치"] is True
    assert result["GUID일치"] is True
    assert result["매칭PC"] == "test-pc"


def test_pc23_judge_partial_auth_guid_unregistered(tmp_path):
    """hostname + mac 일치, guid 미등록 → PARTIAL_AUTH."""
    registry = tmp_path / "reg.json"
    registry.write_text(json.dumps({
        "allowed_pcs": [{
            "name": "test-pc",
            "macs": ["AA:BB:CC:DD:EE:FF"],
            "machine_guid": "",  # 미등록
        }]
    }), encoding="utf-8")
    fp = {
        "hostname": "test-pc",
        "machine_guid": "guid-1",
        "macs": ["AA:BB:CC:DD:EE:FF"],
    }
    result = pc_guard._judge(fp, registry)
    assert result["판정코드"] == "PARTIAL_AUTH"
    assert result["MAC일치"] is True
    assert result["GUID일치"] is False
    assert "GUID 미등록" in result.get("상세", "")


def test_pc24_judge_not_registered(tmp_path):
    """아예 등록 안 된 hostname → NOT_REGISTERED."""
    registry = tmp_path / "reg.json"
    registry.write_text(json.dumps({
        "allowed_pcs": [{
            "name": "other-pc",
            "macs": ["11:22:33:44:55:66"],
            "machine_guid": "g1",
        }]
    }), encoding="utf-8")
    fp = {
        "hostname": "test-pc",
        "machine_guid": "guid-1",
        "macs": ["AA:BB:CC:DD:EE:FF"],
    }
    result = pc_guard._judge(fp, registry)
    assert result["판정코드"] == "NOT_REGISTERED"


def test_pc25_judge_registry_parse_error(tmp_path):
    """registry가 깨진 JSON → REGISTRY_PARSE_ERROR."""
    registry = tmp_path / "reg.json"
    registry.write_text("{ invalid json", encoding="utf-8")
    fp = {"hostname": "x", "machine_guid": "g", "macs": []}
    result = pc_guard._judge(fp, registry)
    assert result["판정코드"] == "REGISTRY_PARSE_ERROR"


def test_pc26_judge_case_insensitive_mac(tmp_path):
    """MAC 비교는 대소문자 무시 (소문자 등록도 OK)."""
    registry = tmp_path / "reg.json"
    registry.write_text(json.dumps({
        "allowed_pcs": [{
            "name": "test-pc",
            "macs": ["aa:bb:cc:dd:ee:ff"],  # 소문자 등록
            "machine_guid": "guid-1",
        }]
    }), encoding="utf-8")
    fp = {
        "hostname": "test-pc",
        "machine_guid": "guid-1",
        "macs": ["AA:BB:CC:DD:EE:FF"],  # 대문자 fingerprint
    }
    result = pc_guard._judge(fp, registry)
    assert result["판정코드"] == "FULL_AUTH"


# ── register ────────────────────────────────────────────

def test_pc30_register_success(tmp_path):
    """hostname 매칭 → machine_guid 채워짐 + 백업 생성."""
    registry = tmp_path / "reg.json"
    registry.write_text(json.dumps({
        "allowed_pcs": [{
            "name": "test-pc",
            "macs": ["AA:BB:CC:DD:EE:FF"],
            "machine_guid": "",
        }]
    }), encoding="utf-8")

    with patch.object(pc_guard, "collect_fingerprint", return_value={
        "hostname": "test-pc",
        "machine_guid": "new-guid",
        "macs": ["AA:BB:CC:DD:EE:FF"],
        "user": "tester",
    }):
        result = pc_guard.register(registry)

    assert result["ok"] is True
    assert result["registered"] == "test-pc"
    assert result["guid"] == "new-guid"
    assert "backup" in result

    # 파일에 저장됐는지 확인
    data = json.loads(registry.read_text(encoding="utf-8"))
    pc = data["allowed_pcs"][0]
    assert pc["machine_guid"] == "new-guid"
    # 백업 파일 존재
    assert Path(result["backup"]).exists()


def test_pc31_register_hostname_not_found(tmp_path):
    """hostname 매칭 없음 → ok=False."""
    registry = tmp_path / "reg.json"
    registry.write_text(json.dumps({
        "allowed_pcs": [{
            "name": "other-pc",
            "macs": ["11:22:33:44:55:66"],
            "machine_guid": "",
        }]
    }), encoding="utf-8")

    with patch.object(pc_guard, "collect_fingerprint", return_value={
        "hostname": "test-pc",
        "machine_guid": "new-guid",
        "macs": ["AA:BB:CC:DD:EE:FF"],
        "user": "tester",
    }):
        result = pc_guard.register(registry)

    assert result["ok"] is False
    assert "test-pc" in result["error"]


def test_pc32_register_no_registry_env(monkeypatch):
    """registry 경로 없음 → ok=False (env unset)."""
    monkeypatch.delenv("PC_GUARD_REGISTRY", raising=False)
    result = pc_guard.register(None)
    assert result["ok"] is False
    assert "미설정" in result["error"]


def test_pc33_register_registry_missing(tmp_path, monkeypatch):
    """registry 파일이 실제로 없을 때 → ok=False."""
    monkeypatch.setenv("PC_GUARD_REGISTRY", str(tmp_path / "nope.json"))
    result = pc_guard.register(None)
    assert result["ok"] is False
    assert "registry 없음" in result["error"]


# ── is_allowed ──────────────────────────────────────────

def test_pc40_is_allowed_disabled(monkeypatch):
    """registry None → True (비활성). env + config_local 둘 다 없음."""
    monkeypatch.delenv("PC_GUARD_REGISTRY", raising=False)
    with patch.object(pc_guard, "_load_local_default", return_value=None):
        allowed, reason = pc_guard.is_allowed(None)
    assert allowed is True
    assert "비활성" in reason


def test_pc41_is_allowed_full_auth(tmp_path):
    """FULL_AUTH → True."""
    registry = tmp_path / "reg.json"
    registry.write_text(json.dumps({
        "allowed_pcs": [{
            "name": "test-pc",
            "macs": ["AA:BB:CC:DD:EE:FF"],
            "machine_guid": "guid-1",
        }]
    }), encoding="utf-8")

    with patch.object(pc_guard, "collect_fingerprint", return_value={
        "hostname": "test-pc",
        "machine_guid": "guid-1",
        "macs": ["AA:BB:CC:DD:EE:FF"],
        "user": "tester",
    }):
        allowed, reason = pc_guard.is_allowed(registry)

    assert allowed is True
    assert "완전 인증" in reason


def test_pc42_is_allowed_partial(tmp_path):
    """PARTIAL_AUTH → False."""
    registry = tmp_path / "reg.json"
    registry.write_text(json.dumps({
        "allowed_pcs": [{
            "name": "test-pc",
            "macs": ["AA:BB:CC:DD:EE:FF"],
            "machine_guid": "",
        }]
    }), encoding="utf-8")

    with patch.object(pc_guard, "collect_fingerprint", return_value={
        "hostname": "test-pc",
        "machine_guid": "guid-1",
        "macs": ["AA:BB:CC:DD:EE:FF"],
        "user": "tester",
    }):
        allowed, reason = pc_guard.is_allowed(registry)

    assert allowed is False
    assert "부분 인증" in reason


def test_pc43_is_allowed_not_registered(tmp_path):
    """NOT_REGISTERED → False."""
    registry = tmp_path / "reg.json"
    registry.write_text(json.dumps({
        "allowed_pcs": [{
            "name": "other-pc",
            "macs": ["11:22:33:44:55:66"],
            "machine_guid": "g1",
        }]
    }), encoding="utf-8")

    with patch.object(pc_guard, "collect_fingerprint", return_value={
        "hostname": "test-pc",
        "machine_guid": "guid-1",
        "macs": ["AA:BB:CC:DD:EE:FF"],
        "user": "tester",
    }):
        allowed, reason = pc_guard.is_allowed(registry)

    assert allowed is False
    assert "미등록" in reason


# ── inspect (전체 리포트) ───────────────────────────────

def test_pc50_inspect_has_3_sections():
    """inspect 결과에 관리정보/하드웨어식별/보안판정 섹션."""
    report = pc_guard.inspect(None)
    assert "관리정보" in report
    assert "하드웨어식별" in report
    assert "보안판정" in report


def test_pc51_inspect_disabled_when_no_registry(monkeypatch):
    """registry 미설정 → DISABLED."""
    monkeypatch.delenv("PC_GUARD_REGISTRY", raising=False)
    report = pc_guard.inspect(None)
    assert report["보안판정"]["판정코드"] == "DISABLED"


def test_pc52_inspect_full_auth(tmp_path):
    """FULL_AUTH 시나리오 inspect."""
    registry = tmp_path / "reg.json"
    registry.write_text(json.dumps({
        "allowed_pcs": [{
            "name": "test-pc",
            "macs": ["AA:BB:CC:DD:EE:FF"],
            "machine_guid": "guid-1",
        }]
    }), encoding="utf-8")

    with patch.object(pc_guard, "collect_fingerprint", return_value={
        "hostname": "test-pc",
        "machine_guid": "guid-1",
        "macs": ["AA:BB:CC:DD:EE:FF"],
        "user": "tester",
    }):
        report = pc_guard.inspect(registry)

    assert report["관리정보"]["호스트명"] == "test-pc"
    assert report["관리정보"]["사용자"] == "tester"
    assert report["하드웨어식별"]["MachineGuid"] == "guid-1"
    assert "AA:BB:CC:DD:EE:FF" in report["하드웨어식별"]["전체MAC"]
    assert report["보안판정"]["판정코드"] == "FULL_AUTH"


# ── CLI 실행 가능 (CI 통합) ───────────────────────────

def test_pc60_cli_runs_no_registry(monkeypatch):
    """CLI --registry 미설정, env 없음 → JSON 정상 출력 + exit 0."""
    monkeypatch.delenv("PC_GUARD_REGISTRY", raising=False)
    env = {k: v for k, v in os.environ.items() if k != "PC_GUARD_REGISTRY"}
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "inspect_pc.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        env=env,
    )
    # 실제 fingerprint 기준이라 FULL_AUTH/PARTIAL/NOT_REGISTERED 가능
    # → 단지 CLI가 실행되고 JSON 출력 + 한국어 키 정상 parse되는지만 확인
    assert result.returncode in (0, 1), f"unexpected exit {result.returncode}\nstderr: {result.stderr}"
    parsed = json.loads(result.stdout.strip())
    assert "보안판정" in parsed
    assert "판정코드" in parsed["보안판정"]


def test_pc61_cli_with_explicit_registry_missing(monkeypatch, tmp_path):
    """CLI with --registry (없는 파일) → REGISTRY_MISSING, exit 1."""
    monkeypatch.delenv("PC_GUARD_REGISTRY", raising=False)
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "inspect_pc.py"),
         "--registry", str(tmp_path / "missing.json")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    assert result.returncode == 1
    parsed = json.loads(result.stdout.strip())
    assert parsed["보안판정"]["판정코드"] == "REGISTRY_MISSING"


def test_pc62_cli_register_no_match(tmp_path, monkeypatch):
    """CLI --register with hostname mismatch → ok=false, exit 1."""
    registry = tmp_path / "reg.json"
    registry.write_text(json.dumps({
        "allowed_pcs": [{
            "name": "other-pc",
            "macs": ["11:22:33:44:55:66"],
            "machine_guid": "",
        }]
    }), encoding="utf-8")
    monkeypatch.delenv("PC_GUARD_REGISTRY", raising=False)

    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "inspect_pc.py"),
         "--register", "--registry", str(registry)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    assert result.returncode == 1
    parsed = json.loads(result.stdout.strip())
    assert parsed["ok"] is False
    assert "미등록" in parsed["error"]
