#!/usr/bin/env bash
set -e

DURATION="${1:-10}"
INTERVAL="${INTERVAL:-u10000}"
NETWORK="${NETWORK:-iotdashboardids_iot-net}"
TARGET="${TARGET:-grpc_server}"
PORT="${PORT:-50051}"

echo "[gRPC HPING3] Target=${TARGET}:${PORT}, Duration=${DURATION}s, Interval=${INTERVAL}, Network=${NETWORK}"

docker run --rm \
  --network "${NETWORK}" \
  --cap-add NET_RAW \
  --cap-add NET_ADMIN \
  debian:bookworm-slim \
  sh -c "apt-get update -qq && apt-get install -y -qq hping3 iputils-ping >/dev/null && timeout ${DURATION} hping3 -S -p ${PORT} -i ${INTERVAL} ${TARGET} || true"
