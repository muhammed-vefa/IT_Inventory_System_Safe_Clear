import os
import re

main_path = r'C:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory_System\main.py'

with open(main_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. sync_all_internal fonksiyonunu tanımlayalım (Route ve Worker ortak kullanacak)
sync_all_internal_code = """
def sync_all_internal():
    \"\"\"Tüm modülleri (Envanter, Yazıcı, Depo, Bilgi Bankası) senkronize eden merkezi fonksiyon.\"\"\"
    results = []
    success = True
    from modules.printer_manager import sync_printers_from_excel_internal
    from modules.depot_manager import sync_depot_from_excel_internal
    from modules.notes_manager import sync_kb_from_excel_internal
    
    # 1. Envanter & Ortak Alanlar
    try:
        inv_stats = sync_excel_to_db_internal()
        results.append(f"Envanter: {inv_stats.get('pc_synced', 0)} cihaz güncellendi.")
        results.append(f"Ortak Alanlar: {inv_stats.get('areas_synced', 0)} kayıt güncellendi.")
    except Exception as e:
        results.append(f"Envanter Hatası: {str(e)}")
        success = False

    # 2. Yazıcılar
    try:
        p_count = sync_printers_from_excel_internal()
        results.append(f"Yazıcılar: {p_count} kayıt senkronize edildi.")
    except Exception as e:
        results.append(f"Yazıcı Hatası: {str(e)}")
        success = False

    # 3. Depo & Bilgi Bankası
    try:
        results.append(f"Depo: {sync_depot_from_excel_internal()} ürün güncellendi.")
        results.append(f"Bilgi Bankası: {sync_kb_from_excel_internal()} kayıt güncellendi.")
    except Exception as e:
        results.append(f"Ek Modül Hatası: {str(e)}")
        success = False
        
    return success, results

@app.route('/api/sync/all', methods=['POST'])
@require_admin
def sync_all():
    \"\"\"Tüm Excel dosyalarını senkronize eder.\"\"\"
    try:
        success, results = sync_all_internal()
        
        # GitHub Otomatik Push (Her başarılı güncellemede)
        if success:
            try:
                import subprocess
                BASE_DIR = os.path.dirname(os.path.abspath(__file__))
                sync_script = os.path.join(BASE_DIR, "..", "sync_repos.py")
                if os.path.exists(sync_script):
                    subprocess.Popen(["python", sync_script], shell=True)
                    results.append("GitHub: Yedekleme başlatıldı.")
            except: pass

        resp = jsonify({
            "success": success,
            "message": "Toplu senkronizasyon tamamlandı." if success else "Bazı modüllerde hatalar oluştu.",
            "details": results
        })
        resp.charset = 'utf-8'
        return resp
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
"""

# sync_all route'unu ve sync_all_internal'ı yerleştir
pattern_sync_all = re.compile(r'@app\.route\(\'/api/sync/all\'.*?return resp', re.DOTALL)
content = pattern_sync_all.sub(sync_all_internal_code, content)

# 2. background_sync_worker fonksiyonunu güncelle (sync_all_internal kullansın)
new_worker_code = """
def background_sync_worker():
    \"\"\"Her sabah 07:00'de otomatik senkronizasyon yapar.\"\"\"
    import logging
    import time
    import datetime
    logging.info("Background Sync Worker started.")
    while True:
        now = datetime.datetime.now()
        # Her gün 07:00
        if now.hour == 7 and now.minute == 0:
            logging.info(f"[{now}] Otomatik senkronizasyon tetiklendi...")
            try:
                # Tüm modülleri senkronize et
                success, results = sync_all_internal()
                logging.info(f"Oto-Sync Sonuç: {results}")
                
                # KeyOS Kontrolü
                try:
                    from modules.keyos_service import get_all_mismatches_internal
                    mismatches, error = get_all_mismatches_internal()
                    if not error:
                        logging.info(f"KeyOS Kontrolü Tamamlandı. {len(mismatches)} uyuşmazlık.")
                except: pass
                
                # CUPS Location Sync
                try:
                    from modules.printer_manager import CUPSHelper
                    CUPSHelper.update_db_cups_locations()
                except: pass
                
                time.sleep(65)
            except Exception as e:
                logging.error(f"Scheduled Sync Error: {e}")
        time.sleep(30)
"""

pattern_worker = re.compile(r'def background_sync_worker\(\):.*?time\.sleep\(30\)', re.DOTALL)
content = pattern_worker.sub(new_worker_code, content)

with open(main_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Scheduler ve Merkezi Sync guncellemesi tamamlandi.")
