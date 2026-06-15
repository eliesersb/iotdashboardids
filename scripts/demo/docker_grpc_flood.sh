#!/bin/bash
DURATION=${1:-15}
RATE=${2:-100}

echo "[DOCKER gRPC FLOOD] duration=${DURATION}s rate=${RATE}"
docker compose --profile tools run --rm attacker python grpc_flood.py --duration "$DURATION" --rate "$RATE"
echo "[DOCKER gRPC FLOOD] Finished"
