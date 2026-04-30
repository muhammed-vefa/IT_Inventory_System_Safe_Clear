
import os
import re

def find_broken_function(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # appData içindeki fonksiyonları bulalım
    # Basitçe 'fonksiyonAdi: function(...) {' desenine bakalım
    matches = re.finditer(r"(\w+):\s*(async\s+)?function\s*\(.*?\)\s*\{", content)
    
    for match in matches:
        name = match.group(1)
        start_idx = match.start()
        
        # Bu noktadan itibaren parantez dengesini izleyelim
        balance = 0
        found_end = False
        for i in range(start_idx, len(content)):
            if content[i] == '{':
                balance += 1
            elif content[i] == '}':
                balance -= 1
                if balance == 0:
                    # Fonksiyon bitti
                    end_idx = i
                    # Bir sonraki karakter virgül mü?
                    after = content[end_idx+1:end_idx+5].strip()
                    # print(f"Function {name} ends at {i} with balance 0. After: {after}")
                    found_end = True
                    break
        
        if not found_end:
            print(f"Function {name} (starting at index {start_idx}) NEVER ENDS!")

find_broken_function('frontend/UI_controller.js')
