import time
import random
import grpc

import grpc_pb2
import grpc_pb2_grpc


def run():
    channel = grpc.insecure_channel("localhost:50051")
    stub = grpc_pb2_grpc.SensorServiceStub(channel)

    while True:
        request = grpc_pb2.SensorRequest(
            device_id="grpc_normal_client",
            temperature=round(random.uniform(26, 29), 2),
            humidity=round(random.uniform(55, 65), 2),
            timestamp=int(time.time())
        )

        try:
            response = stub.SendSensorData(request)
            print(f"[NORMAL] {response.status}", flush=True)
        except Exception as e:
            print(f"[ERROR] {e}", flush=True)

        time.sleep(5)


if __name__ == "__main__":
    run()