// =====================================================
// IT INVENTORY - VPN YONETIMI CONTROLLER (COMPACT CARDS V4)
// =====================================================
window.app = window.app || {};

Object.assign(window.app, {
    vpnList: [],
    vpnFiltered: [],
    vpnFilterType: "TUMU",
    vpnPage: 0,
    vpnPageSize: 40,
    _vpnScrollBound: false,
    _activeVpnUserId: null,
    _activeVpnMode: "view_or_upload",

    loadVpn: async function() {
        try {
            const resp = await this.apiRequest("/vpn/get_all");
            this.vpnList = Array.isArray(resp) ? resp : (resp.data || []);
            this.vpnPage = 0;
            this.vpnFiltered = [];
            this.updateVpnCounts();
            this.renderVpn();
            this._setupVpnScroll();
        } catch (e) {
            console.error("[VPN LOAD ERROR]", e);
            if (this.showToast) this.showToast("VPN verileri yüklenirken hata oluştu", "error");
        }
    },

    updateVpnCounts: function() {
        const total = this.vpnList.length;
        let risk = 0, yaklasan = 0, biten = 0, guncel = 0, hekim = 0, dis = 0;

        for (const item of this.vpnList) {
            if (item.calculated_status === "AYRILDI") risk++;
            else if (item.calculated_status === "SURESI_YAKLASTI") yaklasan++;
            else if (item.calculated_status === "SURESI_BITTI") biten++;
            else if (item.calculated_status === "GUNCEL") guncel++;

            if (item.user_type === "HEKİM") hekim++;
            else if (item.user_type === "DIŞ DESTEK") dis++;
        }

        const setTxt = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.innerText = val;
        };

        setTxt("vpn-count-tumu", total);
        setTxt("vpn-count-risk", risk);
        setTxt("vpn-count-yaklasan", yaklasan);
        setTxt("vpn-count-biten", biten);
        setTxt("vpn-count-guncel", guncel);
        setTxt("vpn-count-hekim", hekim);
        setTxt("vpn-count-dis", dis);
        setTxt("vpn-total-badge", total);
    },

    setVpnFilter: function(type) {
        this.vpnFilterType = type;
        document.querySelectorAll("#vpn-filter-chips .btn-chip").forEach(btn => {
            if (btn.getAttribute("data-filter") === type) btn.classList.add("active");
            else btn.classList.remove("active");
        });
        this.vpnPage = 0;
        this.renderVpn();
    },

    searchVpn: function() {
        this.vpnPage = 0;
        this.renderVpn();
    },

    _setupVpnScroll: function() {
        if (this._vpnScrollBound) return;
        const sentinel = document.getElementById('vpn-scroll-sentinel');
        if (!sentinel) return;

        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                if (this.vpnFiltered && this.vpnFiltered.length > (this.vpnPage) * this.vpnPageSize) {
                    this._loadMoreVpn();
                }
            }
        });
        observer.observe(sentinel);
        this._vpnScrollBound = true;
    },

    renderVpn: function() {
        const grid = document.getElementById("vpn-grid");
        if (!grid) return;

        const search = (document.getElementById("vpn-search")?.value || "").toLowerCase().trim();

        this.vpnFiltered = this.vpnList.filter(item => {
            if (this.vpnFilterType === "RISK" && item.calculated_status !== "AYRILDI") return false;
            if (this.vpnFilterType === "YAKLASAN" && item.calculated_status !== "SURESI_YAKLASTI") return false;
            if (this.vpnFilterType === "BITEN" && item.calculated_status !== "SURESI_BITTI") return false;
            if (this.vpnFilterType === "GUNCEL" && item.calculated_status !== "GUNCEL") return false;
            if (this.vpnFilterType === "HEKİM" && item.user_type !== "HEKİM") return false;
            if (this.vpnFilterType === "DIS_DESTEK" && item.user_type !== "DIŞ DESTEK") return false;

            if (search) {
                const combined = [
                    item.username || "",
                    item.full_name || "",
                    item.tc_no || "",
                    item.phone || "",
                    item.email || "",
                    item.department || "",
                    item.title || "",
                    item.institution || "",
                    item.sicil_no || ""
                ].join(" ").toLowerCase();
                return combined.includes(search);
            }
            return true;
        });

        // SİCİL NO'YA GÖRE KÜÇÜKTEN BÜYÜĞE SIRALAMA (BOŞ OLANLAR EN SONA)
        this.vpnFiltered.sort((a, b) => {
            const hasA = a.sicil_no && String(a.sicil_no).trim() !== "";
            const hasB = b.sicil_no && String(b.sicil_no).trim() !== "";
            if (hasA && !hasB) return -1;
            if (!hasA && hasB) return 1;
            if (!hasA && !hasB) return (a.full_name || a.username || "").localeCompare(b.full_name || b.username || "", "tr");
            
            const numA = parseInt(a.sicil_no, 10);
            const numB = parseInt(b.sicil_no, 10);
            if (!isNaN(numA) && !isNaN(numB)) {
                return numA - numB;
            }
            return String(a.sicil_no).localeCompare(String(b.sicil_no), "tr");
        });

        grid.innerHTML = "";
        this.vpnPage = 0;
        this._loadMoreVpn();
    },

    _loadMoreVpn: function() {
        const grid = document.getElementById("vpn-grid");
        if (!grid) return;

        const start = this.vpnPage * this.vpnPageSize;
        if (start >= this.vpnFiltered.length) return;
        const chunk = this.vpnFiltered.slice(start, start + this.vpnPageSize);
        if (chunk.length === 0) return;

        let html = "";
        for (const item of chunk) {
            const isKapatildi = item.calculated_status === "KAPATILDI" || item.vpn_status === "Kapatıldı";
            const isAyrildi = item.calculated_status === "AYRILDI" && !isKapatildi;
            const isBiten = item.calculated_status === "SURESI_BITTI" && !isKapatildi;
            const isYaklasan = item.calculated_status === "SURESI_YAKLASTI" && !isKapatildi;

            // Bar ve Durum Rengi
            let barColor = "#10b981"; // Yeşil
            let badgeColor = "#10b981";
            let badgeBg = "rgba(16, 185, 129, 0.1)";
            let badgeBorder = "rgba(16, 185, 129, 0.2)";

            if (isKapatildi) {
                barColor = "#64748b";
                badgeColor = "#94a3b8";
                badgeBg = "rgba(148, 163, 184, 0.12)";
                badgeBorder = "rgba(148, 163, 184, 0.3)";
            } else if (isYaklasan) {
                barColor = "#f59e0b";
                badgeColor = "#f59e0b";
                badgeBg = "rgba(245, 158, 11, 0.1)";
                badgeBorder = "rgba(245, 158, 11, 0.2)";
            } else if (isBiten) {
                barColor = "#ef4444";
                badgeColor = "#ef4444";
                badgeBg = "rgba(239, 68, 68, 0.1)";
                badgeBorder = "rgba(239, 68, 68, 0.2)";
            } else if (isAyrildi) {
                barColor = "#ef4444";
                badgeColor = "#fff";
                badgeBg = "#ef4444";
                badgeBorder = "#ef4444";
            }

            const escapedName = (item.full_name || item.username).replace(/'/g, "\\'").replace(/"/g, '&quot;');
            
            // Kart Çerçeve Stili
            let cardStyle = "border: 1px solid rgba(255,255,255,0.05); background: var(--bg-secondary, #111827);";
            if (isKapatildi) {
                cardStyle = "border: 1px solid rgba(148, 163, 184, 0.2); background: rgba(15, 23, 42, 0.6); opacity: 0.85;";
            } else if (isAyrildi) {
                cardStyle = "border: 1px solid #ef4444; background: linear-gradient(145deg, rgba(239, 68, 68, 0.12) 0%, rgba(15, 23, 42, 0.8) 100%);";
            }

            html += `
            <div class="card printer-card-modern fade-in" 
                 style="${cardStyle} min-height: 180px; padding: 12px; display: flex; flex-direction: column; justify-content: space-between;">
                
                <div>
                    <!-- 1. BAŞLIK SATIRI: AD SOYAD (SOLDA) - İŞTEN AYRILDI / DURUM ROZETİ (EN SAĞDA) -->
                    <div class="flex-row" style="justify-content: space-between; align-items: center; margin-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 6px;">
                        <div style="color: #38bdf8; font-weight: 900; font-size: 1rem; letter-spacing: -0.3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 65%;" title="${item.full_name || item.username}">
                            ${item.full_name || item.username}
                        </div>
                        <span class="status-badge" style="background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeBorder}; padding: 2px 8px; font-size: 0.65rem; border-radius: 10px; font-weight: 800; white-space: nowrap; margin-left: auto;">
                            ${item.status_label}
                        </span>
                    </div>

                    <!-- 2. SATIR: KULLANICI ADI (SOL) & CEP TELEFONU (SAĞ - KIRMIZI OKLA İŞARETLENEN ALAN) -->
                    <div class="flex-row mb-2" style="justify-content: space-between; align-items: center; font-size: 0.72rem;">
                        <span style="color: #64748b; font-family: monospace; font-weight: 700;">@${item.username}</span>
                        <span style="color: #38bdf8; font-weight: 700; font-size: 0.72rem; white-space: nowrap;" title="Cep Telefonu">
                            <i class="fas fa-phone-alt" style="opacity: 0.7; margin-right: 3px; font-size: 0.65rem;"></i>${item.phone || '-'}
                        </span>
                    </div>

                    <!-- 3. SATIR: BİRİM KUTUSU (DEPARTMAN, İŞ UNVANI, SİCİL NO, MAİL) -->
                    <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 6px 8px; margin-bottom: 8px; min-height: 52px; display: flex; flex-direction: column; justify-content: center;">
                        <!-- DEPARTMAN -->
                        <div style="font-size: 0.78rem; color: #e2e8f0; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: center; margin-bottom: 3px;" title="${item.department || '-'}">
                            ${(item.department || '-').toUpperCase()}
                        </div>
                        <!-- İŞ UNVANI (SOL) & SİCİL NO (SAĞ) -->
                        <div class="flex-row" style="justify-content: space-between; align-items: center; gap: 8px; font-size: 0.65rem; color: #94a3b8; margin-bottom: 2px;">
                            <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 60%;" title="İş Ünvanı: ${item.title || '-'}">
                                <i class="fas fa-id-badge" style="opacity: 0.6; margin-right: 3px;"></i>${item.title || '-'}
                            </span>
                            ${item.sicil_no ? '<span style="white-space: nowrap; font-weight: 700; color: #c084fc;" title="Sicil No: ' + item.sicil_no + '"><i class="fas fa-hashtag" style="opacity: 0.6; margin-right: 2px;"></i>' + item.sicil_no + '</span>' : ''}
                        </div>
                        <!-- E-MAIL (ALT SATIR) -->
                        <div style="font-size: 0.60rem; color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: center;" title="E-Mail: ${item.email || '-'}">
                            <i class="fas fa-envelope" style="opacity: 0.5; margin-right: 3px;"></i>${item.email || '-'}
                        </div>
                    </div>
                </div>

                <!-- 4. VE 5. BÖLÜM: ALT KISIM (UYARI / PROGRESS BAR VE ALTINDAKİ BUTONLAR) -->
                <div style="margin-top: auto;">
                    ${isKapatildi ? `
                    <!-- VPN KAPATILDI BILDIRIMI -->
                    <div style="background: rgba(148, 163, 184, 0.1); border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 4px; padding: 4px 6px; font-size: 0.65rem; color: #94a3b8; text-align: center; font-weight: 700; margin-bottom: 8px;">
                        <i class="fas fa-check-circle" style="color: #10b981; margin-right: 4px;"></i> PERSONEL AYRILDI - VPN KAPATILDI
                    </div>
                    ` : isAyrildi ? `
                    <!-- PERSONEL AYRILDI UYARISI -->
                    <div style="background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; border-radius: 4px; padding: 4px 6px; font-size: 0.65rem; color: #fca5a5; text-align: center; font-weight: 800; margin-bottom: 8px;">
                        <i class="fas fa-exclamation-triangle"></i> PERSONEL AYRILDI - VPN AÇIK!
                    </div>
                    ` : `
                    <!-- SÜRE DÖNGÜSÜ & PROGRESS BAR -->
                    <div style="margin-bottom: 8px;">
                        <div class="flex-row" style="justify-content: space-between; font-size: 0.65rem; color: #94a3b8; margin-bottom: 3px;">
                            <span>Bitiş: <strong>${item.expiry_date_str}</strong></span>
                            <span style="color: ${barColor}; font-weight: 700;">${item.days_left !== undefined ? item.days_left + ' Gün' : '-'}</span>
                        </div>
                        <div style="width: 100%; height: 4px; background: rgba(255,255,255,0.08); border-radius: 2px; overflow: hidden;">
                            <div style="width: ${item.percent_left}%; height: 100%; background: ${barColor};"></div>
                        </div>
                    </div>
                    `}

                    <!-- EN ALTTAKİ AKSİYON BUTONLARI -->
                    <div class="flex-row gap-2" style="justify-content: flex-end; align-items: center; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px;">
                        ${item.phone ? `
                        <button class="btn-chip" onclick="app.sendVpnWhatsApp('${item.phone}', '${escapedName}', '${item.expiry_date_str}')" 
                                title="WhatsApp ile Hatırlat"
                                style="background: rgba(37, 211, 102, 0.12); color: #25d366; border: 1px solid rgba(37, 211, 102, 0.3); padding: 3px 8px; font-size: 0.68rem; font-weight: 700;">
                            <i class="fab fa-whatsapp"></i> WP
                        </button>
                        ` : ''}

                        <button class="btn-chip" onclick="app.openVpnPetitionModal(${item.id}, 'view_or_upload')" 
                                title="Dilekçeyi Gör veya Yenisini Yükle"
                                style="background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); padding: 3px 8px; font-size: 0.68rem; font-weight: 700;">
                            <i class="fas fa-file-alt"></i> Evrak
                        </button>

                        <button class="btn-chip" onclick="app.extendVpn(${item.id})" 
                                title="Dilekçe Yükleyerek 1 Yıl Uzat"
                                style="background: rgba(16, 185, 129, 0.12); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); padding: 3px 8px; font-size: 0.68rem; font-weight: 700;">
                            <i class="fas fa-plus"></i> +1 Yıl
                        </button>

                        ${isKapatildi ? `
                        <button class="btn-chip" onclick="app.activateVpn(${item.id}, '${escapedName}')" 
                                title="VPN Erişimini Yeniden Aktif Et"
                                style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); padding: 3px 10px; font-size: 0.68rem; font-weight: 800;">
                            <i class="fas fa-play"></i> Aç
                        </button>
                        ` : isAyrildi ? `
                        <button class="btn-chip" onclick="app.closeVpn(${item.id}, '${escapedName}')" 
                                title="VPN Yetkisini Kapat"
                                style="background: #ef4444; color: #fff; border: none; padding: 3px 10px; font-size: 0.68rem; font-weight: 900;">
                            <i class="fas fa-ban"></i> Kapat
                        </button>
                        ` : ''}
                    </div>
                </div>

            </div>
            `;
        }

        grid.insertAdjacentHTML('beforeend', html);
        this.vpnPage++;
    },

    // +1 YIL UZATMA: ARTIK EVRAK YÜKLEMEYİ ZORUNLU KILAR!
    extendVpn: function(id) {
        this.openVpnPetitionModal(id, "extend");
    },


    // VPN YENİDEN AÇMA / AKTİF ETME
    activateVpn: async function(id, name) {
        if (!confirm(`"${name}" kullanıcısının VPN erişimi yeniden AKTİF edilsin mi?`)) return;

        try {
            const res = await this.apiRequest(`/vpn/activate_vpn/${id}`, { method: "POST" });
            if (res && res.success) {
                if (this.showToast) this.showToast("VPN erişimi yeniden aktif edildi!", "success");
                this.loadVpn();
            }
        } catch (e) {
            console.error(e);
        }
    },

    // VPN KAPATMA
    closeVpn: async function(id, name) {
        if (!confirm(`DİKKAT: ${name} isimli kullanıcının VPN erişimi sistemde KAPATILDI olarak işaretlensin mi?`)) return;

        try {
            const res = await this.apiRequest(`/vpn/close_vpn/${id}`, { method: "POST" });
            if (res && res.success) {
                if (this.showToast) this.showToast("Kullanıcı VPN erişimi kapatıldı!", "success");
                this.loadVpn();
            }
        } catch (e) {
            console.error(e);
        }
    },

    // WHATSAPP BİLDİRİMİ
    sendVpnWhatsApp: function(phone, fullName, expiryStr) {
        if (!phone) {
            alert("Kullanıcının kayıtlı telefon numarası bulunamadı!");
            return;
        }

        let cleanPhone = phone.replace(/\D/g, "");
        if (cleanPhone.startsWith("0")) cleanPhone = cleanPhone.substring(1);
        if (!cleanPhone.startsWith("90")) cleanPhone = "90" + cleanPhone;

        const message = `Sayın ${fullName},\n\nBilgi İşlem VPN erişiminizin 1 yıllık geçerlilik süresi ${expiryStr} tarihinde dolacaktır.\n\nErişim kesintisi yaşamamak için güncel ıslak imzalı dilekçenizi Bilgi İşlem Birimi'ne iletmeniz rica olunur.`;
        const encoded = encodeURIComponent(message);
        const url = `https://api.whatsapp.com/send?phone=${cleanPhone}&text=${encoded}`;
        window.open(url, '_blank');
    },

    // EVRAK MODALI: MEVCUT EVRAKI GÖSTERİR VEYA YENİSİNİ YÜKLETİR
    openVpnPetitionModal: function(id, mode) {
        this._activeVpnUserId = id;
        this._activeVpnMode = mode || "view_or_upload";
        
        const item = this.vpnList.find(i => i.id === id);
        if (!item) return;

        const name = item.full_name || item.username;
        const titleEl = document.getElementById("vpn-modal-title");
        const existingEl = document.getElementById("vpn-modal-existing-file");
        const infoEl = document.getElementById("vpn-modal-user-info");
        const submitBtn = document.getElementById("vpn-modal-submit-btn");
        const fileInput = document.getElementById("vpn-petition-file-input");
        if (fileInput) fileInput.value = "";

        // 1. Mevcut Yüklü Evrak Varsa Göster
        if (item.petition_file && existingEl) {
            existingEl.style.display = "block";
            existingEl.innerHTML = `
            <div style="background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 8px; padding: 12px; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <div style="font-weight: 800; color: #38bdf8; font-size: 0.85rem;"><i class="fas fa-file-pdf"></i> Mevcut Yüklü Dilekçe Belgesi</div>
                    <small style="color: #94a3b8; font-size: 0.70rem;">Dosya: ${item.petition_file}</small>
                </div>
                <a href="/api/vpn/petition/${item.petition_file}" target="_blank" class="btn-chip" style="background: #38bdf8; color: #000; text-decoration: none; font-weight: 800; padding: 4px 12px; font-size: 0.75rem;">
                    <i class="fas fa-external-link-alt"></i> Görüntüle
                </a>
            </div>
            `;
        } else if (existingEl) {
            existingEl.style.display = "block";
            existingEl.innerHTML = `
            <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.2); border-radius: 8px; padding: 10px; font-size: 0.75rem; color: #f59e0b;">
                <i class="fas fa-info-circle"></i> Bu kullanıcıya ait henüz taranmış bir dilekçe belgesi yüklenmemiş.
            </div>
            `;
        }

        // 2. Mod Durumuna Göre Başlık ve Talimatlar
        if (this._activeVpnMode === "extend") {
            if (titleEl) titleEl.innerHTML = `<i class="fas fa-sync-alt" style="color: #10b981;"></i> VPN Süresini +1 Yıl Uzat`;
            if (infoEl) infoEl.innerHTML = `
                <div style="font-size: 0.85rem; color: #fff; margin-bottom: 4px;"><strong>${name}</strong> için +1 Yıl Süre Uzatma</div>
                <div style="font-size: 0.75rem; color: #f59e0b;"><i class="fas fa-shield-alt"></i> Güvenlik kuralı: Süre uzatabilmek için yeni ıslak imzalı dilekçeyi yüklemeniz <strong>zorunludur</strong>.</div>
            `;
            if (submitBtn) {
                submitBtn.innerHTML = `<i class="fas fa-check-circle"></i> Dilekçeyi Yükle ve +1 Yıl Uzat`;
                submitBtn.style.background = "#10b981";
            }
        } else {
            if (titleEl) titleEl.innerHTML = `<i class="fas fa-file-alt" style="color: #38bdf8;"></i> VPN Dilekçe Belgesi`;
            if (infoEl) infoEl.innerHTML = `
                <div style="font-size: 0.85rem; color: #fff; margin-bottom: 4px;"><strong>${name}</strong> Dilekçe Yönetimi</div>
                <div style="font-size: 0.75rem; color: #94a3b8;">${item.petition_file ? "Dilekçeyi güncellemek veya yenisini yüklemek için dosya seçin:" : "Yeni dilekçe belgesi (PDF veya Resim) seçin:"}</div>
            `;
            if (submitBtn) {
                submitBtn.innerHTML = `<i class="fas fa-upload"></i> Belgeyi Kaydet`;
                submitBtn.style.background = "#38bdf8";
            }
        }
        
        const modal = document.getElementById("modal-vpn-petition");
        if (modal) modal.style.display = "flex";
    },

    closeVpnModal: function() {
        const modal = document.getElementById("modal-vpn-petition");
        if (modal) modal.style.display = "none";
        this._activeVpnUserId = null;
    },

    submitVpnPetition: async function() {
        if (!this._activeVpnUserId) return;
        const fileInput = document.getElementById("vpn-petition-file-input");
        
        // ZORUNLULUK KONTROLÜ
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            if (this._activeVpnMode === "extend") {
                alert("DİKKAT: Yeni dilekçe belgesi seçilmeden süre uzatılamaz! Lütfen önce taranmış dilekçe dosyasını (PDF veya Resim) seçin.");
            } else {
                alert("Lütfen yüklenecek dilekçe dosyasını (PDF veya Resim) seçin!");
            }
            return;
        }

        const formData = new FormData();
        formData.append("file", fileInput.files[0]);
        if (this._activeVpnMode === "extend") {
            formData.append("extend_one_year", "1");
        }

        try {
            const token = localStorage.getItem("it_token") || (this.state && this.state.token);
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const res = await fetch(`/api/vpn/upload_petition/${this._activeVpnUserId}`, {
                method: "POST",
                headers: headers,
                body: formData
            });

            const data = await res.json();
            if (data && data.success) {
                if (this._activeVpnMode === "extend") {
                    if (this.showToast) this.showToast(`Yeni dilekçe yüklendi ve VPN süresi ${data.new_expiry_date || ''} tarihine kadar uzatıldı!`, "success");
                } else {
                    if (this.showToast) this.showToast("Dilekçe belgesi başarıyla kaydedildi!", "success");
                }
                this.closeVpnModal();
                this.loadVpn();
            } else {
                alert("Hata: " + (data.error || "Bilinmeyen hata"));
            }
        } catch (e) {
            console.error(e);
            alert("Dosya yüklenirken hata oluştu!");
        }
    },


    // YENİ VPN KULLANICISI EKLEME
    openAddVpnModal: function() {
        const modal = document.getElementById("modal-vpn-add");
        if (modal) {
            modal.style.display = "flex";
            document.getElementById("vpn-add-search-input").value = "";
            document.getElementById("vpn-add-results").innerHTML = `
                <div style="text-align: center; color: #64748b; font-size: 0.8rem; padding: 30px 0;">
                    <i class="fas fa-search" style="font-size: 2rem; display: block; margin-bottom: 10px; opacity: 0.3;"></i>
                    TC Kimlik No, Sicil No veya Ad Soyad ile personel arayın
                </div>
            `;
        }
    },

    closeAddVpnModal: function() {
        const modal = document.getElementById("modal-vpn-add");
        if (modal) modal.style.display = "none";
    },

    searchPersonnel: async function() {
        const q = (document.getElementById("vpn-add-search-input")?.value || "").trim();
        const resultsDiv = document.getElementById("vpn-add-results");
        if (!resultsDiv) return;

        if (!q || q.length < 3) {
            resultsDiv.innerHTML = `
                <div style="text-align: center; color: #f59e0b; font-size: 0.8rem; padding: 20px;">
                    <i class="fas fa-exclamation-circle"></i> En az 3 karakter girin
                </div>
            `;
            return;
        }

        resultsDiv.innerHTML = `
            <div style="text-align: center; color: #38bdf8; font-size: 0.8rem; padding: 20px;">
                <i class="fas fa-spinner fa-spin"></i> Aranıyor...
            </div>
        `;

        try {
            const resp = await this.apiRequest(`/vpn/search_personnel?q=${encodeURIComponent(q)}`);
            const results = resp.results || [];

            if (results.length === 0) {
                resultsDiv.innerHTML = `
                    <div style="text-align: center; color: #f59e0b; font-size: 0.8rem; padding: 20px;">
                        <i class="fas fa-user-slash"></i> "${q}" ile eşleşen personel bulunamadı
                    </div>
                `;
                return;
            }

            let html = "";
            for (const p of results) {
                const statusColor = (p.work_status || "").toLowerCase().includes("ayrıl") ? "#ef4444" : "#10b981";
                const statusText = (p.work_status || "").toLowerCase().includes("ayrıl") ? "AYRILDI" : "AKTİF";
                
                html += `
                <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; gap: 12px;">
                    <div style="flex: 1; min-width: 0;">
                        <div style="font-weight: 800; color: #e2e8f0; font-size: 0.9rem; margin-bottom: 2px;">
                            ${p.full_name || p.username}
                            <span style="font-size: 0.65rem; color: ${statusColor}; background: ${statusColor}22; border: 1px solid ${statusColor}44; padding: 1px 6px; border-radius: 8px; margin-left: 6px; font-weight: 700;">${statusText}</span>
                        </div>
                        <div style="font-size: 0.72rem; color: #94a3b8; display: flex; flex-wrap: wrap; gap: 8px;">
                            <span title="Kullanıcı Adı"><i class="fas fa-user" style="opacity: 0.5; margin-right: 2px;"></i>@${p.username}</span>
                            ${p.sicil_no ? '<span title="Sicil No"><i class="fas fa-hashtag" style="opacity: 0.5; margin-right: 2px;"></i>' + p.sicil_no + '</span>' : ''}
                            ${p.tc_no ? '<span title="TC No"><i class="fas fa-id-card" style="opacity: 0.5; margin-right: 2px;"></i>' + p.tc_no + '</span>' : ''}
                        </div>
                        <div style="font-size: 0.68rem; color: #64748b; margin-top: 3px;">
                            ${p.department || '-'} | ${p.title || '-'}
                            ${p.phone ? ' | <i class="fas fa-phone-alt" style="opacity: 0.5;"></i> ' + p.phone : ''}
                        </div>
                    </div>
                    <div style="flex-shrink: 0;">
                        ${p.already_vpn 
                            ? '<span style="background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); padding: 6px 12px; border-radius: 6px; font-size: 0.72rem; font-weight: 800; white-space: nowrap;"><i class="fas fa-check-circle"></i> ZATEN LİSTEDE</span>'
                            : '<button onclick="app.addNewVpnUser(\'' + p.username.replace(/'/g, "\\'") + '\')" class="btn-chip" style="background: #10b981; color: #fff; border: none; padding: 6px 14px; font-size: 0.75rem; font-weight: 800; cursor: pointer; white-space: nowrap; border-radius: 6px;"><i class="fas fa-plus-circle"></i> VPN Aktif Et</button>'
                        }
                    </div>
                </div>
                `;
            }
            resultsDiv.innerHTML = html;
        } catch (e) {
            console.error("[SEARCH ERROR]", e);
            resultsDiv.innerHTML = `
                <div style="text-align: center; color: #ef4444; font-size: 0.8rem; padding: 20px;">
                    <i class="fas fa-exclamation-triangle"></i> Arama sırasında hata oluştu
                </div>
            `;
        }
    },

    addNewVpnUser: async function(username) {
        if (!confirm(`"${username}" kullanıcısını VPN listesine eklemek istediğinize emin misiniz?\n\nVPN süresi bugünden itibaren 1 yıl olarak ayarlanacak.`)) return;

        try {
            const res = await this.apiRequest("/vpn/add_new", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ username: username })
            });

            if (res && res.success) {
                if (this.showToast) this.showToast(res.message || "VPN kullanıcısı eklendi!", "success");
                this.closeAddVpnModal();
                this.loadVpn();
            } else {
                alert("Hata: " + (res.error || "Bilinmeyen hata"));
            }
        } catch (e) {
            console.error(e);
            alert("VPN kullanıcısı eklenirken hata oluştu!");
        }
    },

    // EXCEL EXPORT
    exportVpnToExcel: function() {
        if (!this.vpnFiltered || this.vpnFiltered.length === 0) {
            alert("Dışa aktarılacak veri bulunamadı!");
            return;
        }

        const headers = ["Kullanıcı Adı", "Ad Soyad", "TC No", "Sicil No", "Telefon", "E-Mail", "Departman", "Görev / Unvan", "Kurum", "Kategori", "Durum", "Dilekçe Tarihi", "Bitiş Tarihi", "Kalan Gün"];
        const rows = this.vpnFiltered.map(i => [
            i.username || "",
            i.full_name || "",
            i.tc_no || "",
            i.sicil_no || "",
            i.phone || "",
            i.email || "",
            i.department || "",
            i.title || "",
            i.institution || "",
            i.user_type || "",
            i.status_label || "",
            i.petition_date_str || "",
            i.expiry_date_str || "",
            i.days_left !== undefined ? i.days_left : ""
        ]);

        let csvContent = "\uFEFF" + headers.join(";") + "\n";
        rows.forEach(r => {
            csvContent += r.map(f => `"${String(f).replace(/"/g, '""')}"`).join(";") + "\n";
        });

        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.setAttribute("download", `VPN_Kullanicilari_Rapor_${new Date().toISOString().slice(0,10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
});
