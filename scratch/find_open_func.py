
import os

def find_open_func(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    balance = 0
    # appData starts at line 2
    balance = 1
    
    for i in range(2, 4733):
        line = lines[i]
        balance += line.count('{')
        balance -= line.count('}')
        
        # Eer bir fonksiyonun bittii varsayılan satırda ( }, ) denge 1 deilse o fonksiyon sorunludur
        if '},' in line and balance != 1:
            print(f"Function ending at L{i+1} is SUSPICIOUS. Balance={balance} | {line.strip()}")
            # Muhtemelen bu satır aslında fonksiyonu kapatamadı çünkü içeride bir parantez açık kaldı

find_open_func('frontend/UI_controller.js')
