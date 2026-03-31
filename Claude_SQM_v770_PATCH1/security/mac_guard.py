"""
SQM 재고관리 시스템 - PC 잠금 (MAC + MachineGuid 2중 인증)
==========================================================

v5.6.0: MAC 주소 + Windows MachineGuid 2중 검증
- 둘 다 일치 → 실행
- 하나만 일치 → 경고 후 실행
- 둘 다 불일치 → 차단
"""

import json
import logging
import platform
import re
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SECURITY_CONFIG_PATH = Path(__file__).parent / 'allowed_pcs.json'


def get_current_mac() -> str:
    """현재 PC의 MAC 주소 (XX:XX:XX:XX:XX:XX)"""
    mac_int = uuid.getnode()
    return ':'.join(f'{(mac_int >> (8 * i)) & 0xFF:02X}' for i in reversed(range(6)))


def get_machine_guid() -> str:
    """Windows MachineGuid 조회"""
    if platform.system() != 'Windows':
        return ''
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        )
        guid, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        return str(guid).strip()
    except (OSError, WindowsError, ImportError):
        return ''


def _normalize_mac(mac: str) -> str:
    """MAC 주소 정규화 (XX:XX:XX:XX:XX:XX)"""
    clean = mac.upper().replace('-', '').replace(':', '').replace('.', '').strip()
    if len(clean) != 12:
        return ''
    return ':'.join(clean[i:i+2] for i in range(0, 12, 2))


def load_allowed_pcs() -> List[Dict]:
    """허용 PC 목록 로드"""
    if not SECURITY_CONFIG_PATH.exists():
        return []
    try:
        with open(SECURITY_CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('allowed_pcs', [])
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"[PC Guard] 설정 로드 실패: {e}")
        return []


def verify_pc(show_gui_error: bool = True) -> bool:
    """
    현재 PC 검증 (2중 인증)
    
    Returns:
        True: 실행 허용
        False: 차단
    """
    allowed_pcs = load_allowed_pcs()

    # 허용 목록 비어있으면 잠금 비활성화
    if not allowed_pcs:
        logger.info("[PC Guard] 허용 목록 없음 → 잠금 비활성화")
        return True

    current_mac = _normalize_mac(get_current_mac())
    current_guid = get_machine_guid().lower()

    logger.info(f"[PC Guard] 현재 MAC: {current_mac}")
    logger.info(f"[PC Guard] 현재 GUID: {current_guid}")

    for pc in allowed_pcs:
        allowed_macs = [_normalize_mac(m) for m in pc.get('macs', [])]
        allowed_guid = pc.get('machine_guid', '').lower().strip()
        pc_name = pc.get('name', '알 수 없음')

        mac_match = current_mac in allowed_macs if allowed_macs else False
        guid_match = (current_guid == allowed_guid) if allowed_guid else False

        # 둘 다 일치 → 실행
        if mac_match and guid_match:
            logger.info(f"[PC Guard] ✅ 인증 완료: {pc_name} (MAC+GUID)")
            return True

        # 하나만 일치 → 경고 후 실행
        if mac_match or guid_match:
            matched = "MAC" if mac_match else "GUID"
            missing = "GUID" if mac_match else "MAC"
            logger.warning(f"[PC Guard] ⚠️ 부분 인증: {pc_name} ({matched} 일치, {missing} 불일치)")

            if show_gui_error:
                try:
                    import tkinter as tk

                    from gui_app_modular.utils.custom_messagebox import CustomMessageBox
                    root = tk.Tk()
                    root.withdraw()
                    CustomMessageBox.showwarning(
                        root,
                        "PC 인증 경고",
                        f"PC 정보가 일부 변경되었습니다.\n\n"
                        f"일치: {matched}\n불일치: {missing}\n\n"
                        f"프로그램은 실행되지만 관리자에게 업데이트를 요청하세요."
                    )
                    root.destroy()
                except Exception as e:
                    logger.debug(f"Suppressed: {e}")
            return True

    # 둘 다 불일치 → 차단
    logger.warning(f"[PC Guard] ❌ 차단: MAC={current_mac}, GUID={current_guid}")

    if show_gui_error:
        try:
            import tkinter as tk

            from gui_app_modular.utils.custom_messagebox import CustomMessageBox
            root = tk.Tk()
            root.withdraw()
            CustomMessageBox.showerror(
                root,
                "접근 차단",
                f"이 PC에서는 SQM 재고관리 시스템을 실행할 수 없습니다.\n\n"
                f"MAC: {current_mac}\n"
                f"관리자에게 문의하세요."
            )
            root.destroy()
        except Exception as e:
            logger.debug(f"Suppressed: {e}")

    return False


def save_allowed_pcs(pcs: List[Dict]) -> bool:
    """허용 PC 목록 저장"""
    try:
        data = {
            'allowed_pcs': pcs,
            '_comment': 'MAC: ipconfig /all → 물리적 주소, GUID: 레지스트리 MachineGuid'
        }
        with open(SECURITY_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except (OSError, TypeError) as e:
        logger.error(f"[PC Guard] 저장 실패: {e}")
        return False


def register_current_pc(replace: bool = False) -> Tuple[bool, str]:
    """
    현재 PC를 허용 목록에 등록 (원본 PC에서 1회 실행용).
    실행파일을 이 PC 외에서는 작동하지 않게 하려면, 이 PC에서 한 번 실행한 뒤
    생성된 security/allowed_pcs.json 을 배포 폴더에 포함하면 됩니다.

    Args:
        replace: True면 기존 목록을 현재 PC 1대로 교체, False면 현재 PC를 목록에 병합 추가

    Returns:
        (성공 여부, 메시지)
    """
    current_mac = _normalize_mac(get_current_mac())
    current_guid = get_machine_guid().strip()
    pc_name = (platform.node() or '').strip() or '원본 PC'

    if not current_mac and not current_guid:
        return False, "MAC/GUID를 읽을 수 없어 등록할 수 없습니다."

    entry = {
        'name': pc_name,
        'macs': [current_mac] if current_mac else [],
        'machine_guid': current_guid,
    }
    if replace:
        pcs = [entry]
    else:
        # 다중 PC 허용: 기존 목록에서 동일 GUID/이름 항목은 갱신하고 나머지는 유지
        existing = load_allowed_pcs()
        guid_lower = current_guid.lower()
        existing = [
            p for p in existing
            if (p.get('machine_guid') or '').lower() != guid_lower and (p.get('name') or '') != pc_name
        ]
        existing.append(entry)
        pcs = existing
    if save_allowed_pcs(pcs):
        return True, f"등록 완료: {pc_name} (현재 허용 PC 수: {len(pcs)}). security/allowed_pcs.json 생성됨."
    return False, "저장 실패"


# MAC 패턴 (물리적 주소): XX-XX-XX-XX-XX-XX 또는 XX:XX:...
_MAC_PATTERN = re.compile(
    r'\b([0-9A-Fa-f]{2})[-:]([0-9A-Fa-f]{2})[-:]([0-9A-Fa-f]{2})[-:]([0-9A-Fa-f]{2})[-:]([0-9A-Fa-f]{2})[-:]([0-9A-Fa-f]{2})\b'
)


def _extract_macs_from_ipconfig(text: str) -> List[str]:
    """raw.ipconfig 텍스트에서 '물리적 주소' 줄의 MAC만 추출. DUID 등 오탐 방지."""
    seen = set()
    result = []
    for line in text.splitlines():
        if '물리적 주소' not in line and 'Physical Address' not in line:
            continue
        for m in _MAC_PATTERN.finditer(line):
            raw = f"{m.group(1)}:{m.group(2)}:{m.group(3)}:{m.group(4)}:{m.group(5)}:{m.group(6)}"
            normalized = _normalize_mac(raw)
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
    return result


def parse_pc_info_report(report_path: Path) -> Optional[Dict]:
    """
    PC_INFO_REPORT JSON 파일을 파싱하여 allowed_pcs 항목 1개 생성.

    Returns:
        {'name': hostname, 'macs': [...], 'machine_guid': ...} 또는 실패 시 None
    """
    if not report_path.exists():
        logger.warning(f"[PC Guard] 보고서 파일 없음: {report_path}")
        return None
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"[PC Guard] 보고서 로드 실패: {e}")
        return None

    header = data.get('header') or {}
    identifiers = data.get('identifiers') or {}
    raw = data.get('raw') or {}

    name = (header.get('hostname') or '').strip() or '알 수 없음'
    machine_guid = (identifiers.get('MachineGuid') or '').strip()
    ipconfig_text = raw.get('ipconfig') or raw.get('ipconfig_all') or ''

    macs = _extract_macs_from_ipconfig(ipconfig_text)
    if not macs and raw.get('route'):
        macs = _extract_macs_from_ipconfig(raw.get('route', ''))

    if not machine_guid:
        logger.warning("[PC Guard] 보고서에 MachineGuid 없음")
        return None

    return {
        'name': name,
        'macs': macs,
        'machine_guid': machine_guid,
    }


def load_report_into_allowed_pcs(report_path: Path, merge: bool = True) -> Tuple[bool, str]:
    """
    PC_INFO_REPORT JSON을 로드하여 allowed_pcs.json에 반영.

    Args:
        report_path: PC_INFO_REPORT_*.json 경로
        merge: True면 동일 GUID/이름 항목 갱신 후 유지, False면 해당 PC만 허용 목록으로 대체

    Returns:
        (성공 여부, 메시지)
    """
    report_path = Path(report_path)
    entry = parse_pc_info_report(report_path)
    if not entry:
        return False, "보고서 파싱 실패 또는 파일 없음"

    existing = load_allowed_pcs()
    guid_lower = entry['machine_guid'].lower()

    if merge:
        # 동일 GUID 또는 동일 name 항목 제거 후 새 항목 추가
        existing = [p for p in existing if (p.get('machine_guid') or '').lower() != guid_lower and (p.get('name') or '') != entry['name']]
        existing.append(entry)
        new_pcs = existing
    else:
        new_pcs = [entry]

    if save_allowed_pcs(new_pcs):
        mac_count = len(entry.get('macs', []))
        return True, f"등록 완료: {entry['name']} (GUID 1개, MAC {mac_count}개)"
    return False, "저장 실패"


if __name__ == '__main__':
    if '--register' in sys.argv:
        ok, msg = register_current_pc(replace=True)
        logger.info(f"[PC Guard] {msg}")
        sys.exit(0 if ok else 1)
    if len(sys.argv) >= 2 and not sys.argv[1].startswith('-'):
        # 인자로 JSON 경로가 주어지면 보고서 로드 → 허용 목록 반영
        path = Path(sys.argv[1])
        merge = '--replace' not in sys.argv
        ok, msg = load_report_into_allowed_pcs(path, merge=merge)
        logger.info(f"[PC Guard] {msg}")
        sys.exit(0 if ok else 1)
    mac = get_current_mac()
    guid = get_machine_guid()
    logger.info(f"MAC:  {mac}")
    logger.info(f"GUID: {guid}")
    logger.info(f"허용: {'✅' if verify_pc(False) else '❌'}")
