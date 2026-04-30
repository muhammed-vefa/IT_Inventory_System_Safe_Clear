
import os

def final_fix():
    file_path = 'frontend/UI_controller.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. saveServiceRecord Onarımı
    bad_service_save = """    saveServiceRecord: async function() {
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
            this.renderPrinters(); // Yazıcı durumlarının değişmesi için yenile
            this.loadDashboardStats(); // İstatistikleri güncelle
            this.loadInventory(); 
            this.navigateTo('service'); // Kayıt yapıldığında ilgili sekmeye git
        } catch (e) { alert('Hata: ' + e.message); }
    },"""

    good_service_save = """    saveServiceRecord: async function() {
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
            this.renderPrinters(); // Yazıcı durumlarının değişmesi için yenile
            this.loadDashboardStats(); // İstatistikleri güncelle
            this.loadInventory(); 
            this.navigateTo('service'); // Kayıt yapıldığında ilgili sekmeye git
        } catch (e) { alert('Hata: ' + e.message); }
    },"""

    content = content.replace(bad_service_save, good_service_save)

    # 2. sendPDFRequest CUPS Desteği
    target_pdf_fetch = """            const response = await fetch(this.state.API_BASE + '/documents/generate_tutanak', {
                ...options
            });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Backend hatası');
            }"""

    updated_pdf_fetch = """            const response = await fetch(this.state.API_BASE + '/documents/generate_tutanak', {
                ...options
            });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Backend hatası');
            }
            // --- CUPS CHECK ---
            if (response.headers.get('Content-Type').includes('application/json')) {
                const res = await response.json();
                if (res.success) {
                    this.showToast('<i class="fas fa-print"></i> ' + res.message);
                    return;
                }
            }"""

    content = content.replace(target_pdf_fetch, updated_pdf_fetch)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("UI_controller.js final fix applied.")

final_fix()
