#!/usr/bin/env python3
"""B10 Quality Script: Basic unused import detection using AST.

Scans key project directories (engine_modules/, gui_app_modular/) for
imports that are never referenced in the rest of the file.
"""
import ast
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCAN_DIRS = ["engine_modules", "gui_app_modular"]
EXCLUDE_DIRS = {"__pycache__", ".git", "backup", "temp"}

# Names that are commonly imported for side-effects or re-export
WHITELIST = {
    # typing
    "TYPE_CHECKING", "Optional", "List", "Dict", "Tuple", "Any", "Union",
    "Callable", "Set", "Sequence",
    # common side-effect imports
    "tkinter", "ttk", "tk",
    # __all__ re-exports handled separately
}


class NameCollector(ast.NodeVisitor):
    """Collect all Name references (excluding import statements)."""

    def __init__(self):
        self.names = set()

    def visit_Name(self, node):
        self.names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # Collect the root of attribute chains: foo.bar -> foo
        if isinstance(node.value, ast.Name):
            self.names.add(node.value.id)
        self.generic_visit(node)


def get_imports(tree):
    """Extract imported names from AST."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name.split(".")[0]
                imports.append((name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            # Skip star imports
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname if alias.asname else alias.name
                imports.append((name, node.lineno))
    return imports


def check_file(filepath):
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return findings
    except Exception:
        return findings

    imported = get_imports(tree)
    if not imported:
        return findings

    # Check for __all__; if present, names in __all__ are considered used
    all_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                all_names.add(elt.value)

    # Collect all name references
    collector = NameCollector()
    collector.visit(tree)
    used = collector.names | all_names

    # Also check string literals for dynamic usage (e.g., getattr patterns)
    # Simple heuristic: check if name appears as a string constant
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            used.add(node.value)

    for name, lineno in imported:
        if name in WHITELIST:
            continue
        if name.startswith("_"):
            continue
        if name not in used:
            findings.append({
                "file": filepath,
                "line": lineno,
                "name": name,
            })

    return findings


def main():
    all_findings = []
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
                all_findings.extend(check_file(fp))

    print(f"=== Unused Import Scan ===")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Scanned directories: {', '.join(SCAN_DIRS)}")
    print(f"Files scanned: {file_count}")
    print(f"Potentially unused imports: {len(all_findings)}")
    print()

    if all_findings:
        # Group by file
        by_file = {}
        for f in all_findings:
            by_file.setdefault(f["file"], []).append(f)

        for filepath, items in sorted(by_file.items()):
            relpath = os.path.relpath(filepath, PROJECT_ROOT)
            print(f"  {relpath}:")
            for item in sorted(items, key=lambda x: x["line"]):
                print(f"    line {item['line']}: {item['name']}")
        print()
    else:
        print("No unused imports detected.")
        print()

    print(f"=== Summary ===")
    print(f"  Files scanned: {file_count}")
    print(f"  Unused imports found: {len(all_findings)}")
    print(f"  NOTE: This is a heuristic check. Some imports may be used")
    print(f"        dynamically (getattr, __import__) or for type hints.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
