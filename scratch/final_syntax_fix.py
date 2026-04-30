
import os

def final_syntax_fix():
    file_path = 'frontend/UI_controller.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Hatalı eklenen dummy fonksiyonu temizle
    bad_line = "_dummy: function() {"
    if bad_line in content:
        content = content.replace(bad_line, "")
        print("Removed bad dummy function.")

    # Parantez dengesini tekrar kontrol et
    open_count = content.count('{')
    close_count = content.count('}')
    
    if open_count > close_count:
        # Eğer hala eksik varsa en sona ekle (genelde appData kapanııdır)
        # Ama önce bir tane ekleyip dengeleyelim
        content += "\n};"
        print(f"Added missing closing brace. New balance: {content.count('{')} / {content.count('}')}")

    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("UI_controller.js syntax fixed.")

final_syntax_fix()
