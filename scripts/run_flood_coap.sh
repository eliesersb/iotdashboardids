#!/usr/bin/env bash
set -e
echo "=== CoAP Application Flood ==="
echo "Press CTRL+C to stop if script runs unlimited."
python3 coap_flood.py "$@"
