import re
import os

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Step 1: Remove <section id="view-printers"> completely
html = re.sub(r'<section id="view-printers".*?</section>', '', html, flags=re.DOTALL)

# Step 2: Inject header buttons into view-inventory
btn_html = '''
                        <button id="btn-printer-add" onclick="app.openPrinterAddModal()" title="Yeni Cihaz Ekle" style="display:none; width: 46px; height: 36px; border-radius: 20px; background: rgba(0, 0, 0, 0.5); border: 1px solid #00d2ff; color: #00d2ff; align-items: center; justify-content: center; font-size: 1.1rem; cursor: pointer; box-shadow: 0 0 10px rgba(0, 210, 255, 0.2), inset 0 0 5px rgba(0, 210, 255, 0.1); transition: all 0.3s ease; padding: 0; outline: none;" onmouseover="this.style.boxShadow='0 0 15px rgba(0, 210, 255, 0.4), inset 0 0 10px rgba(0, 210, 255, 0.2)'; this.style.background='rgba(0, 210, 255, 0.05)';" onmouseout="this.style.boxShadow='0 0 10px rgba(0, 210, 255, 0.2), inset 0 0 5px rgba(0, 210, 255, 0.1)'; this.style.background='rgba(0, 0, 0, 0.5)';">
                            <i class="fas fa-plus"></i>
                        </button>
                        <button id="btn-printers-service" onclick="app.navigateTo('service')" title="Servis İşlemleri" style="display:none; width: 46px; height: 36px; border-radius: 20px; background: rgba(0, 0, 0, 0.5); border: 1px solid #00d2ff; color: #00d2ff; align-items: center; justify-content: center; font-size: 1.1rem; cursor: pointer; box-shadow: 0 0 10px rgba(0, 210, 255, 0.2), inset 0 0 5px rgba(0, 210, 255, 0.1); transition: all 0.3s ease; padding: 0; outline: none;" onmouseover="this.style.boxShadow='0 0 15px rgba(0, 210, 255, 0.4), inset 0 0 10px rgba(0, 210, 255, 0.2)'; this.style.background='rgba(0, 210, 255, 0.05)';" onmouseout="this.style.boxShadow='0 0 10px rgba(0, 210, 255, 0.2), inset 0 0 5px rgba(0, 210, 255, 0.1)'; this.style.background='rgba(0, 0, 0, 0.5)';">
                            <i class="fas fa-tools"></i>
                        </button>
                        <div class="search-wrapper" id="printer-search-wrapper" style="display:none; max-width: 300px;">
                            <input type="text" id="printer-search" class="search-bar" placeholder="Hızlı ara..." oninput="app.searchPrinters()">
                            <i class="fas fa-times clear-search" onclick="app.clearSearch('printer-search')"></i>
                        </div>
'''

target_search = '<i class="fas fa-times clear-search" onclick="app.clearSearch(\'main-search\')"></i>\n                        </div>'
html = html.replace(target_search, target_search + '\n' + btn_html)

# Step 3: Inject grid and model filters below inventory-grid
grid_html = '''
            <!-- Model Bazlı Alt Filtreler (Sadece Yazıcı seçiliyken anlamlı) -->
            <div id="printer-model-filters-container" class="mb-4" style="display:none;">
                <div class="filter-chips" id="printer-model-filters" style="margin-bottom: 0; background: rgba(255,255,255,0.02); padding: 5px; border-radius: 12px; display: inline-flex;">
                    <button class="btn-chip active" data-pmodel="ALL" onclick="app.setPrinterModelType('ALL')">Tümü</button>
                    <button class="btn-chip" data-pmodel="5200" onclick="app.setPrinterModelType('5200')">5200</button>
                    <button class="btn-chip" data-pmodel="6900" onclick="app.setPrinterModelType('6900')">6900</button>
                    <button class="btn-chip" data-pmodel="8690" onclick="app.setPrinterModelType('8690')">8690</button>
                </div>
            </div>

            <div class="grid" id="printers-grid" style="display:none;"></div>
            <div id="printers-scroll-sentinel" style="height: 20px; width: 100%; display:none;"></div>
'''

target_grid = '<div id="inventory-scroll-sentinel" style="height: 20px; width: 100%;"></div>'
html = html.replace(target_grid, target_grid + '\n' + grid_html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('index.html updated successfully.')
