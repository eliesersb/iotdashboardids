#!/usr/bin/env bash
set -e
echo "=== REST API Application Flood ==="
echo "Press CTRL+C to stop if script runs unlimited."
python3 rest_flood.py "$@"
