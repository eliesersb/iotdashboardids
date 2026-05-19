import json
import random
import time

import paho.mqtt.client as mqtt


# ============================
# MQTT NORMAL CLIENT
# ============================
BROKER = "localhost"
PORT = 1883
TOPIC = "sensor/temp"

USERNAME = "admin"
PASSWORD = "admin123"

INTERVAL_SECONDS = 5

connected = False


# ============================
# CALLBACKS
# ============================
def on_connect(client, userdata, flags, rc):
    global connected

    if rc == 0:
        connected = True
        print("✅ Connected to MQTT Broker")
    else:
        print(f"❌ Failed to connect, return code {rc}")


def on_publish(client, userdata, mid):
    print(f"📤 Publish ACK mid={mid}")


def on_disconnect(client, userdata, rc):
    global connected
    connected = False
    print(f"⚠️ Disconnected from broker, rc={rc}")


# ============================
# MAIN
# ============================
client = mqtt.Client()
client.username_pw_set(USERNAME, PASSWORD)

client.on_connect = on_connect
client.on_publish = on_publish
client.on_disconnect = on_disconnect

print("[MQTT NORMAL] Connecting to broker...")
client.connect(BROKER, PORT, 60)
client.loop_start()

# Tunggu sampai benar-benar connected
while not connected:
    print("[MQTT NORMAL] Waiting for MQTT connection...")
    time.sleep(1)

print("[MQTT NORMAL] Started")
print(f"Topic    : {TOPIC}")
print(f"Interval : {INTERVAL_SECONDS} seconds")
print("Stop     : CTRL + C")

# Nilai awal, nanti akan terisi dari hasil publish sebelumnya
last_latency_ms = 0.0

try:
    while True:
        payload = {
            "traffic_type": "normal",
            "src": "mqtt_normal_client",
            "temperature": round(random.uniform(25.0, 35.0), 2),
            "humidity": round(random.uniform(55.0, 75.0), 2),
        
        # Latency MQTT memakai hasil waktu publish sebelumnya
            "latency_ms": round(last_latency_ms, 2)
        }

        # Hitung ukuran payload MQTT dalam bytes
        payload_size_bytes = len(json.dumps(payload).encode("utf-8"))
        payload["payload_size_bytes"] = payload_size_bytes

        start_time = time.time()
        # QoS 1 supaya publish menunggu ACK dari broker
        result = client.publish(TOPIC, json.dumps(payload), qos=1)
        result.wait_for_publish()

        end_time = time.time()
        last_latency_ms = (end_time - start_time) * 1000 
    
        print(f"📡 Published to {TOPIC}: {payload} | result={result.rc} | latency={last_latency_ms:.2f} ms | payload_size={payload_size_bytes} bytes")

        time.sleep(INTERVAL_SECONDS)

except KeyboardInterrupt:
    print("\n🛑 MQTT normal client stopped by user")

finally:
    client.loop_stop()
    client.disconnect()