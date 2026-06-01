import time
import requests
import statistics
import sys
import os

BASE_URL = "http://127.0.0.1:5000"
ITERATIONS = 5

ENDPOINTS = [
    {"name": "Ana Sayfa (HTML)", "url": f"{BASE_URL}/", "method": "GET"},
    {"name": "İstatistikler (Dashboard)", "url": f"{BASE_URL}/api/inventory/stats", "method": "GET"},
    {"name": "PC Listesi", "url": f"{BASE_URL}/api/inventory/pcs", "method": "GET"},
    {"name": "Yazıcı Listesi", "url": f"{BASE_URL}/api/printers/printers/get_all", "method": "GET"},
    {"name": "Monitör Listesi", "url": f"{BASE_URL}/api/inventory/monitors", "method": "GET"},
    {"name": "Mahal Listesi", "url": f"{BASE_URL}/api/mahal/get_all", "method": "GET"},
]

def format_ms(seconds):
    return f"{seconds * 1000:.2f} ms"

def run_benchmark():
    print(f"\n{'='*60}")
    print(f" IT INVENTORY SİSTEMİ HIZ TESTİ BAŞLIYOR (Iterasyon: {ITERATIONS})")
    print(f"{'='*60}")
    print(f"Sunucu Adresi: {BASE_URL}")
    print(f"{'='*60}\n")
    
    results = []

    # Login işlemi gerekiyorsa burada login olabiliriz.
    # Ancak GET istekleri @require_auth içermiyorsa direkt yapılabilir.
    # Eğer içermiyorsa session kullanmalıyız. 
    session = requests.Session()
    try:
        # Örnek Login (gerekliyse)
        # session.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": "password"})
        pass
    except Exception as e:
        print("Login Hatası (Gerekliyse):", e)
    
    total_start_time = time.time()

    for endpoint in ENDPOINTS:
        print(f"[*] Test ediliyor: {endpoint['name']} ({endpoint['url']})")
        
        times = []
        error_count = 0
        
        # Isınma turu
        try:
             session.request(endpoint['method'], endpoint['url'], timeout=10)
        except:
             pass
             
        for i in range(ITERATIONS):
            start = time.time()
            try:
                response = session.request(endpoint['method'], endpoint['url'], timeout=10)
                # print(response.status_code) # Hata tespiti için
                if response.status_code >= 400:
                    error_count += 1
            except requests.exceptions.RequestException:
                error_count += 1
            end = time.time()
            
            times.append(end - start)
            
        avg_time = statistics.mean(times)
        max_time = max(times)
        min_time = min(times)
        
        results.append({
            "name": endpoint['name'],
            "avg": avg_time,
            "min": min_time,
            "max": max_time,
            "errors": error_count
        })
        
        print(f"    -> Ortalama: {format_ms(avg_time)} | Min: {format_ms(min_time)} | Max: {format_ms(max_time)} | Hata: {error_count}\n")
        time.sleep(0.5)

    total_duration = time.time() - total_start_time
    
    print(f"{'='*60}")
    print(f" TEST TAMAMLANDI - ÖZET RAPOR")
    print(f"{'='*60}")
    print(f"{'Endpoint':<25} | {'Ortalama':<10} | {'Minimum':<10} | {'Maksimum':<10} | {'Hata'}")
    print(f"-"*60)
    for res in results:
        print(f"{res['name']:<25} | {format_ms(res['avg']):<10} | {format_ms(res['min']):<10} | {format_ms(res['max']):<10} | {res['errors']}")
    print(f"{'='*60}")
    print(f"Toplam Test Süresi: {total_duration:.2f} saniye")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    try:
        run_benchmark()
    except KeyboardInterrupt:
        print("\n[!] Test kullanıcı tarafından durduruldu.")
        sys.exit(0)
