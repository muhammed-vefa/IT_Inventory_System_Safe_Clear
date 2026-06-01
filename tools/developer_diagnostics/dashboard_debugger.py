
import os
import sys
import json
from core.database_sql import get_db_connection
from dotenv import load_dotenv
load_dotenv()

def dashboard_debug_report():
    print("="*60)
    print(" DASHBOARD VERI DOGRULAMA VE DEBUG RAPORU ")
    print("="*60)
    
    conn = get_db_connection()
    
    # 1. PC STATS (INVENTORY)
    pc_query = """
        SELECT 
            COUNT(*) as toplam,
            COUNT(CASE WHEN arizali='1' OR arizali='True' THEN 1 END) as ariza,
            COUNT(CASE WHEN (arizali IS NULL OR arizali='0' OR arizali='False') AND (mahalsiz='1' OR mahalsiz='True') THEN 1 END) as kayip,
            COUNT(CASE WHEN (arizali IS NULL OR arizali='0' OR arizali='False') AND (mahalsiz IS NULL OR mahalsiz='0' OR mahalsiz='False') AND (depo='1' OR depo='True') THEN 1 END) as depo,
            COUNT(CASE WHEN (arizali IS NULL OR arizali='0' OR arizali='False') AND (mahalsiz IS NULL OR mahalsiz='0' OR mahalsiz='False') AND (depo IS NULL OR depo='0' OR depo='False') AND (sahada='1' OR sahada='True') THEN 1 END) as sahada,
            COUNT(CASE WHEN windows='1' OR windows='True' THEN 1 END) as win,
            COUNT(CASE WHEN keyos='1' OR keyos='True' THEN 1 END) as keyos
        FROM inventory WITH (NOLOCK)
        WHERE (device_type='PC' OR device_type IS NULL OR device_type='')
    """
    pc_res = conn.execute(pc_query).fetchone()
    print(f"\n[PC ISTATISTIKLERI]")
    print(f" -> Toplam PC Kaydı: {pc_res['toplam']}")
    print(f" -> Sahada (Kurulu): {pc_res['sahada']}")
    print(f" -> Depoda: {pc_res['depo']}")
    print(f" -> Arizali: {pc_res['ariza']}")
    print(f" -> Kayip: {pc_res['kayip']}")
    print(f" -> OS: Windows ({pc_res['win']}), KeyOS ({pc_res['keyos']})")

    # 2. PRINTER STATS
    pr_query = """
        SELECT 
            COUNT(*) as toplam,
            COUNT(CASE WHEN status IN ('Sahada', 'Kurulu', 'Aktif') THEN 1 END) as sahada,
            COUNT(CASE WHEN status IN ('Arızalı', 'Servis', 'Serviste', 'Tamirde') THEN 1 END) as ariza,
            COUNT(CASE WHEN status IN ('Depo', 'Depoda', 'Stok') THEN 1 END) as depo
        FROM printers WITH (NOLOCK)
        WHERE model NOT LIKE '%Barkod%' AND model NOT LIKE '%Tarayıcı%'
    """
    pr_res = conn.execute(pr_query).fetchone()
    print(f"\n[YAZICI ISTATISTIKLERI]")
    print(f" -> Toplam Yazıcı (DB'de): {pr_res['toplam']}")
    print(f" -> Sahada: {pr_res['sahada']}")
    print(f" -> Depoda: {pr_res['depo']}")
    print(f" -> Arizali: {pr_res['ariza']}")

    # 3. BARCODE & SCANNER
    print(f"\n[BARKOD & TARAYICI DETAYI]")
    bo_depo_stock = conn.execute("SELECT SUM(current_stock) FROM depot_items WHERE UPPER(name) LIKE '%OKUYUCU%'").fetchone()[0] or 0
    bo_kurulu = conn.execute("SELECT COUNT(*) FROM inventory WHERE bo_seri IS NOT NULL AND bo_seri != '' AND bo_seri != '---'").fetchone()[0] or 0
    print(f" -> Barkod Okuyucu: Depo({bo_depo_stock}) + Kurulu({bo_kurulu}) = Toplam({bo_depo_stock + bo_kurulu})")
    
    by_depo_stock = conn.execute("SELECT SUM(current_stock) FROM depot_items WHERE UPPER(name) LIKE '%BARKOD YAZICI%'").fetchone()[0] or 0
    by_kurulu = conn.execute("SELECT COUNT(*) FROM inventory WHERE by_seri IS NOT NULL AND by_seri != '' AND by_seri != '---'").fetchone()[0] or 0
    print(f" -> Barkod Yazıcı: Depo({by_depo_stock}) + Kurulu({by_kurulu}) = Toplam({by_depo_stock + by_kurulu})")

    # 4. KRTIIK KONTROL: Senkronize Edilemeyenler
    print(f"\n[KRITIK KONTROL: SENKRONIZASYON ENGELLERI]")
    # printers tablosuna girmeyen (seri veya mac'i olmayan) kayıt var mı? (Excel'e erişemediğim için DB'deki 'Model' kısıtlamasına bakıyorum)
    null_data = conn.execute("SELECT COUNT(*) FROM printers WHERE (seri IS NULL OR seri = '') AND (mac IS NULL OR mac = '')").fetchone()[0]
    print(f" -> Seri No ve MAC'i eksik oldugu icin gozardi edilen yazıcı kaydı: {null_data}")

    conn.close()
    print("\n" + "="*60)

if __name__ == "__main__":
    dashboard_debug_report()
