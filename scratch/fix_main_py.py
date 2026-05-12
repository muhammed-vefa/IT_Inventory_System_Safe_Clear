import os

path = r'C:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory_System\main.py'

with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Fix the specific block in main.py
old_block = """                        conn.execute(
                            "INSERT INTO printer_service (pr_no, seri, fault_desc, status, sent_date, acq_date, return_date, mahal) VALUES (?,?,?,?,?,?,?,?)",
                            (_clean(_get(r, ['YAZICI NUMARASI', 'PR NO', 'PR NUMARASI', 'ID'])), 
                             _clean(_get(r, ['SERI NUMARASI', 'SERÄ° NUMARASI', 'SERIAL', 'SERI', 'SERÄ°'])), 
                             str(_get(r, ['ARIZA ACIKLAMASI', 'ARIZA AÃ‡IKLAMASI', 'HATA', 'ARIZA', 'FAULT']) or ''),
                             _clean(_get(r, ['DURUM', 'STATUS'])) or 'Serviste',
                             str(_get(r, ['SERVISE GITTIGI TARIH', 'SERVÄ°SE GÄ°TTÄ°ÄžÄ° TARÄ°H', 'DATE', 'TARIH']) or ''),
                             str(_get(r, ['ALINDI TARIH', 'ALINDI TARÄ°H', 'ACQ DATE']) or ''),
                             str(_get(r, ['SERVISTEN GELDIGI TARIH', 'SERVÄ°STEN GELDÄ°ÄžÄ° TARÄ°H', 'RETURN DATE']) or ''),
                             _clean(_get(r, ['MAHAL', 'LOKASYON', 'BIRIM'])))
                        )"""

new_block = """                        conn.execute(
                            "INSERT INTO printer_service (pr_no, seri, mac, fault_desc, status, sent_date, acq_date, return_date, mahal) VALUES (?,?,?,?,?,?,?,?,?)",
                            (_clean(_get(r, ['YAZICI NUMARASI', 'PR NO', 'PR NUMARASI', 'ID'])), 
                             _clean(_get(r, ['SERI NUMARASI', 'SERİ NUMARASI', 'SERIAL', 'SERI', 'SERİ'])), 
                             _clean(_get(r, ['MAC ADRESI', 'MAC ADRESİ', 'MAC', 'MAC ADRESS'])),
                             str(_get(r, ['ARIZA ACIKLAMASI', 'ARIZA AÇIKLAMASI', 'HATA', 'ARIZA', 'FAULT']) or ''),
                             _clean(_get(r, ['DURUM', 'STATUS'])) or 'Serviste',
                             str(_get(r, ['SERVISE GITTIGI TARIH', 'SERVİSE GİTTİĞİ TARİH', 'DATE', 'TARIH']) or ''),
                             str(_get(r, ['ALINDI TARIH', 'ALINDI TARİH', 'ACQ DATE']) or ''),
                             str(_get(r, ['SERVISTEN GELDIGI TARIH', 'SERVİSTEN GELDİĞİ TARİH', 'RETURN DATE']) or ''),
                             _clean(_get(r, ['MAHAL', 'LOKASYON', 'BIRIM'])))
                        )"""

if old_block in content:
    content = content.replace(old_block, new_block)
    print("Block replaced successfully.")
else:
    # Try a more relaxed match if exact match fails due to encoding
    print("Exact block not found, trying partial match.")
    import re
    # Match the INSERT line and its values block
    pattern = re.compile(r'conn\.execute\(\s*"INSERT INTO printer_service \(pr_no, seri, fault_desc, status, sent_date, acq_date, return_date, mahal\) VALUES \(\?,\?,\?,\?,\?,\?,\?,\?\)",.*?\)\s*\)', re.DOTALL)
    if pattern.search(content):
        content = pattern.sub(new_block, content)
        print("Regex replace successful.")
    else:
        print("Regex replace failed.")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
