#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

set -euo pipefail

if [[ -f /opt/grobid/grobid.yaml ]]; then
  cp /opt/grobid/grobid.yaml /opt/grobid/grobid-home/config/grobid.yaml || true
fi

if [[ -x /opt/grobid/grobid-service/bin/grobid-service ]]; then
  /opt/grobid/grobid-service/bin/grobid-service &
elif [[ -x /opt/grobid/grobid-service/bin/grobid.sh ]]; then
  /opt/grobid/grobid-service/bin/grobid.sh &
else
  echo "Could not locate a GROBID launcher in image." >&2
  exit 1
fi

# Wait for internal GROBID to be healthy before starting proxy.
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8070/api/isalive >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

exec uvicorn proxy:app --host 0.0.0.0 --port "${PORT:-7860}" --log-level info

