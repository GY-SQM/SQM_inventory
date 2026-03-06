#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FULL_BUILD_UPLOAD 폴더 구조 생성 후 압축.
실행: python create_full_build_upload.py
생성: FULL_BUILD_UPLOAD.zip
"""
import os
import shutil
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "FULL_BUILD_UPLOAD")

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def copy_file(src_rel, dest_path):
    src = os.path.join(BASE, src_rel)
    if os.path.isfile(src):
        ensure_dir(os.path.dirname(dest_path))
        shutil.copy2(src, dest_path)
        return True
    return False

def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)

    # 00_base
    base_dir = os.path.join(OUT, "00_base")
    ensure_dir(base_dir)
    for name in ["SQM_V6.3.4 (4).Zip", "SQM_V6.3.4_debug_files.zip"]:
        src = os.path.join(BASE, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(base_dir, "SQM_V6.3.4 (4).Zip" if "debug" in name else name))
            break
    if not os.listdir(base_dir):
        with open(os.path.join(base_dir, "README.txt"), "w", encoding="utf-8") as f:
            f.write("SQM_V6.3.4 (4).Zip 을 여기에 넣어주세요.\n")

    # 01_core
    for name in ["run.py", "requirements.txt", "settings.ini", "version.py"]:
        copy_file(name, os.path.join(OUT, "01_core", name))

    # 02_C1
    copy_file("parsers/allocation_parser.py", os.path.join(OUT, "02_C1", "parsers", "allocation_parser.py"))
    copy_file("gui_app_modular/dialogs/allocation_dialog.py", os.path.join(OUT, "02_C1", "gui_app_modular", "dialogs", "allocation_dialog.py"))
    copy_file("engine_modules/inventory_modular/outbound_mixin.py", os.path.join(OUT, "02_C1", "engine_modules", "inventory_modular", "outbound_mixin.py"))

    # 03_C2
    copy_file("parsers/picking_list_parser.py", os.path.join(OUT, "03_C2", "parsers", "picking_list_parser.py"))
    # review_center: 상위 폴더에서 확인
    parent_review = os.path.join(os.path.dirname(BASE), "gui_app_modular", "dialogs", "review_center.py")
    if os.path.isfile(parent_review):
        ensure_dir(os.path.join(OUT, "03_C2", "gui_app_modular", "dialogs"))
        shutil.copy2(parent_review, os.path.join(OUT, "03_C2", "gui_app_modular", "dialogs", "review_center.py"))
    # outbound 매칭 관련
    copy_file("parsers/cross_check_engine.py", os.path.join(OUT, "03_C2", "parsers", "cross_check_engine.py"))
    copy_file("gui_app_modular/handlers/outbound_handlers.py", os.path.join(OUT, "03_C2", "gui_app_modular", "handlers", "outbound_handlers.py"))
    # README for 03_C2
    with open(os.path.join(OUT, "03_C2", "README.txt"), "w", encoding="utf-8") as f:
        f.write("review_center: gui_app_modular/dialogs/review_center.py (상위 폴더에 있으면 포함됨)\n")
        f.write("outbound 매칭: cross_check_engine.py, outbound_handlers.py 포함\n")

    # 04_C3
    copy_file("engine_modules/inventory_modular/outbound_mixin.py", os.path.join(OUT, "04_C3", "outbound_mixin.py"))
    with open(os.path.join(OUT, "04_C3", "README.txt"), "w", encoding="utf-8") as f:
        f.write("final_qc 관련 UI, inbox 관련: 프로젝트에서 해당 이름의 파일을 찾지 못했습니다.\n")
        f.write("outbound_mixin.py 는 포함했습니다.\n")

    # 05_dashboard
    copy_file("gui_app_modular/tabs/dashboard_tab.py", os.path.join(OUT, "05_dashboard", "dashboard_tab.py"))
    copy_file("gui_app_modular/tabs/dashboard_data_mixin.py", os.path.join(OUT, "05_dashboard", "dashboard_data_mixin.py"))
    with open(os.path.join(OUT, "05_dashboard", "README.txt"), "w", encoding="utf-8") as f:
        f.write("outbound_dashboard.py, outbound_status_service.py, state_aggregate.py 는 프로젝트에 없습니다.\n")
        f.write("대신 dashboard_tab.py, dashboard_data_mixin.py 를 포함했습니다.\n")

    # ZIP
    zip_path = os.path.join(BASE, "FULL_BUILD_UPLOAD.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(OUT):
            for f in files:
                abs_path = os.path.join(root, f)
                arcname = os.path.relpath(abs_path, os.path.dirname(OUT))
                zf.write(abs_path, arcname)

    print(f"Created: {zip_path}")
    print(f"Folder: {OUT}")

if __name__ == "__main__":
    main()
