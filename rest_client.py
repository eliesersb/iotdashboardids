import requests
import time

# ============================
# REST NORMAL CLIENT
# ============================
BASE_URL = "http://localhost:5000"
ENDPOINT = "/sensor/temp"
URL = f"{BASE_URL}{ENDPOINT}"

INTERVAL_SECONDS = 5

last_rtt_ms = 0.0

print("[REST NORMAL] Started")
print(f"URL      : {URL}")
print(f"Interval : {INTERVAL_SECONDS} seconds")
print("Stop     : CTRL + C")

try:
    while True:
        headers = {
            "X-Traffic-Type": "normal",
            "X-Client-Name": "rest_normal_client",
            "X-Client-RTT-Ms": str(round(last_rtt_ms, 2))
        }

        try:
            print("[REST NORMAL] Sending request...")

            start_time = time.time()

            response = requests.get(
                URL,
                headers=headers,
                timeout=5
            )

            end_time = time.time()
            last_rtt_ms = (end_time - start_time) * 1000

            print("[REST NORMAL]")
            print("Status:", response.status_code)
            print(f"RTT: {last_rtt_ms:.2f} ms")
            print(f"Sent previous RTT: {headers['X-Client-RTT-Ms']} ms")

            try:
                print("Response:", response.json())
            except Exception:
                print("Response:", response.text)

        except Exception as e:
            print("[REST NORMAL ERROR]", e)

        time.sleep(INTERVAL_SECONDS)

except KeyboardInterrupt:
    print("\n[REST NORMAL] Stopped by user")