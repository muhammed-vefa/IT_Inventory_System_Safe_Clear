import os
from fpdf import FPDF

def tr(t):
    mapping = {
        'ı': 'i', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G', 'ü': 'u', 'Ü': 'U',
        'ş': 's', 'Ş': 'S', 'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
    }
    for k, v in mapping.items():
        t = t.replace(k, v)
    # Strip any other non-ascii characters
    return "".join(c for c in t if ord(c) < 128)

def generate_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font('Courier', size=10)
    
    root = r'C:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory_System'
    files = [
        'main.py', 
        'core/sync_manager.py', 
        'modules/inventory_manager.py', 
        'modules/logs_manager.py', 
        'frontend/UI_controller.js'
    ]
    
    pdf.set_font('Courier', 'B', 14)
    pdf.cell(0, 10, text='IT INVENTORY SYSTEM - DYNAMIC ARCHITECTURE CODEBASE', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(10)
    
    pdf.set_font('Courier', size=9)
    for f_rel in files:
        f_path = os.path.join(root, f_rel)
        if os.path.exists(f_path):
            pdf.set_text_color(0, 0, 255)
            pdf.cell(0, 10, text=f'FILE: {f_rel}', new_x='LMARGIN', new_y='NEXT')
            pdf.set_text_color(0, 0, 0)
            
            with open(f_path, 'r', encoding='utf-8') as f_obj:
                content = f_obj.read()
                pdf.multi_cell(0, 5, text=tr(content))
            pdf.add_page()
            
    output_path = r'C:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory_Codebase_v2.pdf'
    pdf.output(output_path)
    print(f"PDF created at: {output_path}")

if __name__ == "__main__":
    generate_pdf()
