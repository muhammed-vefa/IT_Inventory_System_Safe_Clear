import os
import sys
# Path patch for sub-folder execution
project_root = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(project_root) == 'tools':
    project_root = os.path.dirname(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)
os.chdir(project_root)

import os
import sys
import datetime
import pandas as pd

# Proje ana dizinine erismek icin path ekle
BASE_DIR = project_root
sys.path.append(BASE_DIR)

try:
    from core.database_sql import get_db_connection, DATA_DIR
    
    print("\n" + "="*80)
    print("   IT ENVANTER - SÜPER ŞEFFAF VERI AKTARIMI (V5 - FULL DIAGNOSTIC)")
    print("="*80)
    
    excel_path = r"C:\WebApps\IT_Inventory_Data\database\SQL_Server_Export_Final.xlsx"
    if not os.path.exists(excel_path):
        print(f"[!] HATA: Excel dosyası bulunamadı: {excel_path}")
        sys.exit(1)

    xls = pd.ExcelFile(excel_path)
    conn = get_db_connection()
    cursor = conn.cursor()

    print("[*] Veritabanı temizleniyor...")
    for t in ["inventory", "notes", "shared_areas", "depot_items", "consumable_items", "printers", "scanners", "barcode_readers", "barcode_printers"]:
        try: cursor.execute(f"DELETE FROM [{t}]")
        except: pass

    now = datetime.datetime.now()

    # --- SİTE ETİKET EŞLEŞTİRME REHBERİ (UI Labels) ---
    UI_LABELS = {
        'pc_no': 'Cihaz No', 'ip': 'IP ADRESİ', 'hostname': 'CİHAZ ADI',
        'location_name': 'BİRİM ADI (MERKEZ)', 'mahal_kodu': 'KONUM KODU',
        'pc_seri': 'SERİ NO', 'mac': 'MAC ADRESİ', 'model': 'MODEL',
        'seri': 'SERİ NO', 'mahal': 'KONUM', 'status': 'DURUM',
        'title': 'BAŞLIK', 'content': 'NOT İÇERİĞİ', 'name': 'ÜRÜN ADI',
        'category': 'KATEGORİ', 'quantity': 'MİKTAR', 'serial_no': 'SERİ NO'
    }

    def find_col(df_cols, keywords):
        for kw in keywords:
            for col in df_cols:
                if kw.lower() == str(col).lower(): return col # Önce Tam Eşleşme
        for kw in keywords:
            for col in df_cols:
                if kw.lower() in str(col).lower(): return col # Sonra Kısmi
        return None

    def diagnostic_import(sheets, table_name, query, mapping):
        for sheet in sheets:
            if sheet not in xls.sheet_names: continue
            
            print(f"\n>>> [{sheet.upper()}] Sayfası Analiz Ediliyor...")
            df = pd.read_excel(excel_path, sheet_name=sheet).fillna('-')
            df_cols = list(df.columns)
            
            final_map = {}
            matched_excel_cols = []
            
            print("    Eşleşme Durumu:")
            print("    " + "-"*65)
            print("    {:<15} | {:<15} | {:<25}".format("SQL Sütun", "Excel Başlık", "Sitedeki Etiket"))
            print("    " + "-"*65)
            
            for db_col, kws in mapping.items():
                found = find_col(df_cols, kws)
                excel_name = found if found else "[BULUNAMADI]"
                ui_label = UI_LABELS.get(db_col, db_col)
                print("    {:<15} | {:<15} | {:<25}".format(db_col, str(excel_name)[:15], ui_label))
                if found:
                    final_map[db_col] = found
                    matched_excel_cols.append(found)

            unused = [c for c in df_cols if c not in matched_excel_cols]
            if unused:
                print(f"    [!] Atlanan Kolonlar: {', '.join(unused[:5])}{'...' if len(unused)>5 else ''}")

            count = 0
            for _, row in df.iterrows():
                try:
                    vals = [str(row.get(final_map[db], '-')) if db in final_map else '-' for db in mapping.keys()]
                    cursor.execute(query, (*vals, now))
                    count += 1
                except Exception as e: pass
            print(f"    [+] Başarı: {count} kayıt aktarıldı.")

    # --- MAPPING TANIMLARI (SQL Başlıklarına Göre Tam Uyum) ---
    diagnostic_import(['pcs', 'queing_machines', 'tablets'], 'inventory', 
        "INSERT INTO inventory (pc_no, ip, device_type, hostname, location_name, mahal_kodu, pc_seri, mac, zimmetlenen_kisi, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        {
            'pc_no': ['pc_no', 'cihaz_no', 'envanter_no'],
            'ip': ['ip', 'ip_adresi'],
            'device_type': ['device_type', 'cihaz_tipi'],
            'hostname': ['hostname', 'makine_adi'],
            'location_name': ['location_name', 'birim', 'açıklama'],
            'mahal_kodu': ['mahal_kodu', 'konum_kodu', 'mahal_no'],
            'pc_seri': ['pc_seri', 'seri_no', 'seri'],
            'mac': ['mac', 'mac_adresi'],
            'zimmetlenen_kisi': ['zimmet', 'kisi', 'sorumlu']
        })

    diagnostic_import(['printers'], 'printers', 
        "INSERT INTO printers (pr_no, model, seri, ip, mac, mahal, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        {
            'pr_no': ['pr_no', 'cihaz_no'],
            'model': ['model', 'cihaz'],
            'seri': ['seri', 'serial_no'],
            'ip': ['ip', 'ip_adresi'],
            'mac': ['mac', 'mac_adresi'],
            'mahal': ['mahal', 'konum', 'location_name'],
            'status': ['status', 'durum']
        })

    diagnostic_import(['areas', 'shared_areas'], 'shared_areas',
        "INSERT INTO shared_areas (name, path, [user], password, created_at) VALUES (?, ?, ?, ?, ?)",
        { 'name': ['name', 'ad'], 'path': ['path', 'yol'], 'user': ['user', 'kullanıcı'], 'password': ['password', 'şifre'] })

    diagnostic_import(['depot_items'], 'depot_items',
        "INSERT INTO depot_items (name, category, quantity, created_at) VALUES (?, ?, ?, ?)",
        { 'name': ['name', 'ad'], 'category': ['category', 'kategori'], 'quantity': ['quantity', 'adet', 'miktar'] })

    diagnostic_import(['consumable_items'], 'consumable_items',
        "INSERT INTO consumable_items (name, category, quantity, created_at) VALUES (?, ?, ?, ?)",
        { 'name': ['name', 'ad'], 'category': ['category', 'kategori'], 'quantity': ['quantity', 'adet', 'miktar'] })

    diagnostic_import(['scanners', 'barcode_readers', 'barcode_printers'], 'scanners',
        "INSERT INTO scanners (name, model, serial_no, status, recorded_device_no, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        { 'name': ['name', 'no'], 'model': ['model'], 'serial_no': ['serial_no', 'seri'], 'status': ['status', 'durum'], 'recorded_device_no': ['recorded_device_no', 'bağlı_pc'] })

    conn.commit()
    conn.close()
    print("\n" + "="*80)
    print("   AKTARIM VE ANALİZ TAMAMLANDI! Lütfen yukarıdaki tabloyu kontrol edin.")
    print("="*80 + "\n")

except Exception as e:
    print(f"\n[HATA] {e}")

input("Çıkmak için bir tuşa basın...")
