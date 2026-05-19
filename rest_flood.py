import argparse
import random
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import requests


# ============================
# ARGUMENTS
# ============================
parser = argparse.ArgumentParser(description="REST Flood Client for IoT Security Monitoring TA")
parser.add_argument("--rate", type=float, default=100, help="Target request per second. Use 0 for unlimited.")
parser.add_argument("--duration", type=float, default=0, help="Duration in seconds. Use 0 for unlimited until CTRL+C.")
parser.add_argument("--workers", type=int, default=50, help="Number of worker threads.")
args = parser.parse_args()


# ============================
# CONFIG
# ============================
BASE_URL = "http://localhost:5000"
ENDPOINT = "/sensor/temp"
URL = f"{BASE_URL}{ENDPOINT}"

RATE = args.rate
DURATION = args.duration
WORKERS = args.workers

HEADERS = {
    "X-Traffic-Type": "attack",
    "X-Client-Name": "rest_flood_client"
}


# ============================
# GLOBAL COUNTERS
# ============================
count_success = 0
count_error = 0
last_rtt_ms = 0.0

counter_lock = Lock()
rtt_lock = Lock()

start_time = time.time()

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

def get_total_count():
    with counter_lock:
        return count_success + count_error, count_success, count_error

def send_request():

    payload = {
        "temperature": round(random.uniform(25.0, 35.0), 2),
        "humidity": round(random.uniform(55.0, 75.0), 2)
    }

    previous_rtt_ms = get_last_rtt_ms()

    headers = {
        "X-Traffic-Type": "attack",
        "X-Client-Name": "rest_flood_client",

        # RTT dari request sebelumnya dikirim ke REST server
        "X-Client-RTT-Ms": str(round(previous_rtt_ms, 2))
    }

    try:
        request_start = time.time()

        response = requests.post(
            URL,
            json=payload,
            headers=headers,
            timeout=3
        )

        request_end = time.time()
        current_rtt_ms = (request_end - request_start) * 1000
        update_last_rtt_ms(current_rtt_ms)

        if response.status_code < 500:
            increment_success()
        else:
            increment_error()

    except Exception:
        increment_error()


def unlimited_worker():
    while True:
        send_request()


print("[REST FLOOD] Started")
print(f"URL      : {URL}")
print(f"Rate     : {'unlimited' if RATE == 0 else str(RATE) + ' req/s'}")
print(f"Duration : {'unlimited' if DURATION == 0 else str(DURATION) + ' seconds'}")
print(f"Workers  : {WORKERS}")
print("Mode     : Client-side RTT via X-Client-RTT-Ms")
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
                total, success, error = get_total_count()
                avg_rate = total / elapsed if elapsed > 0 else 0
                current_rtt = get_last_rtt_ms()

                print(
                    f"[REST FLOOD] total={total} | success={success} | "
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

                total, success, error = get_total_count()
                if total > 0 and total % 100 == 0:
                    elapsed = time.time() - start_time
                    avg_rate = total / elapsed if elapsed > 0 else 0
                    current_rtt = get_last_rtt_ms()

                    print(
                        f"[REST FLOOD] total={total} | success={success} | "
                        f"error={error} | avg_rate={avg_rate:.2f} req/s | "
                        f"last_rtt={current_rtt:.2f} ms ",
                        flush=True
                    )

                next_send_time += 1.0 / RATE
                sleep_time = next_send_time - time.time()

                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    next_send_time = time.time()

except KeyboardInterrupt:
    print("\n[REST FLOOD] Stopped by user")

finally:
    elapsed = time.time() - start_time
    total, success, error = get_total_count()
    avg_rate = total / elapsed if elapsed > 0 else 0
    current_rtt = get_last_rtt_ms()

    print(
        f"[REST FLOOD] Total={total} | success={success} | "
        f"error={error} | elapsed={elapsed:.2f}s | "
        f"avg_rate={avg_rate:.2f} req/s | last_rtt={current_rtt:.2f} ms",
        flush=True  
    )