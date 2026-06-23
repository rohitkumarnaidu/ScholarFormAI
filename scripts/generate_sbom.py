#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""SBOM generator and third-party notices updater for ScholarForm AI."""

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
TEMP = REPO_ROOT / "scripts" / "_sbom_tmp"

LICENSE_PRIORITY = [
    "MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause",
    "ISC", "Python-2.0", "PSF", "MPL-2.0",
    "AGPL-3.0", "GPL-3.0", "GPL-2.0", "LGPL-3.0",
    "Unlicense", "CC0-1.0", "Zlib", "0BSD",
]

LICENSE_TEXTS: dict[str, str] = {}


def load_license_texts():
    spdx_dir = Path(__file__).resolve().parent.parent / "scripts" / "_licenses"
    spdx_dir.mkdir(parents=True, exist_ok=True)
    license_path = spdx_dir / "licenses.json"
    if license_path.exists():
        return json.loads(license_path.read_text(encoding="utf-8"))

    texts = {
        "MIT": """MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.""",
        "Apache-2.0": """Apache License, Version 2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.""",
        "BSD-3-Clause": """BSD 3-Clause License

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED.""",
        "BSD-2-Clause": """BSD 2-Clause License

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED.""",
        "ISC": """ISC License

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.""",
        "Python-2.0": """Python Software Foundation License Version 2

1. This LICENSE AGREEMENT is between the Python Software Foundation ("PSF"),
   and the Individual or Organization ("Licensee") accessing and otherwise
   using Python 2.0 software in source or binary form and its associated
   documentation.

2. Subject to the terms and conditions of this License Agreement, PSF hereby
   grants Licensee a nonexclusive, royalty-free, world-wide license to
   reproduce, analyze, test, perform and/or display publicly, prepare
   derivative works, distribute, and otherwise use Python 2.0 alone or in any
   derivative version, provided, however, that PSF's License Agreement and
   PSF's notice of copyright, i.e., "Copyright (c) 2001, 2002, 2003, 2004,
   2005, 2006 Python Software Foundation; All Rights Reserved" are retained
   in Python 2.0 alone or in any derivative version prepared by Licensee.""",
        "PSF": """Python Software Foundation License

Copyright (c) 2001-2025 Python Software Foundation. All rights reserved.

See https://docs.python.org/3/license.html#psf-license for full text.""",
        "MPL-2.0": """Mozilla Public License Version 2.0

1. Definitions
   "Contributor" means each individual or legal entity that creates,
   contributes to the creation of, or owns Covered Software.

2. License Grants
   (a) Each Contributor hereby grants you a world-wide, royalty-free,
   non-exclusive license to use, reproduce, prepare derivative works of,
   distribute, and otherwise exploit the Contribution.

See https://www.mozilla.org/en-US/MPL/2.0/ for full text.""",
        "AGPL-3.0": """GNU AFFERO GENERAL PUBLIC LICENSE Version 3

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.""",
        "GPL-3.0": """GNU GENERAL PUBLIC LICENSE Version 3

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.""",
        "GPL-2.0": """GNU GENERAL PUBLIC LICENSE Version 2

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA.""",
        "LGPL-3.0": """GNU LESSER GENERAL PUBLIC LICENSE Version 3

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See https://www.gnu.org/licenses/lgpl-3.0.html for full text.""",
        "Unlicense": """This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain.""",
        "CC0-1.0": """CC0 1.0 Universal

The person who associated a work with this deed has dedicated the work to
the public domain by waiving all of their rights to the work worldwide
under copyright law, including all related and neighboring rights, to the
extent allowed by law.

You can copy, modify, distribute and perform the work, even for commercial
purposes, all without asking permission.""",
        "Zlib": """zlib License

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented.
2. Altered source versions must be plainly marked as such.
3. This notice may not be removed or altered from any source distribution.""",
        "0BSD": """BSD Zero Clause License

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.""",
    }
    license_path.write_text(json.dumps(texts, indent=2), encoding="utf-8")
    return texts


def normalize_license(lic: str) -> str:
    """Normalize license string to SPDX identifier."""
    if not lic or lic == "UNKNOWN":
        return "Unknown"
    lic = lic.strip()
    mapping = {
        "MIT License": "MIT",
        "MIT license": "MIT",
        "Apache License 2.0": "Apache-2.0",
        "Apache Software License": "Apache-2.0",
        "Apache 2.0": "Apache-2.0",
        "Apache-2.0": "Apache-2.0",
        "Apache License, Version 2.0": "Apache-2.0",
        "Apache 2.0 License": "Apache-2.0",
        "BSD License": "BSD-3-Clause",
        "BSD": "BSD-3-Clause",
        "BSD-3-Clause": "BSD-3-Clause",
        "BSD 3-Clause": "BSD-3-Clause",
        "New BSD License": "BSD-3-Clause",
        "BSD 2-Clause": "BSD-2-Clause",
        "BSD-2-Clause": "BSD-2-Clause",
        "Python Software Foundation License": "PSF",
        "PSF License": "PSF",
        "PSF": "PSF",
        "Python-2.0": "Python-2.0",
        "Python License": "Python-2.0",
        "ISC License": "ISC",
        "ISC": "ISC",
        "GNU General Public License v3": "GPL-3.0",
        "GNU General Public License v3 or later (GPLv3+)": "GPL-3.0",
        "GPLv3": "GPL-3.0",
        "GPLv2": "GPL-2.0",
        "GPL-2.0": "GPL-2.0",
        "GPL-3.0": "GPL-3.0",
        "LGPLv3": "LGPL-3.0",
        "LGPL-3.0": "LGPL-3.0",
        "GNU Lesser General Public License v3": "LGPL-3.0",
        "MPL 2.0": "MPL-2.0",
        "MPL-2.0": "MPL-2.0",
        "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
        "AGPL-3.0": "AGPL-3.0",
        "AGPL 3": "AGPL-3.0",
        "GNU Affero General Public License v3": "AGPL-3.0",
        "CC0-1.0": "CC0-1.0",
        "CC0 1.0 Universal (CC0 1.0) Public Domain Dedication": "CC0-1.0",
        "The Unlicense": "Unlicense",
        "Unlicense": "Unlicense",
        "zlib License": "Zlib",
        "Zlib": "Zlib",
        "0BSD": "0BSD",
        "BSD Zero Clause License": "0BSD",
        "openldap 2.8": "OLDAP-2.8",
        "Apache 2.0 or MIT": "Apache-2.0 OR MIT",
        "MIT OR Apache-2.0": "MIT OR Apache-2.0",
        "(MIT OR CC0-1.0)": "MIT OR CC0-1.0",
        "MIT OR CC0-1.0": "MIT OR CC0-1.0",
        "Public Domain": "Unlicense",
    }
    if lic in mapping:
        return mapping[lic]
    if "MIT" in lic:
        return "MIT"
    if "Apache" in lic:
        return "Apache-2.0"
    if "BSD" in lic:
        return "BSD-3-Clause" if "2" not in lic else "BSD-2-Clause"
    if "GPL" in lic:
        return "GPL-3.0" if "3" in lic else "GPL-2.0"
    if "LGPL" in lic:
        return "LGPL-3.0"
    if "MPL" in lic:
        return "MPL-2.0"
    if "ISC" in lic:
        return "ISC"
    if "AGPL" in lic:
        return "AGPL-3.0"
    if "PSF" in lic or "Python" in lic:
        return "PSF"
    if "CC0" in lic or "Creative Commons" in lic:
        return "CC0-1.0"
    if "Unlicense" in lic or "Public Domain" in lic:
        return "Unlicense"
    if "zlib" in lic.lower():
        return "Zlib"
    return lic


def extract_python_packages() -> list[dict]:
    """Extract all installed Python packages with license info."""
    pkgs = []
    try:
        import importlib.metadata
        for dist in importlib.metadata.distributions():
            meta = dist.metadata
            name = meta.get("Name", dist.metadata.get("Name", "unknown"))
            license_raw = meta.get("License", "") or ""
            pkgs.append({
                "name": name,
                "version": dist.version,
                "license_raw": license_raw,
                "license": normalize_license(license_raw),
                "homepage": meta.get("Home-page", ""),
                "summary": meta.get("Summary", ""),
            })
    except Exception as e:
        print(f"Warning: importlib.metadata failed: {e}", file=sys.stderr)

    pkgs.sort(key=lambda p: p["name"].lower())
    return pkgs


NPM_CACHE = REPO_ROOT / "scripts" / "_sbom_tmp" / "npm_licenses.json"


def extract_npm_packages() -> list[dict]:
    """Extract npm packages with license info (reads cache or runs license-checker)."""
    pkgs = []
    data = None

    if NPM_CACHE.exists():
        data = json.loads(NPM_CACHE.read_text(encoding="utf-8-sig"))
    else:
        try:
            npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
            result = subprocess.run(
                [npx_cmd, "--yes", "license-checker", "--json", "--production"],
                capture_output=True, text=True, timeout=120,
                cwd=str(FRONTEND_DIR),
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                NPM_CACHE.parent.mkdir(parents=True, exist_ok=True)
                NPM_CACHE.write_text(result.stdout, encoding="utf-8")
        except Exception as e:
            print(f"Warning: npm license extraction failed: {e}", file=sys.stderr)

    if data:
        for key, info in data.items():
            name = key.rsplit("@", 1)[0] if key.count("@") >= 1 else key
            ver = key.rsplit("@", 1)[-1] if key.count("@") >= 1 else ""
            lic = info.get("licenses", "UNKNOWN")
            pkgs.append({
                "name": name,
                "version": ver,
                "license_raw": lic,
                "license": normalize_license(lic),
                "homepage": info.get("repository", ""),
                "summary": f"publisher: {info.get('publisher', '')}",
            })

    pkgs.sort(key=lambda p: p["name"].lower())
    return pkgs


def build_cyclonedx_sbom(packages: list[dict], name: str) -> dict:
    """Build a CycloneDX SBOM JSON."""
    components = []
    for pkg in packages:
        comp = {
            "type": "library",
            "name": pkg["name"],
            "version": pkg["version"],
            "licenses": [{"license": {"id": pkg["license"]}}] if pkg["license"] != "Unknown" else [],
            "purl": f"pkg:pypi/{pkg['name']}@{pkg['version']}" if name == "backend" else f"pkg:npm/{pkg['name']}@{pkg['version']}",
        }
        components.append(comp)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "name": f"scholarform-ai-{name}",
                "type": "application",
                "version": "1.0.0",
            }
        },
        "components": components,
    }


def license_sort_key(lic: str):
    try:
        return LICENSE_PRIORITY.index(lic)
    except ValueError:
        return 999


def generate_notice_md(python_pkgs: list[dict], npm_pkgs: list[dict]) -> str:
    """Generate the full THIRD_PARTY_NOTICES.md content."""
    lines = []
    lines.append("# Third-Party Notices")
    lines.append("")
    lines.append("ScholarForm AI uses the following third-party libraries and components.")
    lines.append("Licenses are reproduced below in accordance with their terms.")
    lines.append("")

    # Python packages
    lines.append("## Backend (Python) — All Packages")
    lines.append("")
    lines.append(f"**{len(python_pkgs)} total packages**")
    lines.append("")
    lines.append("| # | Package | Version | License | Homepage |")
    lines.append("|---|---------|---------|---------|----------|")
    for i, pkg in enumerate(python_pkgs, 1):
        hp = pkg.get("homepage", "") or ""
        lines.append(f"| {i} | {pkg['name']} | {pkg['version']} | {pkg['license']} | {hp} |")

    lines.append("")
    lines.append("## Frontend (npm) — Production Packages")
    lines.append("")
    lines.append(f"**{len(npm_pkgs)} total packages**")
    lines.append("")
    lines.append("| # | Package | Version | License |")
    lines.append("|---|---------|---------|---------|")
    for i, pkg in enumerate(npm_pkgs, 1):
        lines.append(f"| {i} | {pkg['name']} | {pkg['version']} | {pkg['license']} |")

    # Infrastructure
    lines.append("")
    lines.append("## Infrastructure Dependencies")
    lines.append("")
    infra = [
        ("PostgreSQL", "PostgreSQL License", "Database"),
        ("Redis", "BSD-3-Clause", "Cache + message broker"),
        ("Docker", "Apache-2.0", "Container runtime"),
        ("GROBID", "AGPL-3.0", "PDF metadata extraction"),
        ("Celery (broker)", "BSD-3-Clause", "Task queue"),
        ("ChromaDB (embedded)", "Apache-2.0", "Vector database"),
    ]
    lines.append("| Component | License | Use |")
    lines.append("|-----------|---------|-----|")
    for comp, lic, use in infra:
        lines.append(f"| {comp} | {lic} | {use} |")

    # License aggregation
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## License Aggregation")
    lines.append("")

    license_groups = defaultdict(list)
    for pkg in python_pkgs + npm_pkgs:
        lic = pkg["license"]
        if lic and lic != "Unknown" and lic not in ("UNKNOWN", "unknown"):
            license_groups[lic].append(pkg["name"])

    sorted_licenses = sorted(license_groups.keys(), key=license_sort_key)
    for lic in sorted_licenses:
        pkgs_in_lic = license_groups[lic]
        lines.append(f"### {lic}")
        lines.append("")
        lines.append(f"Used by: {', '.join(sorted(pkgs_in_lic))}")
        lines.append("")
        if lic in LICENSE_TEXTS:
            lines.append("```text")
            lines.append(LICENSE_TEXTS[lic])
            lines.append("```")
            lines.append("")

    # AGPL commercial note
    lines.append("### Commercial License Notes")
    lines.append("")
    agpl_pkgs = [pkg["name"] for pkg in python_pkgs + npm_pkgs
                 if pkg["license"] == "AGPL-3.0" or pkg["license"] == "GPL-3.0"]
    if agpl_pkgs:
        lines.append("The following packages are licensed under AGPL-3.0 or GPL-3.0:")
        lines.append("")
        for p in agpl_pkgs:
            lines.append(f"- {p}")
        lines.append("")
        lines.append("If you need to use ScholarForm AI in a proprietary product, you must either:")
        lines.append("")
        lines.append("- Obtain a commercial license from the respective authors")
        lines.append("- Replace with an alternative library (e.g., GROBID → Docling, PyMuPDF → PyPDF2)")
        lines.append("- Comply with AGPL/GPL terms (provide source code to your users)")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*This file is auto-generated by `scripts/generate_sbom.py`. Last updated: June 2026*")
    lines.append("")

    return "\n".join(lines)


def main():
    global LICENSE_TEXTS
    LICENSE_TEXTS = load_license_texts()

    print("📦 Extracting Python packages...", file=sys.stderr)
    python_pkgs = extract_python_packages()
    print(f"   → {len(python_pkgs)} packages found", file=sys.stderr)

    print("📦 Extracting npm packages...", file=sys.stderr)
    npm_pkgs = extract_npm_packages()
    print(f"   → {len(npm_pkgs)} packages found", file=sys.stderr)

    # Generate CycloneDX SBOMs
    print("📄 Generating CycloneDX SBOMs...", file=sys.stderr)
    backend_sbom = build_cyclonedx_sbom(python_pkgs, "backend")
    frontend_sbom = build_cyclonedx_sbom(npm_pkgs, "frontend")

    sbom_dir = REPO_ROOT / "sbom"
    sbom_dir.mkdir(parents=True, exist_ok=True)
    (sbom_dir / "backend-sbom.json").write_text(
        json.dumps(backend_sbom, indent=2), encoding="utf-8")
    (sbom_dir / "frontend-sbom.json").write_text(
        json.dumps(frontend_sbom, indent=2), encoding="utf-8")
    print(f"   → Wrote {sbom_dir/'backend-sbom.json'}", file=sys.stderr)
    print(f"   → Wrote {sbom_dir/'frontend-sbom.json'}", file=sys.stderr)

    # Generate THIRD_PARTY_NOTICES.md
    print("📄 Generating THIRD_PARTY_NOTICES.md...", file=sys.stderr)
    notice = generate_notice_md(python_pkgs, npm_pkgs)
    notice_path = REPO_ROOT / "THIRD_PARTY_NOTICES.md"
    notice_path.write_text(notice, encoding="utf-8")
    print(f"   → Wrote {notice_path} ({len(notice)} chars)", file=sys.stderr)

    # Summary
    print(f"\n✅ Complete!", file=sys.stderr)
    print(f"   Python: {len(python_pkgs)} deps", file=sys.stderr)
    print(f"   npm:    {len(npm_pkgs)} deps", file=sys.stderr)
    print(f"   Total:  {len(python_pkgs) + len(npm_pkgs)} deps", file=sys.stderr)


if __name__ == "__main__":
    main()
