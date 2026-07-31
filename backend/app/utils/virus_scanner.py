# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import logging
import socket
import struct
import time
from pathlib import Path
from typing import Dict

from app.config.settings import settings

logger = logging.getLogger(__name__)

try:
    import clamd  # type: ignore
except Exception:  # pragma: no cover - optional dependency in some test environments
    clamd = None


def _parse_scan_result(raw_result: str) -> Dict[str, str | bool]:
    normalized = str(raw_result or "").strip().strip("\x00")
    if not normalized:
        return {"clean": True, "engine": "clamav", "result": "clean"}

    payload = normalized.split(":", 1)[-1].strip() if ":" in normalized else normalized
    upper_payload = payload.upper()

    if upper_payload.endswith(" FOUND"):
        threat_name = payload[:-6].strip() or "unknown_threat"
        return {"clean": False, "engine": "clamav", "result": threat_name}

    if upper_payload in {"OK", "STREAM: OK"} or upper_payload.endswith(": OK"):
        return {"clean": True, "engine": "clamav", "result": "clean"}

    if "ERROR" in upper_payload:
        raise RuntimeError(payload)

    return {"clean": True, "engine": "clamav", "result": "clean"}


def _scan_via_socket(candidate: str, host: str, port: int) -> Dict[str, str | bool]:
    with socket.create_connection((host, port), timeout=10) as client:
        client.sendall(b"zINSTREAM\x00")
        with open(candidate, "rb") as handle:
            while True:
                chunk = handle.read(65536)
                if not chunk:
                    break
                client.sendall(struct.pack("!I", len(chunk)))
                client.sendall(chunk)
        client.sendall(struct.pack("!I", 0))

        response = b""
        while True:
            packet = client.recv(4096)
            if not packet:
                break
            response += packet
            if b"\x00" in packet or b"\n" in packet:
                break

    return _parse_scan_result(response.decode("utf-8", errors="ignore"))


def scan_file(file_path: str) -> Dict[str, str | bool]:
    """
    Scan a file with ClamAV.

    Returns:
        {
          "clean": bool,
          "engine": "clamav" | "unavailable",
          "result": "clean" | "scan_skipped" | "<threat_name>"
        }
    """
    start_time = time.perf_counter()
    try:
        candidate = str(Path(file_path))

        host = settings.CLAMAV_HOST
        port = int(settings.CLAMAV_PORT)

        try:
            with socket.create_connection((host, port), timeout=3) as client:
                client.sendall(b"zPING\x00")
                if b"PONG" not in client.recv(32):
                    raise RuntimeError("Unexpected ClamAV ping response")
        except Exception as exc:
            logger.warning("ClamAV unavailable at %s:%s. Skipping malware scan (%s).", host, port, exc)
            return {"clean": True, "engine": "unavailable", "result": "scan_skipped"}

        if clamd is not None:
            try:
                client = clamd.ClamdNetworkSocket(host=host, port=port)
                client.ping()
                with open(candidate, "rb") as handle:
                    result = client.instream(handle)
                if result:
                    key, value = next(iter(result.items()))
                    status, details = value if isinstance(value, tuple) else ("OK", value)
                    if str(status).upper() == "FOUND":
                        threat_name = str(details or "unknown_threat")
                        return {"clean": False, "engine": "clamav", "result": threat_name}
                    return {"clean": True, "engine": "clamav", "result": "clean"}
                return {"clean": True, "engine": "clamav", "result": "clean"}
            except Exception as exc:
                logger.warning("python-clamd unavailable for %s. Falling back to raw socket scan (%s).", candidate, exc)

        try:
            return _scan_via_socket(candidate, host, port)
        except Exception as exc:
            logger.warning("ClamAV scan failed for %s. Skipping scan (%s).", candidate, exc)
            return {"clean": True, "engine": "unavailable", "result": "scan_skipped"}
    finally:
        duration = time.perf_counter() - start_time
        try:
            from app.middleware.prometheus_metrics import MetricsManager

            MetricsManager.record_clamav_scan_duration(duration)
        except Exception:
            pass


async def scan(file_path: str) -> Dict[str, str | bool]:
    return await asyncio.to_thread(scan_file, file_path)


class VirusScanner:
    async def scan(self, file_path: str) -> Dict[str, str | bool]:
        return await scan(file_path)


virus_scanner = VirusScanner()
