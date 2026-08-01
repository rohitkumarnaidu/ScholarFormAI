# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
ScholarForm AI — Quick Format Example

Formats a DOCX manuscript against a journal template.
Requires a running ScholarForm backend (local or remote).

Usage:
    python format_paper.py --template ieee --input paper.docx --output formatted.docx
"""

import argparse
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Quick-format a DOCX manuscript")
    parser.add_argument("--template", default="ieee", help="Journal template name")
    parser.add_argument("--input", required=True, help="Path to input DOCX file")
    parser.add_argument("--output", default="formatted.docx", help="Output file path")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--api-key", default=None, help="API key (optional)")
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}")
        sys.exit(1)

    api_base = args.api_url.rstrip("/")
    headers = {"Accept": "application/json"}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    # 1. Health check
    print(f"Checking API at {api_base}...")
    try:
        r = requests.get(f"{api_base}/api/v1/health", timeout=5)
        r.raise_for_status()
        health_data = r.json().get("data", r.json())
        print(f"  API is healthy: {health_data}")
    except requests.RequestException as e:
        print(f"  API unreachable: {e}")
        print("  Start the backend: uvicorn app.main:app --reload --port 8000")
        sys.exit(1)

    # 2. Upload document
    print(f"Uploading {input_path.name}...")
    with open(input_path, "rb") as f:
        r = requests.post(
            f"{api_base}/api/v1/documents/upload",
            headers=headers,
            files={"file": (input_path.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"template": args.template},
            timeout=60,
        )
    r.raise_for_status()
    resp = r.json()

    # Handle api_envelope standard response data structure
    if "data" in resp and isinstance(resp["data"], dict) and "job_id" in resp["data"]:
        job_id = resp["data"]["job_id"]
    else:
        job_id = resp.get("job_id")

    if not job_id:
        print(f"Error: Response did not contain job_id: {resp}")
        sys.exit(1)

    print(f"  Job ID: {job_id}")

    # 3. Poll for completion
    print("Formatting...")
    status = "processing"
    while status.lower() not in ("completed", "failed"):
        r = requests.get(f"{api_base}/api/v1/documents/{job_id}/status", headers=headers, timeout=10)
        r.raise_for_status()
        resp = r.json()
        data = resp.get("data", resp)
        status = str(data.get("status", "unknown")).lower()
        progress = data.get("progress", 0)
        print(f"  [{progress:3d}%] {status}", end="\r")
        if status in ("failed", "error"):
            error_details = data.get("error") or resp.get("error", "Unknown error")
            print(f"\n  Error: {error_details}")
            sys.exit(1)
        time.sleep(1)

    print(f"\n  Done!")

    # 4. Download formatted document
    print(f"Downloading to {args.output}...")
    r = requests.get(
        f"{api_base}/api/v1/documents/{job_id}/download",
        headers=headers,
        params={"format": "docx"},
        stream=True,
        timeout=30,
    )
    r.raise_for_status()
    with open(args.output, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"  Saved: {args.output} ({os.path.getsize(args.output):,} bytes)")
    print("Done.")


if __name__ == "__main__":
    main()
