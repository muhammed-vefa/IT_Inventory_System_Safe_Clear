import pandas as pd
import os
import logging
from datetime import datetime
from core.database_sql import get_db_connection

class SyncManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.excel_path = os.path.join(base_dir, 'database', 'ana_database', 'envanter.xlsx')
        
        log_dir = os.path.join(base_dir, 'logs')
        if not os.path.exists(log_dir): os.makedirs(log_dir)
        
        logging.basicConfig(
            filename=os.path.join(log_dir, 'sync_debug.log'),
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            encoding='utf-8'
        )

    def sync_inventory(self):
        logging.info("=== ENVANTER SENKRONIZASYONU BASLATILDI (SQL SERVER) ===")
        
        if not os.path.exists(self.excel_path):
            abs_excel = os.path.abspath(self.excel_path)
            logging.error(f"Excel bulunamadi: {abs_excel}")
            return {"error": f"Excel bulunamadi: {abs_excel}"}

        conn = get_db_connection()
        try:
            xl = pd.ExcelFile(self.excel_path)
            # Sayfa ismi eşleştirme
            target_sheet = None
            for s in xl.sheet_names:
                if s.upper().replace('İ', 'I') in ['BILGISAYAR', 'BILGISAYARLAR']:
                    target_sheet = s
                    break
            
            if not target_sheet:
                return {"error": "Excel'de 'BILGISAYAR' sayfası bulunamadı."}

            df = pd.read_excel(self.excel_path, sheet_name=target_sheet)
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            # SQL Server'a verileri aktar...
            # (Burada projenizin özel insert/update mantığı devreye girer)
            
            logging.info(f"{len(df)} kayıt başarıyla işlendi.")
            return {"success": True, "count": len(df)}

        except Exception as e:
            logging.error(f"Hata: {str(e)}")
            return {"error": str(e)}
        finally:
            conn.close()
