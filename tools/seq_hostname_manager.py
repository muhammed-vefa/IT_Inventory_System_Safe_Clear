import os
import sys
import argparse
import re
import datetime
import urllib3
import requests
from dotenv import load_dotenv

# Base directory setup and path patch
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from core.database_sql import get_db_connection
from modules.keyos_service import KeyOSClient, KEYOS_LOGIN_URL

def parse_args():
    parser = argparse.ArgumentParser(description="IT Inventory System — Hostname Sequence Manager")
    parser.add_argument("--location", required=True, help="Mahalle kodu (Örn: AB1T5143)")
    parser.add_argument("--execute", action="store_true", default=False, help="Değişiklikleri DB ve KeyOS'a uygular (Varsayılan: Dry-Run)")
    parser.add_argument("--keyos-user", help="KeyOS Kullanıcı Adı (Opsiyonel)")
    parser.add_argument("--keyos-pass", help="KeyOS Şifresi (Opsiyonel)")
    return parser.parse_args()

def main():
    args = parse_args()
    location_code = args.location.strip().upper()
    execute_mode = args.execute

    # Load Environment variables
    env_path = os.path.join(project_root, ".env")
    if not os.path.exists(env_path):
        env_path = os.path.join(project_root, "tools", ".env")
    load_dotenv(env_path, override=True)

    print("=" * 70)
    print(f" HOSTNAME SEQUENCE MANAGER — HEDEF MAHALLE: {location_code}")
    print(f" ÇALIŞMA MODU: {'[ EXECUTE / CANLI UYGULAMA ]' if execute_mode else '[ DRY-RUN / SİMÜLASYON TESTİ ]'}")
    print("=" * 70)

    # 1. DB bağlantısı
    conn = get_db_connection()
    if not conn:
        print("[!] Veritabanı bağlantısı kurulamadı. Program sonlandırılıyor.")
        sys.exit(1)

    cursor = conn.cursor()
    cursor.execute("""
        SELECT pc_serial, hostname, ip, mac, pc_no 
        FROM pcs 
        WHERE UPPER(location_code) = ? AND is_deleted = 0
    """, (location_code,))
    
    records = cursor.fetchall()
    if not records:
        print(f"[-] '{location_code}' mahalle koduna bağlı aktif bilgisayar kaydı bulunamadı.")
        conn.close()
        sys.exit(0)

    print(f"[*] Toplam {len(records)} bilgisayar kaydı veritabanından çekildi.")

    # 2. Hostname pattern analizi ve sıralama
    # Pattern: {mahal_kodu}x{sıra_no} -> Örn: AB1T5143x01
    pattern = re.compile(rf"^{re.escape(location_code)}x(\d+)$", re.IGNORECASE)
    
    sequenced_pcs = []
    other_pcs = []

    for r in records:
        serial, hostname, ip, mac, pc_no = r
        hostname_str = str(hostname or '').strip()
        match = pattern.match(hostname_str)
        
        if match:
            seq_num = int(match.group(1))
            sequenced_pcs.append({
                "serial": serial,
                "hostname": hostname_str,
                "seq_num": seq_num,
                "ip": ip or '-',
                "mac": mac or '-',
                "pc_no": pc_no or '-'
            })
        else:
            other_pcs.append({
                "serial": serial,
                "hostname": hostname_str,
                "ip": ip or '-',
                "mac": mac or '-',
                "pc_no": pc_no or '-'
            })

    # Sıra numarasına göre küçükten büyüğe sıralama
    sequenced_pcs.sort(key=lambda x: x["seq_num"])

    # 3. Yeniden sıralama planı oluşturma
    planned_changes = []
    renamed_count = 0

    print("\n[*] Hostname sıralama planı çıkarılıyor...")
    for idx, pc in enumerate(sequenced_pcs, start=1):
        expected_seq = f"{idx:02d}"
        expected_hostname = f"{location_code}x{expected_seq}"
        
        is_changed = pc["hostname"].upper() != expected_hostname.upper()
        if is_changed:
            renamed_count += 1

        planned_changes.append({
            "serial": pc["serial"],
            "old_hostname": pc["hostname"],
            "new_hostname": expected_hostname,
            "ip": pc["ip"],
            "mac": pc["mac"],
            "pc_no": pc["pc_no"],
            "is_changed": is_changed
        })

    # Planı Tablo Olarak Yazdır
    print("\n" + "-" * 105)
    print(f"{'Seri No':<20} | {'PC No':<10} | {'Eski Hostname':<20} | {'Yeni Hostname':<20} | {'IP Adresi':<15} | {'Durum':<10}")
    print("-" * 105)
    for p in planned_changes:
        status_text = "DEĞİŞECEK" if p["is_changed"] else "AYNI KALACAK"
        print(f"{p['serial']:<20} | {p['pc_no']:<10} | {p['old_hostname']:<20} | {p['new_hostname']:<20} | {p['ip']:<15} | {status_text:<10}")
    print("-" * 105)

    if other_pcs:
        print("\n[!] UYARI: Standart isimlendirme formatına uymayan makineler (Sıralamaya DAHİL EDİLMEDİ):")
        for op in other_pcs:
            print(f"  - Seri: {op['serial']} | Hostname: {op['hostname']} | IP: {op['ip']}")

    if renamed_count == 0:
        print("\n[*] Sıralamada herhangi bir kopukluk veya düzensizlik bulunmuyor.")
        conn.close()
        sys.exit(0)

    print(f"\n[*] Toplam {renamed_count} makinenin adı yeniden düzenlenecektir.")

    # 4. Kimlik Doğrulama Bilgilerinin Hazırlanması
    keyos_u = args.keyos_user
    keyos_p = args.keyos_pass

    # Eğer argüman olarak geçilmediyse .env'den oku
    if not keyos_u or not keyos_p:
        env_u = os.getenv("KEYOS_USER")
        env_p = os.getenv("KEYOS_PASS")
        # Varsayılan/örnek değerler değilse kullan
        if env_u and env_u != "dashboard" and env_p and env_p != "DashBoard2025*!":
            keyos_u = env_u
            keyos_p = env_p

    # Eğer hala yoksa çalışmayı durdur (Kullanıcıya bilgi ver)
    if not keyos_u or not keyos_p:
        print("\n[!] HATA: KeyOS MGT kullanıcı adı ve şifresi bulunamadı.")
        print("[*] Lütfen 'tools/.env' dosyasına kendi KEYOS_USER / KEYOS_PASS parametrelerinizi ekleyin veya scripti çalıştırırken '--keyos-user' ve '--keyos-pass' argümanlarıyla kendi bilgilerinizi sağlayın.")
        conn.close()
        sys.exit(1)

    # 5. Canlı Uygulama (Execute) Adımları
    if execute_mode:
        print("\n[*] Canlı güncelleme işlemi başlatılıyor...")
        print(f"[*] KeyOS MGT ({KEYOS_LOGIN_URL}) bağlantısı kuruluyor... (Kullanıcı: {keyos_u})")
        
        client = KeyOSClient(keyos_u, keyos_p)
        keyos_ok = False
        serial_to_id = {}
        
        if client.login():
            print("[+] KeyOS MGT girişi başarılı.")
            # KeyOS'taki tüm bilgisayarları bir kez çek
            api_url = KEYOS_LOGIN_URL.replace("/login", "/computers/getDataTable")
            try:
                resp_all = client.session.post(api_url, data={
                    'draw': 1, 'start': 0, 'length': 10000,
                    'search[value]': '', 'search[regex]': 'false'
                }, timeout=45, verify=False)
                
                if resp_all.status_code == 200:
                    all_computers = resp_all.json().get('data', [])
                    for comp in all_computers:
                        s = str(comp.get('serialNumber', '')).strip().upper()
                        if s and len(s) > 2:
                            serial_to_id[s] = comp.get('id')
                    keyos_ok = True
                    print(f"[+] KeyOS'tan toplam {len(all_computers)} bilgisayar kaydı eşleştirilmek üzere çekildi.")
                else:
                    print(f"[!] HATA: KeyOS bilgisayar tablosu çekilemedi (Statü: {resp_all.status_code}).")
            except Exception as ke:
                print(f"[!] HATA: KeyOS listesi çekilirken bağlantı hatası oluştu: {ke}")
        else:
            print("[!] HATA: KeyOS girişi başarısız oldu. Lütfen KeyOS bilgilerinizi kontrol edin.")
            conn.close()
            sys.exit(1)

        edit_user = "System_Sequence_Manager"
        edit_date = datetime.datetime.now()

        # Database ve KeyOS güncellemelerini döngüyle uygula
        success_db = 0
        success_keyos = 0

        for p in planned_changes:
            if not p["is_changed"]:
                continue

            # A. Veritabanını Güncelle
            try:
                cursor.execute("""
                    UPDATE pcs 
                    SET hostname = ?, last_edit_date = ?, last_edit_user = ? 
                    WHERE pc_serial = ?
                """, (p["new_hostname"], edit_date, edit_user, p["serial"]))
                success_db += 1
            except Exception as dbe:
                print(f"[!] Veritabanı Güncelleme Hatası ({p['serial']}): {dbe}")

            # B. KeyOS MGT Güncelle
            if keyos_ok:
                computer_id = serial_to_id.get(p["serial"].upper())
                if computer_id:
                    try:
                        update_url = KEYOS_LOGIN_URL.replace("/login", "/updateComputer/update")
                        update_payload = {
                            "id": str(computer_id),
                            "serialNumber": p["serial"],
                            "hostName": p["new_hostname"]
                        }
                        update_headers = {
                            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                            "X-Requested-With": "XMLHttpRequest"
                        }
                        # Request call
                        import json
                        r_up = client.session.post(
                            update_url, 
                            data=json.dumps(update_payload), 
                            headers=update_headers, 
                            timeout=15, 
                            verify=False
                        )
                        if r_up.status_code == 200 and "success" in r_up.text:
                            success_keyos += 1
                        else:
                            print(f"[!] KeyOS Güncelleme API Hatası ({p['serial']}): Kod {r_up.status_code} - Cevap: {r_up.text}")
                    except Exception as kup_e:
                        print(f"[!] KeyOS Güncelleme Hatası ({p['serial']}): {kup_e}")
                else:
                    print(f"[-] KeyOS'ta '{p['serial']}' seri numaralı bilgisayar eşleşmedi. KeyOS adı güncellenemedi.")

        # Değişiklikleri kaydet
        conn.commit()
        print(f"\n[+] Canlı Güncelleme Tamamlandı:")
        print(f"  - Veritabanı Güncellenen PC Sayısı: {success_db}/{renamed_count}")
        print(f"  - KeyOS MGT Güncellenen PC Sayısı: {success_keyos}/{renamed_count}")
        print("[*] Sıralama başarıyla güncellendi.")

    else:
        print("\n[*] UYARI: Değişiklikleri uygulamak için scripti '--execute' parametresiyle çalıştırmalısınız.")

    conn.close()
    print("\n[*] Program başarıyla tamamlandı.")

if __name__ == '__main__':
    main()
