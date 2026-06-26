import pandas as pd
import sys

xl = pd.ExcelFile('database/SQL_Server_Export_Final.xlsx')
with open('database/excel_analysis.txt', 'w', encoding='utf-8') as f:
    f.write("EXCEL ANALIZI:\n")
    for s in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=s)
        if df.empty:
            f.write(f"\nSayfa: {s} (BOS)\n")
            continue
            
        empty_cols = [c for c in df.columns if df[c].isna().all()]
        filled_cols = df.dropna(how='all', axis=1).columns.tolist()
        
        f.write(f"\nSayfa: {s}\n")
        f.write(f"  Toplam Sütun: {len(df.columns)}\n")
        f.write(f"  Tamamen Boş Sütunlar: {empty_cols}\n")
        f.write(f"  Veri İçeren Sütunlar: {filled_cols}\n")
