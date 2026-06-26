import re

with open('frontend/UI_controller.js', 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Update setInvCategory
new_func = '''    setInvCategory: function(cat) {
        const isChanged = (this.state.invCategory !== (cat || 'PC'));
        this.state.invCategory = cat || 'PC';
        document.querySelectorAll('#device-type-filters .btn-chip').forEach(btn => btn.classList.toggle('active', btn.dataset.category === cat));
        const dd = document.getElementById('search-category-dropdown');
        if (dd) { dd.value = ["BARKOD YAZICI", "BARKOD OKUYUCU", "TARAYICI"].includes(cat) ? cat : ""; }
        
        const isPrinterCat = ['PRINTER', 'BARCODE_PRINTER', 'BARCODE_READER', 'SCANNER'].includes(cat);
        
        // UI Toggles
        const invGrid = document.getElementById('inventory-grid');
        const prGrid = document.getElementById('printers-grid');
        const prSentinel = document.getElementById('printers-scroll-sentinel');
        if(invGrid) invGrid.style.display = isPrinterCat ? 'none' : 'grid';
        if(prGrid) prGrid.style.display = isPrinterCat ? 'grid' : 'none';
        if(prSentinel) prSentinel.style.display = isPrinterCat ? 'block' : 'none';
        
        const prModelFilters = document.getElementById('printer-model-filters-container');
        if(prModelFilters) prModelFilters.style.display = (cat === 'PRINTER') ? 'block' : 'none';
        
        const mainSearch = document.getElementById('main-search');
        if(mainSearch) {
            const msWrap = mainSearch.closest('.search-wrapper');
            if(msWrap) msWrap.style.display = isPrinterCat ? 'none' : 'flex';
        }
        const prSearchWrap = document.getElementById('printer-search-wrapper');
        if(prSearchWrap) prSearchWrap.style.display = isPrinterCat ? 'flex' : 'none';
        
        const addBtn = document.getElementById('btn-device-add');
        const printerAddBtn = document.getElementById('btn-printer-add');
        const printerServiceBtn = document.getElementById('btn-printers-service');
        
        if (addBtn) addBtn.style.display = (cat === 'SK' || cat === 'TABLET' || cat === 'MONITOR' || cat === 'PC') ? 'inline-flex' : 'none';
        if (printerAddBtn) printerAddBtn.style.display = isPrinterCat ? 'flex' : 'none';
        if (printerServiceBtn) printerServiceBtn.style.display = isPrinterCat ? 'flex' : 'none';
        
        const floorFilters = document.getElementById('floor-filters');
        if (floorFilters) floorFilters.style.display = isPrinterCat ? 'none' : 'block';

        if (isPrinterCat) {
            this.state.printerMainType = cat;
            if (isChanged || !this.state.printers) {
                this.renderPrinters();
            } else {
                this.applyPrinterFilters();
            }
            return;
        }

        if (!this.state.inventoryCache) this.state.inventoryCache = {};
        if (isChanged || !this.state.inventoryCache[cat] || this.state.inventoryCache[cat].length === 0) {
            this.loadInventory();
        } else {
            this.state.inventory = this.state.inventoryCache[cat];
            this.updatePeripheralDatalists();
            this.filterInventory();
        }
    },'''

pattern = re.compile(r'    setInvCategory: function\(cat\) \{.*?^    \},', re.MULTILINE | re.DOTALL)
js = pattern.sub(new_func, js, count=1)

# 2. Redirect navigateTo('printers') 
js = js.replace("this.navigateTo('printers');", "this.navigateTo('inventory'); this.setInvCategory('PRINTER');")

# 3. Clean up allowedViews ('printers')
js = js.replace("'printers', ", "")

with open('frontend/UI_controller.js', 'w', encoding='utf-8') as f:
    f.write(js)
print('UI_controller patched.')
