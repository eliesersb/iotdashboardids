from flask import Flask, jsonify, request
from influxdb import InfluxDBClient
import time
import random

app = Flask(__name__)

# ============================
# INFLUXDB CONFIG
# ============================
INFLUX_HOST = "influxdb"
INFLUX_PORT = 8086
INFLUX_DB = "iot_data"
INFLUX_USER = "admin"
INFLUX_PASSWORD = "admin123"

client = InfluxDBClient(
    host=INFLUX_HOST,
    port=INFLUX_PORT,
    username=INFLUX_USER,
    password=INFLUX_PASSWORD,
    database=INFLUX_DB
)

# ============================
# DUMMY DEVICE DATA
# Tetap dipertahankan untuk kompatibilitas endpoint lama /devices
# ============================
devices = [
    {"id": 1, "name": "sensor1", "location": "lab"},
    {"id": 2, "name": "sensor2", "location": "kelas"}
]


# ============================
# REQUEST TIMER
# ============================
@app.before_request
def start_timer():
    request.start_time = time.time()


# ============================
# LOG REST METRICS TO INFLUXDB
# Measurement: protocol_metrics
# ============================
@app.after_request
def log_request_to_influx(response):
    try:
        server_processing_ms = float((time.time() - request.start_time) * 1000)

        # Ambil RTT dari client jika tersedia.
        # Header ini dikirim oleh rest_client.py / rest_flood.py.
        client_rtt_ms = request.headers.get("X-Client-RTT-Ms")

        try:
            latency_ms = float(client_rtt_ms) if client_rtt_ms is not None else server_processing_ms
        except Exception:
            latency_ms = server_processing_ms

        method = request.method
        status_code = response.status_code

        # Hitung ukuran payload REST dalam bytes
        # Untuk REST, payload yang dihitung adalah ukuran response body.
        response_body = response.get_data() or b""
        payload_size_bytes = len(response_body)

        # Ambil traffic_type dari header.
        # Normal client: X-Traffic-Type: normal
        # Flood client : X-Traffic-Type: attack
        traffic_type = request.headers.get("X-Traffic-Type", "normal").lower()

        # Ambil src dari header supaya lebih rapi di InfluxDB.
        # Kalau header tidak ada, fallback ke IP client.
        src = request.headers.get("X-Client-Name")
        if not src:
            src_ip = request.remote_addr if request.remote_addr else "unknown"
            src = src_ip

        # Standarisasi src jika belum dikirim dari client
        if src == "unknown" or src.replace(".", "").isdigit():
            if traffic_type == "attack":
                src = "rest_flood_client"
            else:
                src = "rest_normal_client"

        # Endpoint diseragamkan untuk pengujian utama
        # Walaupun request lama ke /devices tetap berjalan,
        # data utama TA diarahkan ke /sensor/temp.
        endpoint = "/sensor/temp" if request.path == "/sensor/temp" else request.path

        # Field sensor dibuat tersedia untuk REST juga,
        # supaya sama dengan MQTT, CoAP, dan gRPC.
        temperature = None
        humidity = None

        if request.is_json:
            body = request.get_json(silent=True) or {}
            temperature = body.get("temperature")
            humidity = body.get("humidity")

        if temperature is None:
            temperature = round(random.uniform(25.0, 35.0), 2)

        if humidity is None:
            humidity = round(random.uniform(55.0, 75.0), 2)

        print(
            f"[REST DEBUG] traffic_type={traffic_type} | "
            f"src={src} | client_rtt_ms={client_rtt_ms} | "
            f"latency_ms={latency_ms} | payload_size_bytes={payload_size_bytes}",
            flush=True
        )    

        json_body = [
            {
                "measurement": "protocol_metrics",
                "tags": {
                    "protocol": "rest",
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": str(status_code),
                    "src": src,
                    "traffic_type": traffic_type
                },
                "fields": {
                    "temperature": float(temperature),
                    "humidity": float(humidity),
                    "request_count": 1,
                    "latency_ms": float(latency_ms),
                    "payload_size_bytes": float(payload_size_bytes)
                }
            }
        ]

        client.write_points(json_body)

    except Exception as e:
        print("Gagal kirim metrik REST ke InfluxDB:", e, flush=True)

    return response


# ============================
# HEALTH CHECK
# ============================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "REST API is running"}), 200


# ============================
# ENDPOINT UTAMA UNTUK TA
# REST SENSOR DATA
# ============================
@app.route("/sensor/temp", methods=["GET"])
def get_sensor_temp():
    temperature = round(random.uniform(25.0, 35.0), 2)
    humidity = round(random.uniform(55.0, 75.0), 2)

    return jsonify({
        "protocol": "rest",
        "endpoint": "/sensor/temp",
        "temperature": temperature,
        "humidity": humidity,
        "message": "REST sensor data retrieved successfully"
    }), 200


@app.route("/sensor/temp", methods=["POST"])
def post_sensor_temp():
    data = request.get_json(silent=True) or {}

    temperature = data.get("temperature", round(random.uniform(25.0, 35.0), 2))
    humidity = data.get("humidity", round(random.uniform(55.0, 75.0), 2))

    return jsonify({
        "protocol": "rest",
        "endpoint": "/sensor/temp",
        "temperature": temperature,
        "humidity": humidity,
        "message": "REST sensor data received successfully"
    }), 200


# ============================
# ENDPOINT LAMA
# Tetap dipertahankan agar script lama tidak langsung rusak
# ============================
@app.route("/devices", methods=["GET"])
def get_devices():
    return jsonify(devices), 200


@app.route("/devices", methods=["POST"])
def add_device():
    data = request.get_json() or {}

    new_device = {
        "id": len(devices) + 1,
        "name": data.get("name", "unknown"),
        "location": data.get("location", "unknown")
    }

    devices.append(new_device)

    return jsonify({
        "message": "Device added successfully",
        "device": new_device
    }), 201


# ============================
# MAIN
# ============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)