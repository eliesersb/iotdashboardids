import asyncio
import json
import time
import random

import aiocoap
import aiocoap.resource as resource
from influxdb import InfluxDBClient


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
# COAP SENSOR RESOURCE
# Endpoint: /sensor/temp
# ============================
class SensorResource(resource.Resource):
    async def render_get(self, request):
        start_time = time.time()

        # Deteksi traffic type dari query URI
        # Normal : coap://localhost:5683/sensor/temp
        # Attack : coap://localhost:5683/sensor/temp?attack
        uri_query = request.opt.uri_query
        traffic_type = "attack" if any("attack" in item for item in uri_query) else "normal"

        # Ambil RTT dari client jika tersedia
        client_rtt_ms = None

        for query_item in uri_query:
            if query_item.startswith("rtt_ms="):
                try:
                    client_rtt_ms = float(query_item.split("=", 1)[1])
                except Exception:
                    client_rtt_ms = None

        if traffic_type == "attack":
            src = "coap_flood_client"
        else:
            src = "coap_normal_client"

        temperature = round(random.uniform(25.0, 35.0), 2)
        humidity = round(random.uniform(55.0, 75.0), 2)

        server_processing_ms = float((time.time() - start_time) * 1000)
        latency_ms = client_rtt_ms if client_rtt_ms is not None else server_processing_ms
        
        payload = {
            "protocol": "coap",
            "endpoint": "/sensor/temp",
            "traffic_type": traffic_type,
            "src": src,
            "temperature": temperature,
            "humidity": humidity,
            "latency_ms": round(latency_ms, 2)
        }

        # Hitung ukuran payload CoAP response dalam bytes
        response_payload_bytes = json.dumps(payload).encode("utf-8")
        payload_size_bytes = len(response_payload_bytes)

        try:
            json_body = [
                {
                    "measurement": "protocol_metrics",
                    "tags": {
                        "protocol": "coap",
                        "endpoint": "/sensor/temp",
                        "src": src,
                        "traffic_type": traffic_type
                    },
                    "fields": {
                        "temperature": float(temperature),
                        "humidity": float(humidity),
                        "latency_ms": float(latency_ms),
                        "payload_size_bytes": float(payload_size_bytes),
                        "request_count": 1
                    }
                }
            ]

            client.write_points(json_body)

            print(
                f"[COAP] written to InfluxDB | "
                f"traffic_type={traffic_type} | src={src} | "
                f"temperature={temperature} | humidity={humidity} | "
                f"client_rtt_ms={client_rtt_ms} | "
                f"latency_ms={round(latency_ms, 2)} |" 
                f"payload_size_bytes={payload_size_bytes}",
                flush=True
            )

        except Exception as e:
            print("[COAP ERROR] Gagal kirim metrik ke InfluxDB:", e, flush=True)

        return aiocoap.Message(
            payload=response_payload_bytes,
            content_format=50
        )


# ============================
# MAIN SERVER
# ============================
def main():
    root = resource.Site()
    root.add_resource(["sensor", "temp"], SensorResource())

    asyncio.Task(
        aiocoap.Context.create_server_context(
            root,
            bind=("0.0.0.0", 5683)
        )
    )

    print("CoAP server running on port 5683", flush=True)
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()