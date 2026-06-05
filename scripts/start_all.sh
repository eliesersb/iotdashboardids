#!/usr/bin/env bash
set -e

echo "[1/5] Preparing Snort log directory..."
mkdir -p snort/log
touch snort/log/alert_fast.txt
chmod -R 777 snort/log 2>/dev/null || sudo chmod -R 777 snort/log

echo "[2/5] Starting Docker Compose services..."
docker compose up -d

echo "[3/5] Ensuring Snort log permission after containers started..."
mkdir -p snort/log
touch snort/log/alert_fast.txt
chmod -R 777 snort/log 2>/dev/null || sudo chmod -R 777 snort/log

echo "[4/5] Restarting Telegraf and Django..."
docker compose restart telegraf django_app

echo "[5/5] Current container status:"
docker compose ps

echo "Done. Dashboard: http://localhost:8000/"
