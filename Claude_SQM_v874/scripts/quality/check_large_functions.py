#!/usr/bin/env python3
"""B10 Quality Script: Report functions/methods exceeding 100 lines.

Scans engine_modules/ and gui_app_modular/ for functions and methods
that are longer than 100 lines, sorted by size descending.
"""
import ast
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCAN_DIRS = ["engine_modules", "gui_app_modular"]
EXCLUDE_DIRS = {"__pycache__", ".git", "backup", "temp"}
THRESHOLD = 100  # lines


def get_function_sizes(filepath):
    """Parse a file and return list of (name, start_line, end_line, size)."""
    results = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, Exception):
        return results

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = node.end_lineno if hasattr(node, "end_lineno") and node.end_lineno else start
            size = end - start + 1

            # Build qualified name (check if inside a class)
            name = node.name
            # Walk parents to find class
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef):
                    for child in ast.iter_child_nodes(parent):
                        if child is node:
                            name = f"{parent.name}.{node.name}"
                            break

            if size > THRESHOLD:
                results.append({
                    "file": filepath,
                    "name": name,
                    "start": start,
                    "end": end,
                    "size": size,
                })
    return results


def main():
    all_large = []
    file_count = 0

    for scan_dir in SCAN_DIRS:
        full_dir = os.path.join(PROJECT_ROOT, scan_dir)
        if not os.path.isdir(full_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(full_dir):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                fp = os.path.join(dirpath, fn)
                file_count += 1
                all_large.extend(get_function_sizes(fp))

    # Sort by size descending
    all_large.sort(key=lambda x: x["size"], reverse=True)

    print(f"=== Large Function Report (>{THRESHOLD} lines) ===")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Scanned directories: {', '.join(SCAN_DIRS)}")
    print(f"Files scanned: {file_count}")
    print(f"Large functions found: {len(all_large)}")
    print()

    if all_large:
        print(f"{'Lines':>6}  {'Function':<50}  {'File'}")
        print(f"{'-----':>6}  {'--------':<50}  {'----'}")
        for item in all_large:
            relpath = os.path.relpath(item["file"], PROJECT_ROOT)
            print(f"{item['size']:>6}  {item['name']:<50}  {relpath}:{item['start']}")
        print()

        # Buckets
        over_300 = [x for x in all_large if x["size"] > 300]
        over_200 = [x for x in all_large if 200 < x["size"] <= 300]
        over_100 = [x for x in all_large if x["size"] <= 200]

        print("=== Summary ===")
        print(f"  >300 lines (CRITICAL): {len(over_300)}")
        print(f"  201-300 lines (HIGH):   {len(over_200)}")
        print(f"  101-200 lines (MEDIUM): {len(over_100)}")
        print(f"  TOTAL:                  {len(all_large)}")
    else:
        print("No functions exceeding threshold found.")
        print()
        print("=== Summary ===")
        print(f"  Large functions: 0")

    return 0


if __name__ == "__main__":
    sys.exit(main())
