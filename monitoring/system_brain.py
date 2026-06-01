import time
import requests
from datetime import datetime

# psutil opsiyonel - yoksa fallback kullanir
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("[!] psutil bulunamadi - CPU/RAM verileri simule edilecek. Kurmak icin: pip install psutil")

SYSTEM_STATE = {
    "status": "UNKNOWN",
    "last_check": None,
    "cpu": 0,
    "ram": 0,
    "api_health": {},
    "db_status": "UNKNOWN",
    "deploy_state": "IDLE",
    "error_rate": "0.1%",
    "request_load": "LOW"
}

def check_system_health(base_url):
    global SYSTEM_STATE

    # CPU / RAM
    if HAS_PSUTIL:
        SYSTEM_STATE["cpu"] = psutil.cpu_percent(interval=0.1)
        SYSTEM_STATE["ram"] = psutil.virtual_memory().percent
    else:
        # Fallback: simulated values
        import random
        SYSTEM_STATE["cpu"] = round(random.uniform(5, 35), 1)
        SYSTEM_STATE["ram"] = round(random.uniform(40, 70), 1)

    # API CHECK
    endpoints = [
        "/api/inventory/stats",
        "/api/printers/get_all",
        "/api/users/me"
    ]

    api_results = {}

    for ep in endpoints:
        try:
            r = requests.get(base_url + ep, timeout=2)
            api_results[ep] = r.status_code
        except Exception as e:
            api_results[ep] = "DOWN"

    SYSTEM_STATE["api_health"] = api_results

    # DB SIMULATION STATUS
    SYSTEM_STATE["db_status"] = "OK" if "DOWN" not in api_results.values() else "DEGRADED"

    # OVERALL STATUS
    if SYSTEM_STATE["cpu"] > 90 or SYSTEM_STATE["ram"] > 90:
        SYSTEM_STATE["status"] = "CRITICAL"
    elif "DOWN" in api_results.values():
        SYSTEM_STATE["status"] = "WARNING"
    else:
        SYSTEM_STATE["status"] = "HEALTHY"

    SYSTEM_STATE["last_check"] = datetime.now().strftime("%H:%M:%S")

    return SYSTEM_STATE
