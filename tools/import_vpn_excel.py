import os
import sys
import openpyxl
from datetime import datetime, timedelta

# UTF-8 stdout encoding protection for Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Path patch for sub-folder execution
project_root = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(project_root) == 'tools':
    project_root = os.path.dirname(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)
os.chdir(project_root)

from core.database_sql import get_db_connection

def is_valid_username(u):
    if not u:
        return False
    u_str = str(u).strip()
    if not u_str:
        return False
    u_lower = u_str.lower()
    if u_lower in ['none', 'null', 'toplam', 'toplam:', 'kullanici adi', 'kullanıcı adı']:
        return False
    # Boşluk, noktalı virgül içeren veya 60 karakterden uzun olanlar Excel notu/başlığıdır
    if len(u_str) > 60 or ' ' in u_str or ';' in u_str or '\n' in u_str or '(' in u_str:
        return False
    return True

def find_excel_file():
    candidates = []
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        candidates.append(sys.argv[1])
    
    candidates.extend([
        os.path.join(project_root, "database", "VPN.xlsx"),
        os.path.join(project_root, "VPN.xlsx"),
        os.path.join(os.path.expanduser("~"), "Desktop", "VPN.xlsx"),
        r"C:\Users\MUHAMMED-VEFA-IS\Desktop\VPN.xlsx",
        r"C:\WebApps\IT_Inventory_System\database\VPN.xlsx",
        r"C:\WebApps\IT_Inventory_System\VPN.xlsx"
    ])
    
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None

def ensure_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name='vpn_users')
    BEGIN
        CREATE TABLE vpn_users (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(255),
            full_name NVARCHAR(255),
            tc_no NVARCHAR(50),
            phone NVARCHAR(100),
            email NVARCHAR(255),
            department NVARCHAR(255),
            title NVARCHAR(255),
            institution NVARCHAR(255),
            user_type NVARCHAR(50),
            vpn_status NVARCHAR(50) DEFAULT 'Aktif',
            has_petition NVARCHAR(50) DEFAULT 'YOK',
            petition_date DATETIME,
            expiry_date DATETIME,
            petition_file NVARCHAR(255),
            work_status NVARCHAR(50) DEFAULT N'Çalışıyor',
            is_risk_detected BIT DEFAULT 0,
            sicil_no NVARCHAR(50),
            notes NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )
    END
    
    -- Eger kolon 100 karakter kalmissa 255 karaktere genislet
    IF EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('vpn_users') AND name = 'username')
    BEGIN
        ALTER TABLE vpn_users ALTER COLUMN username NVARCHAR(255)
    END
    
    -- sicil_no kolonu yoksa ekle
    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('vpn_users') AND name = 'sicil_no')
    BEGIN
        ALTER TABLE vpn_users ADD sicil_no NVARCHAR(50)
    END
    
    -- MYM Personel Havuzu tablosu
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name='mym_personnel')
    BEGIN
        CREATE TABLE mym_personnel (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(255),
            sicil_no NVARCHAR(50),
            full_name NVARCHAR(255),
            tc_no NVARCHAR(50),
            phone NVARCHAR(100),
            email NVARCHAR(255),
            department NVARCHAR(255),
            title NVARCHAR(255),
            institution NVARCHAR(255),
            work_status NVARCHAR(50) DEFAULT N'Çalışıyor',
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )
    END
    """)
    conn.commit()

def import_vpn(dry_run=False):
    print("=" * 65)
    print("      IT INVENTORY - VPN KULLANICILARI AKTARIM ARACI")
    print("=" * 65)
    if dry_run:
        print("[!] PROVA MODU (DRY-RUN): Veritabanına hiçbir kayıt yazılmayacak.\n")
        
    excel_path = find_excel_file()
    if not excel_path:
        print("[HATA] VPN.xlsx dosyası bulunamadı!")
        print("Lütfen dosyayı 'database/VPN.xlsx' veya Masaüstüne koyun.")
        sys.exit(1)
        
    print(f"[*] Excel Dosyası Bulundu: {excel_path}")
    print("[*] Excel okunuyor (bu işlem birkaç saniye sürebilir)...")
    
    try:
        wb = openpyxl.load_workbook(excel_path, data_only=True)
    except Exception as e:
        print(f"[HATA] Excel açılamadı: {e}")
        sys.exit(1)
        
    # 1. MYM KULLANICILARI OKU
    mym_users = {}
    if 'MYM KULLANICILAR' in wb.sheetnames:
        ws_mym = wb['MYM KULLANICILAR']
        for row in ws_mym.iter_rows(min_row=2, values_only=True):
            raw_u = row[0]
            if is_valid_username(raw_u):
                u = str(raw_u).strip().lower()
                mym_users[u] = {
                    'username': u,
                    'ad': str(row[3]).strip() if row[3] else '',
                    'soyad': str(row[4]).strip() if row[4] else '',
                    'tc': str(row[5]).strip() if row[5] else '',
                    'kurum': str(row[6]).strip() if row[6] else '',
                    'departman': str(row[7]).strip() if row[7] else '',
                    'unvan': str(row[9]).strip() if row[9] else '',
                    'calisma_durumu': str(row[10]).strip() if row[10] else 'Çalışıyor',
                    'telefon': str(row[11]).strip() if row[11] else '',
                    'email': str(row[12]).strip() if row[12] else '',
                    'sicil_no': str(row[2]).split(' - ')[0].strip() if row[2] and ' - ' in str(row[2]) else ''
                }
        print(f"[*] MYM Personel Havuzu Yüklendi: {len(mym_users)} kişi")
    else:
        print("[!] 'MYM KULLANICILAR' sayfası bulunamadı, eşleştirme atlanacak.")
        
    # 2. VPN EXPORT TARIHLERINI OKU
    exp_dates = {}
    if 'VPN EXPORT' in wb.sheetnames:
        ws_exp = wb['VPN EXPORT']
        for row in ws_exp.iter_rows(min_row=2, values_only=True):
            raw_u = row[1]
            if is_valid_username(raw_u):
                u = str(raw_u).strip().lower()
                d = row[3]
                if isinstance(d, datetime):
                    exp_dates[u] = d
                elif d:
                    try:
                        exp_dates[u] = datetime.strptime(str(d)[:10], '%Y-%m-%d')
                    except Exception:
                        pass
        print(f"[*] VPN Export Listesi Yüklendi: {len(exp_dates)} kayıt")
        
    # 3. BAKANLIK VPN LISTESI VE DIGER VPN KULLANICILARINI HARMANLA
    processed = {}
    
    if 'BAKANLIK-VPN Listesi' in wb.sheetnames:
        ws_bak = wb['BAKANLIK-VPN Listesi']
        for row in ws_bak.iter_rows(min_row=2, values_only=True):
            raw_u = row[1]
            if not is_valid_username(raw_u):
                continue
                
            u = str(raw_u).strip().lower()
            ad = str(row[2]).strip() if row[2] else ''
            soyad = str(row[3]).strip() if row[3] else ''
            full_name = f"{ad} {soyad}".strip()
            tc = str(row[4]).strip() if row[4] else ''
            gorev = str(row[6]).strip() if row[6] else ''
            kurum = str(row[7]).strip() if row[7] else ''
            phone = str(row[8]).strip() if row[8] else ''
            email = str(row[9]).strip() if row[9] else ''
            dilekce_var = str(row[10]).strip().upper() if row[10] else 'YOK'
            has_petition = 'VAR' if 'VAR' in dilekce_var else 'YOK'
            
            mym = mym_users.get(u, {})
            if not full_name and mym:
                full_name = f"{mym.get('ad', '')} {mym.get('soyad', '')}".strip()
            if not phone and mym:
                phone = mym.get('telefon', '')
            if not email and mym:
                email = mym.get('email', '')
            if not tc and mym:
                tc = mym.get('tc', '')
                
            department = mym.get('departman', '') or gorev
            title = gorev or mym.get('unvan', '')
            work_status = mym.get('calisma_durumu', 'Çalışıyor')
            is_risk = 1 if ('ayrıl' in work_status.lower() or 'ayril' in work_status.lower()) else 0
            
            combined_info = f"{title} {department} {kurum}".lower()
            if any(x in combined_info for x in ['tabip', 'hekim', 'asistan', 'uzman doktor', 'doçent', 'prof']):
                user_type = 'HEKİM'
            elif any(x in combined_info for x in ['şirket', 'iss', 'firma', 'teknik', 'destek']):
                user_type = 'DIŞ DESTEK'
            else:
                user_type = 'İDARİ'
                
            pet_date = exp_dates.get(u, datetime(2026, 7, 15))
            exp_date = pet_date + timedelta(days=365)
            
            processed[u] = {
                'username': u,
                'full_name': full_name or u,
                'tc_no': tc,
                'phone': phone,
                'email': email,
                'department': department,
                'title': title,
                'institution': kurum or 'KOCAELİ ENTEGRE SAĞLIK KAMPÜSÜ',
                'user_type': user_type,
                'vpn_status': 'Aktif',
                'has_petition': has_petition,
                'petition_date': pet_date,
                'expiry_date': exp_date,
                'work_status': work_status,
                'is_risk_detected': is_risk,
                'sicil_no': mym.get('sicil_no', '')
            }
            
    # VPN EXPORT'ta olup Bakanlık listesinde olmayan varsa onları da ekle
    for u, p_date in exp_dates.items():
        if u not in processed:
            mym = mym_users.get(u, {})
            full_name = f"{mym.get('ad', '')} {mym.get('soyad', '')}".strip() or u
            phone = mym.get('telefon', '')
            email = mym.get('email', '')
            tc = mym.get('tc', '')
            department = mym.get('departman', '')
            title = mym.get('unvan', '')
            work_status = mym.get('calisma_durumu', 'Çalışıyor')
            is_risk = 1 if ('ayrıl' in work_status.lower() or 'ayril' in work_status.lower()) else 0
            
            combined_info = f"{title} {department}".lower()
            if any(x in combined_info for x in ['tabip', 'hekim', 'asistan', 'uzman doktor', 'doçent', 'prof']):
                user_type = 'HEKİM'
            elif any(x in combined_info for x in ['şirket', 'iss', 'firma', 'teknik']):
                user_type = 'DIŞ DESTEK'
            else:
                user_type = 'İDARİ'
                
            exp_date = p_date + timedelta(days=365)
            processed[u] = {
                'username': u,
                'full_name': full_name,
                'tc_no': tc,
                'phone': phone,
                'email': email,
                'department': department,
                'title': title,
                'institution': 'KOCAELİ ENTEGRE SAĞLIK KAMPÜSÜ',
                'user_type': user_type,
                'vpn_status': 'Aktif',
                'has_petition': 'VAR',
                'petition_date': p_date,
                'expiry_date': exp_date,
                'work_status': work_status,
                'is_risk_detected': is_risk,
                'sicil_no': mym.get('sicil_no', '')
            }
            
    wb.close()
    print(f"[*] Toplam İşlenen VPN Kullanıcısı: {len(processed)}")
    
    risky_users = [v for v in processed.values() if v['is_risk_detected'] == 1]
    print(f"[*] [ALARM] Ayrıldığı Halde VPN'i Açık Tespit Edilen Kullanıcı Sayısı: {len(risky_users)}")
    for r in risky_users:
        print(f"    - {r['username']} ({r['full_name']}) | Görev: {r['title']} | Durum: {r['work_status']}")
        
    if dry_run:
        print("\n[+] Prova (dry-run) tamamlandı. Veritabanına yazılmadı.")
        return
        
    # 4. VERİTABANINA YAZ
    print("\n[*] Veritabanına aktarılıyor...")
    conn = get_db_connection()
    if not conn:
        print("[HATA] Veritabanı bağlantısı kurulamadı!")
        sys.exit(1)
        
    ensure_table(conn)
    cursor = conn.cursor()
    
    inserted = 0
    updated = 0
    
    for u, data in processed.items():
        cursor.execute("SELECT id FROM vpn_users WHERE username = ? AND (is_deleted = 0 OR is_deleted IS NULL)", (u,))
        row = cursor.fetchone()
        
        if row:
            # Guncelle
            cursor.execute("""
                UPDATE vpn_users SET
                    full_name = ?, tc_no = ?, phone = ?, email = ?,
                    department = ?, title = ?, institution = ?, user_type = ?,
                    has_petition = ?, petition_date = ?, expiry_date = ?,
                    work_status = ?, is_risk_detected = ?, sicil_no = ?,
                    last_edit_date = GETDATE(), last_edit_user = 'EXCEL_IMPORT'
                WHERE id = ?
            """, (
                data['full_name'], data['tc_no'], data['phone'], data['email'],
                data['department'], data['title'], data['institution'], data['user_type'],
                data['has_petition'], data['petition_date'], data['expiry_date'],
                data['work_status'], data['is_risk_detected'], data.get('sicil_no', ''), row[0]
            ))
            updated += 1
        else:
            # Ekle
            cursor.execute("""
                INSERT INTO vpn_users (
                    username, full_name, tc_no, phone, email,
                    department, title, institution, user_type,
                    vpn_status, has_petition, petition_date, expiry_date,
                    work_status, is_risk_detected, sicil_no,
                    created_at, last_edit_user, is_deleted
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    GETDATE(), 'EXCEL_IMPORT', 0
                )
            """, (
                data['username'], data['full_name'], data['tc_no'], data['phone'], data['email'],
                data['department'], data['title'], data['institution'], data['user_type'],
                data['vpn_status'], data['has_petition'], data['petition_date'], data['expiry_date'],
                data['work_status'], data['is_risk_detected'], data.get('sicil_no', '')
            ))
            inserted += 1
            
    conn.commit()
    
    # 5. MYM PERSONEL HAVUZUNU AYRI TABLOYA DA AKTAR
    if mym_users:
        print("\n[*] MYM Personel Havuzu mym_personnel tablosuna aktarılıyor...")
        mym_inserted = 0
        mym_updated = 0
        for u, mdata in mym_users.items():
            full_name = f"{mdata.get('ad', '')} {mdata.get('soyad', '')}".strip()
            cursor.execute("SELECT id FROM mym_personnel WHERE username = ? AND (is_deleted = 0 OR is_deleted IS NULL)", (u,))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("""
                    UPDATE mym_personnel SET
                        sicil_no = ?, full_name = ?, tc_no = ?, phone = ?, email = ?,
                        department = ?, title = ?, institution = ?, work_status = ?,
                        last_edit_date = GETDATE(), last_edit_user = 'EXCEL_IMPORT'
                    WHERE id = ?
                """, (
                    mdata.get('sicil_no', ''), full_name, mdata.get('tc', ''),
                    mdata.get('telefon', ''), mdata.get('email', ''),
                    mdata.get('departman', ''), mdata.get('unvan', ''),
                    mdata.get('kurum', ''), mdata.get('calisma_durumu', 'Çalışıyor'),
                    existing[0]
                ))
                mym_updated += 1
            else:
                cursor.execute("""
                    INSERT INTO mym_personnel (
                        username, sicil_no, full_name, tc_no, phone, email,
                        department, title, institution, work_status,
                        created_at, last_edit_user, is_deleted
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), 'EXCEL_IMPORT', 0)
                """, (
                    u, mdata.get('sicil_no', ''), full_name, mdata.get('tc', ''),
                    mdata.get('telefon', ''), mdata.get('email', ''),
                    mdata.get('departman', ''), mdata.get('unvan', ''),
                    mdata.get('kurum', ''), mdata.get('calisma_durumu', 'Çalışıyor')
                ))
                mym_inserted += 1
        conn.commit()
        print(f"  - MYM Yeni Eklenen: {mym_inserted} | Güncellenen: {mym_updated} | Toplam: {len(mym_users)}")
    
    conn.close()
    
    print("\n" + "=" * 65)
    print("  AKTARIM BAŞARIYLA TAMAMLANDI!")
    print(f"  - Yeni Eklenen Kullanıcı : {inserted}")
    print(f"  - Güncellenen Kullanıcı   : {updated}")
    print(f"  - Toplam VPN Kullanıcısı  : {len(processed)}")
    print("=" * 65)

if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    try:
        import_vpn(dry_run=is_dry)
    except Exception as e:
        print(f"\n[BEKLENMEYEN HATA]: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if not is_dry:
            input("\nÇıkmak için Enter'a basın...")
