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
        latency_ms = float((time.time() - request.start_time) * 1000)

        method = request.method
        status_code = response.status_code

        # Ambil traffic_type dari header.
        # Normal client: X-Traffic-Type: normal
        # Flood client : X-Traffic-Type: attack
        traffic_type = request.headers.get("X-Traffic-Type", "normal").lower()

        # Ambil src dari header supaya lebih rapi di Grafana/InfluxDB.
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
                    "latency_ms": float(latency_ms)
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