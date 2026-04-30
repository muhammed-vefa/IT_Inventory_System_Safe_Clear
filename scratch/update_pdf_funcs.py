
import os

def update_pdf_functions():
    file_path = 'frontend/UI_controller.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. generateHTPDF Güncellemesi
    old_ht = "generateHTPDF: function(format) {"
    new_ht = "generateHTPDF: function(format, isDirect = false) {"
    content = content.replace(old_ht, new_ht)

    old_ht_payload = "const payload = { type: 'HT', format, data: items };"
    new_ht_payload = "const payload = { type: 'HT', format, data: items, direct_print: isDirect, printer_id: 'PR-001' };"
    content = content.replace(old_ht_payload, new_ht_payload)

    # 2. generateZimmetPDF Güncellemesi
    old_zimmet = "generateZimmetPDF: function(format) {"
    new_zimmet = "generateZimmetPDF: function(format, isDirect = false) {"
    content = content.replace(old_zimmet, new_zimmet)

    old_zimmet_payload = "const payload = { type: 'ZIMMET', format, data: items };"
    new_zimmet_payload = "const payload = { type: 'ZIMMET', format, data: items, direct_print: isDirect, printer_id: 'PR-001' };"
    content = content.replace(old_zimmet_payload, new_zimmet_payload)

    # 3. generateSLAPDF Güncellemesi
    old_sla = "generateSLAPDF: function(format) {"
    new_sla = "generateSLAPDF: function(format, isDirect = false) {"
    content = content.replace(old_sla, new_sla)

    old_sla_payload = "const payload = { type: 'SLA', format, data: items };"
    new_sla_payload = "const payload = { type: 'SLA', format, data: items, direct_print: isDirect, printer_id: 'PR-001' };"
    content = content.replace(old_sla_payload, new_sla_payload)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("UI_controller.js PDF functions updated.")

update_pdf_functions()
