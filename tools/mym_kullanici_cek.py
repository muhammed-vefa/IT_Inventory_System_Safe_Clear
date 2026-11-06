"""
IT INVENTORY - MYM KULLANICI VE SİCİL NO SENKRONİZASYON ARACI (V2 - EVRENSEL DOSYA DESTEKLİ)
------------------------------------------------------------------------------------------
MYM (mym.kocaelish.com) sistemine bağlanarak güncel kullanıcı listesini çeker,
mym_personnel tablosunu günceller ve VPN kullanıcılarının sicil_no ve
çalışma durumlarını (işten ayrılma güvenlik kontrolü) otomatik senkronize eder.

XLSX, XLS (BIFF8), HTML-XLS ve CSV formatlarının tamamını otomatik tanır ve işler.
"""

import os
import sys
import time
import argparse
import csv
from datetime import datetime

# UTF-8 konsol ayarı
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Proje ana dizinini sys.path'e ekle
project_root = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(project_root) == 'tools':
    project_root = os.path.dirname(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)
os.chdir(project_root)

from core.database_sql import get_db_connection

def ensure_tables(conn):
    """Gerekli tabloların ve kolonların varlığını garantiye alır."""
    cursor = conn.cursor()
    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('vpn_users') AND name = 'sicil_no')
    BEGIN
        ALTER TABLE vpn_users ADD sicil_no NVARCHAR(50)
    END
    
    IF EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('vpn_users') AND name = 'username')
    BEGIN
        ALTER TABLE vpn_users ALTER COLUMN username NVARCHAR(255)
    END

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

def extract_rows_from_file(file_path):
    """Her türlü dosya biçimini (XLSX, XLS, HTML, CSV) otomatik tanır ve satır satır döner."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")
        
    with open(file_path, "rb") as f:
        magic = f.read(2048)
        
    rows = []
    
    # 1. Modern Excel ZIP (XLSX)
    if magic.startswith(b'PK\x03\x04'):
        print("[*] Dosya formatı: Modern Excel (XLSX)")
        import openpyxl
        wb = openpyxl.load_workbook(file_path, data_only=True)
        # MYM KULLANICILAR sayfası varsa onu, yoksa ilk sayfayı al
        if 'MYM KULLANICILAR' in wb.sheetnames:
            ws = wb['MYM KULLANICILAR']
        else:
            ws = wb.active
        for row in ws.iter_rows(values_only=True):
            if any(row):
                rows.append([cell for cell in row])
        wb.close()
        return rows
        
    # 2. Eski İkili Excel (XLS / BIFF8)
    if magic.startswith(b'\xd0\xcf\x11\xe0'):
        print("[*] Dosya formatı: İkili Excel (XLS - BIFF8)")
        try:
            import xlrd
            book = xlrd.open_workbook(file_path)
            sheet = book.sheet_by_index(0)
            for r_idx in range(sheet.nrows):
                rows.append(sheet.row_values(r_idx))
            return rows
        except Exception as e:
            print(f"[!] xlrd okunamadı, pandas deneniyor: {e}")
            import pandas as pd
            df = pd.read_excel(file_path, engine='xlrd')
            rows.append(list(df.columns))
            rows.extend(df.values.tolist())
            return rows
            
    # 3. HTML Tablosu (.xls uzantılı kaydedilmiş ASP.NET çıktısı)
    lower_magic = magic.lower()
    if b'<html' in lower_magic or b'<table' in lower_magic or b'<!doctype' in lower_magic:
        print("[*] Dosya formatı: HTML / ASP.NET Web Tablosu")
        from bs4 import BeautifulSoup
        html_content = ""
        for enc in ['utf-8', 'cp1254', 'iso-8859-9', 'windows-1254']:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    html_content = f.read()
                break
            except Exception:
                continue
                
        soup = BeautifulSoup(html_content, 'html.parser')
        table = soup.find('table')
        if not table:
            text_preview = soup.get_text(strip=True)[:300]
            raise ValueError(f"İndirilen dosyada tablo bulunamadı! Sayfa içeriği: {text_preview}")
            
        for tr in table.find_all('tr'):
            cells = []
            for td in tr.find_all(['td', 'th']):
                cells.append(td.get_text(strip=True))
            if any(cells):
                rows.append(cells)
        return rows
        
    # 4. Metin / CSV Formatı
    print("[*] Dosya formatı: Metin / CSV")
    for enc in ['utf-8', 'cp1254', 'windows-1254']:
        try:
            with open(file_path, "r", encoding=enc) as f:
                reader = csv.reader(f, delimiter=';')
                rows = [r for r in reader if any(r)]
            if len(rows) > 0 and len(rows[0]) > 1:
                return rows
            with open(file_path, "r", encoding=enc) as f:
                reader = csv.reader(f, delimiter=',')
                rows = [r for r in reader if any(r)]
            if len(rows) > 0:
                return rows
        except Exception:
            continue
            
    raise ValueError(f"Dosya biçimi tanınamadı! Dosya boyutu: {len(magic)} bayt")

def sync_data_from_excel(excel_path):
    """İndirilen tablo verilerini veritabanına işler."""
    print(f"\n[*] Dosya çözümleniyor: {excel_path}")
    
    try:
        all_rows = extract_rows_from_file(excel_path)
    except Exception as e:
        print(f"[HATA] Dosya açılamadı / ayrıştırılamadı: {e}")
        return False
        
    if not all_rows or len(all_rows) < 2:
        print("[HATA] Dosyada işlenecek satır bulunamadı!")
        return False
        
    print(f"[*] Toplam Okunan Satır: {len(all_rows)}")
    
    conn = get_db_connection()
    if not conn:
        print("[HATA] Veritabanı bağlantısı kurulamadı!")
        return False
    
    ensure_tables(conn)
    cursor = conn.cursor()
    
    total_mym = 0
    updated_vpn = 0
    risky_detected = 0
    
    # Başlıkları tespit et
    headers = [str(cell).strip().upper() if cell is not None else "" for cell in all_rows[0]]
    
    # Kolon indekslerini belirle
    col_u = 0
    col_c = 2
    col_ad = 3
    col_soyad = 4
    col_tc = 5
    col_kurum = 6
    col_dep = 7
    col_unvan = 9
    col_durum = 10
    col_tel = 11
    col_email = 12
    
    for i, h in enumerate(headers):
        if "KULLANICI ADI" in h or h == "USERNAME": col_u = i
        elif "KULLANICI" in h and "ADI" not in h: col_c = i
        elif h == "ADI" or h == "AD": col_ad = i
        elif h == "SOYADI" or h == "SOYAD": col_soyad = i
        elif "TC" in h: col_tc = i
        elif "KURUM" in h or "ŞİRKET" in h: col_kurum = i
        elif "DEPARTMAN" in h: col_dep = i
        elif "UNVAN" in h or "GÖREV" in h: col_unvan = i
        elif "ÇALIŞMA" in h or "DURUM" in h: col_durum = i
        elif "TELEFON" in h or "CEP" in h: col_tel = i
        elif "MAİL" in h or "EMAIL" in h: col_email = i

    print(f"[*] Kolonlar eşleştirildi: Username={col_u}, Sicil/Kullanıcı={col_c}, Ad={col_ad}, Soyad={col_soyad}, Durum={col_durum}")
    print("[*] Veritabanına aktarım başladı...")
    
    for row in all_rows[1:]:
        if not row or len(row) <= col_u or row[col_u] is None:
            continue
        raw_u = str(row[col_u]).strip()
        if not raw_u or len(raw_u) > 60 or ' ' in raw_u or raw_u.lower() in ['none', 'null', 'toplam', 'toplam:']:
            continue
            
        u = raw_u.lower()
        col_c_val = str(row[col_c]) if len(row) > col_c and row[col_c] else ""
        sicil_no = col_c_val.split(' - ')[0].strip() if ' - ' in col_c_val else ""
        
        ad = str(row[col_ad]).strip() if len(row) > col_ad and row[col_ad] else ""
        soyad = str(row[col_soyad]).strip() if len(row) > col_soyad and row[col_soyad] else ""
        full_name = f"{ad} {soyad}".strip() or u
        tc = str(row[col_tc]).strip() if len(row) > col_tc and row[col_tc] else ""
        kurum = str(row[col_kurum]).strip() if len(row) > col_kurum and row[col_kurum] else ""
        department = str(row[col_dep]).strip() if len(row) > col_dep and row[col_dep] else ""
        title = str(row[col_unvan]).strip() if len(row) > col_unvan and row[col_unvan] else ""
        work_status = str(row[col_durum]).strip() if len(row) > col_durum and row[col_durum] else "Çalışıyor"
        phone = str(row[col_tel]).strip() if len(row) > col_tel and row[col_tel] else ""
        email = str(row[col_email]).strip() if len(row) > col_email and row[col_email] else ""
        
        # 1. mym_personnel tablosunu güncelle/ekle
        cursor.execute("SELECT id FROM mym_personnel WHERE username = ? AND (is_deleted = 0 OR is_deleted IS NULL)", (u,))
        p_row = cursor.fetchone()
        if p_row:
            cursor.execute("""
                UPDATE mym_personnel SET
                    sicil_no = ?, full_name = ?, tc_no = ?, phone = ?, email = ?,
                    department = ?, title = ?, institution = ?, work_status = ?,
                    last_edit_date = GETDATE(), last_edit_user = 'MYM_SYNC'
                WHERE id = ?
            """, (sicil_no, full_name, tc, phone, email, department, title, kurum, work_status, p_row[0]))
        else:
            cursor.execute("""
                INSERT INTO mym_personnel (
                    username, sicil_no, full_name, tc_no, phone, email,
                    department, title, institution, work_status,
                    created_at, last_edit_user, is_deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), 'MYM_SYNC', 0)
            """, (u, sicil_no, full_name, tc, phone, email, department, title, kurum, work_status))
            
        total_mym += 1
        
        # 2. vpn_users tablosundaki mevcut kullanıcıyı güncelle
        cursor.execute("SELECT id, vpn_status FROM vpn_users WHERE username = ? AND (is_deleted = 0 OR is_deleted IS NULL)", (u,))
        v_row = cursor.fetchone()
        if v_row:
            is_risk = 1 if ('ayrıl' in work_status.lower() or 'ayril' in work_status.lower()) else 0
            cursor.execute("""
                UPDATE vpn_users SET
                    sicil_no = COALESCE(NULLIF(?, ''), sicil_no),
                    work_status = ?,
                    is_risk_detected = ?,
                    phone = COALESCE(NULLIF(?, ''), phone),
                    email = COALESCE(NULLIF(?, ''), email),
                    department = COALESCE(NULLIF(?, ''), department),
                    title = COALESCE(NULLIF(?, ''), title),
                    last_edit_date = GETDATE(),
                    last_edit_user = 'MYM_SYNC'
                WHERE id = ?
            """, (sicil_no, work_status, is_risk, phone, email, department, title, v_row[0]))
            updated_vpn += 1
            if is_risk:
                risky_detected += 1
                print(f"    [!] GÜVENLİK ALARMI: {u} ({full_name}) kurumdan ayrılmış görünüyor!")
                
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 65)
    print("  MYM SENKRONİZASYONU TAMAMLANDI!")
    print(f"  - Toplam İşlenen MYM Personeli : {total_mym}")
    print(f"  - Güncellenen VPN Kullanıcısı : {updated_vpn}")
    print(f"  - Ayrıldığı Tespit Edilen Risk: {risky_detected}")
    print("=" * 65)
    return True

def run_mym_sync(username, password, headless=True):
    from playwright.sync_api import sync_playwright
    
    print("=" * 65)
    print("       IT INVENTORY - MYM OTOMATİK VERİ ÇEKME ARACI")
    print("=" * 65)
    print(f"[*] Kullanıcı: {username}")
    print(f"[*] Mod: {'Gizli (Arka Planda)' if headless else 'Görsel (Tarayıcı Açık)'}")
    print("[*] MYM Sistemine bağlanılıyor (https://mym.kocaelish.com)...")
    
    download_dir = os.path.join(project_root, "database")
    os.makedirs(download_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--ignore-certificate-errors',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        context = browser.new_context(
            ignore_https_errors=True,
            accept_downloads=True,
            viewport={'width': 1366, 'height': 768}
        )
        page = context.new_page()
        
        try:
            # 1. Login Sayfasına Git
            page.goto('https://mym.kocaelish.com/Login.aspx', timeout=30000, wait_until='domcontentloaded')
            page.wait_for_timeout(1500)
            
            print("[*] Giriş bilgileri dolduruluyor...")
            user_input = page.locator('input[id*="UserName_Edit_I"], input[name*="UserName"]').first
            pass_input = page.locator('input[type="password"]').first
            
            if not user_input.is_visible(timeout=5000):
                user_input = page.locator('input[type="text"]').first
                
            user_input.fill(username)
            pass_input.fill(password)
            
            # Giriş Butonuna tıkla
            login_btn = page.locator('a.dxm-content:has-text("Giriş"), div#Logon_PopupActions a, a:has-text("Giriş")').first
            if login_btn.is_visible():
                login_btn.click()
            else:
                pass_input.press("Enter")
                
            print("[*] Giriş yapılıyor, sayfa bekleniyor...")
            page.wait_for_timeout(3500)
            
            # Hata kontrolü
            err_box = page.locator('div[id*="ErrorMessage"], span[id*="ErrorMessage"], div.Error')
            if err_box.is_visible():
                err_text = err_box.inner_text().strip()
                if err_text:
                    print(f"\n[HATA] MYM Giriş Başarısız: {err_text}")
                    browser.close()
                    return False
                    
            # 2. Kullanıcılar Listesine Git
            target_url = "https://mym.kocaelish.com/Default.aspx#ViewID=Kullanici_ListView&ObjectClassName=HelpDeskFMS.Module.Kullanici"
            print(f"[*] Kullanıcı listesine gidiliyor...")
            page.goto(target_url, timeout=40000, wait_until='domcontentloaded')
            page.wait_for_timeout(4000)
            
            # 3. Dışa Aktar (Export) Butonunu Bul ve İndir
            print("[*] Dışa Aktar (Excel) butonu aranıyor...")
            export_selectors = [
                'a[title*="Dışa Aktar"]',
                'div[title*="Dışa Aktar"]',
                'a[title*="Export"]',
                'div[id*="ExportAction"]',
                'a.dxm-content:has-text("Dışa Aktar")',
                'a:has-text("Dışa Aktar")',
                'div.dxm-item:has-text("Dışa Aktar")'
            ]
            
            export_btn = None
            for sel in export_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    export_btn = loc
                    break
                    
            actual_saved_file = None
            
            if export_btn:
                print("[*] Dışa Aktar butonuna tıklandı, dosya hazırlanıyor...")
                with page.expect_download(timeout=60000) as download_info:
                    export_btn.click()
                    page.wait_for_timeout(1000)
                    xlsx_opt = page.locator('span:has-text("XLSX"), a:has-text("XLSX"), div:has-text("XLSX")').first
                    if xlsx_opt.is_visible():
                        xlsx_opt.click()
                        
                download = download_info.value
                orig_filename = download.suggested_filename
                ext = os.path.splitext(orig_filename)[1].lower() or '.xlsx'
                actual_saved_file = os.path.join(download_dir, f"MYM_Export_Latest{ext}")
                download.save_as(actual_saved_file)
                print(f"[+] Dosya başarıyla indirildi: {orig_filename} -> {actual_saved_file}")
            else:
                print("[!] Dışa Aktar butonu doğrudan bulunamadı, ekran görüntüsü alınıyor...")
                screenshot_path = os.path.join(project_root, "database", "mym_debug.png")
                page.screenshot(path=screenshot_path)
                print(f"    Ekran görüntüsü kaydedildi: {screenshot_path}")
                
            browser.close()
            
            if actual_saved_file and os.path.exists(actual_saved_file):
                return sync_data_from_excel(actual_saved_file)
            else:
                print("[HATA] MYM'den dosya indirilemedi.")
                return False
                
        except Exception as e:
            print(f"\n[HATA] Senkronizasyon sırasında hata oluştu: {e}")
            import traceback
            traceback.print_exc()
            browser.close()
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MYM Kullanıcı Senkronizasyon Aracı")
    parser.add_argument("--user", help="MYM Kullanıcı Adı")
    parser.add_argument("--pass", dest="password", help="MYM Şifresi")
    parser.add_argument("--headed", action="store_true", help="Tarayıcıyı görünür modda çalıştır")
    args = parser.parse_args()
    
    u = args.user or os.getenv("MYM_USER")
    p = args.password or os.getenv("MYM_PASS")
    
    if not u or not p:
        print("=" * 60)
        print("    MYM GİRİŞ BİLGİLERİ")
        print("=" * 60)
        u = input("MYM Kullanıcı Adı : ").strip()
        import getpass
        try:
            p = getpass.getpass("MYM Şifresi       : ").strip()
        except Exception:
            p = input("MYM Şifresi       : ").strip()
            
    if not u or not p:
        print("[HATA] Kullanıcı adı ve şifre boş bırakılamaz!")
        sys.exit(1)
        
    is_headless = not args.headed
    success = run_mym_sync(u, p, headless=is_headless)
    
    print("\nİşlem tamamlandı. Çıkmak için Enter'a basın...")
    input()
