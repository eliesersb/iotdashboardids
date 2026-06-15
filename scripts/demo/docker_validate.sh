#!/bin/bash

cd "$(dirname "$0")/../.."

echo ""
echo "===== CEK CONTAINER ====="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "===== DATA TERBARU protocol_metrics ====="
docker exec -it influxdb influx -database iot_data -execute 'SELECT protocol, traffic_type, request_count, latency_ms, src FROM protocol_metrics ORDER BY time DESC LIMIT 20' || true

echo ""
echo "===== RINGKASAN TRAFFIC protocol_metrics ====="
docker exec -it influxdb influx -database iot_data -execute 'SELECT SUM(request_count) FROM protocol_metrics GROUP BY protocol, traffic_type' || true

echo ""
echo "===== ALERT TERBARU snort_alerts ====="
docker exec -it influxdb influx -database iot_data -execute 'SELECT msg, sid, src_ip, dst_ip, dst_port FROM snort_alerts ORDER BY time DESC LIMIT 20' || true

echo ""
echo "===== LOG SNORT alert_fast.txt ====="
tail -30 snort/log/alert_fast.txt || true
