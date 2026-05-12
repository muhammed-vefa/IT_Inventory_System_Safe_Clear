import openpyxl
import os

path = r'C:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory_System\database\ana_database\envanter.xlsx'
if os.path.exists(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    sheet = wb.active
    for r_idx, row in enumerate(sheet.iter_rows(min_row=1, max_row=5), start=1):
        values = [cell.value for cell in row]
        print(f"Row {r_idx}: {values}")
else:
    print("File not found")
