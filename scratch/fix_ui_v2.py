
import os

def fix_ui_controller():
    file_path = 'frontend/UI_controller.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 1. openEditServiceModal Onarımı (Satır 3714 civarı)
    # 2. saveServiceRecord Onarımı (Satır 3755 civarı)
    # 3. sendPDFRequest (CUPS Desteği)

    # Dosyayı tek bir metin olarak alıp Regex veya string replace ile güvenli blok değişimi yapalım
    content = "".join(lines)

    # BOZUK BLOK 1: openEditServiceModal ve saveServiceRecord başlangıcı
    # Bu kısmı orijinal sağlıklı haline döndürüyoruz
    bad_segment_1 = """            if(acqDateEl && p.acq_date) acqDateEl.value = p.acq_date.split(' ')[0];
            
        document.getElementById('service-acq-place').value = s.acq_place || '';"""
    
    good_segment_1 = """            if(acqDateEl && p.acq_date) acqDateEl.value = p.acq_date.split(' ')[0];
            
            // Kullanıcıya geri bildirim ver
            this.showToast(`${p.pr_no} seçildi: ${p.model || ''} — ${p.mahal || 'Depo'}`, 'info');
        }
    },

    openEditServiceModal: function(id) {
        const s = this.state_service.raw.find(x => x.id == id);
        if (!s) return;

        document.getElementById('service-modal-title').innerText = 'Servis Kaydı Düzenle';
        document.getElementById('service-edit-id').value = s.id;
        document.getElementById('service-printer-id').value = s.printer_id || '';
        document.getElementById('service-pr-no').value = s.pr_no || '';
        document.getElementById('service-seri').value = s.seri || '';
        document.getElementById('service-mac').value = s.mac || '';
        document.getElementById('service-model').value = s.model || '';
        document.getElementById('service-mahal').value = s.mahal || '';
        document.getElementById('service-acq-place').value = s.acq_place || '';"""

    content = content.replace(bad_segment_1, good_segment_1)

    # BOZUK BLOK 2: saveServiceRecord payload ve fetch
    bad_segment_2 = """            acq_place: document.getElementById('service-acq-place').value,
            
            const resp = await fetch(url, {
                method: method,"""
    
    good_segment_2 = """            acq_place: document.getElementById('service-acq-place').value,
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
            
            const resp = await fetch(url, {"""
    
    content = content.replace(bad_segment_2, good_segment_2)

    # YENİ ÖZELLİK: sendPDFRequest CUPS Desteği
    cups_logic = """            const response = await fetch(this.state.API_BASE + '/documents/generate_tutanak', {
                ...options
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Backend hatası');
            }

            // --- CUPS / DIRECT PRINT CHECK ---
            const contentType = response.headers.get('Content-Type') || '';
            if (contentType.includes('application/json')) {
                const result = await response.json();
                if (result.success) {
                    this.showToast('<i class="fas fa-print"></i> ' + result.message);
                    return;
                } else if (result.error || result.message) {
                    throw new Error(result.error || result.message);
                }
            }
            // ---------------------------------"""

    target_fetch = """            const response = await fetch(this.state.API_BASE + '/documents/generate_tutanak', {
                ...options
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Backend hatası');
            }"""
    
    content = content.replace(target_fetch, cups_logic)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("UI_controller.js fixed and updated with CUPS logic.")

fix_ui_controller()
