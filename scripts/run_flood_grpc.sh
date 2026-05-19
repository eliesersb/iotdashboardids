#!/usr/bin/env bash
set -e
echo "=== gRPC Application Flood ==="
echo "Press CTRL+C to stop if script runs unlimited."
python3 grpc_flood.py "$@"
