#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DB migration 관련 파일만 모아서 zip 생성 (다운로드용)."""

import os
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_ZIP = os.path.join(BASE, "DB_MIGRATION_ONLY.zip")


def add_if_exists(zf: zipfile.ZipFile, src_path: str, arc_name: str) -> bool:
    if os.path.isfile(src_path):
        zf.write(src_path, arc_name)
        return True
    return False


def main() -> None:
    targets = [
        ("engine_modules/db_migration_mixin.py", "engine_modules/db_migration_mixin.py"),
        ("engine_modules/db_schema_mixin.py", "engine_modules/db_schema_mixin.py"),
        ("engine_modules/database.py", "engine_modules/database.py"),
    ]

    added = []
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, arc in targets:
            if add_if_exists(zf, os.path.join(BASE, rel), arc):
                added.append(rel)

        zf.writestr(
            "README.txt",
            (
                "DB migration 관련 파일만 포함했습니다.\n"
                "- engine_modules/db_migration_mixin.py\n"
                "- engine_modules/db_schema_mixin.py\n"
                "- engine_modules/database.py (위 mixin 합성/초기화 연계)\n"
            ).encode("utf-8"),
        )

    print(f"Created: {OUT_ZIP}")
    print("Added:", ", ".join(added))


if __name__ == "__main__":
    main()

