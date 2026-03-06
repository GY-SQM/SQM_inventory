#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
디버깅용 필수 파일만 모아서 압축합니다.
실행: python create_debug_zip.py
생성: SQM_V6.3.4_debug_files.zip (프로젝트 루트에)
"""
import os
import sys
import zipfile
import logging

# 로깅 억제
logging.disable(logging.CRITICAL)

base = os.path.dirname(os.path.abspath(__file__))
os.chdir(base)
sys.path.insert(0, base)
os.environ["SQM_SKIP_LICENSE"] = "1"
sys.argv = ["run.py", "--no-check"]

# 1) GUI 로드 시 필요한 .py 수집
before = set(sys.modules.keys())
try:
    from gui_app_modular import SQMInventoryApp  # noqa: F401
except Exception:
    pass
after = set(sys.modules.keys())

project_py = set()
for m in after - before:
    try:
        mod = sys.modules.get(m)
        if mod is None:
            continue
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        if f.endswith(".pyc"):
            f = f[:-1]
        if not f.endswith(".py"):
            continue
        abs_path = os.path.abspath(f)
        if base in abs_path and "site-packages" not in abs_path:
            project_py.add(abs_path)
    except Exception:
        pass

# 2) run.py, run_bootstrap.py 추가
project_py.add(os.path.join(base, "run.py"))
project_py.add(os.path.join(base, "run_bootstrap.py"))

# 3) 디버깅용 추가 파일
project_py.add(os.path.join(base, "test_s1_onestop.py"))
project_py.add(os.path.join(base, "gui_app_modular", "dialogs", "test_runner_dialog.py"))
for name in [
    "inspect_sales_order_xlsx.py", "fix_truncated_bl_numbers.py",
    "create_allocation_sample_3files.py", "cleanup_allocation_active_duplicates.py",
    "generate_allocation_from_tonbag.py", "parse_packing_pdf.py",
    "generate_virtual_allocation_3files.py", "create_allocation_3files_from_inventory.py",
    "check_allocation_vs_inventory.py", "__init__.py",
]:
    project_py.add(os.path.join(base, "scripts", name))
pytest_ini = os.path.join(base, "pytest.ini")

all_paths = sorted(project_py)
# pytest.ini는 리스트에 경로로 추가
if os.path.isfile(pytest_ini):
    all_paths.append(pytest_ini)

# 4) ZIP 생성 (상대 경로 유지)
zip_path = os.path.join(base, "SQM_V6.3.4_debug_files.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for abs_path in all_paths:
        if not os.path.isfile(abs_path):
            continue
        rel = os.path.relpath(abs_path, base)
        zf.write(abs_path, rel)

print(f"Created: {zip_path}")
print(f"Files: {len(all_paths)}")
