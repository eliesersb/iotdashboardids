# IoT Security Monitoring Dashboard with Snort IDS

Project ini merupakan sistem dashboard monitoring keamanan jaringan IoT berbasis container dengan integrasi Intrusion Detection System (IDS). Sistem ini digunakan untuk memantau traffic normal dan traffic serangan pada beberapa protokol IoT, yaitu MQTT, REST API, CoAP, dan gRPC.

Dashboard final menggunakan **Django + Chart.js** sebagai visualisasi utama. Data traffic aplikasi disimpan pada InfluxDB melalui measurement `protocol_metrics`, sedangkan data alert IDS dari Snort IDS disimpan pada measurement `snort_alerts`.

## Ringkasan Sistem

Sistem ini dirancang untuk membantu proses monitoring keamanan jaringan IoT secara real-time. Setiap protokol IoT memiliki service, client normal, dan script flood masing-masing. Snort IDS digunakan untuk mendeteksi pola serangan, sedangkan Telegraf membantu meneruskan data ke InfluxDB agar dapat divisualisasikan pada dashboard Django.

Alur sederhana sistem:

```text
Traffic Generator / Client
        |
        v
MQTT | REST API | CoAP | gRPC
        |
        v
Snort IDS + Telegraf
        |
        v
InfluxDB
        |
        v
Django + Chart.js Dashboard
```

## Komponen Utama

| Komponen | Fungsi |
|---|---|
| Docker Compose | Menjalankan seluruh service dalam container |
| Django | Dashboard utama sistem |
| Chart.js | Visualisasi grafik real-time |
| InfluxDB 1.8 | Database time-series untuk traffic dan alert |
| Telegraf | Pengumpul dan penghubung data ke InfluxDB |
| Snort IDS | Pendeteksi serangan jaringan |
| MQTT | Simulasi protokol IoT publish/subscribe |
| REST API | Simulasi protokol IoT berbasis HTTP |
| CoAP | Simulasi protokol IoT ringan berbasis UDP |
| gRPC | Simulasi protokol IoT berbasis RPC |
| hping3 | Pengujian serangan network-level |

## Service dan Port

| Service | Port | Keterangan |
|---|---:|---|
| Django Dashboard | 8000 | Dashboard utama |
| InfluxDB | 8086 | Database time-series |
| Telegraf HTTP Listener | 8186 | Listener data line protocol |
| MQTT Broker | 1883 | MQTT TCP |
| MQTT WebSocket | 9001 | MQTT WebSocket |
| REST API | 5000 | REST endpoint |
| CoAP Server | 5683/UDP | CoAP endpoint |
| gRPC Server | 50051 | gRPC endpoint |

## Struktur Project

```text
iotdashboardids/
├── docker-compose.yml
├── README.md
├── .env.example
├── .gitignore
├── mqtt_client.py
├── mqtt_flood.py
├── rest_client.py
├── rest_flood.py
├── rest_server.py
├── coap_client.py
├── coap_flood.py
├── coap_server.py
├── grpc_client.py
├── grpc_flood.py
├── grpc_server.py
├── grpc.proto
├── generate_grpc.sh
├── reset_test_data.sh
├── switch_snort_rules.sh
├── django/
├── telegraf/
├── snort/
├── mosquitto_config/
└── scripts/
```

## Konfigurasi Environment

Buat file `.env` dari `.env.example`.

```bash
cp .env.example .env
```

Kemudian sesuaikan nilai berikut pada file `.env`.

```env
DJANGO_SECRET_KEY=change-this-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

INFLUXDB_HOST=influxdb
INFLUXDB_PORT=8086
INFLUXDB_DB=iot_data
INFLUXDB_USER=admin
INFLUXDB_PASSWORD=admin123

TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
```

File `.env` tidak boleh di-upload ke GitHub karena berisi credential asli. File yang boleh di-upload hanya `.env.example`.

## Menjalankan Sistem

Jalankan seluruh service:

```bash
bash scripts/start_all.sh
```

Atau secara manual:

```bash
docker compose up -d --build --remove-orphans
```

Cek status container:

```bash
docker compose ps
```

Buka dashboard:

```text
http://localhost:8000
```

## Menghentikan Sistem

```bash
bash scripts/stop_all.sh
```

Atau secara manual:

```bash
docker compose down
```

Command tersebut menghentikan container tanpa menghapus volume data.

Jika ingin menghentikan dan menghapus volume:

```bash
docker compose down -v
```

Gunakan `down -v` hanya jika ingin menghapus data container secara penuh.

## Reset Data Pengujian

Untuk membersihkan data pengujian sebelum skenario baru:

```bash
bash reset_test_data.sh
```

Reset data digunakan agar data traffic dan alert dari pengujian sebelumnya tidak bercampur dengan pengujian baru.

## Menjalankan Traffic Normal

Menjalankan seluruh client normal:

```bash
bash scripts/run_all_clients.sh
```

Menghentikan seluruh client normal:

```bash
bash scripts/stop_all_clients.sh
```

Menjalankan client normal satu per satu:

```bash
python3 mqtt_client.py
python3 rest_client.py
python3 coap_client.py
python3 grpc_client.py
```

## Menjalankan Application Flood

Menjalankan flood aplikasi per protokol:

```bash
bash scripts/run_flood_mqtt.sh
bash scripts/run_flood_rest.sh
bash scripts/run_flood_coap.sh
bash scripts/run_flood_grpc.sh
```

Application flood digunakan untuk menguji kemampuan sistem dalam mendeteksi lonjakan traffic pada level aplikasi.

## Menjalankan hping3

Pengujian hping3 digunakan untuk mensimulasikan serangan network-level.

```bash
bash scripts/hping3_mqtt.sh
bash scripts/hping3_rest.sh
bash scripts/hping3_coap.sh
bash scripts/hping3_grpc.sh
```

Command manual:

```bash
sudo timeout 20 hping3 -S --flood -p 1883 127.0.0.1
sudo timeout 20 hping3 -S --flood -p 5000 127.0.0.1
sudo timeout 20 hping3 --udp --flood -p 5683 127.0.0.1
sudo timeout 20 hping3 -S --flood -p 50051 127.0.0.1
```

Target port:

| Protokol | Jenis hping3 | Port |
|---|---|---:|
| MQTT | TCP SYN Flood | 1883 |
| REST API | TCP SYN Flood | 5000 |
| CoAP | UDP Flood | 5683 |
| gRPC | TCP SYN Flood | 50051 |

## Validasi Data InfluxDB

Masuk ke container InfluxDB:

```bash
docker exec -it influxdb influx
```

Gunakan database:

```sql
USE iot_data
```

Cek measurement:

```sql
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

Cek detail alert:

```sql
SELECT * FROM "snort_alerts" WHERE time > now() - 15m LIMIT 20
```

## Validasi Log Snort IDS

Cek log Snort IDS dari host:

```bash
sudo tail -n 30 snort/log/alert_fast.txt
```

Cek log secara realtime:

```bash
sudo tail -f snort/log/alert_fast.txt
```

Cek log container Snort IDS:

```bash
docker logs -f snort_mqtt
docker logs -f snort_rest
docker logs -f snort_coap
docker logs -f snort_grpc
```

## Halaman Dashboard

| Halaman | Fungsi |
|---|---|
| Home | Ringkasan status sistem, total request, alert aktif, latency/RTT, dan throughput |
| Monitoring | Grafik real-time traffic, latency/RTT, dan throughput setiap protokol |
| Alert | Menampilkan alert IDS, severity, timeline, dan jenis serangan |
| Nodes | Informasi node atau service protokol IoT yang dipantau |
| Summary | Ringkasan hasil monitoring dan pengujian |
| Maintenance | Reset data pengujian dan pembersihan log |

## Skenario Pengujian Final

Urutan pengujian final:

| No | Skenario | Tujuan |
|---:|---|---|
| 1 | MQTT Application Flood | Menguji deteksi flood aplikasi MQTT |
| 2 | REST API Application Flood | Menguji deteksi flood aplikasi REST API |
| 3 | CoAP Application Flood | Menguji deteksi flood aplikasi CoAP |
| 4 | gRPC Application Flood | Menguji deteksi flood aplikasi gRPC |
| 5 | MQTT hping3 | Menguji deteksi TCP SYN Flood pada MQTT |
| 6 | REST API hping3 | Menguji deteksi TCP SYN Flood pada REST API |
| 7 | CoAP hping3 | Menguji deteksi UDP Flood pada CoAP |
| 8 | gRPC hping3 | Menguji deteksi TCP SYN Flood pada gRPC |

## Catatan Hasil Pengujian

| Skenario | Catatan |
|---|---|
| MQTT Application Flood | Valid, terbaca sebagai Application Flood / DoS |
| REST API Application Flood | Valid, dapat terbaca sebagai TCP SYN Flood karena REST berbasis TCP dan membuka banyak koneksi |
| CoAP Application Flood | Valid, dapat muncul sebagai CoAP Application Flood dan CoAP UDP Flood karena CoAP berbasis UDP |
| gRPC Application Flood | Valid, terbaca sebagai Application Flood / DoS setelah rule disesuaikan |
| MQTT hping3 | Valid, terbaca sebagai MQTT TCP SYN Flood / hping3 |
| REST API hping3 | Valid, terbaca sebagai REST TCP SYN Flood / hping3 |
| CoAP hping3 | Valid, terbaca sebagai CoAP UDP Flood / hping3 |
| gRPC hping3 | Valid, dapat muncul sebagai gRPC Application Flood dan gRPC TCP SYN Flood / hping3 |

Perbedaan klasifikasi tersebut bukan error besar, melainkan karakteristik deteksi Snort IDS berdasarkan pola traffic, port, dan protokol.

## Troubleshooting

### Container tidak berjalan

```bash
docker compose ps
docker compose logs nama_service
```

### Data tidak masuk ke InfluxDB

```bash
docker logs -f telegraf
docker exec -it influxdb influx
```

Lalu jalankan:

```sql
USE iot_data
SHOW MEASUREMENTS
```

### Alert Snort IDS tidak muncul

```bash
sudo tail -f snort/log/alert_fast.txt
docker logs -f snort_mqtt
docker logs -f snort_rest
docker logs -f snort_coap
docker logs -f snort_grpc
```

### Dashboard tidak bisa dibuka

```bash
docker logs -f django_app
docker compose ps
```

Pastikan port `8000` aktif dan container `django_app` berjalan.

## Deploy di Laptop Lain

Langkah umum:

```bash
git clone https://github.com/eliesersb/iotdashboardids.git
cd iotdashboardids
cp .env.example .env
nano .env
docker compose up -d --build --remove-orphans
docker compose ps
```

Setelah service berjalan, buka:

```text
http://localhost:8000
```

## Persiapan Deploy ke Cloud

Checklist deploy cloud:

1. Gunakan server Ubuntu.
2. Install Docker dan Docker Compose.
3. Clone repository.
4. Buat file `.env` dari `.env.example`.
5. Jangan expose InfluxDB secara publik tanpa proteksi.
6. Expose port Django sesuai kebutuhan.
7. Gunakan firewall.
8. Gunakan reverse proxy jika memakai domain.
9. Simpan token Telegram hanya di `.env`.
10. Jalankan pengujian hping3 hanya pada lingkungan yang legal dan terkontrol.

## Status Project

Project ini sudah difinalisasi dengan dashboard utama berbasis **Django + Chart.js** sebagai dashboard final.

## Lisensi

Project ini dibuat untuk kebutuhan Tugas Akhir dan pengujian sistem monitoring keamanan jaringan IoT berbasis container.

