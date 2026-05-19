import time
import random
import grpc

import grpc_pb2
import grpc_pb2_grpc

# ============================
# GRPC NORMAL CLIENT
# ============================
GRPC_TARGET = "localhost:50051"
INTERVAL_SECONDS = 5

def run():
    channel = grpc.insecure_channel(GRPC_TARGET)
    stub = grpc_pb2_grpc.SensorServiceStub(channel)

    last_rtt_ms = 0.0

    print("[GRPC NORMAL] Started")
    print(f"Target   : {GRPC_TARGET}")
    print(f"Interval : {INTERVAL_SECONDS} seconds")
    print("Stop     : CTRL + C")

    try:
        while True:
            request = grpc_pb2.SensorRequest(
                device_id="grpc_normal_client",
                temperature=round(random.uniform(26, 29), 2),
                humidity=round(random.uniform(55, 65), 2),
                timestamp=int(time.time()),

                # RTT dari request sebelumnya dikirim ke server
                rtt_ms=round(last_rtt_ms, 2)
        )

            try:
                print("[GRPC NORMAL] Sending request...")

                start_time = time.time()

                response = stub.SendSensorData(request, timeout=5)

                end_time = time.time()
                last_rtt_ms = (end_time - start_time) * 1000

                print(
                    f"[GRPC NORMAL] status={response.status} | "
                    f"RTT={last_rtt_ms:.2f} ms | "
                    f"sent_previous_rtt={request.rtt_ms} ms",
                    flush=True
                )
            
            except Exception as e:
                print(f"[GRPC NORMAL ERROR] {e}", flush=True)

            time.sleep(INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n[GRPC NORMAL] Stopped by user")
    
    finally:
        channel.close()

if __name__ == "__main__":
    run()