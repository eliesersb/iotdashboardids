#!/bin/bash
DURATION=${1:-15}
RATE=${2:-100}

cd "$(dirname "$0")/../.."

echo "===== DOCKER ATTACK DEMO ALL ====="
echo "Duration: ${DURATION}s per scenario"
echo "Rate    : ${RATE}"
echo ""

echo "===== 1. MQTT APPLICATION FLOOD ====="
./scripts/demo/docker_mqtt_flood.sh "$DURATION" "$RATE"

echo ""
echo "===== 2. gRPC APPLICATION FLOOD ====="
./scripts/demo/docker_grpc_flood.sh "$DURATION" "$RATE"

echo ""
echo "===== 3. REST HPING3 CONTROLLED TEST ====="
./scripts/demo/docker_rest_hping3.sh "$DURATION"

echo ""
echo "===== 4. CoAP HPING3 CONTROLLED TEST ====="
./scripts/demo/docker_coap_hping3.sh "$DURATION"

echo ""
echo "===== DOCKER ATTACK DEMO FINISHED ====="
echo "Untuk validasi hasil, jalankan:"
echo "./scripts/demo/docker_validate.sh"
