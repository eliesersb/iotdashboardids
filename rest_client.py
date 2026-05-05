import requests
import time

# ============================
# REST NORMAL CLIENT
# ============================
BASE_URL = "http://localhost:5000"
ENDPOINT = "/sensor/temp"

INTERVAL_SECONDS = 5

headers = {
    "X-Traffic-Type": "normal",
    "X-Client-Name": "rest_normal_client"
}

while True:
    try:
        response = requests.get(
            f"{BASE_URL}{ENDPOINT}",
            headers=headers,
            timeout=5
        )

        print("[REST NORMAL]")
        print("Status:", response.status_code)
        print("Response:", response.json())

    except Exception as e:
        print("[REST NORMAL ERROR]", e)

    time.sleep(INTERVAL_SECONDS)