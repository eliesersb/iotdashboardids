# IoT Security Monitoring Dashboard with Snort IDS

Project ini merupakan sistem dashboard monitoring keamanan jaringan IoT berbasis container dengan integrasi Intrusion Detection System (IDS). Sistem ini digunakan untuk memantau traffic normal dan traffic serangan pada protokol MQTT, REST API, CoAP, dan gRPC.

Dashboard final menggunakan Django dan Chart.js sebagai visualisasi utama. Data traffic aplikasi disimpan pada InfluxDB melalui measurement `protocol_metrics`, sedangkan data alert IDS dari Snort disimpan pada measurement `snort_alerts`.

## Komponen Sistem

- Docker Compose: menjalankan seluruh service dalam container.
- Django: dashboard utama sistem.
- Chart.js: visualisasi grafik real-time.
- InfluxDB 1.8: database time-series.
- Telegraf: pengumpul dan penghubung data.
- Snort IDS: pendeteksi serangan jaringan.
- MQTT, REST API, CoAP, dan gRPC: protokol IoT yang diuji.

## Port Service

| Service | Port |
|---|---:|
| Django Dashboard | 8000 |
| InfluxDB | 8086 |
| Telegraf HTTP Listener | 8186 |
| MQTT Broker | 1883 |
| MQTT WebSocket | 9001 |
| REST API | 5000 |
| CoAP Server | 5683/UDP |
| gRPC Server | 50051 |

## Konfigurasi Environment

Buat file `.env` dari `.env.example`.

```bash
cp .env.example .env
```

Isi credential asli hanya di `.env`. Jangan upload `.env` ke GitHub.

## Menjalankan Sistem

```bash
docker compose up -d --build
docker compose ps
```

Buka dashboard:

```text
http://localhost:8000
```

## Menghentikan Sistem

```bash
docker compose down
```

## Reset Data Pengujian

```bash
bash reset_test_data.sh
```

## Menjalankan Traffic Normal

```bash
python3 mqtt_client.py
python3 rest_client.py
python3 coap_client.py
python3 grpc_client.py
```

## Menjalankan Application Flood

```bash
python3 mqtt_flood.py
python3 rest_flood.py
python3 coap_flood.py
python3 grpc_flood.py
```

## Menjalankan hping3

```bash
sudo timeout 20 hping3 -S --flood -p 1883 127.0.0.1
sudo timeout 20 hping3 -S --flood -p 5000 127.0.0.1
sudo timeout 20 hping3 --udp --flood -p 5683 127.0.0.1
sudo timeout 20 hping3 -S --flood -p 50051 127.0.0.1
```

## Validasi InfluxDB

Masuk ke InfluxDB:

```bash
docker exec -it influxdb influx
```

Gunakan database:

```sql
USE iot_data
SHOW MEASUREMENTS
```

Cek traffic aplikasi:

```sql
SELECT COUNT("request_count") FROM "protocol_metrics" WHERE time > now() - 15m GROUP BY "protocol", "traffic_type"
```

Cek alert IDS:

```sql
SELECT COUNT("sid") FROM "snort_alerts" WHERE time > now() - 15m GROUP BY "protocol", "msg"
```

## Validasi Log Snort

```bash
tail -f snort/log/alert_fast.txt
docker logs -f snort_mqtt
docker logs -f snort_rest
docker logs -f snort_coap
docker logs -f snort_grpc
```

## Halaman Dashboard

| Halaman | Fungsi |
|---|---|
| Home | Ringkasan status sistem |
| Monitoring | Grafik traffic, latency/RTT, dan throughput |
| Alert | Alert IDS dan severity |
| Nodes | Informasi node/protokol |
| Summary | Ringkasan hasil monitoring |
| Maintenance | Reset data pengujian |

## Skenario Pengujian Final

1. MQTT Application Flood
2. REST API Application Flood
3. CoAP Application Flood
4. gRPC Application Flood
5. MQTT hping3
6. REST API hping3
7. CoAP hping3
8. gRPC hping3

## Catatan Pengujian

REST API dan gRPC berbasis TCP, sehingga flood aplikasi dapat terlihat sebagai pola TCP SYN Flood. CoAP berbasis UDP, sehingga application flood juga dapat memenuhi pola UDP Flood. Perbedaan klasifikasi ini merupakan karakteristik deteksi Snort berdasarkan pola traffic, port, dan protokol.

## Deploy di Laptop Lain

```bash
git clone <url-repository>
cd iotdashboardids
cp .env.example .env
nano .env
docker compose up -d --build
```

Kemudian buka:

```text
http://localhost:8000
```
