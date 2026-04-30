
import os
import re

def find_imbalance_source(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    balance = 0
    # appData başlangıcı
    balance = 1 # line 2: var appData = {
    
    for i in range(2, len(lines)):
        line = lines[i]
        # Basitçe sayalım
        open_c = line.count('{')
        close_c = line.count('}')
        balance += open_c
        balance -= close_c
        
        # Eer bir fonksiyonun bittii noktada (satır sonu '},') denge 1 deilse sorun oradadır
        if '},' in line and balance != 1:
            # Sadece appData elemanı olan fonksiyonları kontrol edelim
            # (Bu çok kaba bir kontrol ama ia yarayabilir)
            print(f"Possible imbalance after line {i+1}: Balance={balance} -> {line.strip()}")

find_imbalance_source('frontend/UI_controller.js')
