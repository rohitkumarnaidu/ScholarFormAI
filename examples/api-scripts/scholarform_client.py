# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
ScholarForm API Python Client Example

Usage:
    python scholarform_client.py paper.docx --template ieee
    python scholarform_client.py paper.docx --template springer --api-key YOUR_KEY
"""

import argparse
import time
from pathlib import Path

import requests


class ScholarFormClient:
    def __init__(self, api_url="http://localhost:8000", api_key=None):
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"

    def health(self):
        r = self.session.get(f"{self.api_url}/api/v1/health", timeout=5)
        r.raise_for_status()
        resp = r.json()
        return resp.get("data", resp)

    def list_templates(self):
        r = self.session.get(f"{self.api_url}/api/v1/templates", timeout=10)
        r.raise_for_status()
        resp = r.json()
        return resp.get("data", resp)

    def upload(self, filepath, template="ieee"):
        with open(filepath, "rb") as f:
            r = self.session.post(
                f"{self.api_url}/api/v1/documents/upload",
                files={"file": (Path(filepath).name, f)},
                data={"template": template},
                timeout=60,
            )
        r.raise_for_status()
        resp = r.json()
        return resp.get("data", resp)

    def status(self, job_id):
        r = self.session.get(
            f"{self.api_url}/api/v1/documents/{job_id}/status", timeout=10
        )
        r.raise_for_status()
        resp = r.json()
        return resp.get("data", resp)

    def download(self, job_id, output_path, fmt="docx"):
        r = self.session.get(
            f"{self.api_url}/api/v1/documents/{job_id}/download",
            params={"format": fmt},
            stream=True,
            timeout=30,
        )
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return output_path

    def wait_for_completion(self, job_id, poll_interval=1):
        while True:
            data = self.status(job_id)
            status = str(data.get("status", "unknown")).lower()
            progress = data.get("progress", 0)
            print(f"  [{progress:3d}%] {status}")
            if status == "completed":
                return data
            if status in ("failed", "error"):
                raise RuntimeError(data.get("error", "Formatting failed"))
            time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description="ScholarForm API Python client")
    parser.add_argument("file", help="Path to DOCX file")
    parser.add_argument("--template", default="ieee", help="Journal template")
    parser.add_argument("--output", help="Output file path (default: formatted.docx)")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--api-key", default=None)
    args = parser.parse_args()

    client = ScholarFormClient(api_url=args.api_url, api_key=args.api_key)
    output = args.output or f"formatted.{Path(args.file).stem}.docx"

    print("Health check...")
    health_data = client.health()
    health_status = health_data.get("status", "healthy") if isinstance(health_data, dict) else "healthy"
    print(f"  OK: {health_status}")

    print(f"Uploading {args.file}...")
    upload_data = client.upload(args.file, args.template)

    # Handle api_envelope response
    if isinstance(upload_data, dict) and "job_id" in upload_data:
        job_id = upload_data["job_id"]
    elif isinstance(upload_data, dict) and "jobId" in upload_data:
        job_id = upload_data["jobId"]
    else:
        raise ValueError(f"Unexpected upload response data: {upload_data}")

    print(f"  Job ID: {job_id}")

    print("Formatting...")
    client.wait_for_completion(job_id)

    print(f"Downloading to {output}...")
    client.download(job_id, output)

    output_size = Path(output).stat().st_size
    print(f"  Saved: {output} ({output_size:,} bytes)")


if __name__ == "__main__":
    main()
