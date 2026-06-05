#!/usr/bin/env bash
set -e

DURATION="${1:-15}"
NETWORK="${NETWORK:-iotdashboardids_iot-net}"

echo "[MQTT FLOOD] Running for ${DURATION}s on Docker network: ${NETWORK}"

docker run --rm \
  --network "${NETWORK}" \
  -v "$PWD":/app \
  -w /app \
  python:3.10-slim \
  sh -c "pip install -q -r requirements.txt && timeout ${DURATION} python mqtt_flood.py || true"
