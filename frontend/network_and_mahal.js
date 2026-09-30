
// Network and Mahal JS Logic
window.app = window.app || {};
Object.assign(window.app, {
    mahalList: [],
    networkList: [],
    networkCategory: "ZAYIF AKIM",
    networkSubCategory: "TÜMÜ",
    networkTower: "TÜMÜ",
    networkPage: 0,
    networkPageSize: 40,
    networkFiltered: [],
    _networkScrollBound: false,
    
    mahalPage: 0,
    mahalPageSize: 50,
    mahalFiltered: [],
    _mahalScrollBound: false,
    mahalFiltered: [],
    _mahalScrollBound: false,

    loadMahal: async function() {
        const resp = await this.apiRequest("/mahal/get_all");
        this.mahalList = Array.isArray(resp) ? resp : [];
        this.mahalPage = 0;
        this.mahalFiltered = [];
        this.renderMahal();
        this._setupMahalScroll();
    },

    _setupMahalScroll: function() {
        if (this._mahalScrollBound) return;
        const sentinel = document.getElementById('mahal-scroll-sentinel');
        if (!sentinel) return;
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                if (this.mahalFiltered && this.mahalFiltered.length > (this.mahalPage) * this.mahalPageSize) {
                    this._loadMoreMahal();
                }
            }
        });
        observer.observe(sentinel);
        this._mahalScrollBound = true;
    },

    _loadMoreMahal: function() {
        const tbody = document.getElementById("mahal-tbody");
        if (!tbody) return;
        const start = this.mahalPage * this.mahalPageSize;
        if (start >= this.mahalFiltered.length) return; // hepsi yüklendi
        const chunk = this.mahalFiltered.slice(start, start + this.mahalPageSize);
        if (chunk.length === 0) return;

        let html = "";
        for (const item of chunk) {
            html += `<tr>
                <td>${item.location_code}</td>
                <td>${item.mimari_mahal_kodu || ''}</td>
                <td>${item.location_name}</td>
                <td>${item.phone_number || ''}</td>
                <td style="text-align:center;">
                    <i class="fas fa-edit action-icon" onclick="app.openMahalModal(${item.id})" style="color:var(--accent);"></i>
                    <i class="fas fa-trash action-icon" onclick="app.deleteMahal(${item.id})" style="color:#ff4444; margin-left:10px;"></i>
                </td>
            </tr>`;
        }
        tbody.insertAdjacentHTML('beforeend', html);
        this.mahalPage++;
    },

    renderMahal: function() {
        const tbody = document.getElementById("mahal-tbody");
        if (!tbody) return;
        const search = (document.getElementById("mahal-search").value || "").toLowerCase();

        this.mahalFiltered = this.mahalList.filter(item => {
            if (!search) return true;
            return (item.location_code && item.location_code.toLowerCase().includes(search)) ||
                   (item.location_name && item.location_name.toLowerCase().includes(search)) ||
                   (item.phone_number && item.phone_number.toLowerCase().includes(search));
        });

        tbody.innerHTML = "";
        this.mahalPage = 0;
        this._loadMoreMahal();
    },

    searchMahal: function() {
        this.renderMahal();
    },

    openMahalModal: function(id) {
        if (!this.state.isLoggedIn || (this.state.activeUser?.role || "").toUpperCase() !== "ADMIN") {
            this.showNotification("Bu islem icin admin yetkisi gereklidir.", "error");
            return;
        }
        this.state.editingId = id;
        if (id) {
            const item = this.mahalList.find(i => i.id === id);
            document.getElementById("edit-mahal-code").value = item.location_code || "";
            document.getElementById("edit-mahal-mimari").value = item.mimari_mahal_kodu || "";
            document.getElementById("edit-mahal-name").value = item.location_name || "";
            document.getElementById("edit-mahal-phone").value = item.phone_number || "";
            document.getElementById("modal-mahal-title").innerText = "Mahal Duzenle";
        } else {
            document.getElementById("edit-mahal-code").value = "";
            document.getElementById("edit-mahal-mimari").value = "";
            document.getElementById("edit-mahal-name").value = "";
            document.getElementById("edit-mahal-phone").value = "";
            document.getElementById("modal-mahal-title").innerText = "Yeni Mahal Ekle";
        }
        document.getElementById("modal-mahal").style.display = "flex";
    },

    saveMahal: async function() {
        const payload = {
            location_code: document.getElementById("edit-mahal-code").value.trim(),
            mimari_mahal_kodu: document.getElementById("edit-mahal-mimari").value.trim(),
            location_name: document.getElementById("edit-mahal-name").value.trim(),
            phone_number: document.getElementById("edit-mahal-phone").value.trim()
        };
        if (!payload.location_code) {
            this.showNotification("Mahal Kodu zorunludur", "error");
            return;
        }
        
        const endpoint = this.state.editingId ? `/mahal/update/${this.state.editingId}` : "/mahal/add";
        const method = this.state.editingId ? "PUT" : "POST";
        
        const res = await this.apiRequest(endpoint, {
            method: method,
            body: JSON.stringify(payload)
        });
        if (res && res.success) {
            this.showNotification("Basariyla kaydedildi", "success");
            this.closeModal("modal-mahal");
            this.loadMahal();
        }
    },

    deleteMahal: async function(id) {
        if (!this.state.isLoggedIn || (this.state.activeUser?.role || "").toUpperCase() !== "ADMIN") {
            this.showNotification("Bu islem icin admin yetkisi gereklidir.", "error");
            return;
        }
        if (!confirm("Bu mahali silmek istediginize emin misiniz?")) return;
        const res = await this.apiRequest(`/mahal/delete/${id}`, { method: "DELETE" });
        if (res && res.success) {
            this.showNotification("Basariyla silindi", "success");
            this.loadMahal();
        }
    },

    // --- NETWORK ---
    loadNetwork: async function() {
        const resp = await this.apiRequest("/network/get_all");
        this.networkList = Array.isArray(resp) ? resp : [];
        this.networkPage = 0;
        this.networkFiltered = [];
        this.renderNetworkSubCategories();
        this.renderNetwork();
        this._setupNetworkScroll();
    },

    _setupNetworkScroll: function() {
        if (this._networkScrollBound) return;
        const sentinel = document.getElementById('network-scroll-sentinel');
        if (!sentinel) return;
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                if (this.networkFiltered && this.networkFiltered.length > (this.networkPage) * this.networkPageSize) {
                    this._loadMoreNetwork();
                }
            }
        });
        observer.observe(sentinel);
        this._networkScrollBound = true;
    },

    _loadMoreNetwork: function() {
        const grid = document.getElementById("network-grid");
        if (!grid) return;
        const start = this.networkPage * this.networkPageSize;
        if (start >= this.networkFiltered.length) return;
        const chunk = this.networkFiltered.slice(start, start + this.networkPageSize);
        if (chunk.length === 0) return;

        let html = "";
        for (const item of chunk) {
            if (item.device_category === 'AP') {
                html += `
                <div class="card printer-card-modern fade-in" style="cursor:pointer; min-height: 140px; padding: 12px;" onclick="app.openNetworkModal(${item.id})">
                    <!-- BAŞLIK SATIRI -->
                    <div class="flex-row" style="justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px;">
                        <div class="flex-row gap-2" style="align-items: center;">
                            <div style="color: #38bdf8; font-weight: 900; font-size: 1.1rem; letter-spacing: -0.5px;">
                                ${item.device_name || '-'}
                            </div>
                            ${item.location_code && item.location_code !== 'UNKNOWN' ? `<span class="status-badge" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.2); padding: 2px 8px; font-size: 0.65rem; border-radius: 12px; font-weight: 800; letter-spacing: 0.5px;">${item.location_code}</span>` : ''}
                        </div>
                        <div class="flex-row gap-2" style="align-items: center;">
                            <span style="font-size: 0.75rem; color: #64748b; font-weight: 700;">${item.ip_address || 'IP YOK'}</span>
                        </div>
                    </div>

                    <!-- İÇERİK KUTUSU -->
                    <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 8px; margin-bottom: 10px; min-height: 48px; display: flex; align-items: center;">
                        <div class="flex-column" style="width: 100%;">
                            <span style="font-size: 0.85rem; color: #e2e8f0; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: center;"><i class="fas fa-network-wired"></i> ${item.mac_address || 'MAC YOK'}</span>
                            <div class="flex-row" style="justify-content: center; align-items: center; gap: 10px; margin-top: 4px; font-size: 0.65rem;">
                                <span style="opacity: 0.6; color: #10b981;"><i class="fas fa-barcode"></i> ${item.sw_serial_numbers || 'SERI YOK'}</span>
                            </div>
                        </div>
                    </div>
                </div>
                `;
            } else if (item.device_category === 'SUNUCU') {
                html += `
                <div class="card printer-card-modern fade-in" style="cursor:pointer; min-height: 140px; padding: 12px;" onclick="app.openNetworkModal(${item.id})">
                    <!-- BAŞLIK SATIRI -->
                    <div class="flex-column" style="margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px; gap: 6px;">
                        <div style="color: #38bdf8; font-weight: 900; font-size: 0.95rem; letter-spacing: -0.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%;" title="${item.device_name || '-'}">
                            ${item.device_name || '-'}
                        </div>
                        <div class="flex-row" style="justify-content: space-between; align-items: center; width: 100%;">
                            <div class="flex-row gap-2" style="align-items: center;">
                                ${item.location_code && item.location_code !== 'UNKNOWN' ? `<span class="status-badge" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.2); padding: 2px 6px; font-size: 0.60rem; border-radius: 12px; font-weight: 800; letter-spacing: 0.5px; white-space: nowrap;">${item.location_code}</span>` : ''}
                                ${item.sub_category ? `<span class="status-badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); padding: 2px 6px; font-size: 0.60rem; border-radius: 12px; font-weight: 800; letter-spacing: 0.5px; white-space: nowrap;">${item.sub_category}</span>` : ''}
                            </div>
                            <div class="flex-row gap-2" style="align-items: center;">
                                <span style="font-size: 0.75rem; color: #64748b; font-weight: 700; white-space: nowrap;">${item.ip_address || 'IP YOK'}</span>
                            </div>
                        </div>
                    </div>

                    <!-- İÇERİK KUTUSU -->
                    <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 8px; display: flex; align-items: center;">
                        <div class="flex-column" style="width: 100%; gap: 6px;">
                            <div class="flex-row" style="justify-content: center; align-items: center; gap: 8px; flex-wrap: wrap;">
                                <span style="font-size: 0.85rem; color: #e2e8f0; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: center;" title="${item.isletme_mahali || 'OS YOK'}"><i class="fab fa-linux"></i> ${item.isletme_mahali || 'OS YOK'}</span>
                                ${item.warranty_info ? `<span style="font-size: 0.60rem; color: #f59e0b; background: rgba(245, 158, 11, 0.05); border: 1px solid rgba(245, 158, 11, 0.2); padding: 2px 6px; border-radius: 4px; white-space: nowrap;">${item.warranty_info}</span>` : ''}
                            </div>
                            
                            <div class="flex-row" style="justify-content: center; align-items: center; gap: 10px; font-size: 0.65rem; color: #94a3b8;">
                                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;" title="${item.proje_mahali || 'İşlev Belirtilmemiş'}"><i class="fas fa-server"></i> ${item.proje_mahali || 'İşlev Belirtilmemiş'}</span>
                            </div>
                            
                            <div class="flex-row" style="justify-content: center; align-items: center; gap: 10px; font-size: 0.65rem;">
                                <span style="opacity: 0.8; color: #38bdf8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;" title="${item.mac_address || 'Donanım Bilgisi Yok'}"><i class="fas fa-microchip"></i> ${item.mac_address || 'Donanım Bilgisi Yok'}</span>
                            </div>

                            <div class="flex-row" style="justify-content: center; align-items: center; gap: 10px; font-size: 0.65rem;">
                                <span style="opacity: 0.6; color: #ef4444; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;" title="${item.sw_serial_numbers || 'Sorumlu Yok'}"><i class="fas fa-user-tie"></i> ${item.sw_serial_numbers ? item.sw_serial_numbers.split('(')[0].trim() : 'Sorumlu Yok'}</span>
                            </div>
                        </div>
                    </div>
                </div>
                `;
            } else {
                html += `
                <div class="card printer-card-modern fade-in" style="cursor:pointer; min-height: 140px; padding: 12px;" onclick="app.openNetworkModal(${item.id})">
                    <!-- BAŞLIK SATIRI -->
                    <div class="flex-row" style="justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px;">
                        <div class="flex-row gap-2" style="align-items: center;">
                            <div style="color: #38bdf8; font-weight: 900; font-size: 1.1rem; letter-spacing: -0.5px;">
                                ${item.location_code || '-'}
                            </div>
                            <span class="status-badge" style="background: ${item.sub_category === 'HBYS' ? 'rgba(56, 189, 248, 0.1)' : 'rgba(16, 185, 129, 0.1)'}; color: ${item.sub_category === 'HBYS' ? '#38bdf8' : '#10b981'}; border: 1px solid ${item.sub_category === 'HBYS' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(16, 185, 129, 0.2)'}; padding: 2px 8px; font-size: 0.65rem; border-radius: 12px; font-weight: 800; letter-spacing: 0.5px;">${item.sub_category === 'İŞLETME' ? 'ISL' : (item.sub_category || '')}</span>
                        </div>
                        <div class="flex-row gap-2" style="align-items: center;">
                            <span style="font-size: 0.75rem; color: #64748b; font-weight: 700;">${item.ip_address || 'IP YOK'}</span>
                        </div>
                    </div>

                    <!-- İÇERİK KUTUSU -->
                    <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 8px; margin-bottom: 10px; min-height: 48px; display: flex; align-items: center;">
                        <div class="flex-column" style="width: 100%;">
                            <span style="font-size: 0.85rem; color: #e2e8f0; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: center;">${item.device_name || '-'}</span>
                            <div class="flex-row" style="justify-content: center; align-items: center; gap: 10px; margin-top: 4px; font-size: 0.65rem;">
                                <span style="opacity: 0.6; color: #ef4444;"><i class="fas fa-microchip"></i> ${item.proje_mahali || '-'}</span>
                            </div>
                        </div>
                    </div>
                </div>
                `;
            }
        }
        
        grid.insertAdjacentHTML('beforeend', html);
        this.networkPage++;
    },

    setNetworkCat: function(cat) {
        this.networkCategory = cat;
        // Varsayilan alt kategoriyi sec
        if (cat === "ZAYIF AKIM") this.networkSubCategory = "TÜMÜ";
        else if (cat === "AP") this.networkSubCategory = "";
        else if (cat === "SUNUCU") this.networkSubCategory = "";
        else if (cat === "DC") this.networkSubCategory = "MH DC";
        
        // Update Chips UI
        document.querySelectorAll("#network-category-chips .btn-chip").forEach(c => {
            if (c.getAttribute("data-cat") === cat) c.classList.add("active");
            else c.classList.remove("active");
        });
        
        this.renderNetworkSubCategories();
        this.renderNetwork();
    },

    setNetworkSubCat: function(subcat) {
        this.networkSubCategory = subcat;
        document.querySelectorAll("#network-subcategory-chips .btn-chip").forEach(c => {
            if (c.getAttribute("data-subcat") === subcat) c.classList.add("active");
            else c.classList.remove("active");
        });
        this.renderNetwork();
    },

    setNetworkTower: function(tower) {
        this.networkTower = tower;
        document.querySelectorAll("#network-tower-chips .btn-chip").forEach(c => {
            if (c.getAttribute("data-tower") === tower) c.classList.add("active");
            else c.classList.remove("active");
        });
        this.renderNetwork();
    },

    renderNetworkSubCategories: function() {
        const container = document.getElementById("network-subcategory-chips");
        const towerContainer = document.getElementById("network-tower-chips");
        if (!container) return;
        
        let html = "";
        if (this.networkCategory === "ZAYIF AKIM") {
            // Kullanici istegi uzerine Zayif Akim alt kategori butonlari kaldirildi (dogrudan kartta gosterilecek)
            if (towerContainer) towerContainer.style.display = "flex";
        } else if (this.networkCategory === "DC") {
            html += `<button class="btn-chip ${this.networkSubCategory==="MH DC"?"active":""}" data-subcat="MH DC" onclick="app.setNetworkSubCat('MH DC')">MH DC</button>`;
            html += `<button class="btn-chip ${this.networkSubCategory==="TSB DC"?"active":""}" data-subcat="TSB DC" onclick="app.setNetworkSubCat('TSB DC')">TSB DC</button>`;
            if (towerContainer) towerContainer.style.display = "none";
        } else {
            if (towerContainer) towerContainer.style.display = "none";
        }
        container.innerHTML = html;
        container.style.display = html ? "flex" : "none";
    },

    renderNetwork: function() {
        const grid = document.getElementById("network-grid");
        if (!grid) return;
        const search = (document.getElementById("network-search").value || "").toLowerCase();
        
        let filtered = this.networkList.filter(i => i.device_category === this.networkCategory);
        
        // AP lerde mac ve seri no bilgisi yok ise listelenmesin
        if (this.networkCategory === "AP") {
            filtered = filtered.filter(i => {
                const mac = (i.mac_address || "").trim().toLowerCase();
                const serial = (i.sw_serial_numbers || "").trim().toLowerCase();
                
                const isMacEmpty = mac === "" || mac === "nan" || mac === "bilinmiyor";
                const isSerialEmpty = serial === "" || serial === "nan" || serial === "bilinmiyor";
                
                // İkisi de yoksa filtrele (gösterme)
                return !(isMacEmpty && isSerialEmpty);
            });
        }

        if (this.networkSubCategory && this.networkSubCategory !== "TÜMÜ") {
            filtered = filtered.filter(i => i.sub_category === this.networkSubCategory);
        }
        
        if (this.networkCategory === "ZAYIF AKIM" && this.networkTower && this.networkTower !== "TÜMÜ") {
            filtered = filtered.filter(i => (i.tower || "").toUpperCase() === this.networkTower.toUpperCase());
        }
        
        if (search) {
            filtered = filtered.filter(i => 
                (i.location_code || "").toLowerCase().includes(search) || 
                (i.proje_mahali || "").toLowerCase().includes(search) || 
                (i.isletme_mahali || "").toLowerCase().includes(search) || 
                (i.device_name || "").toLowerCase().includes(search) || 
                (i.ip_address || "").toLowerCase().includes(search) ||
                (i.mac_address || "").toLowerCase().includes(search) ||
                (i.sw_serial_numbers || "").toLowerCase().includes(search)
            );
        }

        // Siralama: AP ise adına göre, Zayıf Akım ise mahal koduna göre
        const collator = (window.app && window.app.trCollator) || new Intl.Collator('tr', {numeric: true, sensitivity: 'base'});
        filtered.sort((a, b) => {
            if (this.networkCategory === 'AP') {
                const nameA = (a.device_name || "").toLowerCase();
                const nameB = (b.device_name || "").toLowerCase();
                return collator.compare(nameA, nameB);
            } else {
                const locA = (a.location_code || "").toLowerCase();
                const locB = (b.location_code || "").toLowerCase();
                
                if (locA < locB) return -1;
                if (locA > locB) return 1;
                
                // Lokasyon ayniysa, HBYS'yi ISLETME'nin onune al
                const rankA = a.sub_category === "HBYS" ? 1 : 2;
                const rankB = b.sub_category === "HBYS" ? 1 : 2;
                return rankA - rankB;
            }
        });
        
        const countEl = document.getElementById('network-count');
        if (countEl) {
            countEl.innerHTML = 'Toplam Ağ Cihazı: <span style="color:#fff;">' + filtered.length + '</span>';
        }

        this.networkFiltered = filtered;
        this.networkPage = 0;
        grid.innerHTML = "";
        
        if (filtered.length === 0) {
            grid.innerHTML = '<div style="text-align:center; padding:50px; grid-column:1/-1; color:#aaa;">Kayıt bulunamadı.</div>';
        } else {
            this._loadMoreNetwork();
        }
    },

    searchNetwork: function() {
        this.renderNetwork();
    },

    updateNetworkSubCatDropdown: function() {
        const catEl = document.getElementById("edit-nw-cat");
        if (!catEl) return;
        const cat = catEl.value;
        const sub = document.getElementById("edit-nw-subcat");
        const warrantyGroup = document.getElementById("group-nw-warranty");
        if (sub) sub.innerHTML = "";
        
        // Find labels (cached)
        if (!this._networkLabelsCache) {
            const labels = Array.from(document.querySelectorAll("#modal-network .form-group label"));
            labels.forEach(l => l.dataset.origText = l.textContent.trim());
            this._networkLabelsCache = labels;
        }
        const labels = this._networkLabelsCache;
        const getLabel = (text) => labels.find(l => (l.dataset.origText || l.textContent).includes(text));

        const lblTower = getLabel("KULE");
        const lblLoc = getLabel("MAHAL KODU");
        const lblMac = getLabel("MAC ADRESİ");
        const lblProj = getLabel("PROJE MAHALİ");
        const lblIsl = getLabel("İŞLETME MAHALİ");
        const lblSerial = getLabel("SWITCH SERİ NUMARALARI");

        if (cat === "ZAYIF AKIM") {
            sub.innerHTML = "<option value=\"HBYS\">HBYS</option><option value=\"İŞLETME\">İŞLETME</option>";
            sub.parentElement.style.display = "block";
            if (warrantyGroup) warrantyGroup.style.display = "none";
            
            if(lblTower) lblTower.textContent = "KULE";
            if(lblLoc) lblLoc.textContent = "MAHAL KODU (BAŞLIK)";
            if(lblMac) lblMac.textContent = "MAC ADRESİ (AP vb.)";
            if(lblProj) lblProj.textContent = "PROJE MAHALİ";
            if(lblIsl) lblIsl.textContent = "İŞLETME MAHALİ";
            if(lblSerial) lblSerial.textContent = "SWITCH SERİ NUMARALARI (ALT ALTA YAZIN)";
        } else if (cat === "DC") {
            sub.innerHTML = "<option value=\"MH DC\">MH DC</option><option value=\"TSB DC\">TSB DC</option>";
            sub.parentElement.style.display = "block";
            if (warrantyGroup) warrantyGroup.style.display = "none";
            
            if(lblTower) lblTower.textContent = "KULE";
            if(lblLoc) lblLoc.textContent = "MAHAL KODU (BAŞLIK)";
            if(lblMac) lblMac.textContent = "MAC ADRESİ (AP vb.)";
            if(lblProj) lblProj.textContent = "PROJE MAHALİ";
            if(lblIsl) lblIsl.textContent = "İŞLETME MAHALİ";
            if(lblSerial) lblSerial.textContent = "SWITCH SERİ NUMARALARI (ALT ALTA YAZIN)";
        } else if (cat === "SUNUCU") {
            sub.innerHTML = "<option value=\"Sanal\">Sanal</option><option value=\"Fiziksel\">Fiziksel</option>";
            sub.parentElement.style.display = "block";
            if (warrantyGroup) warrantyGroup.style.display = "block";
            
            if(lblTower) lblTower.textContent = "MARKA & MODEL";
            if(lblLoc) lblLoc.textContent = "LOKASYON (Örn: Sunucu Odası)";
            if(lblMac) lblMac.textContent = "DONANIM (CPU / RAM / DİSK)";
            if(lblProj) lblProj.textContent = "ANA İŞLEV / SERVİSLER";
            if(lblIsl) lblIsl.textContent = "İŞLETİM SİSTEMİ";
            if(lblSerial) lblSerial.textContent = "SORUMLU KİŞİLER / İLETİŞİM BİLGİSİ";
        } else {
            sub.innerHTML = "<option value=\"\"></option>";
            sub.parentElement.style.display = "none";
            if (warrantyGroup) warrantyGroup.style.display = "none";
            
            if(lblTower) lblTower.textContent = "KULE";
            if(lblLoc) lblLoc.textContent = "MAHAL KODU (BAŞLIK)";
            if(lblMac) lblMac.textContent = "MAC ADRESİ (AP vb.)";
            if(lblProj) lblProj.textContent = "PROJE MAHALİ";
            if(lblIsl) lblIsl.textContent = "İŞLETME MAHALİ";
            if(lblSerial) lblSerial.textContent = "DONANIM/SERİ NUMARALARI";
        }
    },

    openNetworkModal: function(id) {
        if (!this.state.isLoggedIn || (this.state.activeUser?.role || "").toUpperCase() !== "ADMIN") {
            this.showNotification("Bu islem icin admin yetkisi gereklidir.", "error");
            return;
        }
        this.state.editingId = id;
        if (id) {
            const item = this.networkList.find(i => i.id === id);
            document.getElementById("edit-nw-cat").value = item.device_category || "ZAYIF AKIM";
            this.updateNetworkSubCatDropdown();
            document.getElementById("edit-nw-subcat").value = item.sub_category || "";
            document.getElementById("edit-nw-loc").value = item.location_code || "";
            document.getElementById("edit-nw-ip").value = item.ip_address || "";
            document.getElementById("edit-nw-mac").value = item.mac_address || "";
            document.getElementById("edit-nw-proj").value = item.proje_mahali || "";
            document.getElementById("edit-nw-isl").value = item.isletme_mahali || "";
            if (document.getElementById("edit-nw-warranty")) document.getElementById("edit-nw-warranty").value = item.warranty_info || "";
            document.getElementById("edit-nw-serial").value = item.sw_serial_numbers || "";
            document.getElementById("edit-nw-tower").value = item.tower || "";
            document.getElementById("edit-nw-device-name").value = item.device_name || "";
            const titleName = item.device_name || "Ağ Cihazı";
            document.getElementById("modal-network-title").innerHTML = `<span style="color:#ff4b2b;">${titleName}</span> Detay`;
            
            // Silme butonu ekle
            let footer = document.querySelector("#modal-network .modal-footer");
            if (!document.getElementById("btn-delete-network")) {
                const delBtn = document.createElement("button");
                delBtn.id = "btn-delete-network";
                delBtn.className = "btn";
                delBtn.style.cssText = "background: rgba(239,68,68,0.1); color: #ef4444; border: 1px solid rgba(239,68,68,0.2);";
                delBtn.innerHTML = '<i class="fas fa-trash-alt"></i> Sil';
                delBtn.onclick = () => app.deleteNetwork(id);
                footer.insertBefore(delBtn, footer.firstChild);
            }
        } else {
            document.getElementById("edit-nw-cat").value = this.networkCategory || "ZAYIF AKIM";
            this.updateNetworkSubCatDropdown();
            document.getElementById("edit-nw-subcat").value = this.networkSubCategory || "";
            document.getElementById("edit-nw-loc").value = "";
            document.getElementById("edit-nw-ip").value = "";
            document.getElementById("edit-nw-mac").value = "";
            document.getElementById("edit-nw-proj").value = "";
            document.getElementById("edit-nw-isl").value = "";
            if (document.getElementById("edit-nw-warranty")) document.getElementById("edit-nw-warranty").value = "";
            document.getElementById("edit-nw-serial").value = "";
            document.getElementById("edit-nw-tower").value = this.networkTower !== "TÜMÜ" ? this.networkTower : "";
            document.getElementById("edit-nw-device-name").value = "";
            document.getElementById("modal-network-title").innerHTML = `<span style="color:#00d2ff;">Yeni Ağ Cihazı</span> Ekle`;
            
            let delBtn = document.getElementById("btn-delete-network");
            if (delBtn) delBtn.remove();
        }
        document.getElementById("modal-network").style.display = "flex";
    },

    saveNetwork: async function() {
        const payload = {
            device_category: document.getElementById("edit-nw-cat").value,
            sub_category: document.getElementById("edit-nw-subcat").value,
            location_code: document.getElementById("edit-nw-loc").value,
            ip_address: document.getElementById("edit-nw-ip").value,
            mac_address: document.getElementById("edit-nw-mac").value,
            proje_mahali: document.getElementById("edit-nw-proj").value,
            isletme_mahali: document.getElementById("edit-nw-isl").value,
            sw_serial_numbers: document.getElementById("edit-nw-serial").value,
            tower: document.getElementById("edit-nw-tower").value,
            device_name: document.getElementById("edit-nw-device-name").value,
            warranty_info: document.getElementById("edit-nw-warranty") ? document.getElementById("edit-nw-warranty").value : ""
        };
        
        if (!payload.location_code || !payload.device_category) {
            this.showNotification("Kategori ve Mahal Kodu (Başlık) zorunludur", "error");
            return;
        }
        
        const endpoint = this.state.editingId ? `/network/update/${this.state.editingId}` : "/network/add";
        const method = this.state.editingId ? "PUT" : "POST";
        
        const res = await this.apiRequest(endpoint, {
            method: method,
            body: JSON.stringify(payload)
        });
        if (res && res.success) {
            this.showNotification("Basariyla kaydedildi", "success");
            this.closeModal("modal-network");
            this.loadNetwork();
        }
    },

    deleteNetwork: async function(id) {
        if (!confirm("Bu cihazi silmek istediginize emin misiniz?")) return;
        const res = await this.apiRequest(`/network/delete/${id}`, { method: "DELETE" });
        if (res && res.success) {
            this.showNotification("Basariyla silindi", "success");
            this.closeModal("modal-network");
            this.loadNetwork();
        }
    }
});

