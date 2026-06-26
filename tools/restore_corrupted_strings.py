import shutil

shutil.copy('backups/index_html_pre_charset_fix.html', 'index.html')

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    '<a href="#" id="menu-system-update" onclick="app.triggerSystemUpdate()" style="display:none; color:#ffb400;"><i class="fas fa-sync-alt"></i> Sistemi Güncelle & Yeniden Başlat</a>',
    '<a href="#" id="menu-system-update" onclick="app.triggerSystemUpdate()" style="display:none; color:#ffb400;"><i class="fas fa-sync-alt"></i> Sistemi Güncelle & Yeniden Başlat</a>\n                        \n                        <!-- Arşiv Toggle (Taslak/Silinmiş) -->\n                        <a href="#" id="menu-archive-toggle" onclick="app.toggleArchiveView()" style="display:none; color:#f43f5e; font-weight: bold;"><i class="fas fa-trash-can-arrow-up"></i> <span id="archive-toggle-text">Arşivlenenleri Göster</span></a>'
)

text = text.replace('frontend/UI_controller.js?v=9999999.24', 'frontend/UI_controller.js?v=9999999.27')
text = text.replace('frontend/UI_controller.js?v=9999999.26', 'frontend/UI_controller.js?v=9999999.27')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print('Restored index.html')

with open('frontend/UI_controller.js', 'r', encoding='utf-8') as f:
    text = f.read()

replacements = {
    'MURAT COKUN': 'Ahmet Yılmaz',
    'PINAR ENDOAN': 'PINAR ERDOĞAN',
    'deiiklik': 'değişiklik',
    'istediinize': 'istediğinize',
    'Eer formda': 'Eğer formda',
    'GÜNCELLEME BAÅžARILI!': 'GÜNCELLEME BAŞARILI!',
    'ARÅžİVLE': 'ARŞİVLE'
}

for bad, good in replacements.items():
    text = text.replace(bad, good)

with open('frontend/UI_controller.js', 'w', encoding='utf-8') as f:
    f.write(text)
print('Restored UI_controller.js')
