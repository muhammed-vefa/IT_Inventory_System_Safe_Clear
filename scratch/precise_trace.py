
import os

def precise_trace(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    balance = 0
    for i, line in enumerate(lines):
        # Yorumları ve stringleri basitçe dılayarak sadece gerçek parantezleri saymaya çalıalım
        # (Bu çok kaba ama genellikle iş görür)
        clean_line = line.split('//')[0].split('/*')[0]
        
        open_c = clean_line.count('{')
        close_c = clean_line.count('}')
        balance += open_c
        balance -= close_c
        
        # Fonksiyon sonu ve nesne elemanı sonu ( }, ) kontrolü
        if '},' in line or '};' in line:
            # appData içindeki her eleman bittiinde denge 1 olmalı
            # (appData dıındaki app.init gibi yerlerde 0 olmalı)
            pass
        
        if i < 100:
            print(f"L{i+1} | Bal: {balance} | {line.strip()}")

precise_trace('frontend/UI_controller.js')
