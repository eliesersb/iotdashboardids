# IoT Security Monitoring Dashboard

Project ini adalah sistem monitoring keamanan jaringan IoT berbasis Docker dengan integrasi IDS Snort, InfluxDB, Telegraf, dan Grafana.

Sistem ini digunakan untuk memonitor trafik normal dan flood/attack pada empat protokol IoT:

- MQTT
- REST API
- CoAP
- gRPC

Data trafik disimpan ke InfluxDB pada measurement `protocol_metrics`, sedangkan alert IDS Snort disimpan pada measurement `snort_alerts`.

---

## Arsitektur Singkat

### Alur Data Trafik

Normal Client / Flood Client
↓
MQTT / REST / CoAP / gRPC Service
↓
InfluxDB: protocol_metrics
↓
Grafana / Django Chart.js

### Alur IDS

Network Traffic
↓
Snort IDS
↓
alert_fast.txt
↓
Telegraf
↓
InfluxDB: snort_alerts
↓
Grafana / Django Chart.js

---

## Service dan Port

| Service | Port |
|---|---:|
| MQTT Broker | 1883 |
| MQTT WebSocket | 9001 |
| REST API | 5000 |
| CoAP Server | 5683/udp |
| gRPC Server | 50051 |
| InfluxDB | 8086 |
| Telegraf HTTP Listener | 8186 |
| Grafana | 3030 |

---

## Menjalankan Sistem

Masuk ke folder project:

`cd 2iotdashboard`

Bersihkan log Snort sebelum pengujian:

`truncate -s 0 snort/log/alert_fast.txt`

Jalankan semua container:

`docker compose up -d --build`

Cek container:

`docker ps`

Container yang harus aktif:

- mqtt_broker
- rest_api
- coap_server
- grpc_server
- snort_mqtt
- snort_rest
- snort_coap
- snort_grpc
- influxdb
- telegraf
- grafana

---

## Instalasi Dependency Python

`pip install -r requirements.txt`

---

## Menjalankan Normal Client

Jalankan masing-masing di terminal berbeda:

`python3 mqtt_client.py`

`python3 rest_client.py`

`python3 coap_client.py`

`python3 grpc_client.py`

---

## Menjalankan Flood Client

Rate awal yang disarankan adalah 100 request/message per detik.

`python3 mqtt_flood.py --rate 100 --duration 0`

`python3 rest_flood.py --rate 100 --duration 0 --workers 50`

`python3 coap_flood.py --rate 100 --duration 0 --concurrency 100`

`python3 grpc_flood.py --rate 100 --duration 0 --workers 50`

Keterangan:

`--rate 100` = target 100 request/message per detik

`--duration 0` = berjalan terus sampai dihentikan dengan CTRL + C

---

## Mengecek Data di InfluxDB

Masuk ke InfluxDB:

`docker exec -it influxdb influx`

Pilih database:

`USE iot_data`

Cek measurement:

`SHOW MEASUREMENTS`

Cek trafik normal:

`SELECT SUM("request_count") FROM "protocol_metrics" WHERE time > now() - 5m AND "traffic_type"='normal' GROUP BY "protocol"`

Cek trafik attack:

`SELECT SUM("request_count") FROM "protocol_metrics" WHERE time > now() - 5m AND "traffic_type"='attack' GROUP BY "protocol"`

Cek normal vs attack:

`SELECT SUM("request_count") FROM "protocol_metrics" WHERE time > now() - 5m GROUP BY "protocol","traffic_type"`

Cek latency:

`SELECT MEAN("latency_ms") FROM "protocol_metrics" WHERE time > now() - 5m GROUP BY "protocol","traffic_type"`

---

## Mengecek Alert Snort

MQTT:

`SELECT COUNT("sid") FROM "snort_alerts" WHERE time > now() - 10m AND "sid"='1000004'`

REST:

`SELECT COUNT("sid") FROM "snort_alerts" WHERE time > now() - 10m AND "sid"='1000005'`

CoAP:

`SELECT COUNT("sid") FROM "snort_alerts" WHERE time > now() - 10m AND "sid"='1000006'`

gRPC:

`SELECT COUNT("sid") FROM "snort_alerts" WHERE time > now() - 10m AND "sid"='1000007'`

---

## SID Snort

| SID | Protokol | Alert |
|---:|---|---|
| 1000004 | MQTT | MQTT Flood Detected |
| 1000005 | REST | REST Flood Detected |
| 1000006 | CoAP | CoAP Flood Detected |
| 1000007 | gRPC | gRPC Flood Detected |

---

## Akses Grafana

Buka:

`http://localhost:3030`

Default login:

`username: admin`

`password: admin`

---

## Catatan Jika Dijalankan dari Device Lain

Jika semua service dan script dijalankan pada device yang sama, gunakan `localhost`.

Jika Docker berjalan di device A dan client/flood dijalankan dari device B, maka `localhost` pada script client/flood harus diganti menjadi IP device A.

Contoh:

Device A IP = `192.168.1.10`

Maka target menjadi:

- MQTT = `192.168.1.10:1883`
- REST = `http://192.168.1.10:5000`
- CoAP = `coap://192.168.1.10:5683/sensor/temp`
- gRPC = `192.168.1.10:50051`

---

## Status Implementasi

- Semua normal client MQTT, REST, CoAP, dan gRPC masuk ke InfluxDB.
- Semua flood client MQTT, REST, CoAP, dan gRPC masuk ke InfluxDB.
- Semua protokol berhasil terdeteksi Snort.
- Alert Snort berhasil masuk ke InfluxDB.
- Data siap digunakan untuk Grafana dan Django Chart.js.