#!/usr/bin/env bash
set -e

echo "=== Starting IoT Dashboard IDS System ==="
docker compose up -d --build --remove-orphans --remove-orphans

echo
echo "=== Container Status ==="
docker compose ps

echo
echo "=== Dashboard URL ==="
echo "Django Dashboard: http://localhost:8000"

echo
echo "=== Important Services ==="
docker compose config --services
