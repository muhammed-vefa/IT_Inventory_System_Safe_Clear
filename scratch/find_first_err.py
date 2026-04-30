
import os

def find_first_imbalance(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    balance = 0
    # appData başlangıcı (line 2: var appData = {)
    balance = 1
    
    for i in range(2, len(lines)):
        line = lines[i]
        old_balance = balance
        balance += line.count('{')
        balance -= line.count('}')
        
        # Eer denge 1'in üzerine çıkmısa ve satır bir fonksiyon balangıcı deilse risklidir
        # Ama en garantisi, denge 2'ye çıktıktan sonra bir daha asla 1'e dümediği ilk anı bulmak
        # Ancak burada appData içindeki fonksiyonlar zaten dengeyi 2'ye çıkarır. 
        # Önemli olan fonksiyon bittiğinde ( }, ) dengenin 1'e dönmesidir.
        
        if '},' in line and balance > 1:
            print(f"CRITICAL: Balance remains {balance} after '}},' at line {i+1}: {line.strip()}")
            # İlk hatayı bulunca duralım
            break

find_first_imbalance('frontend/UI_controller.js')
