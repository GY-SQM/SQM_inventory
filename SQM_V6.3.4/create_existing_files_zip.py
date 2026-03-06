#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""있는 파일만 모아서 ReviewCenter_Dashboard.zip 생성 (다운로드용)."""
import os
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(BASE)
OUT_ZIP = os.path.join(BASE, "ReviewCenter_Dashboard.zip")


def add_if_exists(zf, src_path: str, arc_name: str) -> bool:
    if os.path.isfile(src_path):
        zf.write(src_path, arc_name)
        return True
    return False


def main():
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        added = []

        # review_center: 상위 gui_app_modular 또는 내부 FULL_BUILD_UPLOAD 복사본
        r1 = os.path.join(PARENT, "gui_app_modular", "dialogs", "review_center.py")
        r2 = os.path.join(BASE, "FULL_BUILD_UPLOAD", "03_C2", "gui_app_modular", "dialogs", "review_center.py")
        if add_if_exists(zf, r1, "gui_app_modular/dialogs/review_center.py"):
            added.append("review_center.py (상위)")
        elif add_if_exists(zf, r2, "gui_app_modular/dialogs/review_center.py"):
            added.append("review_center.py (FULL_BUILD)")

        # dashboard
        for name in ["dashboard_tab.py", "dashboard_data_mixin.py"]:
            path = os.path.join(BASE, "gui_app_modular", "tabs", name)
            if add_if_exists(zf, path, f"gui_app_modular/tabs/{name}"):
                added.append(name)

        # README
        readme = (
            "포함된 파일 (있는 것만):\n"
            "- gui_app_modular/dialogs/review_center.py\n"
            "- gui_app_modular/tabs/dashboard_tab.py\n"
            "- gui_app_modular/tabs/dashboard_data_mixin.py\n"
            "\nfinal_qc, inbox 관련 파일은 프로젝트에 없어 제외되었습니다."
        )
        zf.writestr("README.txt", readme.encode("utf-8"))

    print(f"Created: {OUT_ZIP}")
    print("Added:", ", ".join(added))


if __name__ == "__main__":
    main()
