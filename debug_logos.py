import os
from PIL import Image as PILImage
import openpyxl
from openpyxl.drawing.image import Image as XLImage

# Yapılandırma
BASE_DIR = r"C:\Users\MUHAMMED-VEFA-IS\Desktop\IT_Inventory_System"
LOGO_DIR = os.path.join(BASE_DIR, "logo")
LOGOS = ["ht_left.png", "ht_right.png", "zimmet_left.png", "zimmet_right.png"]

print(f"--- LOGO KONTROL RAPORU ---")
print(f"Ana Dizin: {BASE_DIR}")
print(f"Logo Dizini: {LOGO_DIR}")

if not os.path.exists(LOGO_DIR):
    print(f"HATA: Logo dizini bulunamadi!")
else:
    for logo in LOGOS:
        path = os.path.join(LOGO_DIR, logo)
        exists = os.path.exists(path)
        print(f"Dosya: {logo} -> {'VAR' if exists else 'YOK'} ({path})")
        if exists:
            try:
                with PILImage.open(path) as img:
                    print(f"  - Format: {img.format}, Boyut: {img.size}")
            except Exception as e:
                print(f"  - HATA (Pillow): {e}")

# Excel Testi
try:
    wb = openpyxl.Workbook()
    ws = wb.active
    logo_path = os.path.join(LOGO_DIR, "ht_left.png")
    if os.path.exists(logo_path):
        img = XLImage(logo_path)
        ws.add_image(img, "A1")
        print(f"Excel'e resim ekleme testi: BASARILI")
    wb.close()
except Exception as e:
    print(f"Excel Test Hatasi: {e}")

print("--- RAPOR SONU ---")
