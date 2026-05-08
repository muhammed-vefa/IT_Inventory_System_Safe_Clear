import openpyxl
import os

def create_dummy_xlsx(path, headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    wb.save(path)

base_path = "IT_Inventory_System_Safe_Temp_Clear/database/güncel_database"
if not os.path.exists(base_path):
    os.makedirs(base_path)

# Envanter
create_dummy_xlsx(
    os.path.join(base_path, "envanter_güncel.xlsx"),
    ["PC NO", "KATEGORİ", "MAHAL ADI", "IP ADRES", "SERİ NUMARASI", "DURUM"],
    [["PC-001", "PC", "Demo Mahal 1", "10.0.0.11", "SN1001", "Kurulu"]]
)

# Yazıcılar
create_dummy_xlsx(
    os.path.join(base_path, "yazıcılar_güncel.xlsx"),
    ["PR NUMARASI", "MODEL", "IP ADRES", "SERİ NUMARASI", "MAC ADRES", "DURUM"],
    [["PR-001", "Demo Model", "10.0.0.51", "SN5001", "00:11:22:33:44:55", "Kurulu"]]
)

print("Dummy Excel dosyaları oluşturuldu.")
