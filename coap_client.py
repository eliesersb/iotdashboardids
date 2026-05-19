import asyncio
import json
import time
from aiocoap import *


# ============================
# COAP NORMAL CLIENT
# ============================
BASE_COAP_URL = "coap://localhost:5683/sensor/temp"
INTERVAL_SECONDS = 5

last_rtt_ms = 0.0

async def main():
    global last_rtt_ms

    protocol = await Context.create_client_context()

    print("[COAP NORMAL] Started")
    print(f"URL      : {BASE_COAP_URL}")
    print(f"Interval : {INTERVAL_SECONDS} seconds")
    print("Stop     : CTRL + C")

    while True:
        try:
            # RTT request sebelumnya dikirim ke server
            coap_url = f"{BASE_COAP_URL}?rtt_ms={round(last_rtt_ms, 2)}"

            print("[COAP NORMAL] Sending request...")

            start_time = time.time()

            request = Message(code=GET, uri=coap_url)
            response = await protocol.request(request).response

            end_time = time.time()
            last_rtt_ms = (end_time - start_time) * 1000

            payload = json.loads(response.payload.decode("utf-8"))

            print("[COAP NORMAL]")
            print("Response:", payload)
            print(f"RTT: {last_rtt_ms:.2f} ms")
            print(f"Sent previous RTT: {coap_url}")

        except Exception as e:
            print("[COAP NORMAL ERROR]", e)

        await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())