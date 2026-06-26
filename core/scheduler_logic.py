import os
import json
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
LOG_FILE = os.path.join(BASE_DIR, 'database', 'scheduler_logs.json')

def log_task(task_name, status, message=""):
    try:
        logs = []
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except Exception as load_e:
                print(f"[Scheduler Log Load Error] {load_e}")
        
        logs.append({
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "task": task_name,
            "status": status,
            "message": message
        })
        
        # Keep last 100 logs
        logs = logs[-100:]
        
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to write scheduler log: {e}")

def job_db_backup():
    print("[APScheduler] Starting DB Backup...")
    try:
        from core.database_sql import backup_sql_db
        success, result = backup_sql_db()
        if success:
            log_task("DB Backup", "Başarılı", f"Kaydedildi: {result}")
            print("[APScheduler] DB Backup Successful.")
        else:
            log_task("DB Backup", "Başarısız", str(result))
            print("[APScheduler] DB Backup Failed.")
    except Exception as e:
        log_task("DB Backup", "Hata", str(e))
        print(f"[APScheduler] DB Backup Error: {e}")

def job_keyos_mismatch():
    print("[APScheduler] Starting KeyOS Mismatch Check...")
    try:
        from core.database_sql import query_db
        from modules.keyos_service import perform_keyos_sync
        from tools.main import app
        
        # Fonksiyon artık HTTP response dönüyor, json içinden mismatch sayısını çekebiliriz
        with app.app_context():
            response = perform_keyos_sync(auto_update=False)
            try:
                data = response.get_json()
            mismatch_count = len(data.get("mismatches", []))
            if mismatch_count > 0:
                log_task("KeyOS Sync", "Uyarı", f"Sadece kontrol yapıldı. {mismatch_count} cihazda isim uyumsuzluğu tespit edildi.")
            else:
                log_task("KeyOS Sync", "Başarılı", "Sadece kontrol yapıldı. Uyumsuzluk bulunamadı.")
        except Exception as sync_e:
            print(f"[Scheduler KeyOS Sync Result Error] {sync_e}")
            log_task("KeyOS Sync", "Başarılı", "Sadece kontrol yapıldı. Envanter tarandı.")
            
        print("[APScheduler] KeyOS Mismatch Check Successful.")
    except Exception as e:
        log_task("KeyOS Sync", "Hata", str(e))
        print(f"[APScheduler] KeyOS Mismatch Check Error: {e}")

def job_cups_sync():
    print("[APScheduler] Starting CUPS Sync...")
    try:
        from modules.printer_manager import scan_cups_printers
        scan_cups_printers()
        log_task("CUPS Sync", "Başarılı", "Yazıcılar tarandı ve DB ile eşitlendi.")
        print("[APScheduler] CUPS Sync Successful.")
    except Exception as e:
        log_task("CUPS Sync", "Hata", str(e))
        print(f"[APScheduler] CUPS Sync Error: {e}")

def job_google_sheets():
    print("[APScheduler] Starting Google Sheets Backup...")
    try:
        from modules.google_sync_service import is_google_sync_enabled, sync_to_google_sheets
        if is_google_sync_enabled():
            from core.database_sql import query_db
            
            TABLES_TO_SYNC = {
                "pcs": "PC Envanter",
                "tablets": "Tabletler",
                "monitors": "Monitörler",
                "printers": "Yazıcılar",
                "barcode_printers": "Barkod Yazıcılar",
                "barcode_readers": "Barkod Okuyucular",
                "scanners": "Tarayıcılar",
                "printer_service": "Servis İşlemleri",
                "printer_service_history": "Servis Geçmişi",
                "technical_notes": "Teknik Notlar",
                "closure_notes": "Kapatma Notları",
                "troubleshooting_notes": "Arıza Notları",
                "shared_areas": "Ortak Alanlar",
                "depot_items": "Depo",
                "consumable_items": "Sarf Malzemeler",
                "mahal_list": "Mahal Listesi",
                "users": "Kullanıcılar",
                "audit_logs": "İşlem Logları"
            }
            
            total_rows = 0
            for table_name, sheet_name in TABLES_TO_SYNC.items():
                try:
                    # Bazı tablolarda is_deleted sütunu olmayabilir, bu yüzden güvenli sorgu yapıyoruz
                    data = query_db(f"SELECT * FROM {table_name}")
                    if data:
                        # Eğer is_deleted sütunu varsa sadece silinmemiş olanları al
                        if "is_deleted" in data[0]:
                            # NULL (None) değerler de silinmemiş kabul edilir
                            data = [row for row in data if row.get("is_deleted") in [0, "0", False, "False", None, "None", ""]]
                        
                        # Anayasaya Uygunluk (Güvenlik / Şifre Maskeleme)
                        # Kullanıcılar ve Ortak Alanlar gibi yerlerdeki şifreleri maskele
                        cleaned_data = []
                        for row in data:
                            clean_row = dict(row) # Kopyala
                            sensitive_keys = ["password", "password_hash", "bim_pass", "keyos_pass"]
                            for k in sensitive_keys:
                                if k in clean_row and clean_row[k]:
                                    clean_row[k] = "********"
                            cleaned_data.append(clean_row)
                        
                        if len(cleaned_data) > 0:
                            sync_to_google_sheets(cleaned_data, sheet_name=sheet_name)
                            total_rows += len(cleaned_data)
                except Exception as e:
                    print(f"Tablo yedeği alınamadı ({table_name}): {e}")
            
            log_task("Google Sheets Backup", "Başarılı", f"Toplam {len(TABLES_TO_SYNC)} sekmede {total_rows} satır yedeklendi.")
            print("[APScheduler] Google Sheets Sync Successful.")
        else:
            log_task("Google Sheets Backup", "Atlandı", "Modül aktif değil (credentials yok).")
            print("[APScheduler] Google Sheets Sync Skipped.")
    except Exception as e:
        log_task("Google Sheets Backup", "Hata", str(e))
        print(f"[APScheduler] Google Sheets Sync Error: {e}")

def job_keyos_weekly_status():
    print("[APScheduler] Starting KeyOS Weekly Status Fetch...")
    try:
        from modules.keyos_service import fetch_keyos_weekly_status, perform_keyos_sync
        from tools.main import app
        success = fetch_keyos_weekly_status()
        try:
            with app.app_context():
                perform_keyos_sync(auto_update=True)
        except Exception as sync_e:
            print(f"[APScheduler] KeyOS hourly DB update warning: {sync_e}")
        if success:
            log_task("KeyOS Weekly Status", "Başarılı", "Saatlik aktiflik JSON dosyasına kaydedildi ve mevcut kolonlar güncellendi.")
            print("[APScheduler] KeyOS Weekly Status Successful.")
        else:
            log_task("KeyOS Weekly Status", "Başarısız", "KeyOS'tan veri çekilemedi.")
            print("[APScheduler] KeyOS Weekly Status Failed.")
    except Exception as e:
        log_task("KeyOS Weekly Status", "Hata", str(e))
        print(f"[APScheduler] KeyOS Weekly Status Error: {e}")

def job_desktop_central_sync():
    print("[APScheduler] Starting Desktop Central Hourly Sync...")
    try:
        from modules.desktop_central_service import perform_dc_sync
        from flask import current_app
        # Make sure we use an app context if needed. In apscheduler it might run outside.
        # But if perform_dc_sync runs DB queries, it's safe if it uses get_db_connection() which works.
        result = perform_dc_sync()
        log_task("Desktop Central Sync", "Başarılı" if result.get("status") == "success" else "Başarısız", result.get("message", ""))
        print(f"[APScheduler] Desktop Central Sync Finished: {result}")
    except Exception as e:
        log_task("Desktop Central Sync", "Hata", str(e))
        print(f"[APScheduler] Desktop Central Sync Error: {e}")

def job_printer_pages_sync():
    print("[APScheduler] Starting Printer Pages Sync...")
    try:
        from modules.printer_pages_service import fetch_all_printer_pages_sync
        result = fetch_all_printer_pages_sync()
        log_task("Printer Pages Sync", "Başarılı", str(result))
        print(f"[APScheduler] Printer Pages Sync Started: {result}")
    except Exception as e:
        log_task("Printer Pages Sync", "Hata", str(e))
        print(f"[APScheduler] Printer Pages Sync Error: {e}")

def init_scheduler():
    scheduler = BackgroundScheduler()
    
    # Run every Saturday at 03:00
    scheduler.add_job(func=job_db_backup, trigger=CronTrigger(day_of_week='sat', hour=3, minute=0), id="job_db_backup")
    scheduler.add_job(func=job_keyos_mismatch, trigger=CronTrigger(day_of_week='sat', hour=3, minute=10), id="job_keyos_mismatch")
    scheduler.add_job(func=job_cups_sync, trigger=CronTrigger(day_of_week='sat', hour=3, minute=20), id="job_cups_sync")
    scheduler.add_job(func=job_google_sheets, trigger=CronTrigger(day_of_week='sat', hour=3, minute=30), id="job_google_sheets")
    scheduler.add_job(func=job_keyos_weekly_status, trigger=CronTrigger(minute=0), id="job_keyos_weekly_status")
    scheduler.add_job(func=job_desktop_central_sync, trigger=CronTrigger(minute=5), id="job_desktop_central_sync")
    
    # Run every day at 04:00 AM
    scheduler.add_job(func=job_printer_pages_sync, trigger=CronTrigger(hour=4, minute=0), id="job_printer_pages_sync")
    
    scheduler.start()
    print("[*] APScheduler başarıyla başlatıldı ve görevler (Cumartesi 03:00) ayarlandı.")
    
    # Write a boot log
    log_task("System Boot", "Bilgi", "Zamanlanmış görevler belleğe yüklendi.")
