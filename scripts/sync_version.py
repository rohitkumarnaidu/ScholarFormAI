# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Single source of truth for ScholarForm AI version.

Canonical source: backend/pyproject.toml → version field.
Propagates to: frontend/package.json, CITATION.cff, docs/ frontmatter.

Usage:
    python scripts/sync_version.py          # sync all files
    python scripts/sync_version.py --check  # dry-run, exit 1 if mismatches
    python scripts/sync_version.py --show   # print current version
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Files to sync
FILES = [
    {
        "path": REPO_ROOT / "frontend" / "package.json",
        "read": lambda p: json.loads(p.read_text())["version"],
        "write": lambda p, v: p.write_text(
            re.sub(
                r'"version":\s*"[^"]+"',
                f'"version": "{v}"',
                p.read_text(),
            )
        ),
    },
    {
        "path": REPO_ROOT / "CITATION.cff",
        "read": lambda p: re.search(
            r'^version:\s*(.+)', p.read_text(), re.M
        ).group(1),
        "write": lambda p, v: p.write_text(
            re.sub(r'^version:\s*.+', f"version: {v}", p.read_text(), flags=re.M)
        ),
    },
]


def get_canonical_version():
    pyproject = REPO_ROOT / "backend" / "pyproject.toml"
    m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(), re.M)
    if not m:
        print("ERROR: version not found in backend/pyproject.toml", file=sys.stderr)
        sys.exit(1)
    return m.group(1)


def sync(dry_run=False):
    version = get_canonical_version()
    mismatches = []

    for f in FILES:
        if not f["path"].exists():
            mismatches.append((f["path"].name, "missing"))
            continue
        current = f["read"](f["path"])
        if current != version:
            mismatches.append((f["path"].name, current, version))
            if not dry_run:
                f["write"](f["path"], version)
                print(f"  {f['path'].name}: {current} -> {version}")

    return mismatches


def main():
    args = set(sys.argv[1:])

    if "--show" in args:
        print(get_canonical_version())
        return

    dry_run = "--check" in args

    if dry_run:
        print(f"Canonical version: {get_canonical_version()}")
        print("Checking files...")

    mismatches = sync(dry_run=dry_run)

    if mismatches:
        for m in mismatches:
            print(f"  MISMATCH: {m[0]} has {m[1]}, expected {m[2]}")
        if dry_run:
            print("\nRun without --check to sync.")
            sys.exit(1)
    else:
        if dry_run:
            print("All files match canonical version.")
        else:
            print(f"All files synced to version {get_canonical_version()}.")


if __name__ == "__main__":
    main()
