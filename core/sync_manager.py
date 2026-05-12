import os, datetime
from core.database_sql import get_db_connection
from core.excel_utils import read_excel_data
from core.utils import _get, _norm_key, _norm_pc_id, _clean
class SyncManager:
 def __init__(self, base_dir):
 self.base_dir = base_dir
 self.db_path = os.path.join(base_dir, 'database', 'ana_database')
 def sync_mahal_and_phones(self):
 p = os.path.join(self.db_path, "mahal_telefon.xlsx")
 if not os.path.exists(p): return
 data = read_excel_data(p)
 conn = get_db_connection()
 # Bu tabloyu ayr bir yerde tutuyor olabiliriz veya inventory gncellerken kullanyoruz.
 # Mahal veritaban genellikle inventory iin referansdr.
 conn.close()
 def sync_inventory(self):
 p = os.path.join(self.db_path, "envanter.xlsx")
 if not os.path.exists(p): return {"skipped": 0}
 data = read_excel_data(p)
 conn = get_db_connection()
 stats = {"added": 0, "updated": 0, "skipped": 0}
 for r in data:
 pc_no = _norm_pc_id(_get(r, ['PC_NO', 'PC NO']))
 if not pc_no:
 stats["skipped"] += 1
 continue
 ip = _get(r, ['IP', 'IP ADRESI'])
 kule = _get(r, ['KULE', 'BLOK'])
 m_kodu = _get(r, ['MAHAL_KODU', 'MAHAL KODU'])
 m_adi = _get(r, ['MAHAL_ADI', 'MAHAL ADI'])
 seri = _get(r, ['SERI_NO', 'SER NO'])
 mac = _get(r, ['MAC', 'MAC ADRESI'])
 win = 1 if 'W' in str(_get(r, ['OS', 'ISLETIM SISTEMI'])).upper() else 0
 keyos = 1 if 'K' in str(_get(r, ['OS', 'ISLETIM SISTEMI'])).upper() else 0
 row = conn.execute("SELECT id FROM inventory WHERE pc_no=?", (pc_no,)).fetchone()
 if row:
 conn.execute("""UPDATE inventory SET ip=?, kule=?, mahal_kodu=?, mahal_adi=?,
 seri_no=?, mac_adresi=?, windows=?, keyos=? WHERE id=?""",
 (ip, kule, m_kodu, m_adi, seri, mac, win, keyos, row.id))
 stats["updated"] += 1
 else:
 conn.execute("""INSERT INTO inventory (pc_no, ip, kule, mahal_kodu, mahal_adi,
 seri_no, mac_adresi, windows, keyos, sahada, type)
 VALUES (?,?,?,?,?,?,?,?,?,1,'PC')""",
 (pc_no, ip, kule, m_kodu, m_adi, seri, mac, win, keyos))
 stats["added"] += 1
 conn.commit()
 conn.close()
 return stats
 def sync_service_records(self):
 # Servis kaytlar senkronizasyonu
 pass
