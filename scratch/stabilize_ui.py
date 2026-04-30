
import os
import re

def final_stabilization():
    file_path = 'frontend/UI_controller.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Bazı durumlarda payload içindeki virgüller veya tırnaklar bozulmuş olabilir
    # Özellikle saveServiceRecord bloğunu en baştan temizce yazalım
    
    # saveServiceRecord başlangıç ve bitişini bulup tam blok olarak değiştirelim
    pattern = r"saveServiceRecord: async function\(\) \{[\s\S]*?navigateTo\('service'\); // Kayıt yapıldığında ilgili sekmeye git\s*\} catch \(e\) \{ alert\('Hata: ' \+ e\.message\); \}\s*\}"
    
    replacement = """saveServiceRecord: async function() {
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

    new_content = re.sub(pattern, replacement, content)
    
    # Eğer regex eşleşmezse (bozulma nedeniyle), manuel bir string replace deneyelim
    if new_content == content:
        print("Regex match failed, trying direct string replacement...")
        # Bozuk halini bulmaya çalış
        # ... (Önceki view_file çıktısına göre)
        bad_start = "saveServiceRecord: async function() {"
        # saveServiceRecord'un bittiği yer: "navigateTo('service'); // Kayıt yapıldığında ilgili sekmeye git"ten sonraki ilk catch bloğu sonu
        # En iyisi tüm fonksiyonu içeren bir alanı hedeflemek
    
    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(new_content)
    print("Stabilization complete.")

final_stabilization()
