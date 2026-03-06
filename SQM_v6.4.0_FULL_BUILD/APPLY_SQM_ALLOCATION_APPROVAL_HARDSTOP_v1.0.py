
# -*- coding: utf-8 -*-
"""
APPLY_SQM_ALLOCATION_APPROVAL_HARDSTOP_v1.0.py

루비안 패치:
Allocation 업로드 단계에서는 절대 RESERVED를 만들지 않고
무조건 STAGED + PENDING_APPROVAL 로 적재.

승인 시점에서만 RESERVED 반영.
"""

import re
from pathlib import Path
from datetime import datetime

def backup(path: Path):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(path.suffix + ".bak_" + ts)
    backup_path.write_bytes(path.read_bytes())
    return backup_path

def patch_outbound_mixin(path: Path):
    txt = path.read_text(encoding="utf-8", errors="ignore")

    if "ALLOCATION_FORCE_APPROVAL_ALL" not in txt:
        txt = "ALLOCATION_FORCE_APPROVAL_ALL = True\n\n" + txt

    txt = re.sub(
        r"need_approval\s*=\s*self\._allocation_requires_approval\(",
        "need_approval = True or self._allocation_requires_approval(",
        txt
    )

    backup(path)
    path.write_text(txt, encoding="utf-8")

def patch_approval_dialog(path: Path):
    txt = path.read_text(encoding="utf-8", errors="ignore")

    if "apply_approved_allocation_reservations" not in txt:
        insert = '''
try:
    if hasattr(self.engine, "apply_approved_allocation_reservations"):
        self.engine.apply_approved_allocation_reservations(plan_ids=ids)
except Exception as e:
    print("Apply approved allocation failed:", e)
'''
        txt += insert

    backup(path)
    path.write_text(txt, encoding="utf-8")

def main():
    root = Path.cwd()

    outbound = root / "engine_modules" / "inventory_modular" / "outbound_mixin.py"
    approval = root / "gui_app_modular" / "dialogs" / "allocation_approval_dialog.py"

    if outbound.exists():
        patch_outbound_mixin(outbound)
        print("patched:", outbound)

    if approval.exists():
        patch_approval_dialog(approval)
        print("patched:", approval)

    print("완료: Allocation 승인 하드스톱 적용")

if __name__ == "__main__":
    main()
