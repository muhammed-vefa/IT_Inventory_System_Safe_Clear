from flask import Blueprint, jsonify
from core.database_sql import query_db
from core.auth import require_auth
from playwright.sync_api import sync_playwright
import os
import time
import urllib3
import re
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

desktop_central_service_bp = Blueprint('desktop_central_service', __name__, url_prefix='/desktop_central')

def scrape_desktop_central_computers():
    """
    Playwright kullanarak ManageEngine Desktop Central'a baglanir ve 
    bilgisayarlarin IP ve Son Gorulme zamanlarini bir sozluk (IP -> Last Contact Time) olarak dondurur.
    """
    # Eger sistemde proxy vs varsa asmak icin env
    os.environ['NO_PROXY'] = '*'
    
    DC_URL = "https://desktopcentral.ornek-kurum.com:8383"
    USER = "ornek.sistem"
    PASS = "OrnekSifre123!"
    
    results = {}
    
    with sync_playwright() as p:
        # Arka planda gorunmez olarak baslat
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors'])
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        
        try:
            print("[DC] Giris sayfasina gidiliyor...")
            page.goto(DC_URL + "/emsapi/j_security_check", timeout=30000)
            
            # Gizli veya acik inputlara zorla yaz
            try:
                page.fill("input[name='j_username'], #userName", USER, force=True)
                page.fill("input[name='j_password'], #password", PASS, force=True)
                page.select_option("select[name='domainName']", label="Local Authentication", timeout=2000)
            except Exception:
                pass # Domain dropdown olmayabilir
                
            print("[DC] Login tusuna basiliyor...")
            try:
                page.click("input[type='submit'], button[type='submit'], #loginButton", force=True)
            except Exception:
                page.evaluate("document.forms[0].submit()")
                
            page.wait_for_load_state("networkidle", timeout=15000)
            
            if "login" in page.url.lower():
                print("[DC] Login basarisiz! Guncel URL:", page.url)
                return None
                
            print("[DC] Login basarili, bilgisayarlar sayfasina gidiliyor...")
            # Bu API csv dondurur: /som.do?actionToCall=somComputers&exportType=csv
            # Eger indirme API'si kapaliysa UI'dan cekecegiz. CSV'yi indirmeyi deneyelim.
            
            try:
                with page.expect_download(timeout=60000) as download_info:
                    # Goto may not resolve properly for downloads, so we don't await its load state
                    page.goto(DC_URL + "/som.do?actionToCall=somComputers&exportType=csv", timeout=60000)
                    
                download = download_info.value
                temp_path = "C:\\Temp\\dc_computers.csv"
                if not os.path.exists("C:\\Temp"):
                    os.makedirs("C:\\Temp")
                download.save_as(temp_path)
                
                print("[DC] CSV dosyasi indirildi, parse ediliyor...")
                # Parse CSV
                import csv
                with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        ip = row.get("IP Address") or row.get("IP Adresi")
                        last_contact = row.get("Last Contact Time") or row.get("Son Bağlantı Zamanı")
                        os_name = row.get("OS Name") or row.get("İşletim Sistemi")
                        
                        if ip and last_contact:
                            results[ip.strip()] = {
                                "last_contact": last_contact.strip(),
                                "os": os_name.strip() if os_name else "Windows"
                            }
                            
                # Temp dosyayi temizle
                try:
                    os.remove(temp_path)
                except:
                    pass
            except Exception as dl_err:
                print(f"[DC] Download hatasi veya desteklenmiyor: {dl_err}")
                print("[DC] UI uzerinden scrape denemesi...")
                try:
                    page.goto(DC_URL + "/webclient#/uems/agent/som/computers", timeout=60000)
                    page.wait_for_load_state("networkidle", timeout=30000)
                    # UI scrape is not fully implemented as it requires exact table DOM structure
                    # pass
                except Exception as ui_err:
                    print(f"[DC] UI navigation failed: {ui_err}")
                
        except Exception as e:
            print(f"[DC] Scrape Hatasi: {e}")
        finally:
            browser.close()
            
    return results


def perform_dc_sync():
    """
    Desktop Central'dan bilgileri ceker ve pcs tablosunu IP uzerinden gunceller.
    """
    print("[DC] Senkronizasyon baslatildi...")
    dc_data = scrape_desktop_central_computers()
    
    if not dc_data:
        return {"status": "error", "message": "Desktop Central listesi okunamadi. Baglanti veya login hatasi olabilir."}
        
    print(f"[DC] Toplam {len(dc_data)} bilgisayar bulundu. DB guncelleniyor...")
    
    pcs = query_db("SELECT id, ip, pc_serial FROM pcs WHERE is_deleted = 0 AND ip IS NOT NULL AND ip != ''")
    
    matched_count = 0
    updated_count = 0
    
    for pc in pcs:
        db_ip = str(pc['ip']).strip()
        if db_ip in dc_data:
            matched_count += 1
            info = dc_data[db_ip]
            try:
                query_db(
                    "UPDATE pcs SET last_active = ?, operating_system = ? WHERE id = ?",
                    (info['last_contact'], info['os'], pc['id'])
                )
                updated_count += 1
            except Exception as e:
                print(f"[DC] Guncelleme hatasi (ID: {pc['id']}): {e}")
                
    return {
        "status": "success", 
        "message": f"Senkronizasyon tamamlandi. {len(dc_data)} cihaz DC'den okundu, {updated_count} envanter kaydi güncellendi."
    }


@desktop_central_service_bp.route('/manual_sync', methods=['POST'])
@require_auth
def manual_sync():
    try:
        result = perform_dc_sync()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
