#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
풀버전 작성용 업로드 파일 목록 기준으로 압축 생성.
- 01_base_core.zip  : 실행/설정 필수
- C1_core.zip       : Allocation 승인 엔진
- C2_core.zip       : Picking List + Review Center
- C3_core.zip       : 최종 QC + INBOX (있는 것만)
- Dashboard_core.zip : 대시보드 (있는 것만)
- 02_optional_core.zip : DB/리포트 등 권장
- 풀버전_업로드_전체.zip : 위 전체 한 번에
"""
import os
import shutil
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(BASE)  # Sqm 재고관리

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def add_to_zip(zf, src_path, arc_name):
    if os.path.isfile(src_path):
        zf.write(src_path, arc_name)
        return True
    return False

def add_parent_to_zip(zf, parent_rel, arc_name):
    path = os.path.join(PARENT, parent_rel)
    return add_to_zip(zf, path, arc_name)

def write_readme(zf, arc_name, lines):
    from io import BytesIO
    buf = BytesIO("\n".join(lines).encode("utf-8"))
    zf.writestr(arc_name, buf.getvalue())

def main():
    # 1) 01_base_core.zip
    with zipfile.ZipFile(os.path.join(BASE, "01_base_core.zip"), "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ["run.py", "requirements.txt", "settings.ini", "version.py"]:
            add_to_zip(zf, os.path.join(BASE, name), name)
    print("Created: 01_base_core.zip")

    # 2) C1_core.zip
    with zipfile.ZipFile(os.path.join(BASE, "C1_core.zip"), "w", zipfile.ZIP_DEFLATED) as zf:
        add_to_zip(zf, os.path.join(BASE, "parsers", "allocation_parser.py"), "parsers/allocation_parser.py")
        add_to_zip(zf, os.path.join(BASE, "gui_app_modular", "dialogs", "allocation_dialog.py"), "gui_app_modular/dialogs/allocation_dialog.py")
        add_to_zip(zf, os.path.join(BASE, "engine_modules", "inventory_modular", "outbound_mixin.py"), "engine_modules/inventory_modular/outbound_mixin.py")
    print("Created: C1_core.zip")

    # 3) C2_core.zip
    with zipfile.ZipFile(os.path.join(BASE, "C2_core.zip"), "w", zipfile.ZIP_DEFLATED) as zf:
        add_to_zip(zf, os.path.join(BASE, "parsers", "picking_list_parser.py"), "parsers/picking_list_parser.py")
        add_to_zip(zf, os.path.join(BASE, "parsers", "cross_check_engine.py"), "parsers/cross_check_engine.py")
        add_to_zip(zf, os.path.join(BASE, "engine_modules", "inventory_modular", "outbound_mixin.py"), "engine_modules/inventory_modular/outbound_mixin.py")
        if add_parent_to_zip(zf, "gui_app_modular/dialogs/review_center.py", "gui_app_modular/dialogs/review_center.py"):
            pass  # included
        add_parent_to_zip(zf, "gui_app_modular/utils/ocr_utils.py", "gui_app_modular/utils/ocr_utils.py")
        add_parent_to_zip(zf, "gui_app_modular/utils/review_rules.py", "gui_app_modular/utils/review_rules.py")
    print("Created: C2_core.zip")

    # 4) C3_core.zip
    with zipfile.ZipFile(os.path.join(BASE, "C3_core.zip"), "w", zipfile.ZIP_DEFLATED) as zf:
        add_to_zip(zf, os.path.join(BASE, "engine_modules", "inventory_modular", "outbound_mixin.py"), "engine_modules/inventory_modular/outbound_mixin.py")
        write_readme(zf, "README.txt", [
            "final_qc_dialog.py, picking_inbox.py 등은 프로젝트에서 찾지 못했습니다.",
            "outbound_mixin.py 만 포함했습니다.",
        ])
    print("Created: C3_core.zip")

    # 5) Dashboard_core.zip
    with zipfile.ZipFile(os.path.join(BASE, "Dashboard_core.zip"), "w", zipfile.ZIP_DEFLATED) as zf:
        add_to_zip(zf, os.path.join(BASE, "gui_app_modular", "tabs", "dashboard_tab.py"), "gui_app_modular/tabs/dashboard_tab.py")
        add_to_zip(zf, os.path.join(BASE, "gui_app_modular", "tabs", "dashboard_data_mixin.py"), "gui_app_modular/tabs/dashboard_data_mixin.py")
        write_readme(zf, "README.txt", [
            "outbound_dashboard.py, outbound_status_service.py, state_aggregate.py 는 없습니다.",
            "dashboard_tab.py, dashboard_data_mixin.py 를 포함했습니다.",
        ])
    print("Created: Dashboard_core.zip")

    # 6) 02_optional_core.zip (있으면 좋은 파일)
    with zipfile.ZipFile(os.path.join(BASE, "02_optional_core.zip"), "w", zipfile.ZIP_DEFLATED) as zf:
        add_to_zip(zf, os.path.join(BASE, "engine_modules", "db_migration_mixin.py"), "engine_modules/db_migration_mixin.py")
        add_to_zip(zf, os.path.join(BASE, "engine_modules", "db_schema_mixin.py"), "engine_modules/db_schema_mixin.py")
    print("Created: 02_optional_core.zip")

    # 7) 풀버전_업로드_전체.zip (전체 한 번에)
    out_dir = os.path.join(BASE, "풀버전_업로드_폴더")
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    ensure_dir(out_dir)
    # base
    for name in ["run.py", "requirements.txt", "settings.ini", "version.py"]:
        src = os.path.join(BASE, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(out_dir, name))
    # C1
    for rel in ["parsers/allocation_parser.py", "gui_app_modular/dialogs/allocation_dialog.py", "engine_modules/inventory_modular/outbound_mixin.py"]:
        src = os.path.join(BASE, rel)
        if os.path.isfile(src):
            dest = os.path.join(out_dir, rel)
            ensure_dir(os.path.dirname(dest))
            shutil.copy2(src, dest)
    # C2
    for rel in ["parsers/picking_list_parser.py", "parsers/cross_check_engine.py", "engine_modules/inventory_modular/outbound_mixin.py"]:
        src = os.path.join(BASE, rel)
        if os.path.isfile(src):
            dest = os.path.join(out_dir, rel)
            ensure_dir(os.path.dirname(dest))
            shutil.copy2(src, dest)
    review_src = os.path.join(PARENT, "gui_app_modular", "dialogs", "review_center.py")
    if os.path.isfile(review_src):
        dest = os.path.join(out_dir, "gui_app_modular", "dialogs", "review_center.py")
        ensure_dir(os.path.dirname(dest))
        shutil.copy2(review_src, dest)
    for rel in ["gui_app_modular/utils/ocr_utils.py", "gui_app_modular/utils/review_rules.py"]:
        src = os.path.join(PARENT, rel)
        if os.path.isfile(src):
            dest = os.path.join(out_dir, rel)
            ensure_dir(os.path.dirname(dest))
            shutil.copy2(src, dest)
    # C3
    src = os.path.join(BASE, "engine_modules/inventory_modular/outbound_mixin.py")
    if os.path.isfile(src):
        dest = os.path.join(out_dir, "engine_modules/inventory_modular/outbound_mixin.py")
        ensure_dir(os.path.dirname(dest))
        shutil.copy2(src, dest)
    # Dashboard
    for rel in ["gui_app_modular/tabs/dashboard_tab.py", "gui_app_modular/tabs/dashboard_data_mixin.py"]:
        src = os.path.join(BASE, rel)
        if os.path.isfile(src):
            dest = os.path.join(out_dir, rel)
            ensure_dir(os.path.dirname(dest))
            shutil.copy2(src, dest)
    # optional
    for rel in ["engine_modules/db_migration_mixin.py", "engine_modules/db_schema_mixin.py"]:
        src = os.path.join(BASE, rel)
        if os.path.isfile(src):
            dest = os.path.join(out_dir, rel)
            ensure_dir(os.path.dirname(dest))
            shutil.copy2(src, dest)
    with open(os.path.join(out_dir, "업로드_목록_README.txt"), "w", encoding="utf-8") as f:
        f.write("풀버전 작성용 업로드 파일 (해당되는 것만 포함)\n")
        f.write("- 기본: run.py, requirements.txt, settings.ini, version.py\n")
        f.write("- C1: allocation_parser, allocation_dialog, outbound_mixin\n")
        f.write("- C2: picking_list_parser, review_center, cross_check_engine, ocr_utils, review_rules\n")
        f.write("- C3: outbound_mixin (final_qc/inbox 미포함)\n")
        f.write("- Dashboard: dashboard_tab, dashboard_data_mixin\n")
        f.write("- optional: db_migration_mixin, db_schema_mixin\n")
    zip_path = os.path.join(BASE, "풀버전_업로드_전체.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(out_dir):
            for f in files:
                abs_path = os.path.join(root, f)
                arcname = os.path.relpath(abs_path, os.path.dirname(out_dir))
                zf.write(abs_path, arcname)
    shutil.rmtree(out_dir)
    print("Created: 풀버전_업로드_전체.zip")

if __name__ == "__main__":
    main()
