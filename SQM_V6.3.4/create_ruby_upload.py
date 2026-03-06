#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
루비 권장안: 풀버전 작성용 업로드 파일 압축
- 01_FULL: 기존 FULL ZIP 1개
- 02_C1_핵심: 3파일
- 03_C2_핵심: Picking List + Review Center + outbound 매칭
- 04_C3_핵심: final_qc/inbox(있으면) + outbound_mixin
- 05_Dashboard_핵심: dashboard UI + 상태 집계/조회(있으면)
생성: 루비_권장_업로드.zip
"""
import os
import shutil
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(BASE)

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def copy(src, dst_dir):
    if os.path.isfile(src):
        ensure_dir(os.path.dirname(dst_dir))
        shutil.copy2(src, dst_dir)
        return True
    return False

# 출력 폴더
OUT = os.path.join(BASE, "루비_업로드_폴더")
if os.path.exists(OUT):
    shutil.rmtree(OUT)
ensure_dir(OUT)

# 1) 기존 FULL ZIP 1개
full_dir = os.path.join(OUT, "01_FULL")
ensure_dir(full_dir)
for cand in ["SQM_V6.3.4 (4).Zip", "SQM_V6.3.4_debug_files.zip", "FULL_BUILD_UPLOAD.zip"]:
    src = os.path.join(BASE, cand)
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(full_dir, "SQM_V6.3.4 (4).Zip"))
        break
if not os.listdir(full_dir):
    with open(os.path.join(full_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write("SQM_V6.3.4 (4).Zip 을 여기에 넣어주세요.\n")

# 2) C1 핵심 3파일
c1 = os.path.join(OUT, "02_C1_핵심")
copy(os.path.join(BASE, "parsers", "allocation_parser.py"), os.path.join(c1, "parsers", "allocation_parser.py"))
copy(os.path.join(BASE, "gui_app_modular", "dialogs", "allocation_dialog.py"), os.path.join(c1, "gui_app_modular", "dialogs", "allocation_dialog.py"))
copy(os.path.join(BASE, "engine_modules", "inventory_modular", "outbound_mixin.py"), os.path.join(c1, "engine_modules", "inventory_modular", "outbound_mixin.py"))

# 3) C2 핵심
c2 = os.path.join(OUT, "03_C2_핵심")
copy(os.path.join(BASE, "parsers", "picking_list_parser.py"), os.path.join(c2, "parsers", "picking_list_parser.py"))
copy(os.path.join(BASE, "parsers", "cross_check_engine.py"), os.path.join(c2, "parsers", "cross_check_engine.py"))
copy(os.path.join(BASE, "engine_modules", "inventory_modular", "outbound_mixin.py"), os.path.join(c2, "engine_modules", "inventory_modular", "outbound_mixin.py"))
if copy(os.path.join(PARENT, "gui_app_modular", "dialogs", "review_center.py"), os.path.join(c2, "gui_app_modular", "dialogs", "review_center.py")):
    for rel in ["gui_app_modular/utils/ocr_utils.py", "gui_app_modular/utils/review_rules.py"]:
        copy(os.path.join(PARENT, rel), os.path.join(c2, rel))

# 4) C3 핵심
c3 = os.path.join(OUT, "04_C3_핵심")
copy(os.path.join(BASE, "engine_modules", "inventory_modular", "outbound_mixin.py"), os.path.join(c3, "engine_modules", "inventory_modular", "outbound_mixin.py"))
with open(os.path.join(c3, "README.txt"), "w", encoding="utf-8") as f:
    f.write("final_qc 관련 UI, inbox 관련 파일은 프로젝트에 없어 outbound_mixin.py 만 포함했습니다.\n")

# 5) Dashboard 핵심
dash = os.path.join(OUT, "05_Dashboard_핵심")
copy(os.path.join(BASE, "gui_app_modular", "tabs", "dashboard_tab.py"), os.path.join(dash, "gui_app_modular", "tabs", "dashboard_tab.py"))
copy(os.path.join(BASE, "gui_app_modular", "tabs", "dashboard_data_mixin.py"), os.path.join(dash, "gui_app_modular", "tabs", "dashboard_data_mixin.py"))
with open(os.path.join(dash, "README.txt"), "w", encoding="utf-8") as f:
    f.write("outbound_dashboard.py, outbound_status_service.py, state_aggregate.py 는 없습니다. dashboard_tab, dashboard_data_mixin 포함.\n")

# ZIP 생성
zip_path = os.path.join(BASE, "루비_권장_업로드.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(OUT):
        for f in files:
            abs_path = os.path.join(root, f)
            arc = os.path.relpath(abs_path, os.path.dirname(OUT))
            zf.write(abs_path, arc)
shutil.rmtree(OUT)
print("Created:", zip_path)
