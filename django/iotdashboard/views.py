from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse
from influxdb import InfluxDBClient
from collections import Counter
from datetime import datetime, timedelta, timezone
from django.views.decorators.http import require_POST
import random
import json
import requests
import os
import time

def home(request):
    return render(request, 'iotdashboard/home.html')

def get_first_value(result, default=0):
    try:
        value = result["results"][0]["series"][0]["values"][0][1]
        return value if value is not None else default
    except Exception:
        return default


def get_series_values(result):
    try:
        return result["results"][0]["series"][0]["values"]
    except Exception:
        return []


def format_influx_time(value):
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            dt = dt + timedelta(hours=7)
            return dt.strftime("%Y-%m-%d %H:%M")

        if isinstance(value, int):
            dt = datetime.fromtimestamp(value / 1_000_000_000)
            dt = dt + timedelta(hours=7)
            return dt.strftime("%Y-%m-%d %H:%M")

        return "-"
    except Exception:
        return "-"

def format_chart_time(value):
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            dt = dt + timedelta(hours=7)
            return dt.strftime("%H:%M")

        if isinstance(value, int):
            dt = datetime.fromtimestamp(value / 1_000_000_000)
            dt = dt + timedelta(hours=7)
            return dt.strftime("%H:%M")

        return "-"
    except Exception:
        return "-"

def get_system_status(total_requests, detected_alerts):
    """
    Status global untuk halaman Home.
    """
    if detected_alerts > 0:
        return {
            "label": "Under Attack",
            "level": "alert",
            "description": "Snort mendeteksi adanya alert pada 5 menit terakhir."
        }

    if total_requests >= 100:
        return {
            "label": "Warning",
            "level": "warning",
            "description": "Traffic meningkat, tetapi belum ada alert dari Snort."
        }

    return {
        "label": "Normal",
        "level": "normal",
        "description": "Tidak ada indikasi serangan pada 5 menit terakhir."
    }

def overview_data(request):
    range_time = "5m"
    status_range_time = "60s"
    range_seconds = 5 * 60 

    protocols = {
        "mqtt": "MQTT",
        "rest": "REST API",
        "coap": "CoAP",
        "grpc": "gRPC",
    }

    alert_keywords = {
        "mqtt": "MQTT",
        "rest": "REST",
        "coap": "CoAP",
        "grpc": "gRPC",
    }

    protocol_activity = []
    traffic_labels = []
    traffic_data = []
    total_requests = 0


    # =========================
    # Summary: Total Requests
    # =========================
    q_total_requests = f"""
    SELECT SUM(request_count)
    FROM protocol_metrics
    WHERE time > now() - {range_time}
    """

    total_requests_result = query_influx(q_total_requests)
    total_requests = int(get_first_value(total_requests_result, 0))

    # =========================
    # Summary: Detected Alerts
    # =========================
    q_detected_alerts = f"""
    SELECT COUNT(msg)
    FROM snort_alerts
    WHERE time > now() - {range_time}
    """

    detected_alerts_result = query_influx(q_detected_alerts)
    detected_alerts = int(get_first_value(detected_alerts_result, 0))

    # System Status
    system_status = get_system_status(total_requests, detected_alerts)

    # =========================
    # Summary: Average Latency
    # =========================
    q_avg_latency = f"""
    SELECT MEAN(latency_ms)
    FROM protocol_metrics
    WHERE time > now() - {range_time}
    """

    avg_latency_result = query_influx(q_avg_latency)
    avg_latency_value = float(get_first_value(avg_latency_result, 0))

    # =========================
    # Summary: Throughput
    # Throughput Mbps = total bytes * 8 / durasi detik / 1.000.000
    # =========================
    q_payload_size = f"""
    SELECT SUM(payload_size_bytes)
    FROM protocol_metrics
    WHERE time > now() - {range_time}
    """

    payload_result = query_influx(q_payload_size)
    total_payload_bytes = float(get_first_value(payload_result, 0))

    throughput_kibps = (total_payload_bytes / 1024) / range_seconds

    # =========================
    # Protocol Activity
    # =========================
    for proto_key, proto_name in protocols.items():
        # Total request per protocol dalam 5 menit terakhir
        q_request = f"""
        SELECT SUM(request_count)
        FROM protocol_metrics
        WHERE time > now() - {range_time}
        AND protocol = '{proto_key}'
        """

        request_result = query_influx(q_request)
        request_count = int(get_first_value(request_result, 0))

        # Avg latency per protocol dalam 5 menit terakhir
        q_latency = f"""
        SELECT MEAN(latency_ms)
        FROM protocol_metrics
        WHERE time > now() - {range_time}
        AND protocol = '{proto_key}'
        """

        latency_result = query_influx(q_latency)
        latency_value = float(get_first_value(latency_result, 0))

        # Last update per protocol
        q_last_update = f"""
        SELECT LAST(request_count)
        FROM protocol_metrics
        WHERE protocol = '{proto_key}'
        """

        last_update_result = query_influx(q_last_update)

        try:
            last_time_raw = last_update_result["results"][0]["series"][0]["values"][0][0]
            last_update_raw = format_influx_time(last_time_raw)
        except Exception:
            last_update_raw = "-"

        if request_count == 0:
            last_update = "No recent data"
        else:
            last_update = last_update_raw

        # Alert per protocol dari Snort msg
        keyword = alert_keywords[proto_key]

        q_alert_proto = f"""
        SELECT COUNT(msg)
        FROM snort_alerts
        WHERE time > now() - {status_range_time}
        AND msg =~ /{keyword}/
        """

        alert_proto_result = query_influx(q_alert_proto)
        protocol_alert_count = int(get_first_value(alert_proto_result, 0))

        # Status dan reason
        # Catatan:
        # - Alert digunakan jika Snort mendeteksi alert pada protokol tersebut.
        # - Normal digunakan jika hanya ada traffic normal atau tidak ada traffic terbaru.
        # - High request normal tidak langsung dianggap Warning agar tidak ambigu bagi user.
        if protocol_alert_count > 0:
            status = "Under Attack"
            reason = "IDS Snort detected attack traffic"
        elif request_count == 0:
            status = "Normal"
            reason = "No recent traffic"
        else:
            status = "Normal"
            reason = "Normal traffic"

        protocol_activity.append({
            "protocol": proto_name,
            "status": status,
            "request_count": request_count,
            "avg_latency": f"{latency_value:.2f} ms",
            "last_update": last_update,
            "reason": reason,
        })

        traffic_labels.append(proto_name)
        traffic_data.append(request_count)

    # =========================
    # Application attack requests untuk menentukan status Home
    # =========================
    q_attack_requests_home = f"""
    SELECT COUNT(request_count)
    FROM protocol_metrics
    WHERE time > now() - {range_time}
    AND traffic_type = 'attack'
    """

    attack_requests_result = query_influx(q_attack_requests_home)
    attack_requests = int(get_first_value(attack_requests_result, 0))

    # =========================
    # Recent IDS alerts khusus untuk status Home agar lebih near real-time
    # =========================
    q_recent_detected_alerts_home = f"""
    SELECT COUNT(msg)
    FROM snort_alerts
    WHERE time > now() - {status_range_time}
    """

    recent_detected_alerts_result = query_influx(q_recent_detected_alerts_home)
    recent_detected_alerts = int(get_first_value(recent_detected_alerts_result, 0))

    # =========================
    # Recent application attack khusus untuk status Home agar lebih near real-time
    # =========================
    q_recent_attack_requests_home = f"""
    SELECT COUNT(request_count)
    FROM protocol_metrics
    WHERE time > now() - {status_range_time}
    AND traffic_type = 'attack'
    """

    recent_attack_requests_result = query_influx(q_recent_attack_requests_home)
    recent_attack_requests = int(get_first_value(recent_attack_requests_result, 0))

    # =========================
    # System Security Status
    # =========================
    if recent_detected_alerts > 0:
        system_status = {
            "label": "Under Attack",
            "class": "alert",
            "reason": "IDS Snort mendeteksi indikasi serangan pada jaringan dalam 60 detik terakhir."
        }
    elif recent_attack_requests > 0:
        system_status = {
            "label": "Suspicious",
            "class": "warning",
            "reason": "Terdapat traffic attack aplikasi dalam 60 detik terakhir, tetapi belum ada alert dari IDS Snort."
        }
    else:
        system_status = {
            "label": "Normal",
            "class": "normal",
            "reason": "Tidak ada traffic attack atau alert IDS dalam 60 detik terakhir."
        }

    data = {
        "summary_cards": {
            "total_requests": total_requests,
            "detected_alerts": detected_alerts,
            "avg_latency": f"{avg_latency_value:.2f} ms",
            "throughput": f"{throughput_kibps:.3f} KiB/s",
        },
        "system_status": system_status,
        "protocol_activity": protocol_activity,
        "traffic_distribution": {
            "labels": traffic_labels,
            "data": traffic_data,
        },
        "last_updated": (datetime.utcnow() + timedelta(hours=7)).strftime("%H:%M:%S"),
        "data_range": "Last 5 minutes",
        "auto_refresh": "5 seconds",
    }

    return JsonResponse(data)

def monitoring(request):
    return render(request, 'iotdashboard/monitoring.html')

INFLUX_URL = "http://influxdb:8086/query"
INFLUX_DB = "iot_data"
INFLUX_AUTH = ("admin", "admin123")

def query_influx(q):
    response = requests.get(
        INFLUX_URL,
        params={
            "db": INFLUX_DB,
            "q": q
        },
        auth=INFLUX_AUTH,
        timeout=10
    )
    response.raise_for_status()
    return response.json()

def parse_influx_series(data):
    results = data.get("results", [])

    if not results or "series" not in results[0]:
        return {}

    series = results[0]["series"][0]
    columns = series["columns"]
    values = series.get("values", [])

    parsed = {}

    for row in values:
        item = dict(zip(columns, row))
        time_value = item.get("time")

        metric_value = 0
        for key in item:
            if key != "time":
                metric_value = item.get(key) or 0

        parsed[time_value] = metric_value

    return parsed

def format_time_label(time_str, duration="5m"):
    try:
        dt = datetime.replace(
            datetime.fromisoformat(time_str.replace("Z", "+00:00")),
            tzinfo=timezone.utc
        )
        dt = dt + timedelta(hours=7)

        if duration in ["1m", "5m"]:
            return dt.strftime("%H:%M:%S")

        return dt.strftime("%H:%M")
    except Exception:
        return time_str

def max_value_from_dicts(*dicts):
    values = []
    for d in dicts:
        values.extend([v for v in d.values() if v is not None])
    return max(values) if values else 0

def sum_value_from_dict(d):
    return sum([v for v in d.values() if v is not None])

def get_monitoring_insight(total_alerts, peak_request_rate, highest_latency):
    """
    Membuat ringkasan sederhana untuk membantu user membaca halaman Monitoring.
    total_alerts berasal dari IDS/Snort, sedangkan peak_request_rate dan latency berasal dari metrik aplikasi.
    """

    if total_alerts > 0:
        return {
            "level": "alert",
            "message": "Serangan terdeteksi pada rentang waktu yang dipilih. Periksa grafik Request Rate, Throughput, dan IDS Alert Timeline untuk melihat hubungan antara lonjakan traffic dan deteksi Snort."
        }

    if peak_request_rate >= 100:
        return {
            "level": "warning",
            "message": "Aktivitas request aplikasi meningkat pada rentang waktu yang dipilih, tetapi belum ada serangan yang terdeteksi oleh Snort."
        }

    if highest_latency >= 100:
        return {
            "level": "warning",
            "message": "Latency layanan cukup tinggi pada rentang waktu yang dipilih. Periksa grafik Latency Trend untuk melihat protokol yang mengalami perlambatan."
        }

    return {
        "level": "normal",
        "message": "Belum ada serangan yang terdeteksi pada rentang waktu yang dipilih. Grafik performa menampilkan aktivitas request aplikasi yang sedang berjalan."
    }


def monitoring_data(request):
    range_value = request.GET.get("range", "-5m")

    range_map = {
    "-1m": "1m",
    "-5m": "5m",
    "-15m": "15m",
    "-30m": "30m",
    "-1h": "1h",
    }

    duration = range_map.get(range_value, "5m")

    # MQTT: REQUEST_RATE dihitung dari jumlah data temperature yang masuk
    mqtt_q = f"""
    SELECT SUM(request_count)
    FROM protocol_metrics
    WHERE time > now() - {duration} AND protocol='mqtt'
    GROUP BY time(10s) fill(0)
    """

    #MQTT : LATENCY pakai waktu publish sampai ACK publish diterima (latency_ms_float)
    mqtt_latency_q = f"""
    SELECT MEAN(latency_ms)
    FROM protocol_metrics
    WHERE time > now() - {duration} AND protocol='mqtt'
    GROUP BY time(10s) fill(0)
    """

    #MQTT : THROUGHPUT dihitung dari payload_size yang dikirim dalam response
    mqtt_throughput_q = f"""
    SELECT SUM(payload_size_bytes)
    FROM protocol_metrics
    WHERE time > now() - {duration} AND protocol='mqtt'
    GROUP BY time(10s) fill(0)
    """

    # REST API: REQUEST_RATE pakai request_count
    rest_q = f"""
    SELECT SUM(request_count)
    FROM protocol_metrics
    WHERE time > now() - {duration} AND protocol='rest'
    GROUP BY time(10s) fill(0)
    """

    # REST API : LATENCY pakai latency_ms_float
    rest_latency_q = f"""
    SELECT MEAN(latency_ms)
    FROM protocol_metrics
    WHERE time > now() - {duration} AND protocol='rest'
    GROUP BY time(10s) fill(0)
    """

    #REST API : THROUGHPUT dihitung dari payload_size yang dikirim dalam response
    rest_throughput_q = f"""
    SELECT SUM(payload_size_bytes)
    FROM protocol_metrics
    WHERE time > now() - {duration} AND protocol='rest'
    GROUP BY time(10s) fill(0)
    """

    # CoAP: REQUEST_RATE dari protocol_metrics
    coap_q = f"""
    SELECT SUM(request_count)
    FROM protocol_metrics
    WHERE time > now() - {duration} AND protocol='coap'
    GROUP BY time(10s) fill(0)
    """
    # CoAP : LATENCY pakai latency_ms_float
    coap_latency_q = f"""
    SELECT MEAN(latency_ms)
    FROM protocol_metrics
    WHERE time > now() - {duration} AND protocol='coap'
    GROUP BY time(10s) fill(0)
    """

    #CoAP : THROUGHPUT dihitung dari payload_size yang dikirim dalam response
    coap_throughput_q = f"""
    SELECT SUM(payload_size_bytes)
    FROM protocol_metrics
    WHERE time > now() - {duration} AND protocol='coap'
    GROUP BY time(10s) fill(0)
    """

    # gRPC: REQUEST_RATE dihitung dari jumlah data temperature yang masuk
    grpc_q = f"""
    SELECT SUM(request_count)
    FROM protocol_metrics
    WHERE time > now() - {duration} AND protocol='grpc'
    GROUP BY time(10s) fill(0)
    """
    # gRPC : LATENCY pakai latency_ms_float
    grpc_latency_q = f"""
    SELECT MEAN(latency_ms)
    FROM protocol_metrics
    WHERE time > now() - {duration} AND protocol='grpc'
    GROUP BY time(10s) fill(0)
    """

    # gRPC : THROUGHPUT dihitung dari payload_size yang dikirim dalam response
    grpc_throughput_q = f"""
    SELECT SUM(payload_size_bytes)
    FROM protocol_metrics
    WHERE time > now() - {duration} AND protocol='grpc'
    GROUP BY time(10s) fill(0)
    """

    # ALERT TIMELINE: jumlah alert dari Snort
    alert_timeline_q = f"""
    SELECT COUNT(msg)
    FROM snort_alerts
    WHERE time > now() - {duration}
    GROUP BY time(10s) fill(0)
    """

    # PARSE DATA UNTUK REQUEST_RATE
    mqtt_data = parse_influx_series(query_influx(mqtt_q))
    rest_data = parse_influx_series(query_influx(rest_q))
    coap_data = parse_influx_series(query_influx(coap_q))
    grpc_data = parse_influx_series(query_influx(grpc_q))
       
    # PARSE DATA UNTUK LATENCY
    mqtt_latency_data = parse_influx_series(query_influx(mqtt_latency_q))
    rest_latency_data = parse_influx_series(query_influx(rest_latency_q))
    coap_latency_data = parse_influx_series(query_influx(coap_latency_q))
    grpc_latency_data = parse_influx_series(query_influx(grpc_latency_q))

    # PARSE DATA UNTUK THROUGHPUT
    mqtt_throughput_data = parse_influx_series(query_influx(mqtt_throughput_q))
    rest_throughput_data = parse_influx_series(query_influx(rest_throughput_q))
    coap_throughput_data = parse_influx_series(query_influx(coap_throughput_q))
    grpc_throughput_data = parse_influx_series(query_influx(grpc_throughput_q))

    # PARSE DATA UNTUK ALERT TIMELINE
    alert_timeline_data = parse_influx_series(query_influx(alert_timeline_q))

    peak_request_rate = max_value_from_dicts(
    mqtt_data,
    rest_data,
    coap_data,
    grpc_data
    )

    highest_latency = max_value_from_dicts(
    mqtt_latency_data,
    rest_latency_data,
    coap_latency_data,
    grpc_latency_data
    )

    highest_throughput_bytes = max_value_from_dicts(
    mqtt_throughput_data,
    rest_throughput_data,
    coap_throughput_data,
    grpc_throughput_data
    )

    highest_throughput_kib = round(highest_throughput_bytes / 1024, 3)

    total_alerts = sum_value_from_dict(alert_timeline_data)

    monitoring_insight = get_monitoring_insight(
    total_alerts,
    peak_request_rate,
    highest_latency
    )

    all_times = sorted(
        set(mqtt_data.keys())
        | set(rest_data.keys())
        | set(coap_data.keys())
        | set(grpc_data.keys())
        | set(alert_timeline_data.keys())
    )

    labels = [format_time_label(t, duration) for t in all_times]

    data = {
        "labels": labels,

        "summary": {
        "peak_request_rate": int(peak_request_rate),
        "highest_latency": f"{float(highest_latency):.2f} ms",
        "highest_throughput": f"{highest_throughput_kib} KiB / 10s",
        "total_alerts": int(total_alerts),
    },

        "insight": monitoring_insight,

        "request_rate": {
            "mqtt": [mqtt_data.get(t, 0) for t in all_times],
            "rest": [rest_data.get(t, 0) for t in all_times],
            "coap": [coap_data.get(t, 0) for t in all_times],
            "grpc": [grpc_data.get(t, 0) for t in all_times],
        },

        "latency": {
            "mqtt": [mqtt_latency_data.get(t, 0) for t in all_times],
            "rest": [rest_latency_data.get(t, 0) for t in all_times],
            "coap": [coap_latency_data.get(t, 0) for t in all_times],
            "grpc": [grpc_latency_data.get(t, 0) for t in all_times], 
        },

        "throughput": {
            "mqtt": [round(mqtt_throughput_data.get(t, 0) / 1024, 3) for t in all_times],
            "rest": [round(rest_throughput_data.get(t, 0) / 1024, 3) for t in all_times],
            "coap": [round(coap_throughput_data.get(t, 0) / 1024, 3) for t in all_times],
            "grpc": [round(grpc_throughput_data.get(t, 0) / 1024, 3) for t in all_times],
        },

        "alert_timeline": [alert_timeline_data.get(t, 0) for t in all_times],
        
        "last_updated": (datetime.utcnow() + timedelta(hours=7)).strftime("%H:%M:%S"),

        "insight": monitoring_insight,
    }

    return JsonResponse(data)
    

def alert(request):
    return render(request, 'iotdashboard/alert.html')


def get_iot_protocol(dst_port, msg=""):
    """
    Mapping alert Snort ke protokol IoT berdasarkan destination port atau isi message.
    """
    dst_port = str(dst_port)
    msg_upper = str(msg).upper()

    if dst_port == "1883" or "MQTT" in msg_upper:
        return "MQTT"
    elif dst_port == "5000" or "REST" in msg_upper:
        return "REST API"
    elif dst_port == "5683" or "COAP" in msg_upper:
        return "CoAP"
    elif dst_port == "50051" or "GRPC" in msg_upper:
        return "gRPC"
    else:
        return "Unknown"




def get_detected_attack_display(msg="", dst_port="", sid=""):
    """
    Standardize Detected Attack display for Recent IDS Alert Logs.
    This makes application flood and hping3/network flood easier to distinguish.
    """
    msg_lower = str(msg or "").lower()
    dst_port = str(dst_port or "")
    sid = str(sid or "")

    # Explicit hping3 / SYN / UDP rule messages
    if "mqtt" in msg_lower and ("hping3" in msg_lower or "syn" in msg_lower or sid == "1000014"):
        return "MQTT TCP SYN Flood / hping3 Detected"

    if ("rest" in msg_lower or dst_port == "5000") and ("hping3" in msg_lower or "syn" in msg_lower or sid == "1000015"):
        return "REST TCP SYN Flood / hping3 Detected"

    if ("coap" in msg_lower or dst_port == "5683") and ("hping3" in msg_lower or "udp flood" in msg_lower or sid == "1000016"):
        return "CoAP UDP Flood / hping3 Detected"

    if ("grpc" in msg_lower or dst_port == "50051") and ("hping3" in msg_lower or "syn" in msg_lower or sid == "1000017"):
        return "gRPC TCP SYN Flood / hping3 Detected"

    # Application flood messages
    if "mqtt" in msg_lower and ("application" in msg_lower or sid == "1000004"):
        return "MQTT Application Flood Detected"

    if ("rest" in msg_lower or dst_port == "5000") and ("application" in msg_lower or sid == "1000005"):
        return "REST Application Flood Detected"

    if ("coap" in msg_lower or dst_port == "5683") and ("application" in msg_lower or sid == "1000006"):
        return "CoAP Application Flood Detected"

    if ("grpc" in msg_lower or dst_port == "50051") and ("application" in msg_lower or sid == "1000007"):
        return "gRPC Application Flood Detected"

    # Fallback for old rule messages
    if msg_lower == "mqtt flood detected":
        return "MQTT Application Flood Detected"

    if msg_lower == "rest flood detected":
        return "REST Application or TCP SYN Flood Detected"

    if msg_lower == "coap flood detected":
        return "CoAP Application or UDP Flood Detected"

    if msg_lower == "grpc flood detected":
        return "gRPC Application or TCP SYN Flood Detected"

    return msg or "IDS Alert Detected"


def get_log_severity(priority, msg=""):
    """
    Severity untuk tabel Recent Alert Logs.
    Ini tetap menilai 1 alert/log secara individual.
    Bagian ini masih boleh memakai Low/Medium/High/Critical
    karena hanya untuk label log, bukan Threat Activity chart.
    """
    msg_upper = str(msg).upper()

    if "FLOOD" in msg_upper or "DOS" in msg_upper:
        return "High"

    try:
        priority = int(priority)
    except:
        return "Low"

    if priority == 1:
        return "Critical"
    elif priority == 2:
        return "High"
    elif priority == 3:
        return "Medium"
    else:
        return "Low"


def get_range_minutes(selected_range):
    """
    Mengubah pilihan range menjadi durasi menit.
    """
    range_minutes = {
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "24h": 1440,
    }

    return range_minutes.get(selected_range, 30)


def get_threat_activity_level(alert_count_per_minute):
    """
    Threat Activity dihitung berdasarkan jumlah alert IDS per 1 menit.
    Level hanya Low, Medium, dan High.
    """
    if alert_count_per_minute == 0:
        return "No Activity"
    elif alert_count_per_minute <= 500:
        return "Low"
    elif alert_count_per_minute <= 1500:
        return "Medium"
    else:
        return "High"


telegram_cooldown_cache = {}
TELEGRAM_COOLDOWN_SECONDS = 60


def send_telegram_alert(protocol, activity_level, alert_count, alert_rate, selected_range):
    """
    Disabled old Telegram notification.
    Final Telegram notification is handled by notification_data().
    """
    return False


def format_time(influx_time):
    try:
        dt = datetime.fromisoformat(influx_time.replace("Z", "+00:00"))
        dt = dt + timedelta(hours=7)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return influx_time


def alert_data(request):
    allowed_ranges = {
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "24h": "24h",
    }

    protocol_labels = ["MQTT", "REST API", "CoAP", "gRPC"]

    selected_range = request.GET.get("range", "5m")

    if selected_range not in allowed_ranges:
        selected_range = "5m"

    should_notify = False  # disabled old alert_data Telegram notification
    influx_range = allowed_ranges[selected_range]

    client = InfluxDBClient(
        host="influxdb",
        port=8086,
        database="iot_data"
    )

    # Total alert untuk summary card.
    total_query = f'''
        SELECT COUNT("msg") AS total
        FROM "snort_alerts"
        WHERE time > now() - {influx_range}
    '''

    # Detail alert untuk protocol cards, threat activity timeline, dan recent logs.
    log_query = f'''
        SELECT *
        FROM "snort_alerts"
        WHERE time > now() - {influx_range}
        ORDER BY time DESC
        LIMIT 10000000
    '''

    total_result = client.query(total_query)
    total_points = list(total_result.get_points())

    if total_points:
        total_alerts = total_points[0].get("total", 0)
    else:
        total_alerts = 0

    log_result = client.query(log_query)
    points = list(log_result.get_points())

    protocol_counter = Counter()
    alert_logs = []
    active_dos_alerts = 0

    # Counter timeline per protocol.
    # Contoh:
    # {
    #   "MQTT": Counter({"2026-05-12T10:01:00+00:00": 120}),
    #   "REST API": Counter(...),
    # }
    protocol_timeline_counter = {
        protocol: Counter()
        for protocol in protocol_labels
    }

    for item in points:
        msg = item.get("msg", "").replace('"', '')
        dst_port = item.get("dst_port", "")
        src_ip = item.get("src_ip", "")
        priority = item.get("priority", "")
        influx_time = item.get("time", "")

        iot_protocol = get_iot_protocol(dst_port, msg)

        if iot_protocol not in protocol_labels:
            continue

        log_severity = get_log_severity(priority, msg)

        # Total per protocol untuk protocol alert cards.
        protocol_counter[iot_protocol] += 1

        # Total DoS/Flood alerts.
        if "flood" in msg.lower() or "dos" in msg.lower():
            active_dos_alerts += 1

        # Recent Alert Logs.
        detected_attack_display = get_detected_attack_display(
            msg=msg,
            dst_port=dst_port,
            sid=item.get("sid", "")
        )

        alert_logs.append({
            "time": format_time(influx_time),
            "protocol": iot_protocol,
            "alert_type": detected_attack_display,
            "severity": log_severity,
            "source_ip": src_ip,
            "destination_port": dst_port,
            "status": "Detected",
        })

        # Threat Activity per protocol.
        # Window fixed 1 menit.
        try:
            dt = datetime.fromisoformat(influx_time.replace("Z", "+00:00"))
            dt_window = dt.replace(second=0, microsecond=0)
            window_key = dt_window.isoformat()

            protocol_timeline_counter[iot_protocol][window_key] += 1

        except Exception:
            pass

    # =====================================================
    # Build Threat Activity per Protocol
    # =====================================================

    threat_activities = {}

    peak_threat_time = "-"
    peak_threat_count = 0
    peak_threat_activity = "-"
    peak_threat_protocol = "-"

    for protocol in protocol_labels:
        window_counter = protocol_timeline_counter[protocol]
        sorted_window_keys = sorted(window_counter.keys())

        points_data = []

        for window_key in sorted_window_keys:
            alert_count = window_counter.get(window_key, 0)
            activity_level = get_threat_activity_level(alert_count)

            try:
                dt = datetime.fromisoformat(window_key)
                dt_wib = dt + timedelta(hours=7)
                label_time = dt_wib.strftime("%H:%M")
            except Exception:
                label_time = window_key

            points_data.append({
                "x": label_time,
                "y": alert_count,
                "activity": activity_level,
            })

            # Most Peak Threat Time:
            # waktu dengan alert count per menit tertinggi dari semua protocol.
            if alert_count > peak_threat_count:
                peak_threat_count = alert_count
                peak_threat_time = label_time
                peak_threat_activity = activity_level
                peak_threat_protocol = protocol

        threat_activities[protocol] = {
            "points": points_data
        }

    if peak_threat_time != "-":
        most_peak_threat_time = f"{peak_threat_time}"
    else:
        most_peak_threat_time = "-"

    # =====================================================
    # Telegram Notification
    # =====================================================

    if False and should_notify:
        activity_rank = {
            "High": 3,
            "Medium": 2,
            "Low": 1,
            "No Activity": 0,
        }

        for protocol in protocol_labels:
            highest_protocol_activity = "No Activity"
            highest_protocol_count = 0

            for point in threat_activities[protocol]["points"]:
                activity_level = point.get("activity", "No Activity")
                alert_count = point.get("y", 0)

                if (
                    activity_rank.get(activity_level, 0)
                    > activity_rank.get(highest_protocol_activity, 0)
                ):
                    highest_protocol_activity = activity_level
                    highest_protocol_count = alert_count

            if highest_protocol_activity == "High":
                send_telegram_alert(
                    protocol=protocol,
                    activity_level=highest_protocol_activity,
                    alert_count=highest_protocol_count,
                    alert_rate=highest_protocol_count,
                    selected_range=selected_range
                )

    # =====================================================
    # Summary Cards
    # =====================================================

    if protocol_counter:
        most_targeted_protocol = protocol_counter.most_common(1)[0][0]
    else:
        most_targeted_protocol = "-"

    data = {
        "selected_range": selected_range,

        "summary_cards": {
            "total_alerts": total_alerts,
            "detected_dos_alerts": active_dos_alerts,
            "most_targeted_protocol": most_targeted_protocol,
            "most_peak_threat_time": most_peak_threat_time,
        },

        # Ini nanti dipakai untuk protocol alert cards, bukan chart bar.
        "alerts_by_protocol": {
            "labels": protocol_labels,
            "data": [
                protocol_counter.get("MQTT", 0),
                protocol_counter.get("REST API", 0),
                protocol_counter.get("CoAP", 0),
                protocol_counter.get("gRPC", 0),
            ],
            "items": {
                "MQTT": protocol_counter.get("MQTT", 0),
                "REST API": protocol_counter.get("REST API", 0),
                "CoAP": protocol_counter.get("CoAP", 0),
                "gRPC": protocol_counter.get("gRPC", 0),
            }
        },

        "threat_activities": threat_activities,

        "alert_logs": alert_logs[:10],
        "last_updated": (datetime.utcnow() + timedelta(hours=7)).strftime("%H:%M:%S"),
    }

    return JsonResponse(data)
    
def nodes(request):
    return render(request, 'iotdashboard/nodes.html')


def nodes_data(request):
    range_time = "5m"
    status_range_time = "60s"

    protocol_nodes = {
        "mqtt": {
            "entity": "NODE-MQTT",
            "type": "Client/Broker",
            "protocol": "MQTT",
            "alert_keyword": "MQTT",
        },
        "rest": {
            "entity": "NODE-REST",
            "type": "Service",
            "protocol": "REST API",
            "alert_keyword": "REST",
        },
        "coap": {
            "entity": "NODE-COAP",
            "type": "Service",
            "protocol": "CoAP",
            "alert_keyword": "CoAP",
        },
        "grpc": {
            "entity": "NODE-GRPC",
            "type": "Service",
            "protocol": "gRPC",
            "alert_keyword": "gRPC",
        },
    }

    node_list = []

    total_nodes = len(protocol_nodes)
    active_nodes = 0
    inactive_nodes = 0
    alert_nodes = 0

    # =========================
    # NODE TABLE DATA
    # =========================
    for proto_key, meta in protocol_nodes.items():

        # Request count dalam 5 menit terakhir
        q_request = f"""
        SELECT SUM(request_count)
        FROM protocol_metrics
        WHERE time > now() - {range_time}
        AND protocol = '{proto_key}'
        """

        request_result = query_influx(q_request)
        request_count = int(get_first_value(request_result, 0))

       # Avg temperature dan humidity dalam 5 menit terakhir
        q_sensor = f"""
        SELECT MEAN(temperature), MEAN(humidity)
        FROM protocol_metrics
        WHERE time > now() - {range_time}
        AND protocol = '{proto_key}'
        """

        sensor_result = query_influx(q_sensor)

        try:
            values = sensor_result["results"][0]["series"][0]["values"][0]
            avg_temp = values[1]
            avg_humidity = values[2]
        except Exception:
            avg_temp = None
            avg_humidity = None

        if avg_temp is None:
            avg_temp_display = "-"
        else:
            avg_temp_display = f"{float(avg_temp):.2f} °C"

        if avg_humidity is None:
            avg_humidity_display = "-"
        else:
            avg_humidity_display = f"{float(avg_humidity):.2f} %"

        # Last seen
        q_last_seen = f"""
        SELECT LAST(request_count)
        FROM protocol_metrics
        WHERE protocol = '{proto_key}'
        """

        last_seen_result = query_influx(q_last_seen)

        try:
            last_time_raw = last_seen_result["results"][0]["series"][0]["values"][0][0]
            last_seen_raw = format_influx_time(last_time_raw)
        except Exception:
            last_seen_raw = "-"

        if request_count == 0:
            last_seen = "No recent data"
        else:
            last_seen = last_seen_raw

        # Alert count per protokol
        keyword = meta["alert_keyword"]

        q_alert = f"""
        SELECT COUNT(msg)
        FROM snort_alerts
        WHERE time > now() - {status_range_time}
        AND msg =~ /{keyword}/
        """

        alert_result = query_influx(q_alert)
        alert_count = int(get_first_value(alert_result, 0))

        # Status logic
        if alert_count > 0:
            status = "Under Attack"
            alert_nodes += 1
            active_nodes += 1
        elif request_count > 0:
            status = "Active"
            active_nodes += 1
        else:
            status = "Inactive"
            inactive_nodes += 1

        node_list.append({
            "entity": meta["entity"],
            "type": meta["type"],
            "protocol": meta["protocol"],
            "status": status,
            "last_seen": last_seen,
            "avg_temperature": avg_temp_display,
            "avg_humidity": avg_humidity_display,
            "alerts": alert_count,
        })

    # =========================
    # TELEMETRY TREND CHART
    # =========================
    temperature_series = {}
    humidity_series = {}

    for proto_key in protocol_nodes.keys():
        q_temperature_trend = f"""
        SELECT MEAN(temperature)
        FROM protocol_metrics
        WHERE time > now() - {range_time}
        AND protocol = '{proto_key}'
        GROUP BY time(10s) fill(null)
        """

        q_humidity_trend = f"""
        SELECT MEAN(humidity)
        FROM protocol_metrics
        WHERE time > now() - {range_time}
        AND protocol = '{proto_key}'
        GROUP BY time(10s) fill(null)
        """

        temperature_series[proto_key] = parse_influx_series(
            query_influx(q_temperature_trend)
        )

        humidity_series[proto_key] = parse_influx_series(
            query_influx(q_humidity_trend)
        )

    all_telemetry_times = sorted(
        set(temperature_series["mqtt"].keys())
        | set(temperature_series["rest"].keys())
        | set(temperature_series["coap"].keys())
        | set(temperature_series["grpc"].keys())
        | set(humidity_series["mqtt"].keys())
        | set(humidity_series["rest"].keys())
        | set(humidity_series["coap"].keys())
        | set(humidity_series["grpc"].keys())
    )

    telemetry_labels = [format_time_label(t, "5m") for t in all_telemetry_times]

    data = {
        "summary_cards": {
            "total_nodes": total_nodes,
            "active_nodes": active_nodes,
            "inactive_nodes": inactive_nodes,
            "alert_nodes": alert_nodes,
        },
        "node_list": node_list,
        "telemetry_trend": {
            "labels": telemetry_labels,
            "temperature": {
                "mqtt": [temperature_series["mqtt"].get(t, None) for t in all_telemetry_times],
                "rest": [temperature_series["rest"].get(t, None) for t in all_telemetry_times],
                "coap": [temperature_series["coap"].get(t, None) for t in all_telemetry_times],
                "grpc": [temperature_series["grpc"].get(t, None) for t in all_telemetry_times],
            },
            "humidity": {
                "mqtt": [humidity_series["mqtt"].get(t, None) for t in all_telemetry_times],
                "rest": [humidity_series["rest"].get(t, None) for t in all_telemetry_times],
                "coap": [humidity_series["coap"].get(t, None) for t in all_telemetry_times],
                "grpc": [humidity_series["grpc"].get(t, None) for t in all_telemetry_times],
            },
        },
        "last_updated": (datetime.utcnow() + timedelta(hours=7)).strftime("%H:%M:%S"),
        "data_range": "Last 5 minutes",
    }

    return JsonResponse(data)

def summary(request):
    return render(request, 'iotdashboard/summary.html')


def get_summary_range_seconds(selected_range):
    range_seconds = {
        "5m": 5 * 60,
        "15m": 15 * 60,
        "30m": 30 * 60,
        "1h": 60 * 60,
        "24h": 24 * 60 * 60,
    }

    return range_seconds.get(selected_range, 30 * 60)


def get_summary_value(query, default=0):
    result = query_influx(query)

    try:
        value = result["results"][0]["series"][0]["values"][0][1]
        return value if value is not None else default
    except Exception:
        return default


def get_grouped_tag_values(query, tag_name):
    result = query_influx(query)

    try:
        series = result["results"][0].get("series", [])
    except Exception:
        return []

    values = []

    for item in series:
        tags = item.get("tags", {})
        tag_value = tags.get(tag_name)

        if tag_value:
            values.append(tag_value)

    return values


def summary_data(request):
    allowed_ranges = {
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "24h": "24h",
    }

    selected_range = request.GET.get("range", "5m")

    if selected_range not in allowed_ranges:
        selected_range = "5m"

    influx_range = allowed_ranges[selected_range]
    range_seconds = get_summary_range_seconds(selected_range)

    protocols = [
        {
            "key": "mqtt",
            "name": "MQTT",
            "port": "1883",
            "alert_keyword": "MQTT",
        },
        {
            "key": "rest",
            "name": "REST API",
            "port": "5000",
            "alert_keyword": "REST",
        },
        {
            "key": "coap",
            "name": "CoAP",
            "port": "5683",
            "alert_keyword": "CoAP",
        },
        {
            "key": "grpc",
            "name": "gRPC",
            "port": "50051",
            "alert_keyword": "gRPC",
        },
    ]

    summary_rows = []

    total_normal_all = 0
    total_attack_all = 0
    total_packet_all = 0
    total_payload_all = 0
    total_ids_alert_all = 0

    for proto in protocols:
        proto_key = proto["key"]
        proto_name = proto["name"]
        proto_port = proto["port"]
        alert_keyword = proto["alert_keyword"]

        # Jumlah traffic normal dari protocol_metrics
        q_normal = f"""
        SELECT SUM(request_count)
        FROM protocol_metrics
        WHERE time > now() - {influx_range}
        AND protocol = '{proto_key}'
        AND traffic_type = 'normal'
        """

        normal_count = int(get_summary_value(q_normal, 0))

        # Jumlah traffic attack dari protocol_metrics
        q_attack = f"""
        SELECT SUM(request_count)
        FROM protocol_metrics
        WHERE time > now() - {influx_range}
        AND protocol = '{proto_key}'
        AND traffic_type = 'attack'
        """

        attack_count = int(get_summary_value(q_attack, 0))

        total_count = normal_count + attack_count

        # Average latency per protocol
        q_latency = f"""
        SELECT MEAN(latency_ms)
        FROM protocol_metrics
        WHERE time > now() - {influx_range}
        AND protocol = '{proto_key}'
        """

        avg_latency = float(get_summary_value(q_latency, 0))

        # Total payload untuk hitung throughput
        q_payload = f"""
        SELECT SUM(payload_size_bytes)
        FROM protocol_metrics
        WHERE time > now() - {influx_range}
        AND protocol = '{proto_key}'
        """

        total_payload_bytes = float(get_summary_value(q_payload, 0))

        # Throughput KiB/s = total payload bytes / durasi detik / 1024
        avg_throughput_kibps = (total_payload_bytes / range_seconds) / 1024 if range_seconds > 0 else 0

        # Source/client dari protocol_metrics
        q_sources = f"""
        SELECT COUNT(request_count)
        FROM protocol_metrics
        WHERE time > now() - {influx_range}
        AND protocol = '{proto_key}'
        GROUP BY src
        """

        sources = get_grouped_tag_values(q_sources, "src")

        # IDS Alert Count dari snort_alerts.
        # Termasuk alert dari pengujian hping3, karena hping3 terdeteksi oleh Snort,
        # bukan dicatat sebagai request aplikasi di protocol_metrics.
        q_ids_alert = f"""
        SELECT COUNT(msg)
        FROM snort_alerts
        WHERE time > now() - {influx_range}
        AND msg =~ /{alert_keyword}/
        """

        ids_alert_count = int(get_summary_value(q_ids_alert, 0))

        # Source Client hanya dari protocol_metrics agar tidak tercampur dengan source IP Snort/hping3.
        source_display = ", ".join(sources) if sources else "-"

        summary_rows.append({
            "protocol": proto_name,
            "port": proto_port,
            "normal_packet": normal_count,
            "attack_packet": attack_count,
            "total_packet": total_count,
            "ids_alert_count": ids_alert_count,
            "avg_latency": f"{avg_latency:.2f} ms",
            "avg_throughput": f"{avg_throughput_kibps:.3f} KiB/s",
            "source_ip": source_display,
        })

        total_normal_all += normal_count
        total_attack_all += attack_count
        total_packet_all += total_count
        total_payload_all += total_payload_bytes
        total_ids_alert_all += ids_alert_count

    avg_latency_all_query = f"""
    SELECT MEAN(latency_ms)
    FROM protocol_metrics
    WHERE time > now() - {influx_range}
    """

    avg_latency_all = float(get_summary_value(avg_latency_all_query, 0))
    avg_throughput_all = (total_payload_all / range_seconds) / 1024 if range_seconds > 0 else 0

    data = {
        "selected_range": selected_range,
        "summary_cards": {
            "normal_packet": total_normal_all,
            "attack_packet": total_attack_all,
            "total_packet": total_packet_all,
            "ids_alert_count": total_ids_alert_all,
            "avg_latency": f"{avg_latency_all:.2f} ms",
            "avg_throughput": f"{avg_throughput_all:.3f} KiB/s",
        },
        "summary_rows": summary_rows,
        "last_updated": (datetime.utcnow() + timedelta(hours=7)).strftime("%H:%M:%S"),
    }

    return JsonResponse(data)




@csrf_exempt
def maintenance_clear_all_influx_data(request):
    """
    Reset data dashboard di InfluxDB:
    - protocol_metrics
    - snort_alerts

    Catatan:
    File Snort alert_fast.txt tidak ikut dihapus dari tombol ini.
    Untuk reset penuh, gunakan ./reset_test_data.sh dari terminal.
    """
    if request.method != "POST":
        return JsonResponse({
            "status": "error",
            "message": "Method not allowed. Gunakan POST."
        }, status=405)

    errors = []

    try:
        query_influx('DROP MEASUREMENT "protocol_metrics"')
    except Exception as e:
        errors.append(f"protocol_metrics: {str(e)}")

    try:
        query_influx('DROP MEASUREMENT "snort_alerts"')
    except Exception as e:
        errors.append(f"snort_alerts: {str(e)}")

    if errors:
        return JsonResponse({
            "status": "error",
            "message": "Sebagian data gagal dihapus: " + " | ".join(errors)
        }, status=500)

    return JsonResponse({
        "status": "success",
        "message": "Data dashboard berhasil direset. protocol_metrics dan snort_alerts telah dihapus dari InfluxDB."
    })


def dashboard(request):
    return render(request, 'iotdashboard/dashboard.html')


def maintenance(request):
    return render(request, 'iotdashboard/maintenance.html')

@require_POST
def maintenance_clear_protocol_metrics(request):
    try:
        q = 'DROP MEASUREMENT "protocol_metrics"'
        query_influx(q)

        return JsonResponse({
            "success": True,
            "message": "Protocol metrics berhasil dihapus dari InfluxDB."
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Gagal menghapus protocol metrics: {str(e)}"
        }, status=500)


@require_POST
def maintenance_clear_snort_alerts(request):
    try:
        q = 'DROP MEASUREMENT "snort_alerts"'
        query_influx(q)

        return JsonResponse({
            "success": True,
            "message": "Snort alerts berhasil dihapus dari InfluxDB."
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Gagal menghapus snort alerts: {str(e)}"
        }, status=500)

# ============================================================
# FINAL IDS NOTIFICATION ENDPOINT
# Source: snort_alerts
# Severity: based on each IDS alert type
# Alert Intensity: based on alert count in 1 minute
# Notification Level: Severity + Alert Intensity
# ============================================================

def notification_data(request):
    client = InfluxDBClient(
        host="influxdb",
        port=8086,
        database="iot_data"
    )

    query = '''
        SELECT *
        FROM "snort_alerts"
        WHERE time > now() - 1m
        ORDER BY time DESC
        LIMIT 100000
    '''

    try:
        result = client.query(query)
        points = list(result.get_points())
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e),
            "notifications": []
        }, status=500)

    if not points:
        return JsonResponse({
            "status": "ok",
            "notifications": []
        })

    grouped = {
        "MQTT": [],
        "REST API": [],
        "CoAP": [],
        "gRPC": [],
    }

    for item in points:
        msg = item.get("msg", "").replace('"', '')
        dst_port = item.get("dst_port", "")
        protocol = get_iot_protocol(dst_port, msg)

        if protocol in grouped:
            grouped[protocol].append(item)

    notifications = []

    for protocol, items in grouped.items():
        if not items:
            continue

        latest = items[0]
        msg = latest.get("msg", "").replace('"', '') or "IDS alert detected"
        dst_port = latest.get("dst_port", "")
        src_ip = latest.get("src_ip", "") or latest.get("source_ip", "") or "Unknown"
        alert_count = len(items)

        # Severity = tingkat keparahan dari satu alert
        if "flood" in msg.lower() or "dos" in msg.lower() or "syn" in msg.lower() or "hping" in msg.lower():
            severity = "High"
        else:
            severity = "Low"

        # Alert Intensity = jumlah alert IDS dalam 1 menit
        if alert_count <= 10:
            alert_intensity = "Low"
        elif alert_count <= 50:
            alert_intensity = "Medium"
        else:
            alert_intensity = "High"

        # Notification Level = gabungan Severity + Alert Intensity
        if severity == "High" and alert_intensity == "High":
            notification_level = "Critical"
        elif severity == "High" and alert_intensity == "Medium":
            notification_level = "High"
        elif severity == "High" and alert_intensity == "Low":
            notification_level = "Medium"
        else:
            notification_level = "Low"

        # Attack type
        if "hping" in msg.lower():
            attack_type = "Network Flood / hping3"
        elif "syn" in msg.lower():
            attack_type = "TCP SYN Flood / hping3"
        elif "flood" in msg.lower() or "dos" in msg.lower():
            attack_type = "Application or Network Flood / DoS"
        else:
            attack_type = "IDS Alert"

        notifications.append({
            "protocol": protocol,
            "attack_type": attack_type,
            "severity": severity,
            "alert_intensity": alert_intensity,
            "notification_level": notification_level,
            "alert_count": alert_count,
            "source_ip": src_ip,
            "message": msg,
            "time_window": "1 minute",
        })

    rank = {
        "Low": 1,
        "Medium": 2,
        "High": 3,
        "Critical": 4,
    }

    notifications.sort(
        key=lambda item: rank.get(item.get("notification_level"), 0),
        reverse=True
    )

    return JsonResponse({
        "status": "ok",
        "notifications": notifications
    })


# ============================================================
# FINAL IDS NOTIFICATION + TELEGRAM
# This final block overrides previous notification_data definitions.
# ============================================================

IDS_NOTIFICATION_WINDOW = "1m"
IDS_TELEGRAM_COOLDOWN_SECONDS = 60
ids_telegram_cooldown_cache = {}


def ids_notification_rank(level):
    return {
        "Low": 1,
        "Medium": 2,
        "High": 3,
        "Critical": 4,
    }.get(str(level), 0)


def ids_get_severity(msg="", priority=""):
    """
    Severity is based on one IDS alert type, not total alert count.
    """
    msg_upper = str(msg or "").upper()

    if "FLOOD" in msg_upper or "DOS" in msg_upper or "SYN" in msg_upper or "HPING" in msg_upper:
        return "High"

    if "SCAN" in msg_upper or "PROBE" in msg_upper:
        return "Medium"

    try:
        priority = int(priority)
    except Exception:
        return "Low"

    if priority == 1:
        return "Critical"
    if priority == 2:
        return "High"
    if priority == 3:
        return "Medium"

    return "Low"


def ids_get_intensity(alert_count):
    """
    Alert Intensity is based on number of IDS alerts in the last 1 minute.
    """
    try:
        alert_count = int(alert_count)
    except Exception:
        alert_count = 0

    if alert_count <= 0:
        return "No Activity"
    if alert_count <= 10:
        return "Low"
    if alert_count <= 50:
        return "Medium"
    return "High"


def ids_get_notification_level(severity, intensity):
    """
    Notification Level = Severity + Alert Intensity.
    This controls popup color and Telegram priority.
    """
    if severity in ["Critical"] and intensity in ["Medium", "High"]:
        return "Critical"

    if severity in ["High", "Critical"] and intensity == "High":
        return "Critical"

    if severity in ["High", "Critical"] and intensity == "Medium":
        return "High"

    if severity in ["High", "Critical"] and intensity == "Low":
        return "Medium"

    if severity == "Medium" and intensity in ["Medium", "High"]:
        return "Medium"

    return "Low"


def ids_get_attack_type(msg="", dst_port="", sid=""):
    msg_lower = str(msg or "").lower()
    dst_port = str(dst_port or "")
    sid = str(sid or "")

    if "hping3" in msg_lower or "hping" in msg_lower:
        if "udp" in msg_lower:
            return "UDP Flood / hping3"
        if "syn" in msg_lower:
            return "TCP SYN Flood / hping3"
        return "Network Flood / hping3"

    if "tcp syn" in msg_lower or "syn flood" in msg_lower:
        return "TCP SYN Flood / hping3"

    if "udp flood" in msg_lower and dst_port == "5683":
        return "UDP Flood / hping3"

    if "application flood" in msg_lower:
        return "Application Flood / DoS"

    if "flood" in msg_lower or "dos" in msg_lower:
        return "Application or Network Flood / DoS"

    return "IDS Alert"


def ids_build_telegram_message(notification):
    level = notification.get("notification_level", "Low")
    protocol = notification.get("protocol", "Unknown")
    attack_type = notification.get("attack_type", "IDS Alert")
    severity = notification.get("severity", "Unknown")
    intensity = notification.get("alert_intensity", "Unknown")
    alert_count = notification.get("alert_count", 0)
    source_ip = notification.get("source_ip", "Unknown")
    message = notification.get("message", "IDS alert detected")
    time_window = notification.get("time_window", "1 minute")

    icon = "🚨" if level in ["High", "Critical"] else "⚠️"

    return (
        f"{icon} <b>IDS NOTIFICATION - {level.upper()}</b>\\n\\n"
        f"<b>Protocol:</b> {protocol}\\n"
        f"<b>Attack Type:</b> {attack_type}\\n"
        f"<b>Severity:</b> {severity}\\n"
        f"<b>Alert Intensity:</b> {intensity}\\n"
        f"<b>Total Alerts:</b> {alert_count} alerts in the last {time_window}\\n"
        f"<b>Source IP:</b> {source_ip}\\n"
        f"<b>Detection Source:</b> Snort IDS\\n"
        f"<b>Message:</b> {message}\\n\\n"
        f"Please check the Django IoT IDS Dashboard for more details."
    )


def ids_send_telegram(notification):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("Telegram skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not configured.")
        return False

    level = notification.get("notification_level", "Low")
    protocol = notification.get("protocol", "Unknown")

    # Telegram only for Medium, High, Critical
    if level not in ["Medium", "High", "Critical"]:
        return False

    key = f"{protocol}_{level}".lower().replace(" ", "_")
    now = time.time()

    last_data = ids_telegram_cooldown_cache.get(key)
    if last_data:
        last_time = last_data.get("time", 0)
        last_level = last_data.get("level", "Low")

        cooldown_active = now - last_time < IDS_TELEGRAM_COOLDOWN_SECONDS
        not_escalated = ids_notification_rank(level) <= ids_notification_rank(last_level)

        if cooldown_active and not_escalated:
            return False

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": ids_build_telegram_message(notification),
            "parse_mode": "HTML",
        }

        response = requests.post(url, json=payload, timeout=8)

        if response.status_code == 200:
            ids_telegram_cooldown_cache[key] = {
                "time": now,
                "level": level,
            }
            return True

        print("Final Telegram failed:", response.text)
        return False

    except Exception as e:
        print("Final Telegram error:", e)
        return False


def notification_data(request):
    client = InfluxDBClient(
        host="influxdb",
        port=8086,
        database="iot_data"
    )

    query = f'''
        SELECT *
        FROM "snort_alerts"
        WHERE time > now() - {IDS_NOTIFICATION_WINDOW}
        ORDER BY time DESC
        LIMIT 100000
    '''

    try:
        result = client.query(query)
        points = list(result.get_points())
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e),
            "notifications": []
        }, status=500)

    if not points:
        return JsonResponse({
            "status": "ok",
            "notifications": []
        })

    grouped = {
        "MQTT": [],
        "REST API": [],
        "CoAP": [],
        "gRPC": [],
    }

    for item in points:
        msg = item.get("msg", "").replace('"', '')
        dst_port = item.get("dst_port", "")
        protocol = get_iot_protocol(dst_port, msg)

        if protocol in grouped:
            grouped[protocol].append(item)

    notifications = []

    for protocol, items in grouped.items():
        if not items:
            continue

        latest = items[0]
        msg = latest.get("msg", "").replace('"', '') or "IDS alert detected"
        dst_port = latest.get("dst_port", "")
        priority = latest.get("priority", "")
        sid = latest.get("sid", "")
        src_ip = latest.get("src_ip", "") or latest.get("source_ip", "") or "Unknown"
        alert_count = len(items)

        severity = ids_get_severity(msg, priority)
        intensity = ids_get_intensity(alert_count)
        level = ids_get_notification_level(severity, intensity)
        attack_type = ids_get_attack_type(msg, dst_port, sid)

        notification = {
            "protocol": protocol,
            "attack_type": attack_type,
            "severity": severity,
            "alert_intensity": intensity,
            "notification_level": level,
            "alert_count": alert_count,
            "source_ip": src_ip,
            "message": msg,
            "time_window": "1 minute",
        }

        notifications.append(notification)
        ids_send_telegram(notification)

    notifications.sort(
        key=lambda item: ids_notification_rank(item.get("notification_level")),
        reverse=True
    )

    return JsonResponse({
        "status": "ok",
        "notifications": notifications
    })


# ============================================================
# FINAL TELEGRAM MESSAGE OVERRIDE
# Fix: use real newline instead of literal \n
# ============================================================

def ids_build_telegram_message(notification):
    level = notification.get("notification_level", "Low")
    protocol = notification.get("protocol", "Unknown")
    attack_type = notification.get("attack_type", "IDS Alert")
    severity = notification.get("severity", "Unknown")
    intensity = notification.get("alert_intensity", "Unknown")
    alert_count = notification.get("alert_count", 0)
    source_ip = notification.get("source_ip", "Unknown")
    message = notification.get("message", "IDS alert detected")
    time_window = notification.get("time_window", "1 minute")

    icon = "🚨" if level in ["High", "Critical"] else "⚠️"

    return (
        f"{icon} <b>IDS NOTIFICATION - {level.upper()}</b>\n\n"
        f"<b>Protocol:</b> {protocol}\n"
        f"<b>Attack Type:</b> {attack_type}\n"
        f"<b>Severity:</b> {severity}\n"
        f"<b>Alert Intensity:</b> {intensity}\n"
        f"<b>Total Alerts:</b> {alert_count} alerts in the last {time_window}\n"
        f"<b>Source IP:</b> {source_ip}\n"
        f"<b>Detection Source:</b> Snort IDS\n"
        f"<b>Message:</b> {message}\n\n"
        f"Please check the Django IoT IDS Dashboard for more details."
    )

