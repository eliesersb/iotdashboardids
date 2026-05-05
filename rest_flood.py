import argparse
import random
import time
from concurrent.futures import ThreadPoolExecutor

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
start_time = time.time()


def send_request():
    global count_success, count_error

    payload = {
        "temperature": round(random.uniform(25.0, 35.0), 2),
        "humidity": round(random.uniform(55.0, 75.0), 2)
    }

    try:
        response = requests.post(
            URL,
            json=payload,
            headers=HEADERS,
            timeout=3
        )

        if response.status_code < 500:
            count_success += 1
        else:
            count_error += 1

    except Exception:
        count_error += 1


def unlimited_worker():
    while True:
        send_request()


print("[REST FLOOD] Started")
print(f"URL      : {URL}")
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
                    f"[REST FLOOD] total={total} | success={count_success} | "
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
                        f"[REST FLOOD] total={total} | success={count_success} | "
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
    print("\n[REST FLOOD] Stopped by user")

finally:
    elapsed = time.time() - start_time
    total = count_success + count_error
    avg_rate = total / elapsed if elapsed > 0 else 0

    print(
        f"[REST FLOOD] Total={total} | success={count_success} | "
        f"error={count_error} | elapsed={elapsed:.2f}s | avg_rate={avg_rate:.2f} req/s"
    )