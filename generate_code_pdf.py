import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_code_pdf(base_dir, output_pdf):
    doc = SimpleDocTemplate(output_pdf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Custom Code Style
    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10,
        textColor=colors.black,
        backColor=colors.lightgrey,
        borderPadding=5
    )

    files_to_include = [
        'main.py',
        'core/sync_manager.py',
        'core/database_sql.py',
        'debug_sync.py'
    ]

    story.append(Paragraph("IT INVENTORY SYSTEM - KOD DOKUMANI", styles['Title']))
    story.append(Spacer(1, 12))

    for rel_path in files_to_include:
        abs_path = os.path.join(base_dir, rel_path.replace('/', os.sep))
        if os.path.exists(abs_path):
            story.append(Paragraph(f"Dosya: {rel_path}", styles['Heading2']))
            story.append(Spacer(1, 6))
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Simple escape for XML-like tags in content
                content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Preformatted(content, code_style))
            story.append(Spacer(1, 20))

    doc.build(story)

if __name__ == "__main__":
    # Scratch dizini yolu
    scratch_path = r"C:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory_System"
    output_pdf = os.path.join(scratch_path, "Sistem_Kod_Dokumani.pdf")
    generate_code_pdf(scratch_path, output_pdf)
    print(f"PDF olusturuldu: {output_pdf}")
