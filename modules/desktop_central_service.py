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
    bilgisayarlarin IP ve Son Gorulme zamanlarini API uzerinden dondurur.
    """
    os.environ['NO_PROXY'] = '*'
    
    DC_URL = "https://desktopcentral.kocaelish.com:8383"
    USER = "kocaeli.sistem"
    PASS = "4141KocaeliSistem*!"
    
    results = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors'])
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        
        try:
            print("[DC] Giris sayfasina gidiliyor...")
            page.goto(DC_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            try:
                page.fill("input[name='j_username'], #userName", USER, force=True)
                page.fill("input[name='j_password'], #password", PASS, force=True)
                page.click("input[type='submit'], button[type='submit'], #loginButton", force=True)
                page.wait_for_load_state("networkidle", timeout=30000)
            except Exception as e:
                print(f"[DC] Login formu doldurulamadi: {e}")
                
            print("[DC] API'den veriler cekiliyor...")
            
            page_num = 1
            has_more = True
            
            while has_more:
                resp = context.request.get(f"{DC_URL}/api/1.3/som/computers?page={page_num}")
                if resp.ok:
                    data = resp.json()
                    message_resp = data.get('message_response', {})
                    computers = message_resp.get('computers', [])
                    
                    for row in computers:
                        ip = row.get("ip_address")
                        last_contact_ms = row.get("agent_last_contact_time")
                        os_name = row.get("os_name") or row.get("os_platform_name") or "Windows"
                        
                        if ip and last_contact_ms:
                            dt = datetime.fromtimestamp(last_contact_ms / 1000.0)
                            results[ip.strip()] = {
                                "last_contact": dt.strftime('%Y-%m-%d %H:%M:%S'),
                                "os": str(os_name).strip()
                            }
                            
                    total = message_resp.get('total', 0)
                    limit = message_resp.get('limit', 25)
                    
                    if page_num * limit >= total or not computers:
                        has_more = False
                    else:
                        page_num += 1
                else:
                    print(f"[DC] API cagrisi basarisiz: HTTP {resp.status} (Sayfa: {page_num})")
                    break
                
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
    
    # Save DC data to a separate JSON file for the Excel report
    import json
    try:
        dc_file_path = os.path.join(os.getcwd(), 'data', 'dc_weekly_status.json')
        with open(dc_file_path, "w", encoding="utf-8") as f:
            json.dump({"devices": dc_data}, f, ensure_ascii=False, indent=4)
        print("[DC] dc_weekly_status.json dosyasi kaydedildi.")
    except Exception as e:
        print(f"[DC] dc_weekly_status.json kaydedilemedi: {e}")
        
    # Ensure last_active exists silently
    try:
        from modules.inventory_core import check_column_exists, _SCHEMA_CACHE
        if not check_column_exists('pcs', 'last_active'):
            try:
                query_db("ALTER TABLE pcs ADD last_active VARCHAR(50)")
            except Exception:
                pass
            if 'pcs' in _SCHEMA_CACHE:
                del _SCHEMA_CACHE['pcs']
    except Exception:
        pass # Zaten varsa yoksay
    
    pcs = query_db("SELECT id, ip, pc_serial, last_active FROM pcs WHERE is_deleted = 0 AND ip IS NOT NULL AND ip != ''")
    
    db_ips = {}
    for pc in pcs:
        db_ip = str(pc['ip']).strip()
        if db_ip:
            if db_ip not in db_ips:
                db_ips[db_ip] = []
            db_ips[db_ip].append(pc)
    
    matched_count = 0
    updated_count = 0
    
    import dateutil.parser as parser
    
    for ip, info in dc_data.items():
        if ip in db_ips:
            matched_count += 1
            for pc in db_ips[ip]:
                try:
                    if "windows" in str(info['os']).lower():
                        # Tarih kiyaslamasi (KeyOS'un yeni verisini ezmemek icin)
                        db_last_active = pc.get('last_active')
                        new_last_active = info['last_contact']
                        
                        should_update = True
                        if db_last_active and new_last_active:
                            try:
                                db_dt = parser.parse(str(db_last_active), fuzzy=True)
                                new_dt = parser.parse(str(new_last_active), fuzzy=True)
                                
                                # Eger DB'deki KeyOS/DC tarihi, DC'den gelen tarihten daha yeniyse
                                if new_dt < db_dt:
                                    should_update = False
                                    print(f"[DC DEBUG] Skipping update for PC ID {pc['id']} because DB has newer activity ({db_dt}) than DC ({new_dt})")
                            except Exception:
                                pass
                        
                        if should_update:
                            print(f"[DC DEBUG] Updating PC ID {pc['id']} (IP: {ip}) with last_contact: {new_last_active}")
                            query_db(
                                "UPDATE pcs SET last_active = ?, windows = 1, keyos = 0 WHERE id = ?",
                                (new_last_active, pc['id'])
                            )
                            updated_count += 1
                except Exception as e:
                    print(f"[DC] DB Guncelleme Hatasi (ID {pc['id']}): {e}")
                
    print(f"[DC] Eslesen makine sayisi: {matched_count}")
    print(f"[DC] Guncellenen Windows makine sayisi: {updated_count}")
    return {"status": "success", "message": f"{updated_count} adet bilgisayar veritabaninda guncellendi."}


@desktop_central_service_bp.route('/sync', methods=['POST'])
@require_auth
def manual_sync():
    success = perform_dc_sync()
    if success:
        return jsonify({"success": True, "message": "Desktop Central senkronizasyonu tamamlandı."})
    else:
        return jsonify({"success": False, "error": "Senkronizasyon sırasında hata oluştu. Logları kontrol edin."}), 500

import threading
from modules.remote_installer import remote_install_msi

def background_bulk_install(ips, username, password, msi_path):
    print(f"--- Toplu Ajan Kurulumu Basladi ({len(ips)} cihaz) ---")
    for ip in ips:
        ip = ip.strip()
        if not ip: continue
        print(f"[{ip}] Kurulum baslatiliyor...")
        succ, msg = remote_install_msi(ip, username, password, msi_path)
        if succ:
            print(f"[{ip}] BASARILI: {msg}")
        else:
            print(f"[{ip}] HATA: {msg}")
    print(f"--- Toplu Ajan Kurulumu Bitti ---")

@desktop_central_service_bp.route('/bulk_install', methods=['POST'])
@require_auth
def bulk_install_agent():
    """Toplu ajan kurulumunu baslatir"""
    try:
        data = request.json
        ips_raw = data.get('ips', '')
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not ips_raw or not username or not password:
            return jsonify({"success": False, "error": "IP listesi, kullanici adi ve sifre zorunludur."}), 400
            
        ips = [ip.strip() for ip in ips_raw.replace('\n', ',').split(',') if ip.strip()]
        if not ips:
            return jsonify({"success": False, "error": "Gecerli bir IP adresi bulunamadi."}), 400
            
        installer_folder = os.path.join(os.getcwd(), 'data', 'agent_installer', 'directsetup')
        if not os.path.exists(installer_folder):
            return jsonify({"success": False, "error": f"Sunucuda kurulum klasoru bulunamadi: {installer_folder}. Lütfen ajan zip dosyasini cikarip bu yola koyun."}), 404
            
        # Arka planda calistir
        thread = threading.Thread(target=background_bulk_install, args=(ips, username, password, installer_folder))
        thread.daemon = True
        thread.start()
        
        return jsonify({"success": True, "message": f"{len(ips)} cihaz icin kurulum islemi arka planda baslatildi."})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
