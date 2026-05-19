import argparse
import json
import random
import time

import paho.mqtt.client as mqtt


# ============================
# ARGUMENTS
# ============================
parser = argparse.ArgumentParser(description="MQTT Flood Client for IoT Security Monitoring TA")
parser.add_argument("--rate", type=float, default=100, help="Target request/message per second. Use 0 for unlimited.")
parser.add_argument("--duration", type=float, default=0, help="Duration in seconds. Use 0 for unlimited until CTRL+C.")
args = parser.parse_args()


# ============================
# CONFIG
# ============================
BROKER = "localhost"
PORT = 1883
TOPIC = "sensor/temp"

USERNAME = "admin"
PASSWORD = "admin123"

RATE = args.rate
DURATION = args.duration

# ============================
# CALLBACKS
# ============================
connected = False

def on_connect(client, userdata, flags, rc):
    global connected

    if rc == 0:
        connected = True
        print("✅ Connected to MQTT Broker")
    else:
        print(f"❌ Failed to connect, return code {rc}")

def on_disconnect(client, userdata, rc):
    global connected
    connected = False
    print(f"⚠️ Disconnected from broker, rc={rc}")

# ============================
# MQTT SETUP
# ============================
client = mqtt.Client()
client.username_pw_set(USERNAME, PASSWORD)

client.on_connect = on_connect
client.on_disconnect = on_disconnect

print("[MQTT FLOOD] Connecting to broker...")
client.connect(BROKER, PORT, 60)
client.loop_start()

while not connected:
    print("[MQTT FLOOD] Waiting for MQTT connection...")
    time.sleep(1)

# ============================
# FLOOD LOOP
# ============================
count = 0
start_time = time.time()
next_send_time = start_time

# Nilai latency awal. Nanti akan diisi dari hasil publish sebelumnya.
last_latency_ms = 0.0

print("[MQTT FLOOD] Started")
print(f"Rate     : {'unlimited' if RATE == 0 else str(RATE) + ' msg/s'}")
print(f"Duration : {'unlimited' if DURATION == 0 else str(DURATION) + ' seconds'}")
print("QoS      : 1")
print("Stop     : CTRL + C")

try:
    while True:
        now = time.time()

        if DURATION > 0 and (now - start_time) >= DURATION:
            break

        payload = {
            "traffic_type": "attack",
            "src": "mqtt_flood_client",
            "temperature": round(random.uniform(25.0, 35.0), 2),
            "humidity": round(random.uniform(55.0, 75.0), 2),
            "latency_ms": round(last_latency_ms, 2)
        }

        # Hitung ukuran payload MQTT dalam bytes
        payload_size_bytes = len(json.dumps(payload).encode("utf-8"))
        payload["payload_size_bytes"] = payload_size_bytes

        publish_start = time.time()

        # QoS 1 supaya publish menunggu ACK dari broker,
        # sehingga latency_ms bisa dihitung lebih masuk akal.
        result = client.publish(TOPIC, json.dumps(payload), qos=1)
        result.wait_for_publish()

        publish_end = time.time()
        last_latency_ms = (publish_end - publish_start) * 1000

        count += 1

        if count % 100 == 0:
            elapsed = time.time() - start_time
            current_rate = count / elapsed if elapsed > 0 else 0
            print(f"[MQTT FLOOD] sent={count} | avg_rate={current_rate:.2f} msg/s | latency={last_latency_ms:.2f} ms", flush=True)

        # RATE = 0 berarti unlimited, tidak ada sleep
        if RATE > 0:
            next_send_time += 1.0 / RATE
            sleep_time = next_send_time - time.time()

            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                # Kalau sistem sudah telat, reset supaya tidak numpuk delay
                next_send_time = time.time()

except KeyboardInterrupt:
    print("\n[MQTT FLOOD] Stopped by user")

finally:
    elapsed = time.time() - start_time
    avg_rate = count / elapsed if elapsed > 0 else 0

    print(f"[MQTT FLOOD] Total sent={count} | elapsed={elapsed:.2f}s | avg_rate={avg_rate:.2f} msg/s | last_latency={last_latency_ms:.2f} ms | last_payload_size={payload_size_bytes} bytes", flush=True)

    client.loop_stop()
    client.disconnect()