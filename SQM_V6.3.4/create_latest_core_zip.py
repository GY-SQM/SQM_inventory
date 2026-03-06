#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LATEST_CORE.zip 생성: 지정 5개 파일만 루트에 담기. (review_center_bridge.py 없으면 4개만)"""
import os
import zipfile

base = os.path.dirname(os.path.abspath(__file__))

# (프로젝트 내 경로, ZIP 내 이름)
files = [
    ("parsers/allocation_parser.py", "allocation_parser.py"),
    ("gui_app_modular/dialogs/allocation_dialog.py", "allocation_dialog.py"),
    ("engine_modules/inventory_modular/outbound_mixin.py", "outbound_mixin.py"),
    ("parsers/picking_list_parser.py", "picking_list_parser.py"),
    ("review_center_bridge.py", "review_center_bridge.py"),  # 없을 수 있음
]

zip_path = os.path.join(base, "LATEST_CORE.zip")
added = 0
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for rel_path, arc_name in files:
        abs_path = os.path.join(base, rel_path)
        if os.path.isfile(abs_path):
            zf.write(abs_path, arc_name)
            added += 1

print(f"Created: {zip_path}")
print(f"Files: {added}/5 (review_center_bridge.py not in project)")
