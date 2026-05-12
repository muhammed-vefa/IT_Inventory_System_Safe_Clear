
import pandas as pd
import os

def inspect_excel():
    paths = [
        os.path.join('database', 'ana_database', 'envanter.xlsx'),
        os.path.join('database', 'güncel_database', 'envanter.xlsx')
    ]
    
    for path in paths:
        if os.path.exists(path):
            print(f"\n--- Dosya: {path} ---")
            try:
                # Sütunları ve ilk 5 satırı oku
                df = pd.read_excel(path, nrows=5)
                print("Sütun Başlıkları:")
                print(df.columns.tolist())
                print("\nİlk 5 Satır Verisi:")
                print(df.to_string())
            except Exception as e:
                print(f"Hata: {e}")
        else:
            print(f"Dosya bulunamadı: {path}")

if __name__ == "__main__":
    inspect_excel()
