import argparse
import random
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

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

# ============================
# GLOBAL COUNTERS
# ============================
count_success = 0
count_error = 0
last_rtt_ms = 0.0

counter_lock = Lock()
rtt_lock = Lock()

start_time = time.time()


# ============================
# SHARED CHANNEL
# ============================
channel = grpc.insecure_channel(GRPC_TARGET)
stub = grpc_pb2_grpc.SensorServiceStub(channel)

def get_last_rtt_ms():
    with rtt_lock:
        return last_rtt_ms


def update_last_rtt_ms(value):
    global last_rtt_ms
    with rtt_lock:
        last_rtt_ms = value


def increment_success():
    global count_success
    with counter_lock:
        count_success += 1


def increment_error():
    global count_error
    with counter_lock:
        count_error += 1


def get_counts():
    with counter_lock:
        return count_success, count_error

def send_request():
    previous_rtt_ms = get_last_rtt_ms()

    request = grpc_pb2.SensorRequest(
        device_id="grpc_flood_client",
        temperature=round(random.uniform(25.0, 35.0), 2),
        humidity=round(random.uniform(55.0, 75.0), 2),
        timestamp=int(time.time()),

        # RTT dari request sebelumnya dikirim ke server
        rtt_ms=round(previous_rtt_ms, 2)
    )

    try:
        request_start = time.time()

        stub.SendSensorData(request, timeout=3)

        request_end = time.time()
        current_rtt_ms = (request_end - request_start) * 1000
        update_last_rtt_ms(current_rtt_ms)

        increment_success()

    except Exception:
        increment_error()


def unlimited_worker():
    while True:
        send_request()


print("[GRPC FLOOD] Started")
print(f"Target   : {GRPC_TARGET}")
print(f"Rate     : {'unlimited' if RATE == 0 else str(RATE) + ' req/s'}")
print(f"Duration : {'unlimited' if DURATION == 0 else str(DURATION) + ' seconds'}")
print(f"Workers  : {WORKERS}")
print("Mode     : Client-side RTT via protobuf rtt_ms")
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
                success, error = get_counts()
                total = success + error
                avg_rate = total / elapsed if elapsed > 0 else 0
                current_rtt = get_last_rtt_ms()

                print(
                    f"[GRPC FLOOD] total={total} | success={success} | "
                    f"error={error} | avg_rate={avg_rate:.2f} req/s | "
                    f"last_rtt={current_rtt:.2f} ms",
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

                success, error = get_counts()
                total = success + error

                if total > 0 and total % 100 == 0:
                    elapsed = time.time() - start_time
                    avg_rate = total / elapsed if elapsed > 0 else 0
                    current_rtt = get_last_rtt_ms()

                    print(
                        f"[GRPC FLOOD] total={total} | success={success} | "
                        f"error={error} | avg_rate={avg_rate:.2f} req/s | "
                        f"last_rtt={current_rtt:.2f} ms",
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
    success, error = get_counts()
    total = success + error
    avg_rate = total / elapsed if elapsed > 0 else 0
    current_rtt = get_last_rtt_ms()

    print(
        f"[GRPC FLOOD] Total={total} | success={success} | "
        f"error={error} | elapsed={elapsed:.2f}s | "
        f"avg_rate={avg_rate:.2f} req/s | last_rtt={current_rtt:.2f} ms"
    )

    channel.close()