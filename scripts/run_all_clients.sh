#!/usr/bin/env bash
set -e

echo "=== Running all normal clients in background ==="

python3 mqtt_client.py > /tmp/mqtt_client.log 2>&1 &
echo $! > /tmp/mqtt_client.pid
echo "MQTT normal client started. PID: $(cat /tmp/mqtt_client.pid)"

python3 rest_client.py > /tmp/rest_client.log 2>&1 &
echo $! > /tmp/rest_client.pid
echo "REST normal client started. PID: $(cat /tmp/rest_client.pid)"

python3 coap_client.py > /tmp/coap_client.log 2>&1 &
echo $! > /tmp/coap_client.pid
echo "CoAP normal client started. PID: $(cat /tmp/coap_client.pid)"

python3 grpc_client.py > /tmp/grpc_client.log 2>&1 &
echo $! > /tmp/grpc_client.pid
echo "gRPC normal client started. PID: $(cat /tmp/grpc_client.pid)"

echo
echo "All normal clients are running in background."
echo "Stop them with: bash scripts/stop_all_clients.sh"
