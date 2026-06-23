#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Local dependency audit runner for ScholarForm AI.

Usage:
    python scripts/audit_deps.py             # Full audit
    python scripts/audit_deps.py --quick      # Quick scan (pip-audit + npm audit only)
    python scripts/audit_deps.py --sbom       # Regenerate SBOM only
    python scripts/audit_deps.py --fix        # Attempt auto-fix (audit fix)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"


def run(cmd: list[str], cwd: str | Path | None = None, check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    try:
        return subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                              check=check, timeout=timeout,
                              capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"     {e.stderr[:500]}", file=sys.stderr)
        return e
    except FileNotFoundError:
        print(f"  ⚠️  Command not found: {cmd[0]}", file=sys.stderr)
        return subprocess.CompletedProcess(cmd, returncode=-1)


def check_python() -> list[str]:
    """Run Python dependency checks: pip-audit, safety."""
    issues = []
    print("\n🔍 Python dependency audit...")

    # pip-audit
    print("  → pip-audit (CVE scan)...")
    r = run(["python", "-m", "pip_audit", "--requirement",
             str(BACKEND_DIR / "requirements.txt"),
             "--require-license", "--desc"])
    if r.returncode != 0:
        issues.append(f"pip-audit found issues:\n{r.stdout[:1000]}")
        print(f"    ⚠️  {len(r.stdout.splitlines())} issues")
    else:
        print("    ✅ No vulnerabilities found")

    # safety
    print("  → safety (CVE scan)...")
    r = run(["python", "-m", "safety", "check", "-r",
             str(BACKEND_DIR / "requirements.txt")])
    if r.returncode != 0:
        issues.append(f"safety found issues:\n{r.stdout[:1000]}")
        print(f"    ⚠️  Vulnerabilities detected")
    else:
        print("    ✅ No vulnerabilities found")

    # bandit SAST
    print("  → bandit (SAST)...")
    r = run(["python", "-m", "bandit", "-r",
             str(BACKEND_DIR / "app"),
             "-x", "app/tests", "-ll", "-q"])
    if r.returncode != 0:
        issues.append(f"bandit found issues:\n{r.stdout[:1000]}")
        print(f"    ⚠️  Security issues detected")
    else:
        print("    ✅ No security issues found")

    return issues


def check_npm() -> list[str]:
    """Run npm dependency checks: audit."""
    issues = []
    print("\n🔍 npm dependency audit...")

    print("  → npm audit...")
    r = run(["npm.cmd" if sys.platform == "win32" else "npm", "audit",
             "--audit-level=high"],
            cwd=FRONTEND_DIR, check=False)
    if r.returncode != 0:
        issues.append(f"npm audit found issues:\n{r.stdout[:1000]}")
        print(f"    ⚠️  {len(r.stdout.splitlines())} issues")
    else:
        print("    ✅ No high/critical vulnerabilities found")

    return issues


def generate_sbom():
    """Regenerate CycloneDX SBOM and THIRD_PARTY_NOTICES."""
    print("\n📄 Regenerating SBOM...")
    r = run(["python", "scripts/generate_sbom.py"], cwd=REPO_ROOT)
    if r.returncode != 0:
        print(f"  ❌ SBOM generation failed: {r.stderr[:500]}", file=sys.stderr)
    else:
        print("  ✅ SBOM regenerated")


def main():
    parser = argparse.ArgumentParser(description="ScholarForm AI dependency auditor")
    parser.add_argument("--quick", action="store_true",
                        help="Quick scan: pip-audit + npm audit only")
    parser.add_argument("--sbom", action="store_true",
                        help="Regenerate SBOM and notices")
    parser.add_argument("--fix", action="store_true",
                        help="Attempt auto-fix (npm audit fix)")
    args = parser.parse_args()

    print("=" * 60)
    print("  ScholarForm AI — Dependency Auditor")
    print("=" * 60)

    all_issues: list[str] = []

    if args.sbom:
        generate_sbom()
        return

    if not args.quick:
        all_issues.extend(check_python())
    else:
        print("\n🔍 Quick mode: pip-audit only...")
        r = run(["python", "-m", "pip_audit", "--requirement",
                 str(BACKEND_DIR / "requirements.txt")])
        if r.returncode != 0:
            all_issues.append(f"pip-audit: {r.stdout[:500]}")

    all_issues.extend(check_npm())

    if args.fix:
        print("\n🔧 Attempting auto-fix...")
        r = run(["npm.cmd" if sys.platform == "win32" else "npm", "audit", "fix"],
                cwd=FRONTEND_DIR, check=False)
        if r.returncode == 0:
            print("  ✅ npm audit fix applied")

    print("\n" + "=" * 60)
    if all_issues:
        print(f"  ❌ {len(all_issues)} issue(s) found:")
        for issue in all_issues:
            print(f"     - {issue[:200]}")
        sys.exit(1)
    else:
        print("  ✅ All audits passed — no issues found")
        print("=" * 60)


if __name__ == "__main__":
    main()
