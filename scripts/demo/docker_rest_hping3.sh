#!/bin/bash
DURATION=${1:-15}

echo "[DOCKER REST HPING3] target=rest_api:5000 duration=${DURATION}s"
echo "[INFO] Controlled SYN test, tidak menggunakan --flood"
docker compose --profile tools run --rm attacker timeout "${DURATION}s" hping3 -S -p 5000 -i u5000 rest_api || true
echo "[DOCKER REST HPING3] Finished"
