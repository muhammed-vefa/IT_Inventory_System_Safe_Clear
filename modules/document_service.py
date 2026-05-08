import os
import shutil
import datetime
import openpyxl
from flask import Blueprint, request, send_file, jsonify
from fpdf import FPDF
import json
from openpyxl.drawing.image import Image
from PIL import Image as PILImage
from docx import Document
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import requests
import urllib3
from core.extensions import limiter
from core.auth import require_auth, require_admin

# Disable SSL warnings for local CUPS server
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CUPS_BASE_URL = "https://10.241.1.21:49631/printers/"

def print_file_to_cups(printer_id, file_path):
    """Belirtilen PDF dosyasını curl kullanarak CUPS sunucusuna (auth ile) gönderir."""
    try:
        # CUPS Web arayüzü dosya gönderme simülasyonu
        url = f"https://10.241.1.21:49631/printers/{printer_id}"
        
        # printer_manager'daki CUPSHelper mantığını burada da kullanıyoruz
        import subprocess
        import re
        
        # 1. SID Al
        cookie_file = "cups_print_cookies.txt"
        sid_cmd = [
            'curl.exe', '-k', '-L', '-s',
            '--anyauth', '--user', "root:1234qqqQ",
            '-c', cookie_file,
            f"https://10.241.1.21:49631/admin/"
        ]
        sid_output = subprocess.run(sid_cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore').stdout
        match = re.search(r'name=["\']org\.cups\.sid["\'][^>]*value=["\']?([a-f0-9]+)["\']?', sid_output, re.I)
        sid = match.group(1) if match else None
        
        if not sid:
            return False, "CUPS SID alınamadı. (Giriş sorunu)"

        # 2. Dosyayı Yazdır (Multipart POST)
        print_cmd = [
            'curl.exe', '-k', '-L', '-s',
            '--anyauth', '--user', "root:1234qqqQ",
            '-b', cookie_file,
            '-H', f'Referer: {url}',
            '-F', f'org.cups.sid={sid}',
            '-F', 'OP=print-job',
            '-F', f'printer_name={printer_id}',
            '-F', f'file=@{file_path}',
            '-F', 'title=IT_Inventory_Print',
            url
        ]
        
        res = subprocess.run(print_cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        
        if "Print file sent" in res.stdout or res.returncode == 0:
            return True, "Yazdırma işlemi başarıyla CUPS kuyruğuna gönderildi."
        else:
            return False, f"CUPS Hatası: {res.stdout[:100]}"
            
    except Exception as e:
        return False, f"Sistem Hatası: {str(e)}"

document_service_bp = Blueprint('document_service', __name__)

# Yapılandırma
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
ANA_DB_DIR = os.path.join(DATABASE_DIR, "ana_database")
SABLON_DIR = os.path.join(DATABASE_DIR, "sablonlar")
ARCHIVE_DIR = os.path.join(BASE_DIR, "Arşiv")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# Klasörleri oluştur
os.makedirs(TEMP_DIR, exist_ok=True)

TEMPLATES = {
    "ZIMMET": os.path.join(SABLON_DIR, "zimmet.xlsx"),
    "HT": os.path.join(SABLON_DIR, "hasar_tespit.xlsx"),
    "IZIN": os.path.join(SABLON_DIR, "İzin İstek Formu.xlsx"),
    "SLA": os.path.join(SABLON_DIR, "SLA Sehven Tutanak.docx"),
    "BC55": os.path.join(SABLON_DIR, "MANUEL BARKOD 55-45.docx"),
    "BC100": os.path.join(SABLON_DIR, "MANUEL BARKOD 100-100.docx")
}

class TutanakPDF(FPDF):
    def __init__(self, t_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.t_type = t_type
        # Türkçe karakterler için font ekle (Windows varsayılan yolları)
        font_path = r"C:\Windows\Fonts\arial.ttf"
        if os.path.exists(font_path):
            self.add_font("ArialTR", "", font_path)
            self.add_font("ArialTR", "B", r"C:\Windows\Fonts\arialbd.ttf")
        else:
            # Fallback (Eğer font bulunamazsa standart kullanır ama karakterler bozulabilir)
            self.set_fallback_fonts(["Arial"])

    def header(self):
        PROJECT_ROOT = r"C:\Users\MUHAMMED-VEFA-IS\Desktop\IT_Inventory_System"
        LOGO_DIR = os.path.join(PROJECT_ROOT, "logo")
        
        # Sayfa Kenarlığı (Border)
        self.rect(5, 5, 200, 287)
        
        # Logoları yerleştir
        l_logo = "ht_left.png" if self.t_type == "HT" else "zimmet_left.png"
        r_logo = "ht_right.png" if self.t_type == "HT" else "zimmet_right.png"
        
        l_path = os.path.join(LOGO_DIR, l_logo)
        r_path = os.path.join(LOGO_DIR, r_logo)
        
        if os.path.exists(l_path):
            self.image(l_path, 10, 8, 33)
        if os.path.exists(r_path):
            self.image(r_path, 165, 8, 33)
            
        self.set_font("ArialTR", "B", 16)
        self.ln(20)
        
        if self.t_type == "HT":
            title = "HASAR TESPİT TUTANAĞI"
        elif self.t_type == "SERVICE":
            title = "YAZICI SERVİS TESLİM FORMU"
        else:
            title = "ZİMMET TUTANAĞI"
            
        self.cell(0, 10, title, ln=True, align="C")
        self.ln(5)

def generate_pdf_direct(t_type, items, photo_path=None):
    """Excel kullanmadan doğrudan PDF oluşturur."""
    pdf = TutanakPDF(t_type)
    pdf.add_page()
    pdf.set_font("ArialTR", "", 11)
    
    now_str = datetime.datetime.now().strftime("%d.%m.%Y")
    
    if t_type == "HT":
        # --- ÜST TABLO (ORİJİNAL ŞABLONA BENZER) ---
        pdf.set_font("ArialTR", "B", 10)
        # 1. Satır: Logolar ve Başlık
        pdf.rect(10, 10, 190, 30) # Ana çerçeve
        pdf.line(45, 10, 45, 40) # Sol ayırıcı
        pdf.line(155, 10, 155, 40) # Sağ ayırıcı
        
        pdf.set_y(15)
        pdf.set_x(50)
        pdf.set_font("ArialTR", "B", 14)
        pdf.cell(100, 10, "HASAR TESPİT TUTANAĞI", ln=True, align="C")
        
        pdf.set_y(25)
        pdf.set_x(50)
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(100, 5, "KOCAELİ ŞEHİR HASTANESİ", ln=True, align="C")
        pdf.set_x(50)
        pdf.cell(100, 5, "BİLGİ İŞLEM HASAR TESPİT TUTANAĞI", ln=True, align="C")
        
        pdf.set_y(45)
        # Tarih
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(160)
        pdf.cell(30, 8, f"Tarih: {now_str}", ln=True, align="R")
        
        # Üst Bilgi Bloğu
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("ArialTR", "B", 11)
        pdf.cell(45, 10, " SLA / İŞ EMRİ NO:", border=1, fill=True)
        pdf.set_font("ArialTR", "", 11)
        pdf.cell(0, 10, f" {items.get('sla', '-')}", border=1, ln=True)
        pdf.ln(5)
        
        # Ekipman Listesi
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(0, 8, " CİHAZ / EKİPMAN BİLGİSİ:", ln=True)
        pdf.set_font("ArialTR", "", 9)
        
        equipment_list = [
            "Bilgisayar", "Klavye", "Monitör", "Mouse", 
            "Yazıcı", "43\" Ekran", "Barkod Yazıcı", 
            "24\" Ekran", "Barkod Okuyucu", "Kiosk", "Switch"
        ]
        user_eq = items.get("equipment", [])
        
        # Checkbox Grid
        start_y = pdf.get_y()
        pdf.rect(10, start_y, 190, 45) # Kutu çerçevesi
        pdf.set_y(start_y + 2)
        
        for i in range(0, len(equipment_list), 2):
            e1 = equipment_list[i]
            e2 = equipment_list[i+1] if i+1 < len(equipment_list) else ""
            
            pdf.set_x(15)
            check1 = "[ X ]" if e1 in user_eq else "[   ]"
            pdf.cell(90, 7, f"{check1} {e1}")
            
            if e2:
                check2 = "[ X ]" if e2 in user_eq else "[   ]"
                pdf.cell(90, 7, f"{check2} {e2}")
            pdf.ln()
            
        if "Diğer" in user_eq:
            pdf.set_x(15)
            pdf.cell(0, 7, f"[ X ] Diğer: {items.get('other_equipment', '')}", ln=True)
            
        pdf.set_y(start_y + 45)
        pdf.ln(5)
        
        # Açıklama Alanı
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(0, 8, " HASAR / ARIZA AÇIKLAMASI:", ln=True)
        pdf.set_font("ArialTR", "", 10)
        pdf.multi_cell(0, 6, items.get("desc", "-"), border=1)
        pdf.ln(5)
        
        # Fotoğraf Alanı (Eğer varsa)
        if photo_path and os.path.exists(photo_path):
            pdf.set_font("ArialTR", "B", 10)
            pdf.cell(0, 8, " HASAR GÖRSELİ:", ln=True)
            current_y = pdf.get_y()
            pdf.rect(10, current_y, 190, 80)
            pdf.image(photo_path, x=45, y=current_y + 5, w=120, h=70)
            pdf.set_y(current_y + 80)
            pdf.ln(5)
            
        # Seri / Model Bilgisi
        pdf.set_fill_color(245, 245, 245)
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(30, 8, " SERİ NO:", border=1, fill=True)
        pdf.set_font("ArialTR", "", 10)
        pdf.cell(65, 8, f" {items.get('seri', '-')}", border=1)
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(30, 8, " MODEL:", border=1, fill=True)
        pdf.set_font("ArialTR", "", 10)
        pdf.cell(65, 8, f" {items.get('model', '-')}", border=1, ln=True)
        
        # İmzalar
        pdf.set_y(250)
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(63, 7, "KULLANICI / SORUMLU", border="TLR", align="C")
        pdf.cell(64, 7, "TESPİT EDEN", border="TLR", align="C")
        pdf.cell(63, 7, "BİRİM SORUMLUSU", border="TLR", align="C", ln=True)
        
        pdf.set_font("ArialTR", "", 8)
        pdf.cell(63, 5, "Ad-Soyad/Unvan/İmza", border="LR", align="C")
        pdf.cell(64, 5, "Ad-Soyad/Unvan/İmza", border="LR", align="C")
        pdf.cell(63, 5, "Ad-Soyad/Unvan/İmza", border="LR", align="C", ln=True)
        
        pdf.cell(63, 10, "", border="LR", align="C") # İmza boşluğu
        pdf.cell(64, 10, "", border="LR", align="C")
        pdf.cell(63, 10, "", border="LR", align="C", ln=True)
        
        pdf.set_font("ArialTR", "B", 9)
        pdf.cell(63, 6, items.get("teslimEden", "-"), border="LR", align="C")
        pdf.cell(64, 6, items.get("tespitEden", "-"), border="LR", align="C")
        pdf.cell(63, 6, items.get("birimSorumlusu", "MURAT COŞKUN"), border="LR", align="C", ln=True)
        
        pdf.set_font("ArialTR", "", 8)
        pdf.cell(63, 5, items.get("userUnvan", "-"), border="BLR", align="C")
        pdf.cell(64, 5, items.get("tespitUnvan", "-"), border="BLR", align="C")
        pdf.cell(63, 5, items.get("birimUnvan", "BİLGİ İŞLEM MÜDÜRÜ"), border="BLR", align="C", ln=True)

    elif t_type == "SERVICE":
        # Servis Teslim Formu (Resim 2 Formatı Benzeri)
        pdf.set_font("ArialTR", "B", 14)
        pdf.cell(0, 10, "YAZICI SERVİS TESLİM FORMU", ln=True, align="C")
        pdf.set_font("ArialTR", "", 10)
        pdf.cell(0, 10, f"Tarih: {now_str}", ln=True, align="R")
        pdf.ln(5)

        # Tablo Başlıkları
        pdf.set_font("ArialTR", "B", 9)
        pdf.set_fill_color(220, 220, 220)
        cols = [
            (10, "NO"), (25, "PR NO"), (40, "SERİ NO"), 
            (40, "MAC ADRESİ"), (40, "MODEL"), (35, "DURUM")
        ]
        for w, txt in cols:
            pdf.cell(w, 8, txt, border=1, fill=True, align="C")
        pdf.ln()

        # Tablo Verileri
        pdf.set_font("ArialTR", "", 8)
        for idx, item in enumerate(items.get("records", [])):
            pdf.cell(10, 7, str(idx + 1), border=1, align="C")
            pdf.cell(25, 7, str(item.get("pr_no", "-")), border=1, align="C")
            pdf.cell(40, 7, str(item.get("seri", "-")), border=1, align="C")
            pdf.cell(40, 7, str(item.get("mac", "-")), border=1, align="C")
            pdf.cell(40, 7, str(item.get("model", "-")), border=1, align="C")
            pdf.cell(35, 7, str(item.get("status", "-")), border=1, align="C")
            pdf.ln()

        pdf.ln(10)
        # Açıklama Alanı
        if items.get("note"):
            pdf.set_font("ArialTR", "B", 10)
            pdf.cell(0, 8, "NOTLAR:", ln=True)
            pdf.set_font("ArialTR", "", 9)
            pdf.multi_cell(0, 6, items.get("note"), border=1)
            pdf.ln(10)

        # İmzalar
        pdf.set_y(250)
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(95, 7, "TESLİM EDEN", align="C")
        pdf.cell(95, 7, "TESLİM ALAN", align="C", ln=True)
        pdf.set_font("ArialTR", "", 10)
        pdf.cell(95, 7, items.get("veren", "BİLGİ İŞLEM"), align="C")
        pdf.cell(95, 7, items.get("alan", "...................."), align="C", ln=True)

    else:
        # Zimmet PDF Yapısı
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(160)
        pdf.cell(30, 10, f"Tarih: {now_str}", ln=True)
        
        pdf.set_font("ArialTR", "", 11)
        staff = items.get("staff", "......")
        text = f"Aşağıda marka, model ve seri numaraları belirtilmiş cihazlar KEYDATA firmasından {staff} isimli personele / firmaya elden teslim edilmiştir."
        pdf.multi_cell(0, 7, text)
        pdf.ln(10)
        
        # Tablo Başlığı
        pdf.set_font("ArialTR", "B", 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(15, 10, "Adet", border=1, fill=True, align="C")
        pdf.cell(35, 10, "Cihaz Tipi", border=1, fill=True, align="C")
        pdf.cell(40, 10, "Marka", border=1, fill=True, align="C")
        pdf.cell(50, 10, "Model", border=1, fill=True, align="C")
        pdf.cell(50, 10, "Seri No", border=1, fill=True, align="C", ln=True)
        
        # Tablo Verileri
        pdf.set_font("ArialTR", "", 10)
        for d in items.get("devices", []):
            pdf.cell(15, 8, str(d.get("adet", "1")), border=1, align="C")
            pdf.cell(35, 8, d.get("tip", "-"), border=1)
            pdf.cell(40, 8, d.get("marka", "-"), border=1)
            pdf.cell(50, 8, d.get("model", "-"), border=1)
            pdf.cell(50, 8, d.get("seri", "-"), border=1, ln=True)
            
        # İmzalar
        pdf.ln(30)
        pdf.set_font("ArialTR", "B", 11)
        pdf.cell(95, 10, "TESLİM EDEN", align="C")
        pdf.cell(95, 10, "TESLİM ALAN", align="C", ln=True)
        
        pdf.set_font("ArialTR", "", 10)
        pdf.cell(95, 6, items.get("veren", "-"), align="C")
        pdf.cell(95, 6, items.get("alan", "-"), align="C", ln=True)

    # Geçici PDF dosyasını kaydet
    temp_pdf_path = os.path.join(BASE_DIR, f"temp_direct_{datetime.datetime.now().timestamp()}.pdf")
    pdf.output(temp_pdf_path)
    return temp_pdf_path

def generate_special_pdf(t_type, items):
    """SLA ve Barkodlar için özel PDF oluşturur."""
    pdf = TutanakPDF(t_type)
    
    if t_type == "SLA":
        pdf.add_page()
        pdf.set_font("ArialTR", "B", 16)
        pdf.cell(0, 10, "SLA SEHVEN KAPATMA TUTANAĞI", ln=True, align="C")
        pdf.ln(10)
        
        pdf.set_font("ArialTR", "B", 11)
        pdf.cell(40, 10, "Tarih:")
        pdf.set_font("ArialTR", "", 11)
        pdf.cell(0, 10, datetime.datetime.now().strftime("%d.%m.%Y"), ln=True)
        
        pdf.set_font("ArialTR", "B", 11)
        pdf.cell(40, 10, "Ticket / İş Emri:")
        pdf.set_font("ArialTR", "", 11)
        pdf.cell(0, 10, items.get("ticket_no", "-"), ln=True)
        
        pdf.set_font("ArialTR", "B", 11)
        pdf.cell(40, 10, "Cihaz Bilgisi:")
        pdf.set_font("ArialTR", "", 11)
        pdf.cell(0, 10, items.get("cihaz", "-"), ln=True)
        
        pdf.ln(5)
        pdf.set_font("ArialTR", "B", 11)
        pdf.cell(0, 10, "Açıklama:", ln=True)
        pdf.set_font("ArialTR", "", 11)
        pdf.multi_cell(0, 10, items.get("aciklama", "-"), border=1)
        
        pdf.ln(20)
        pdf.set_font("ArialTR", "B", 11)
        pdf.cell(95, 10, "DÜZENLEYEN", align="C")
        pdf.cell(95, 10, "ONAYLAYAN", align="C", ln=True)
        
        pdf.set_font("ArialTR", "", 11)
        pdf.cell(95, 10, items.get("personel", "-"), align="C")
        pdf.cell(95, 10, items.get("onaylayan", "MURAT COŞKUN"), align="C", ln=True)
        
    elif t_type == "BC55":
        # 55mm x 45mm barkod (Etiket boyutu)
        # 1mm = 2.83pt
        pdf = TutanakPDF(t_type, orientation='L', unit='mm', format=[55, 45])
        for _ in range(int(items.get("count", 1))):
            pdf.add_page()
            pdf.set_font("ArialTR", "B", 14)
            pdf.cell(0, 15, items.get("text", ""), ln=True, align="C")
            pdf.set_font("ArialTR", "", 10)
            pdf.cell(0, 10, items.get("subtext", ""), ln=True, align="C")
            
    elif t_type == "BC100":
        # 100mm x 100mm barkod
        pdf = TutanakPDF(t_type, orientation='P', unit='mm', format=[100, 100])
        for _ in range(int(items.get("count", 1))):
            pdf.add_page()
            pdf.set_font("ArialTR", "B", 24)
            pdf.ln(10)
            pdf.cell(0, 20, items.get("text", ""), ln=True, align="C")
            pdf.set_font("ArialTR", "", 12)
            pdf.multi_cell(0, 10, items.get("desc", ""), align="C")

    temp_pdf_path = os.path.join(BASE_DIR, f"temp_special_{datetime.datetime.now().timestamp()}.pdf")
    pdf.output(temp_pdf_path)
    return temp_pdf_path


def ensure_pillow():
    """Pillow kütüphanesinin yüklü olduğundan emin olur."""
    try:
        from PIL import Image
    except ImportError:
        import subprocess
        import sys
        print("Pillow eksik, kuruluyor...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])

def add_report_logos(wb, t_type):
    """Tutanak türüne göre logoları Excel dosyasındaki TÜM sayfalara ekler."""
    ensure_pillow()
    try:
        from PIL import Image as PILImage
        PROJECT_ROOT = r"C:\Users\MUHAMMED-VEFA-IS\Desktop\IT_Inventory_System"
        LOGO_DIR = os.path.join(PROJECT_ROOT, "logo")
        
        if t_type == "HT":
            logos = [("ht_left.png", "B1"), ("ht_right.png", "K1")]
        else:
            logos = [("zimmet_left.png", "A1"), ("zimmet_right.png", "I52")]
            
        for l_name, anchor in logos:
            path = os.path.join(LOGO_DIR, l_name)
            if os.path.exists(path):
                with PILImage.open(path) as pil_img:
                    rgb_img = pil_img.convert("RGB")
                    temp_img_path = os.path.join(PROJECT_ROOT, f"tmp_logo_{l_name}.jpg")
                    rgb_img.save(temp_img_path, "JPEG")
                    
                    for sheet in wb.worksheets:
                        xl_img = Image(temp_img_path)
                        xl_img.width, xl_img.height = 130, 70
                        xl_img.anchor = anchor
                        sheet.add_image(xl_img)
    except Exception as e:
        pass

def insert_image_to_excel(ws, photo_path, start_cell="G36"):
    """Resmi belirli bir aralığa (G36:K45) sığacak şekilde yerleştirir."""
    ensure_pillow()
    try:
        img = Image(photo_path)
        img.width = 350  
        img.height = 180 
        img.anchor = start_cell
        ws.add_image(img)
    except Exception as e:
        pass

def safe_write_cell(ws, cell_addr, value):
    """Birleştirilmiş hücrelere (Merged Cells) güvenli şekilde veri yazar."""
    from openpyxl.cell.cell import MergedCell
    try:
        cell = ws[cell_addr]
        if isinstance(cell, MergedCell):
            for merged_range in ws.merged_cells.ranges:
                if cell_addr in merged_range:
                    ws.cell(row=merged_range.min_row, column=merged_range.min_col).value = value
                    return
        else:
            ws[cell_addr] = value
    except Exception as e:
        pass

def excel_to_pdf_win32(excel_path, pdf_path):
    """Excel dosyasını win32com kullanarak PDF'e dönüştürür. Şablonu korumak için FitToPages kullanır."""
    excel = None
    try:
        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        
        abs_excel = os.path.abspath(excel_path)
        abs_pdf = os.path.abspath(pdf_path)
        
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        
        wb = excel.Workbooks.Open(abs_excel, ReadOnly=True)
        ws = wb.Active
        
        # Sayfa Ayarları (Şablonun bozulmaması için)
        ws.PageSetup.Orientation = 1 # 1=Portrait, 2=Landscape
        ws.PageSetup.Zoom = False
        ws.PageSetup.FitToPagesWide = 1
        ws.PageSetup.FitToPagesTall = 1
        
        # 0 = xlTypePDF
        wb.ExportAsFixedFormat(0, abs_pdf)
        wb.Close(False)
        excel.Quit()
        excel = None
        return True
    except Exception as e:
        print(f"Win32 PDF Error: {str(e)}")
        return False
    finally:
        if excel:
            try: excel.Quit()
            except: pass
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except: pass

def generate_barcode_pdf(output_path, text, subtext, width_mm, height_mm, frame_style='dotted'):
    """ReportLab kullanarak barkod etiketi oluşturur. Stil desteği: dotted, solid, rounded."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    import os

    w = width_mm * mm
    h = height_mm * mm
    c = canvas.Canvas(output_path, pagesize=(w, h))

    # Çerçeve Çizimi (Kullanıcı Talebi: Sıfır kenar payı, Alt kısım 3mm içeride)
    c.setLineWidth(1)
    # x=0, y=3mm, width=w, height=h-3.5mm (top 0.5mm gap)
    if frame_style == 'dotted':
        c.setDash(2, 2)
        c.rect(0, 3*mm, w, h - 3.5*mm)
    elif frame_style == 'solid':
        c.setDash()
        c.rect(0, 3*mm, w, h - 3.5*mm)
    elif frame_style == 'rounded':
        c.setDash()
        c.roundRect(0, 3*mm, w, h - 3.5*mm, 2*mm)
    
    # Metin Yazımı (Türkçe karakter desteği için standart fontlar bazen sorun çıkarabilir)
    c.setFont("Helvetica-Bold", 14 if width_mm > 60 else 10)
    c.drawCentredString(w/2, h/2 + 2*mm, text)
    
    c.setFont("Helvetica", 10 if width_mm > 60 else 8)
    c.drawCentredString(w/2, h/2 - 4*mm, subtext)

    c.showPage()
    c.save()
    return True

@document_service_bp.route('/generate_tutanak', methods=['POST'])
@limiter.limit("10 per minute")
@require_auth
def generate_tutanak():
    """Tutanak oluşturma işini envanterden bağımsız bir mikro-servis gibi yürütür."""
    if request.content_type and 'multipart/form-data' in request.content_type:
        t_type = request.form.get("type")
        mahal = request.form.get("mahal", "Genel")
        items = json.loads(request.form.get("data", "{}"))
        req_format = request.form.get("format", "pdf")
        photo = request.files.get("photo")
    else:
        data = request.json
        t_type = data.get("type")
        items = data.get("data")
        mahal = data.get("mahal", "Genel")
        req_format = data.get("format", "pdf")
        photo = None
    
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    now_str = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    filename = f"Tutanak_{mahal}_{now_str}"
    temp_xlsx = os.path.join(TEMP_DIR, f"temp_{t_type}_{unique_id}.xlsx")
    final_pdf = os.path.join(TEMP_DIR, f"{filename}_{unique_id}.pdf")

    photo_temp = None
    if photo:
        photo_temp = os.path.join(TEMP_DIR, f"temp_photo_{unique_id}.png")
        photo.save(photo_temp)

    wb = None
    try:
        # 1. Excel'i doldur (Orijinal Şablon Kullanılıyor)
        template_path = TEMPLATES.get(t_type)
        use_excel_template = False
        
        # Eğer kullanıcı özellikle EXCEL istiyorsa ve tip SLA ise şablonu zimmet.xlsx olarak değiştir
        if t_type == "SLA" and req_format == 'excel':
            template_path = os.path.join(SABLON_DIR, "zimmet.xlsx")

        if template_path and os.path.exists(template_path):
            ext = os.path.splitext(template_path)[1].lower()
            if ext in ['.xlsx', '.xlsm', '.xltx', '.xltm']:
                use_excel_template = True
                shutil.copy2(template_path, temp_xlsx)
                wb = openpyxl.load_workbook(temp_xlsx)
                sheet = wb.active
            else:
                # Word şablonu veya diğer formatlar için farklı mantık gerekebilir
                use_excel_template = False
                shutil.copy2(template_path, temp_xlsx) # Sadece kopyala, doldurma mantığı şimdilik yok
                # Gelecekte python-docx eklenebilir

            
            if t_type == "SLA" and use_excel_template:
                safe_write_cell(sheet, 'J4', datetime.datetime.now().strftime("%d.%m.%Y"))
                full_text = f"SLA SEHVEN TUTANAĞI: {items.get('ticket', '-')} nolu iş emri / cihaz ({items.get('cihaz', '-')}) sehven kapatılmıştır. Açıklama: {items.get('aciklama', '-')}"
                safe_write_cell(sheet, 'B9', full_text)
                safe_write_cell(sheet, 'A47', items.get("personel", "-"))
                safe_write_cell(sheet, 'I47', items.get("onaylayan", "-"))

            if t_type == "HT":
                safe_write_cell(sheet, 'F10', items.get("sla", "."))
                safe_write_cell(sheet, 'K6', datetime.datetime.now().strftime("%d.%m.%Y"))
                safe_write_cell(sheet, 'B28', items.get("desc", "-"))
                safe_write_cell(sheet, 'F32', items.get("seri", "-"))
                safe_write_cell(sheet, 'F33', items.get("model", "-"))
                safe_write_cell(sheet, 'E49', items.get("tespitEden", "-"))
                safe_write_cell(sheet, 'E50', items.get("tespitUnvan", "-"))
                safe_write_cell(sheet, 'B49', items.get("teslimEden", "-"))
                safe_write_cell(sheet, 'B50', items.get("userUnvan", "-"))
                safe_write_cell(sheet, 'I49', "MURAT COŞKUN")
                safe_write_cell(sheet, 'I50', "BİLGİ İŞLEM MÜDÜRÜ")
                
                equipment = items.get("equipment", [])
                mapping = {
                    "Bilgisayar": "E12", "Klavye": "I12", "Monitör": "E14", "Mouse": "I14",
                    "Yazıcı": "E16", "43\" Ekran": "I16", "Barkod Yazıcı": "E18",
                    "24\" Ekran": "I18", "Barkod Okuyucu": "E20", "Kiosk": "I20", "Switch": "I22"
                }
                for name, cell in mapping.items():
                    if name in equipment: safe_write_cell(sheet, cell, "[ X ]")
                if "Diğer" in equipment:
                    safe_write_cell(sheet, 'E22', f"[ X ] {items.get('other_equipment', '')}")
                if photo_temp:
                    insert_image_to_excel(sheet, photo_temp, start_cell="G36")
            elif t_type == "ZIMMET":
                safe_write_cell(sheet, 'J4', datetime.datetime.now().strftime("%d.%m.%Y"))
                staff_name = items.get("staff", "......")
                full_text = f"Aşağıda marka, model ve seri numaraları belirtilmiş cihazlar KEYDATA firmasından {staff_name} isimli personele / firmaya elden teslim edilmiştir."
                safe_write_cell(sheet, 'B9', full_text)
                for idx, d in enumerate(items.get("devices", [])):
                    row = 15 + idx
                    safe_write_cell(sheet, f'B{row}', d.get("adet", "1"))
                    safe_write_cell(sheet, f'C{row}', d.get("tip", "-"))
                    safe_write_cell(sheet, f'E{row}', d.get("marka", "-"))
                    safe_write_cell(sheet, f'G{row}', d.get("model", "-"))
                    safe_write_cell(sheet, f'I{row}', d.get("seri", "-"))
                safe_write_cell(sheet, 'A47', items.get("veren", "-"))
                safe_write_cell(sheet, 'I47', items.get("alan", "-"))
            elif t_type == "IZIN":
                safe_write_cell(sheet, 'B6', datetime.datetime.now().strftime("%d.%m.%Y"))
                safe_write_cell(sheet, 'B7', items.get("ad_soyad", ""))
                safe_write_cell(sheet, 'F7', items.get("bolum", ""))
                safe_write_cell(sheet, 'B8', items.get("sicil", ""))
                safe_write_cell(sheet, 'F8', items.get("gorev", ""))
                safe_write_cell(sheet, 'B9', items.get("sebep", "-"))
                
                # Tarih formatlarını düzelt (DD.MM.YYYY)
                def fmt_date(d):
                    if not d: return ""
                    try:
                        dt = datetime.datetime.strptime(d, "%Y-%m-%d")
                        return dt.strftime("%d.%m.%Y")
                    except: return d

                safe_write_cell(sheet, 'B10', fmt_date(items.get("baslangic", "")))
                safe_write_cell(sheet, 'D10', items.get("bas_saat") or "08:00")
                
                safe_write_cell(sheet, 'B11', fmt_date(items.get("bitis", "")))
                safe_write_cell(sheet, 'D11', items.get("bit_saat") or "17:00")
                
                safe_write_cell(sheet, 'B12', fmt_date(items.get("isbasi", "")))
                safe_write_cell(sheet, 'D12', items.get("isbasi_saat") or "08:00")
                
                # İzin Süresi (Gün / Saat)
                safe_write_cell(sheet, 'F11', f"{items.get('sure_gun', '...')} Gün / {items.get('sure_saat', '...')} Saat")
                
                # İzin türü cümlesi ve altını çizme simülasyonu (Büyük harf ve vurgu ile)
                izin_turu = items.get('tur', 'Ücretli İzin').upper()
                if "ÜCRETLİ" in izin_turu and "ÜCRETSİZ" not in izin_turu:
                    tur_metni = "Yukarıda Adı Soyadı Yazılı Çalışanımıza mazeretine binaen aşağıda belirtilen tarih / tarihleri arasında ÜCRETLİ izin verilmesi uygun görülmüştür."
                elif "ÜCRETSİZ" in izin_turu:
                    tur_metni = "Yukarıda Adı Soyadı Yazılı Çalışanımıza mazeretine binaen aşağıda belirtilen tarih / tarihleri arasında ÜCRETSİZ izin verilmesi uygun görülmüştür."
                else:
                    tur_metni = f"Yukarıda Adı Soyadı Yazılı Çalışanımıza mazeretine binaen aşağıda belirtilen tarih / tarihleri arasında {izin_turu} izin verilmesi uygun görülmüştür."
                
                safe_write_cell(sheet, 'A13', tur_metni)
                
                # İmza Alanları
                safe_write_cell(sheet, 'A16', items.get("talep_eden_ad", ""))
                safe_write_cell(sheet, 'B16', items.get("takim_lideri_ad", ""))
                # İmza yerlerini kullanıcı geri bildirimine göre tam koordinatlarla eşleştiriyoruz
                # C-D-E Birleşmiş Hücre -> Murat Coşkun (C16)
                # F-G Birleşmiş Hücre -> Pınar Şendoğan (F16)
                safe_write_cell(sheet, 'C16', items.get("bolum_muduru_ad") or "MURAT COŞKUN") 
                safe_write_cell(sheet, 'F16', items.get("ik_ad") or "PINAR ŞENDOĞAN")
            
            elif t_type == "SLA" and template_path.lower().endswith('.docx'):
                # Word Belgesi İşleme (SLA)
                doc = Document(template_path)
                
                # Basit Yer Tutucu Değişimi ({{ticket}}, {{cihaz}}, {{aciklama}}, {{personel}}, {{onaylayan}})
                placeholders = {
                    "{{ticket}}": items.get("ticket", items.get("ticket_no", "-")),
                    "{{cihaz}}": items.get("cihaz", "-"),
                    "{{aciklama}}": items.get("aciklama", "-"),
                    "{{personel}}": items.get("personel", "-"),
                    "{{onaylayan}}": items.get("onaylayan", "-"),
                    "{{tarih}}": datetime.datetime.now().strftime("%d.%m.%Y")
                }
                
                for p in doc.paragraphs:
                    for key, val in placeholders.items():
                        if key in p.text:
                            p.text = p.text.replace(key, val)
                
                # Tablo içindeki yer tutucuları da kontrol et
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for paragraph in cell.paragraphs:
                                for key, val in placeholders.items():
                                    if key in paragraph.text:
                                        paragraph.text = paragraph.text.replace(key, val)
                
                temp_docx = os.path.join(TEMP_DIR, f"temp_{t_type}_{unique_id}.docx")
                doc.save(temp_docx)
                
                response = send_file(temp_docx, as_attachment=True, download_name=f"{filename}.docx")
                @response.call_on_close
                def cleanup_docx():
                    try: 
                        if os.path.exists(temp_docx): os.remove(temp_docx)
                    except: pass
                return response

            if wb:
                wb.save(temp_xlsx)
                wb.close()
            use_excel_template = (wb is not None)

        # Eğer kullanıcı özellikle EXCEL istiyorsa, PDF yapmadan gönder (Birebir şablon koruması için)
        if req_format == 'excel':
            response = send_file(temp_xlsx, as_attachment=True, download_name=f"{filename}.xlsx")
            @response.call_on_close
            def cleanup_excel():
                try: 
                    if os.path.exists(temp_xlsx): os.remove(temp_xlsx)
                except: pass
            return response

        # 2. PDF'e dönüştür (RESMİ EVRAK: SADECE EXCEL-TO-PDF KULLANILMALI)
        generated_pdf = None
        if use_excel_template:
            # Win32 ile orijinal şablonu PDF yap (Birebir aynısı olması için ŞART)
            if excel_to_pdf_win32(temp_xlsx, final_pdf):
                generated_pdf = final_pdf
            else:
                # KRİTİK İYİLEŞTİRME: Eğer PDF dönüştürme başarısız olursa (WinError 32 vb.), 
                # kullanıcıya hata vermek yerine otomatik olarak EXCEL dosyasını gönder.
                # Böylece iş akışı aksamaz.
                print("UYARI: PDF dönüştürme başarısız, otomatik Excel indirmeye geçiliyor.")
                response = send_file(temp_xlsx, as_attachment=True, download_name=f"{filename}.xlsx")
                @response.call_on_close
                def cleanup_fallback():
                    try: 
                        if os.path.exists(temp_xlsx): os.remove(temp_xlsx)
                    except: pass
                return response
        elif t_type == "BC55":
            generate_barcode_pdf(final_pdf, items.get("text", ""), items.get("subtext", ""), 55, 45, frame_style='dotted')
            generated_pdf = final_pdf
        elif t_type == "BC100":
            generate_barcode_pdf(final_pdf, items.get("text", ""), items.get("subtext", ""), 100, 100, frame_style='dotted')
            generated_pdf = final_pdf
        else:
             return jsonify({"error": "Şablon dosyası bulunamadı."}), 500

        if not generated_pdf or not os.path.exists(generated_pdf):
             return jsonify({"error": "PDF oluşturulamadı."}), 500

        # Arşivle
        archive_map = {"HT": "Hasar_Tespit", "ZIMMET": "Zimmet", "IZIN": "Izin", "SLA": "SLA", "BC55": "Barkod", "BC100": "Barkod", "SERVICE": "Servis"}
        SUB_ARCHIVE = os.path.join(ARCHIVE_DIR, archive_map.get(t_type, "Diger"))
        if not os.path.exists(SUB_ARCHIVE): os.makedirs(SUB_ARCHIVE)
        
        shutil.copy(generated_pdf, os.path.join(SUB_ARCHIVE, f"{filename}.pdf"))
        if os.path.exists(temp_xlsx):
            shutil.copy(temp_xlsx, os.path.join(SUB_ARCHIVE, f"{filename}.xlsx"))

        # --- DOĞRUDAN YAZDIRMA MANTIĞI ---
        direct_print = (request.args.get('direct_print') == 'true')
        if not direct_print and request.is_json:
            direct_print = request.json.get('direct_print')
            
        if direct_print:
            printer_id = request.args.get('printer_id') or (request.json.get('printer_id') if request.is_json else 'PR-001')
            success, msg = print_file_to_cups(printer_id, generated_pdf)
            
            # Temizlik
            if os.path.exists(generated_pdf): os.remove(generated_pdf)
            if os.path.exists(temp_xlsx): os.remove(temp_xlsx)
            
            return jsonify({"success": success, "message": msg})
        # --------------------------------

        response = send_file(generated_pdf, as_attachment=True, download_name=f"{filename}.pdf")
        
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(generated_pdf): os.remove(generated_pdf)
                if os.path.exists(temp_xlsx): os.remove(temp_xlsx)
                if photo_temp and os.path.exists(photo_temp): os.remove(photo_temp)
            except: pass
        
        return response

    except Exception as e:
        print(f"Genel Hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Sistem Hatası: {str(e)}"}), 500
