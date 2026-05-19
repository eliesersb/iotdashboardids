#!/usr/bin/env bash
set -e
echo "=== MQTT Application Flood ==="
echo "Press CTRL+C to stop if script runs unlimited."
python3 mqtt_flood.py "$@"
