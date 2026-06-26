import pyodbc

# Veritabanı bağlantı bilgileri
SERVER = 'localhost\\SQLEXPRESS'
DATABASE = 'IT_INVENTORY'
TRUSTED_CONNECTION = 'yes'

def fix_orphaned_pcs():
    try:
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection={TRUSTED_CONNECTION};"
        try:
            conn = pyodbc.connect(conn_str, autocommit=True)
        except pyodbc.Error:
            conn_str = f"DRIVER={{SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection={TRUSTED_CONNECTION};"
            conn = pyodbc.connect(conn_str, autocommit=True)
            
        cursor = conn.cursor()
        
        # Hatalı şekilde SCANNER veya BARCODE_PRINTER'a dönüşmüş PC'leri düzelt
        cursor.execute("UPDATE pcs SET device_type = 'PC' WHERE device_type != 'PC' OR device_type IS NULL")
        
        # Lokasyonları kaybolan PC-007 ve PC-023 için özel düzeltme
        cursor.execute("UPDATE pcs SET location_code = 'A.G0.T6.192', warehouse = 0, on_field = 1 WHERE pc_no = 'PC-007'")
        cursor.execute("UPDATE pcs SET location_code = 'A.07.T6.738.18', warehouse = 0, on_field = 1 WHERE pc_no = 'PC-023'")
        
        conn.commit()
        conn.close()
        print("Bozulan PC'ler (PC-007 ve PC-023 dahil) başariyla onarildi ve listeye geri eklendi!")
        print("Lütfen bu pencereyi kapatip sayfayi yenileyin.")
        
    except Exception as e:
        print(f"Hata oluştu: {str(e)}")

if __name__ == '__main__':
    fix_orphaned_pcs()
    input("Çikmak için ENTER'a basin...")
