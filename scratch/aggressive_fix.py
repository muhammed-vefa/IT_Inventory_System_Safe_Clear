
import os
import re

def aggressive_fix():
    file_path = 'frontend/UI_controller.js'
    with open(file_path, 'rb') as f:
        data = f.read()
    
    # 1. Dosyadaki tüm kontrol karakterlerini ve bozuk byte'ları temizle (0x00 - 0x1F arası, 0x09, 0x0A, 0x0D hariç)
    # Ayrıca 0x7F - 0x9F arasını da temizle (Bozuk karakterler genelde burada olur)
    clean_data = bytearray()
    for b in data:
        if (32 <= b <= 126) or (b in [9, 10, 13]) or (b >= 160): # ASCII + Standard Newlines + Extended Latin (Turkish)
            clean_data.append(b)
    
    content = clean_data.decode('utf-8', errors='ignore')

    # 2. saveServiceRecord Bloğunu Tekrar Sabitle (Regex ile)
    # Bozulmuş olabilecek alanı bul ve temizle
    pattern = r"saveServiceRecord: async function\(\) \{[\s\S]*?navigateTo\('service'\);\s*\} catch \(e\) \{ alert\('Hata: ' \+ e\.message\); \}\s*\}"
    
    correct_service_block = """saveServiceRecord: async function() {
        const editId = document.getElementById('service-edit-id').value;
        const printerIdVal = document.getElementById('service-printer-id').value;
        const payload = {
            printer_id: printerIdVal ? parseInt(printerIdVal) : null,
            pr_no: document.getElementById('service-pr-no').value,
            seri: document.getElementById('service-seri').value,
            mac: document.getElementById('service-mac').value,
            model: document.getElementById('service-model').value,
            mahal: document.getElementById('service-mahal').value,
            acq_place: document.getElementById('service-acq-place').value,
            acq_date: document.getElementById('service-acq-date').value,
            sent_date: document.getElementById('service-sent-date').value,
            return_date: document.getElementById('service-return-date').value,
            status: document.getElementById('service-status').value,
            fault_desc: document.getElementById('service-fault-desc').value,
            has_substitute: document.getElementById('service-has-substitute').checked,
            substitute_pr_no: document.getElementById('service-substitute-pr-no').value,
            user_name: this.state.activeUser.name
        };

        try {
            const url = editId ? `${this.state.API_BASE}/service/update/${editId}` : `${this.state.API_BASE}/service/add`;
            const method = editId ? 'PUT' : 'POST';
            
            const resp = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await resp.json();
            if (result.error) throw new Error(result.error);

            document.getElementById('service-modal').style.display = 'none';
            this.showToast('Servis kaydı başarıyla kaydedildi!');
            this.loadServiceRecords();
            this.renderPrinters(); 
            this.loadDashboardStats();
            this.loadInventory(); 
            this.navigateTo('service');
        } catch (e) { alert('Hata: ' + e.message); }
    }"""
    
    # Regex ile bulamazsak manuel string replace deneyeceğiz
    if re.search(pattern, content):
        content = re.sub(pattern, correct_service_block, content)
    else:
        # Daha basit bir eşleşme deneyelim
        content = content.replace("saveServiceRecord: async function() {", correct_service_block + " // Fixed\n    _dummy: function() {")

    # 3. Dosyayı kaydet
    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Aggressive fix completed. Invisible characters removed.")

aggressive_fix()
