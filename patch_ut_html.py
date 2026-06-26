import re

with open(r'c:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'<input type="text" id="ut-kisi3-ad" class="search-bar" style="flex:1; font-size:0.85rem; height:36px;" placeholder="Ad Soyad" value="">',
    r'<input type="text" id="ut-kisi3-ad" class="search-bar" style="flex:1; font-size:0.85rem; height:36px;" placeholder="Düzenleyen / Tespit Eden (Ad Soyad)" value="">',
    content
)

content = re.sub(
    r'<input type="text" id="ut-kisi3-unvan" class="search-bar" style="flex:1; font-size:0.8rem; height:36px; opacity:0.7;" placeholder=".*?" value="">',
    r'<input type="text" id="ut-kisi3-unvan" class="search-bar" style="flex:1; font-size:0.8rem; height:36px; opacity:0.7;" placeholder="Ünvanı" value="Bilgi İşlem ve HBYS Uzm. Yrd.">',
    content
)

with open(r'c:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory\index.html', 'w', encoding='utf-8') as f:
    f.write(content)
