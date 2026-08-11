"""Release version gate for SQM Inventory.

Checks that version.py matches the intended GitHub release tag and that the
remote repository does not already contain that tag.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "version.py"
TAG_RE = re.compile(r"^v?\d+(?:\.\d+)*(?:-[0-9A-Za-z.-]+)?$")


def read_version() -> str:
    tree = ast.parse(VERSION_FILE.read_text(encoding="utf-8"))
    values: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"VERSION", "__version__"}:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        values[target.id] = node.value.value

    version = values.get("VERSION")
    dunder = values.get("__version__")
    if not version or not dunder:
        raise RuntimeError("version.py must define both VERSION and __version__")
    if version != dunder:
        raise RuntimeError(f"VERSION ({version}) != __version__ ({dunder})")
    return version


def run_git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout


def remote_tags(remote: str) -> set[str]:
    output = run_git(["ls-remote", "--tags", remote])
    tags: set[str] = set()
    for line in output.splitlines():
        ref = line.rsplit("/", 1)[-1]
        if ref.endswith("^{}"):
            ref = ref[:-3]
        tags.add(ref)
    return tags


def normalize_release(release: str) -> str:
    release = release.strip()
    if not TAG_RE.match(release):
        raise RuntimeError(f"Invalid release tag format: {release}")
    return release if release.startswith("v") else f"v{release}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check SQM release version consistency.")
    parser.add_argument("--release", required=True, help="Intended release tag, e.g. v9.0.7.2")
    parser.add_argument("--remote", default="origin", help="Git remote to inspect")
    args = parser.parse_args()

    version = read_version()
    release_tag = normalize_release(args.release)
    expected_tag = f"v{version}"

    if release_tag != expected_tag:
        print(f"FAIL: release tag {release_tag} does not match version.py {expected_tag}")
        return 1

    tags = remote_tags(args.remote)
    if release_tag in tags:
        print(f"FAIL: remote {args.remote} already has tag {release_tag}")
        return 1

    print(f"PASS: version.py {version} matches release tag {release_tag}; remote tag is free")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
