#!/bin/bash

TARGET=$1
COUNT=${2:-500}
INTERVAL=${3:-u500}

PROJECT_DIR="$(pwd)"
SCRIPT_DIR="${PROJECT_DIR}/scripts"
ATTACK_SCRIPT="/scripts/hping3_attack.sh"
IMAGE_NAME="iot-hping3-attacker"
CONTAINER_NAME="hping3_attacker"

if [ -z "$TARGET" ]; then
    echo "Usage:"
    echo "  ./scripts/run_hping3_attacker.sh mqtt [count] [interval]"
    echo "  ./scripts/run_hping3_attacker.sh rest [count] [interval]"
    echo "  ./scripts/run_hping3_attacker.sh coap [count] [interval]"
    echo "  ./scripts/run_hping3_attacker.sh grpc [count] [interval]"
    echo "  ./scripts/run_hping3_attacker.sh all  [count] [interval]"
    exit 1
fi

if [ ! -f "${SCRIPT_DIR}/hping3_attack.sh" ]; then
    echo "[ERROR] scripts/hping3_attack.sh not found."
    exit 1
fi

if ! docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
    echo "[ERROR] Docker image ${IMAGE_NAME} not found."
    echo "Build it first:"
    echo "  docker build -t iot-hping3-attacker -f scripts/Dockerfile.hping3 ."
    exit 1
fi

NETWORK_NAME=$(docker inspect rest_api --format '{{range $name, $conf := .NetworkSettings.Networks}}{{$name}}{{end}}' 2>/dev/null)

if [ -z "$NETWORK_NAME" ]; then
    echo "[ERROR] Could not detect Docker network from rest_api container."
    echo "Make sure containers are running:"
    echo "  docker compose up -d"
    exit 1
fi

docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

echo "============================================================"
echo "HPING3 ATTACKER CONTAINER"
echo "============================================================"
echo "Docker network : ${NETWORK_NAME}"
echo "Target         : ${TARGET}"
echo "Count          : ${COUNT}"
echo "Interval       : ${INTERVAL}"
echo "Image          : ${IMAGE_NAME}"
echo "============================================================"

docker run --rm -it \
    --name "${CONTAINER_NAME}" \
    --network "${NETWORK_NAME}" \
    --cap-add=NET_RAW \
    --cap-add=NET_ADMIN \
    -v "${SCRIPT_DIR}:/scripts" \
    "${IMAGE_NAME}" bash -c "
        chmod +x ${ATTACK_SCRIPT}
        ${ATTACK_SCRIPT} ${TARGET} ${COUNT} ${INTERVAL}
    "
