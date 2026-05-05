import argparse
import random
import time
from concurrent.futures import ThreadPoolExecutor

import grpc

import grpc_pb2
import grpc_pb2_grpc


# ============================
# ARGUMENTS
# ============================
parser = argparse.ArgumentParser(description="gRPC Flood Client for IoT Security Monitoring TA")
parser.add_argument("--rate", type=float, default=100, help="Target request per second. Use 0 for unlimited.")
parser.add_argument("--duration", type=float, default=0, help="Duration in seconds. Use 0 for unlimited until CTRL+C.")
parser.add_argument("--workers", type=int, default=50, help="Number of worker threads.")
args = parser.parse_args()


# ============================
# CONFIG
# ============================
GRPC_TARGET = "localhost:50051"

RATE = args.rate
DURATION = args.duration
WORKERS = args.workers

count_success = 0
count_error = 0
start_time = time.time()


# ============================
# SHARED CHANNEL
# ============================
channel = grpc.insecure_channel(GRPC_TARGET)
stub = grpc_pb2_grpc.SensorServiceStub(channel)


def send_request():
    global count_success, count_error

    request = grpc_pb2.SensorRequest(
        device_id="grpc_flood_client",
        temperature=round(random.uniform(25.0, 35.0), 2),
        humidity=round(random.uniform(55.0, 75.0), 2),
        timestamp=int(time.time())
    )

    try:
        stub.SendSensorData(request, timeout=3)
        count_success += 1

    except Exception:
        count_error += 1


def unlimited_worker():
    while True:
        send_request()


print("[GRPC FLOOD] Started")
print(f"Target   : {GRPC_TARGET}")
print(f"Rate     : {'unlimited' if RATE == 0 else str(RATE) + ' req/s'}")
print(f"Duration : {'unlimited' if DURATION == 0 else str(DURATION) + ' seconds'}")
print(f"Workers  : {WORKERS}")
print("Stop     : CTRL + C")

try:
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        if RATE == 0:
            # Mode unlimited: semua worker loop tanpa henti
            for _ in range(WORKERS):
                executor.submit(unlimited_worker)

            while True:
                time.sleep(1)

                elapsed = time.time() - start_time
                total = count_success + count_error
                avg_rate = total / elapsed if elapsed > 0 else 0

                print(
                    f"[GRPC FLOOD] total={total} | success={count_success} | "
                    f"error={count_error} | avg_rate={avg_rate:.2f} req/s",
                    flush=True
                )

        else:
            # Mode rate-controlled
            next_send_time = time.time()

            while True:
                now = time.time()

                if DURATION > 0 and (now - start_time) >= DURATION:
                    break

                executor.submit(send_request)

                total = count_success + count_error
                if total > 0 and total % 100 == 0:
                    elapsed = time.time() - start_time
                    avg_rate = total / elapsed if elapsed > 0 else 0

                    print(
                        f"[GRPC FLOOD] total={total} | success={count_success} | "
                        f"error={count_error} | avg_rate={avg_rate:.2f} req/s",
                        flush=True
                    )

                next_send_time += 1.0 / RATE
                sleep_time = next_send_time - time.time()

                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    next_send_time = time.time()

except KeyboardInterrupt:
    print("\n[GRPC FLOOD] Stopped by user")

finally:
    elapsed = time.time() - start_time
    total = count_success + count_error
    avg_rate = total / elapsed if elapsed > 0 else 0

    print(
        f"[GRPC FLOOD] Total={total} | success={count_success} | "
        f"error={count_error} | elapsed={elapsed:.2f}s | avg_rate={avg_rate:.2f} req/s"
    )

    channel.close()