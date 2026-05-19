#!/bin/bash

MODE="$1"
RULE_FILE="snort/rules/local.rules"

if [ -z "$MODE" ]; then
  echo "Gunakan:"
  echo "  ./switch_snort_rules.sh app"
  echo "  ./switch_snort_rules.sh hping"
  exit 1
fi

cp "$RULE_FILE" "$RULE_FILE.bak_switch_$(date +%Y%m%d_%H%M%S)"

if [ "$MODE" = "app" ]; then
cat > "$RULE_FILE" <<'RULES'
# ============================
# LOCAL SNORT RULES - APPLICATION FLOOD MODE
# Digunakan untuk pengujian mqtt_flood.py, rest_flood.py, coap_flood.py, grpc_flood.py
# ============================

alert tcp any any -> any 1883 (
    msg:"MQTT Application Flood Detected";
    content:"sensor/temp";
    detection_filter:track by_src,count 15,seconds 5;
    sid:1000004;
    rev:10;
)

alert tcp any any -> any 5000 (
    msg:"REST Application Flood Detected";
    flow:to_server,established;
    detection_filter:track by_src,count 30,seconds 5;
    sid:1000005;
    rev:20;
)

alert udp any any -> any 5683 (
    msg:"CoAP Application Flood Detected";
    content:"sensor";
    content:"temp";
    detection_filter:track by_src,count 15,seconds 5;
    sid:1000006;
    rev:10;
)

alert tcp any any -> any 50051 (
    msg:"gRPC Application Flood Detected";
    flow:to_server,established;
    detection_filter:track by_src,count 30,seconds 5;
    sid:1000007;
    rev:20;
)
RULES

elif [ "$MODE" = "hping" ]; then
cat > "$RULE_FILE" <<'RULES'
# ============================
# LOCAL SNORT RULES - HPING3 / NETWORK FLOOD MODE
# Digunakan untuk pengujian hping3 MQTT, REST API, CoAP, dan gRPC
# ============================

alert tcp any any -> any 1883 (
    msg:"MQTT TCP SYN Flood / hping3 Detected";
    flags:S;
    detection_filter:track by_src,count 15,seconds 5;
    sid:1000014;
    rev:10;
)

alert tcp any any -> any 5000 (
    msg:"REST TCP SYN Flood / hping3 Detected";
    flags:S;
    detection_filter:track by_src,count 15,seconds 5;
    sid:1000015;
    rev:10;
)

alert udp any any -> any 5683 (
    msg:"CoAP UDP Flood / hping3 Detected";
    detection_filter:track by_src,count 30,seconds 5;
    sid:1000016;
    rev:10;
)

alert tcp any any -> any 50051 (
    msg:"gRPC TCP SYN Flood / hping3 Detected";
    flags:S;
    detection_filter:track by_src,count 15,seconds 5;
    sid:1000017;
    rev:10;
)
RULES

else
  echo "Mode tidak dikenal: $MODE"
  echo "Gunakan: app atau hping"
  exit 1
fi

echo "Mode Snort rules diganti ke: $MODE"
docker compose restart snort_mqtt snort_rest snort_coap snort_grpc telegraf django_app
echo "Restart selesai."
