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
./scripts/hping3_mqtt.sh
./scripts/hping3_rest.sh
./scripts/hping3_coap.sh
./scripts/hping3_grpc.sh
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



---

## Final Deployment dan Alur Pengujian

Bagian ini digunakan untuk menjalankan sistem pada laptop baru, laptop kosong, atau cloud/VPS.

### 1. Clone Repository

```bash
git clone https://github.com/eliesersb/iotdashboardids.git
cd iotdashboardids
```

### 2. Siapkan File Environment

```bash
cp .env.example .env
```

Isi konfigurasi Telegram pada file `.env`:

```text
TELEGRAM_BOT_TOKEN=isi_token_bot_telegram
TELEGRAM_CHAT_ID=isi_chat_id_telegram
```

Jika Telegram tidak digunakan, sistem utama tetap dapat berjalan, tetapi notifikasi Telegram tidak akan terkirim.

### 3. Jalankan Sistem

```bash
docker compose up -d
docker compose ps
```

Dashboard dapat dibuka melalui:

```text
http://localhost:8000/
```

### 4. Menjalankan Normal Client

Normal client dapat dijalankan langsung dari WSL atau terminal lokal:

```bash
python3 rest_client.py
python3 mqtt_client.py
python3 coap_client.py
python3 grpc_client.py
```

Normal traffic akan masuk ke InfluxDB dan ditampilkan pada dashboard.

### 5. Menjalankan Application Flood

Application flood dijalankan melalui Docker network agar target service stabil. Default durasi adalah 15 detik.

```bash
./scripts/run_flood_rest.sh
./scripts/run_flood_mqtt.sh
./scripts/run_flood_coap.sh
./scripts/run_flood_grpc.sh
```

Durasi dapat diubah, contoh:

```bash
./scripts/run_flood_rest.sh 30
```

Target internal Docker:

```text
REST  -> http://rest_api:5000
MQTT  -> mqtt_broker:1883
CoAP  -> coap://coap_server:5683/sensor/temp
gRPC  -> grpc_server:50051
```

### 6. Menjalankan hping3 Ringan

hping3 dijalankan melalui Docker network dengan nama service sebagai target. Default durasi 10 detik, default interval u10000, dan tidak menggunakan --flood.

```bash
./scripts/hping3_rest.sh
./scripts/hping3_mqtt.sh
./scripts/hping3_coap.sh
./scripts/hping3_grpc.sh
```

Durasi dapat diubah:

```bash
./scripts/hping3_rest.sh 15
```

Interval dapat diubah:

```bash
INTERVAL=u20000 ./scripts/hping3_rest.sh 10
```

Catatan penting:

```text
Jangan menggunakan hping3 --flood untuk demo biasa.
Mode --flood dapat menghasilkan alert sangat besar, membuat file log membengkak, dan dashboard menjadi lambat.
Gunakan runner hping3 ringan untuk pengujian normal, demo, dan validasi TA.
```

### 7. Reset Data Pengujian

Gunakan reset ini sebelum pengujian resmi agar data bersih:

```bash
docker exec influxdb influx -database iot_data -execute 'DROP MEASUREMENT protocol_metrics'
docker exec influxdb influx -database iot_data -execute 'DROP MEASUREMENT snort_alerts'
: > snort/log/alert_fast.txt
chmod 777 snort/log/alert_fast.txt
docker compose restart telegraf django_app
```

### 8. Validasi InfluxDB

```bash
docker exec influxdb influx -database iot_data -execute 'SHOW MEASUREMENTS'
docker exec influxdb influx -database iot_data -execute 'SELECT * FROM protocol_metrics ORDER BY time DESC LIMIT 10'
docker exec influxdb influx -database iot_data -execute 'SELECT * FROM snort_alerts ORDER BY time DESC LIMIT 10'
```

### 9. Validasi Snort Log

```bash
tail -20 snort/log/alert_fast.txt
```

Alert yang diharapkan:

```text
MQTT Application Flood Detected
REST Flood Detected
COAP Application Flood Detected
gRPC Application Flood Detected
MQTT TCP SYN Flood / hping3 Detected
REST TCP SYN Flood / hping3 Detected
COAP UDP Flood / hping3 Detected
gRPC TCP SYN Flood / hping3 Detected
```

Pada pengujian gRPC, alert application flood juga dapat muncul ketika trafik ke port 50051 tinggi. Hal tersebut masih wajar selama alert hping3 gRPC juga terdeteksi.

### 10. Validasi Dashboard dan Telegram

Setelah normal client, application flood, atau hping3 dijalankan, cek:

```text
1. Dashboard berubah dari Normal menjadi Under Attack
2. Grafik protocol metrics bertambah
3. Alert muncul pada panel dashboard
4. Notifikasi popup dashboard muncul
5. Telegram menerima alert
6. Data masuk ke InfluxDB
7. Log Snort bertambah
```

---

## Catatan Permission Snort Log Setelah Clone Baru

Jika alert Snort tidak muncul di dashboard atau Telegram setelah clone baru, pastikan permission folder `snort/log` sudah terbuka agar Telegraf dapat membaca file `alert_fast.txt`.

Jalankan command berikut:

```bash
mkdir -p snort/log
touch snort/log/alert_fast.txt
sudo chmod -R 777 snort/log
docker compose restart telegraf django_app
```

Untuk startup yang lebih aman, gunakan script berikut:

```bash
./scripts/start_all.sh
```

