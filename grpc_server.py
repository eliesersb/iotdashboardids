import time
import grpc
import requests
from concurrent import futures

import grpc_pb2
import grpc_pb2_grpc


# ============================
# TELEGRAF CONFIG
# ============================
TELEGRAF_URL = "http://telegraf:8186/write"


# ============================
# GRPC SENSOR SERVICE
# ============================
class SensorService(grpc_pb2_grpc.SensorServiceServicer):
    def SendSensorData(self, request, context):
        start_time = time.time()

        try:
            latency_ms = float((time.time() - start_time) * 1000)

            device_id = request.device_id

            if "attack" in device_id or "attacker" in device_id or "flood" in device_id:
                traffic_type = "attack"
                src = "grpc_flood_client"
            else:
                traffic_type = "normal"
                src = "grpc_normal_client"

            temperature = float(request.temperature)
            humidity = float(request.humidity)

            # Measurement: protocol_metrics
            # Tags: protocol, traffic_type, src, endpoint
            # Fields: temperature, humidity, latency_ms, request_count
            line = (
                f"protocol_metrics,"
                f"protocol=grpc,"
                f"traffic_type={traffic_type},"
                f"src={src},"
                f"endpoint=/sensor/temp "
                f"temperature={temperature},"
                f"humidity={humidity},"
                f"latency_ms={latency_ms},"
                f"request_count=1i"
            )

            response = requests.post(
                TELEGRAF_URL,
                data=line,
                headers={"Content-Type": "text/plain"},
                timeout=3
            )

            print(
                f"[GRPC] written to Telegraf | "
                f"status={response.status_code} | "
                f"traffic_type={traffic_type} | src={src} | "
                f"temperature={temperature} | humidity={humidity} | "
                f"latency_ms={round(latency_ms, 2)}",
                flush=True
            )

        except Exception as e:
            print(f"[GRPC ERROR] gagal kirim ke Telegraf: {e}", flush=True)

        return grpc_pb2.SensorReply(
            status="OK",
            message="Data diterima oleh gRPC server"
        )


# ============================
# MAIN SERVER
# ============================
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=50))
    grpc_pb2_grpc.add_SensorServiceServicer_to_server(SensorService(), server)

    server.add_insecure_port("[::]:50051")
    server.start()

    print("gRPC server running on port 50051", flush=True)

    server.wait_for_termination()


if __name__ == "__main__":
    serve()