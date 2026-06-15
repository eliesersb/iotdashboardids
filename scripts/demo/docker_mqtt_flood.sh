#!/bin/bash
DURATION=${1:-15}
RATE=${2:-100}

echo "[DOCKER MQTT FLOOD] duration=${DURATION}s rate=${RATE}"
docker compose --profile tools run --rm attacker python mqtt_flood.py --duration "$DURATION" --rate "$RATE"
echo "[DOCKER MQTT FLOOD] Finished"
