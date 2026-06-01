
import pyodbc
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def recover_pc_numbers():
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_NAME')
    uid = os.getenv('DB_USER')
    pwd = os.getenv('DB_PASS')
    
    conn_str = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={uid};PWD={pwd};'
    excel_path = os.path.join('database', 'ana_database', 'envanter.xlsx')
    
    if not os.path.exists(excel_path):
        print(f"Hata: Excel dosyası bulunamadı: {excel_path}")
        return

    try:
        # 1. Excel'den gerçek veriyi oku
        print("Excel verisi okunuyor...")
        df = pd.read_excel(excel_path)
        
        # Olası sütun isimlerini kontrol et
        pc_col = None
        for col in ['PC', 'PC NO', 'BİLGİSAYAR NO', 'ID']:
            if col in df.columns:
                pc_col = col
                break
        
        if not pc_col:
            print("Hata: Excel'de PC numarası sütunu bulunamadı!")
            return

        print(f"Excel'de bulunan PC sütunu: {pc_col}")
        
        # 2. Veritabanına bağlan
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # 3. Bozuk kayıtları bul (hostname ve mahal ile eşleşme yapacağız)
        print("Veritabanındaki bozuk kayıtlar kontrol ediliyor...")
        cursor.execute("SELECT id, hostname, mahal_kodu FROM inventory WHERE pc_no = '---' OR pc_no IS NULL OR pc_no = ''")
        broken_records = cursor.fetchall()
        
        if not broken_records:
            print("Veritabanında bozuk (---) kayıt bulunamadı. Belki veritabanı PC No'ları kaybetmedi, sadece UI'da öyle görünüyor?")
            conn.close()
            return

        print(f"{len(broken_records)} adet bozuk kayıt bulundu. Restorasyon başlıyor...")
        
        success_count = 0
        for rid, host, mk in broken_records:
            # Excel'de aynı mahal ve hostname (veya benzeri) olan satırı bul
            # Not: hostname DB'de otomatik oluştuğu için Excel'de olmayabilir. 
            # Bu yüzden Excel'deki Mahal Kodu ve o mahalin N. sırasındaki PC'yi eşleştirmeyi deneyelim.
            
            # Daha basit: Excel'deki satır sırasına göre DB ID'leri eşleşiyor mu?
            # Eğer DB ID'leri 1'den başlıyorsa ve Excel sırası ile aynıysa:
            match = df[df.index == (rid - 1)] # SQL ID'si 1-based, index 0-based
            if not match.empty:
                real_pc = str(match.iloc[0][pc_col]).strip().upper()
                if real_pc and real_pc != '---' and real_pc != 'NAN':
                    cursor.execute("UPDATE inventory SET pc_no = ? WHERE id = ?", (real_pc, rid))
                    success_count += 1
        
        conn.commit()
        print(f"İşlem Tamamlandı! {success_count} adet PC numarası geri getirildi.")
        conn.close()
        
    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    recover_pc_numbers()
