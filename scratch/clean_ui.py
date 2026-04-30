
import os
import re

def clean_and_fix_ui():
    file_path = 'frontend/UI_controller.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fazladan eklenen boş satırları temizle (\n\n -> \n)
    # Birden fazla ardışık boş satırı tek bir boş satıra indirir
    content = re.sub(r'\n\s*\n', '\n', content)

    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("UI_controller.js cleaned and compact.")

clean_and_fix_ui()
