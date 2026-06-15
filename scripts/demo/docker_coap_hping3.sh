#!/bin/bash
DURATION=${1:-15}

echo "[DOCKER CoAP HPING3] target=coap_server:5683/UDP duration=${DURATION}s"
echo "[INFO] Controlled UDP test, tidak menggunakan --flood"
docker compose --profile tools run --rm attacker timeout "${DURATION}s" hping3 --udp -p 5683 -i u5000 coap_server || true
echo "[DOCKER CoAP HPING3] Finished"
