#!/usr/bin/env bash
set -e

echo "=== Stopping IoT Dashboard IDS System ==="
docker compose down

echo
echo "System stopped. Docker volumes are kept."
echo "Use 'docker compose down -v' only if you want to delete volumes."
