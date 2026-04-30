
import os
import re

def fix_all_corrupted_regex():
    file_path = 'frontend/UI_controller.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. replace(//g, ... eklentilerini temizle veya dorula
    # Bu hatalar genelde u karakterler iindi: , , , , , 
    # Ama en güvenlisi, bozuk olanları standart harflere çeviren bir regex ile temizlemek
    
    # 1673. satırdaki özel durumu düzelt
    bad_line = "const norm = (s) => (s || '').toUpperCase().replace(/İ/g, 'I').replace(//g, 'G').replace(//g, 'U').replace(//g, 'S').replace(//g, 'O').replace(//g, 'C').trim();"
    good_line = "const norm = (s) => (s || '').toUpperCase().replace(/İ/g, 'I').replace(/Ğ/g, 'G').replace(/Ü/g, 'U').replace(/Ş/g, 'S').replace(/Ö/g, 'O').replace(/Ç/g, 'C').trim();"
    
    if bad_line in content:
        content = content.replace(bad_line, good_line)
        print("Fixed corrupted norm function at L1673.")
    else:
        # Daha esnek bir regex ile bulmaya çalış
        content = re.sub(r"replace\(//g,\s*'G'\)", "replace(/Ğ/g, 'G')", content)
        content = re.sub(r"replace\(//g,\s*'U'\)", "replace(/Ü/g, 'U')", content)
        content = re.sub(r"replace\(//g,\s*'S'\)", "replace(/Ş/g, 'S')", content)
        content = re.sub(r"replace\(//g,\s*'O'\)", "replace(/Ö/g, 'O')", content)
        content = re.sub(r"replace\(//g,\s*'C'\)", "replace(/Ç/g, 'C')", content)

    # 2. Dosyada hala //g kalan yerler var mı kontrol et (Regex içinde olması gereken ama bozulmuş olanlar)
    content = content.replace(".replace(//g, \"S\")", ".replace(/Ş/g, \"S\")")
    content = content.replace(".replace(//g, \"s\")", ".replace(/ş/g, \"s\")")
    content = content.replace(".replace(//g, \"G\")", ".replace(/Ğ/g, \"G\")")
    content = content.replace(".replace(//g, \"g\")", ".replace(/ğ/g, \"g\")")

    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("All corrupted regex replacements fixed.")

fix_all_corrupted_regex()
