import asyncio
import json
import time
from aiocoap import *


# ============================
# COAP NORMAL CLIENT
# ============================
COAP_URL = "coap://localhost:5683/sensor/temp"
INTERVAL_SECONDS = 5


async def main():
    protocol = await Context.create_client_context()

    while True:
        try:
            start_time = time.time()

            request = Message(code=GET, uri=COAP_URL)
            response = await protocol.request(request).response

            latency_ms = round((time.time() - start_time) * 1000, 2)

            payload = json.loads(response.payload.decode("utf-8"))

            print("[COAP NORMAL]")
            print("Response:", payload)
            print("Client RTT latency_ms:", latency_ms)

        except Exception as e:
            print("[COAP NORMAL ERROR]", e)

        await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())