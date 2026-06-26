import re

with open('frontend/UI_controller.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Line 1323 block removal
js = re.sub(r'\} else if \(view === \'printers\'\) \{\s*this\.renderPrinters\(\);\s*\}', '', js)

# Line 1351
js = js.replace("if (view === 'printers' && (this.state.printers || []).length === 0) this.renderPrinters();", "if (view === 'inventory' && ['PRINTER', 'BARCODE_PRINTER', 'BARCODE_READER', 'SCANNER'].includes(this.state.invCategory) && (this.state.printers || []).length === 0) this.renderPrinters();")

# Line 1370
js = js.replace("else if (view === 'printers') await this.renderPrinters();", "else if (view === 'inventory' && ['PRINTER', 'BARCODE_PRINTER', 'BARCODE_READER', 'SCANNER'].includes(this.state.invCategory)) await this.renderPrinters();")

# Line 2515
js = js.replace("if (this.state.view !== 'printers') {", "if (this.state.view !== 'inventory') {")

# Line 6813
js = js.replace("if (view === 'printers' && !this.state.printers.length) {", "if (view === 'inventory' && ['PRINTER', 'BARCODE_PRINTER', 'BARCODE_READER', 'SCANNER'].includes(this.state.invCategory) && !this.state.printers.length) {")

with open('frontend/UI_controller.js', 'w', encoding='utf-8') as f:
    f.write(js)
print('UI_controller.js references to view=printers replaced.')
