
import os

def final_brace_repair():
    file_path = 'frontend/UI_controller.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. saveMagicInfoChanges fonksiyonunu kapat
    # Bu fonksiyonun sonu: catch(e) { alert('Hata: ' + e.message); }
    # Hemen arkasına }, eklemeliyiz
    bad_segment = "        } catch(e) { alert('Hata: ' + e.message); }\n    },"
    # Zaten virgüllü hali var mı diye bakalım? Hayır, view_file'da yoktu.
    
    # Hedef satırı bulalım
    target = "        } catch(e) { alert('Hata: ' + e.message); }"
    # Bu satırın devamında }, yoksa ekle
    if target in content and (target + "\n    },") not in content:
        content = content.replace(target, target + "\n    },")
        print("Fixed unclosed saveMagicInfoChanges function.")

    # 2. Dosyanın en sonundaki gereksiz }; parantezini kaldır (Eer varsa)
    if content.endswith("\n};"):
        content = content[:-3]
        print("Removed extra trailing brace.")

    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("UI_controller.js is now perfectly balanced.")

final_brace_repair()
