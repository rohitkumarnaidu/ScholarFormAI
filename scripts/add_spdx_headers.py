"""
Add SPDX license headers to all source files for OpenSSF compliance.
Skips files that already have an SPDX header.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SPDX_LINE = "SPDX-License-Identifier: MIT"
COPYRIGHT_LINE = "Copyright (c) 2026 ScholarForm AI"

# Mapping of file extensions to comment styles
STYLES: dict[str, tuple[str, str, str]] = {
    # (prefix, suffix, line_comment)
    ".py":    ("", "", "#"),
    ".sh":    ("", "", "#"),
    ".ps1":   ("", "", "#"),
    ".yml":   ("", "", "#"),
    ".yaml":  ("", "", "#"),
    ".toml":  ("", "", "#"),
    ".ini":   ("", "", "#"),
    ".cfg":   ("", "", "#"),
    ".ts":    ("", "", "//"),
    ".tsx":   ("", "", "//"),
    ".js":    ("", "", "//"),
    ".jsx":   ("", "", "//"),
    ".mjs":   ("", "", "//"),
    ".cjs":   ("", "", "//"),
    ".css":   ("/* ", " */", ""),
    ".scss":  ("/* ", " */", ""),
    ".html":  ("<!-- ", " -->", ""),
    ".md":    ("<!-- ", " -->", ""),
}

INCLUDE_DIRS = [
    "backend/app",
    "backend/tests",
    "backend/alembic",
    "backend/docker",
    "backend/ops",
    "backend/scripts",
    "backend/docs",
    "deploy",
    "docs",
    ".docs",
    "examples",
    "fuzz",
    "logo",
    "frontend/app",
    "frontend/src",
    "frontend/e2e",
    "frontend/public",
    "frontend/__mocks__",
    "scripts",
    ".github/workflows",
    ".github/ISSUE_TEMPLATE",
    ".github",
]

EXCLUDE_PATHS = {
    "backend/htmlcov",
    "backend/output",
    "frontend/coverage",
    "frontend/dist",
    "frontend/playwright-report",
    "frontend/test-results",
    "frontend/.next",
    "graphify-out",
    "htmlcov",
    ".venv",
    "node_modules",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".opencode",
}

EXCLUDE_DIRS = {
    "__pycache__", ".venv", "node_modules", ".git",
    "__init__",  # handled via .py
}

SPDX_RE = re.compile(r"SPDX-License-Identifier:")


def has_spdx_header(text: str) -> bool:
    return bool(SPDX_RE.search(text))


def _skip_path(path: Path, root: Path | None = None) -> bool:
    rel = path.relative_to(root or ROOT).as_posix()
    for excl in EXCLUDE_PATHS:
        if rel == excl or rel.startswith(excl + "/"):
            return True
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    return False


def make_header(ext: str) -> str:
    style = STYLES.get(ext)
    if style is None:
        return ""
    pref, suff, lc = style
    lines: list[str] = []
    if lc:
        lines.append(f"{lc} {SPDX_LINE}")
        lines.append(f"{lc} {COPYRIGHT_LINE}")
    elif pref:
        lines.append(f"{pref}{SPDX_LINE}{suff}")
        lines.append(f"{pref}{COPYRIGHT_LINE}{suff}")
        lines.append("")
    return "\n".join(lines) + "\n\n"


def process_file(path: Path, root: Path | None = None) -> bool:
    ext = path.suffix.lower()
    if ext not in STYLES:
        return False
    if _skip_path(path, root or ROOT):
        return False

    original = path.read_text(encoding="utf-8-sig", errors="replace")  # utf-8-sig strips BOM
    if has_spdx_header(original):
        return False  # already has it

    header = make_header(ext)
    if not header:
        return False

    # If file starts with a shebang, insert after it
    if original.startswith("#!"):
        newline_idx = original.index("\n")
        new_text = original[: newline_idx + 1] + header + original[newline_idx + 1 :]
    else:
        new_text = header + original

    path.write_text(new_text, encoding="utf-8")
    return True


ROOT_GLOBS = [
    "*.md",
    "*.yml",
    "*.yaml",
    "*.js",
    "*.mjs",
    "*.cjs",
    "*.cfg",
    "*.toml",
    "*.ini",
    ".pre-commit-config.yaml",
    ".fossa.yml",
    ".gitattributes",
    ".gitignore",
]

# Subdirectory root config files (e.g., frontend/*.js, backend/*.toml)
SUBROOT_CONFIG = {
    "frontend": ["*.js", "*.mjs", "*.cjs", "*.css"],
    "backend":  ["*.ini", "*.toml", "*.cfg"],
}


def main():
    total = 0
    added = 0
    skipped_existing = 0

    for include_dir in INCLUDE_DIRS:
        search_path = ROOT / include_dir
        if not search_path.exists():
            continue
        for fpath in sorted(search_path.rglob("*")):
            if not fpath.is_file():
                continue
            total += 1
            if process_file(fpath, ROOT):
                added += 1
                print(f"  + {fpath.relative_to(ROOT)}")
            else:
                if fpath.suffix.lower() in STYLES:
                    skipped_existing += 1

    # Root-level files
    for pattern in ROOT_GLOBS:
        for fpath in sorted(ROOT.glob(pattern)):
            if not fpath.is_file() or fpath.name.startswith("package-lock") or fpath.name.startswith("next-env"):
                continue
            total += 1
            if process_file(fpath):
                added += 1
                print(f"  + {fpath.relative_to(ROOT)}")
            else:
                if fpath.suffix.lower() in STYLES:
                    skipped_existing += 1

    # Subroot config files (e.g., frontend/postcss.config.js, backend/pyproject.toml)
    for subdir, patterns in SUBROOT_CONFIG.items():
        sub_path = ROOT / subdir
        if not sub_path.exists():
            continue
        for pattern in patterns:
            for fpath in sorted(sub_path.glob(pattern)):
                if not fpath.is_file() or fpath.name.startswith("next-env"):
                    continue
                total += 1
                if process_file(fpath, ROOT):
                    added += 1
                    print(f"  + {fpath.relative_to(ROOT)}")
                else:
                    if fpath.suffix.lower() in STYLES:
                        skipped_existing += 1

    print(f"\nDone. {added} files updated, {skipped_existing} already had SPDX header, {total} total scanned.")


if __name__ == "__main__":
    main()
