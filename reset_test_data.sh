#!/bin/bash

echo "=== Reset InfluxDB measurements ==="
docker exec influxdb influx -database iot_data -execute 'DROP MEASUREMENT "protocol_metrics"'
docker exec influxdb influx -database iot_data -execute 'DROP MEASUREMENT "snort_alerts"'

echo "=== Clear Snort alert_fast.txt logs ==="
docker exec snort_mqtt sh -c "truncate -s 0 /var/log/snort/alert_fast.txt"
docker exec snort_rest sh -c "truncate -s 0 /var/log/snort/alert_fast.txt"
docker exec snort_coap sh -c "truncate -s 0 /var/log/snort/alert_fast.txt"
docker exec snort_grpc sh -c "truncate -s 0 /var/log/snort/alert_fast.txt"

echo "=== Restart related services ==="
docker restart telegraf django_app snort_mqtt snort_rest snort_coap snort_grpc

echo "=== Done. Test data has been reset. ==="
