console.log(">>> UI_controller.js v8.1 LOADED SUCCESSFULLY <<<");
var app = window.app || {};
var appData = {
    state: {
        API_BASE: (window.location.origin || '') + '/api',
        isLoggedIn: false,
        activeUser: null,
        chart: null,
        view: 'printers',
        countMode: false,
        zimmetDevices: [],
        inventory: [],
        printers: [],
        areas: [],
        depot: [],
        noteCounts: {},
        editingId: null,
        editingType: null,
        initialFormData: null, // Deiiklik kontrolü için
        lastFilteredList: [], // Sayım ve sıralama için son filtrelenmi liste
        currentHistoryIndex: 0,
        mahalMap: {},
        auditLogs: [],
        users: [],
        invCategory: 'PC',
        invBlock: 'ALL',
        invKat: 'ALL',
        depot_activeFilter: 'ALL',
        printerMainType: 'PRINTER',
        printerModelType: 'ALL',
        selectedBatchIds: new Set(),
        deferredPrompt: null
    },
    openMulti: async function() { // GHOST CODE REMOVED

        if (!urls || !Array.isArray(urls)) return;
        let blocked = false;
        for (let i = 0; i < urls.length; i++) {
            let win = window.open(urls[i], '_blank');
            if (!win) blocked = true;
        }
        if (blocked) {
            app.showNotification("Uyarı: Birden fazla sekme açılması tarayıcınız tarafından engellendi. Lütfen adres çubuğunun sağındaki 'Pop-up (Açılır pencere) engellendi' simgesine tıklayıp bu site için HER ZAMAN İZİN VER seçeneğini işaretleyin.", "warning", 10000);
        }
    },
    state_service: {
        raw: [],
        filtered: []
    },
    state_kb: {
        tab: 'kodlar'
    },
    // 
    //  INITIALIZATION
    // 
    // Helper to parse complex date string (v13.1)
    parseComplexDate: function(str) {
        if (!str) return null;
        try {
            const cleanStr = String(str).trim();
            // Format A: 'Mar 30 2026' veya 'March 30 2026' veya 'Mar 30 2026 12:00AM'
            const matchA = cleanStr.match(/^([A-Za-zÄğÅşÇçÖöÜüİı]{3,9})\s+(\d{1,2})\s+(\d{4})/i);
            if (matchA) {
                const months = {
                    jan: 0, oca: 0,
                    feb: 1, şub: 1, sub: 1,
                    mar: 2,
                    apr: 3, nis: 3,
                    may: 4,
                    jun: 5, haz: 5,
                    jul: 6, tem: 6,
                    aug: 7, ağu: 7, agu: 7,
                    sep: 8, eyl: 8,
                    oct: 9, eki: 9,
                    nov: 10, kas: 10,
                    dec: 11, ara: 11
                };
                const mKey = matchA[1].substring(0, 3).toLowerCase();
                if (months[mKey] !== undefined) {
                    return new Date(parseInt(matchA[3]), months[mKey], parseInt(matchA[2]));
                }
            }

            // Format B: '30 Mar 2026'
            const matchB = cleanStr.match(/^(\d{1,2})\s+([A-Za-zÄğÅşÇçÖöÜüİı]{3,9})\s+(\d{4})/i);
            if (matchB) {
                const months = {
                    jan: 0, oca: 0,
                    feb: 1, şub: 1, sub: 1,
                    mar: 2,
                    apr: 3, nis: 3,
                    may: 4,
                    jun: 5, haz: 5,
                    jul: 6, tem: 6,
                    aug: 7, ağu: 7, agu: 7,
                    sep: 8, eyl: 8,
                    oct: 9, eki: 9,
                    nov: 10, kas: 10,
                    dec: 11, ara: 11
                };
                const mKey = matchB[2].substring(0, 3).toLowerCase();
                if (months[mKey] !== undefined) {
                    return new Date(parseInt(matchB[3]), months[mKey], parseInt(matchB[1]));
                }
            }
        } catch(e) { console.error(e); }
        
        // Native parse fallback
        const d = new Date(str);
        return isNaN(d.getTime()) ? null : d;
    },

    // Date formatter DD.MM.YYYY - Robust Multi-format Parser (v12.9)
    formatDate: function(dateStr) {
        if (!dateStr || dateStr === '-' || dateStr === 'None') return '-';
        try {
            const str = String(dateStr).trim();
            // 1. Zaten DD.MM.YYYY formatındaysa doğrudan döndür
            if (/^\d{2}\.\d{2}\.\d{4}$/.test(str)) {
                return str;
            }
            // 2. YYYY-MM-DD veya YYYY-MM-DD HH:MM:SS formatı
            if (/^\d{4}-\d{2}-\d{2}/.test(str)) {
                const parts = str.split(' ')[0].split('-');
                return `${parts[2]}.${parts[1]}.${parts[0]}`;
            }
            // 3. Kompleks Tarih Formatları
            const parsedDate = this.parseComplexDate(str);
            if (parsedDate) {
                const day = String(parsedDate.getDate()).padStart(2, '0');
                const month = String(parsedDate.getMonth() + 1).padStart(2, '0');
                const year = parsedDate.getFullYear();
                return `${day}.${month}.${year}`;
            }
            return str;
        } catch(e) { return dateStr; }
    },
    // Input (type="date") için YYYY-MM-DD formati donduren yardimci (v13)
    formatDateForInput: function(dateStr) {
        if (!dateStr || dateStr === '-' || dateStr === 'None') return '';
        try {
            const str = String(dateStr).trim();
            if (/^\d{4}-\d{2}-\d{2}/.test(str)) return str.split(' ')[0];
            if (/^\d{2}\.\d{2}\.\d{4}$/.test(str)) {
                const parts = str.split('.');
                return `${parts[2]}-${parts[1]}-${parts[0]}`;
            }
            const d = this.parseComplexDate(str);
            if (d) {
                return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
            }
        } catch(e) { console.error(e); }
        return '';
    },
    showLoginOverlay: function() {
        var overlay = document.getElementById('login-overlay');
        if (overlay) overlay.style.display = 'flex';
        document.body.classList.add('login-required');
    },
    setupBatchEventListeners: function() {
        // ... batch event listeners implementation ...
    },
    // --- GÜVENLİ FETCH KATMANI (AÅAMA 5) ---
    apiRequest: async function(endpoint, options = {}) {
        try {
            const url = endpoint.startsWith('http') ? endpoint : (this.state.API_BASE + endpoint);
            
            if (options.body && typeof options.body === 'string') {
                options.headers = options.headers || {};
                if (!options.headers['Content-Type']) {
                    options.headers['Content-Type'] = 'application/json';
                }
            }
            
            const response = await fetch(url, options);
            
            // --- UI RESILIENCE (AÅAMA 6): 404/405 Hatalarinda Cokus Engelleme ---
            if (response.status === 404 || response.status === 405) {
                console.warn(`[API ${response.status}] Hata: ${url}`);
                return []; 
            }

            const contentType = response.headers.get('content-type');

            if (!contentType || !contentType.includes('application/json')) {
                // Eğer JSON değilse ama response 404 ise, 404 JSON handler'ımız devreye girmiş olmalı
                // Ama eğer hala HTML geliyorsa (örn. Nginx fallback), burada yakalıyoruz.
                const text = await response.text();
                console.error("Beklenmeyen Yanıt Formatı (HTML):", text.substring(0, 200));
                throw new Error(`Sunucudan geçersiz yanıt geldi (JSON bekleniyordu).`);
            }

            const data = await response.json();

            // --- Standart Yanıt Zarfı Desteği (AÅAMA 3) ---
            if (data && typeof data === 'object' && 'success' in data) {
                if (!data.success) {
                    throw new Error(data.error || data.message || `İşlem başarısız (Kod: ${response.status})`);
                }
                return data.data !== undefined ? data.data : data;
            }

            if (!response.ok) {
                throw new Error(data.error || data.message || `İşlem başarısız (Kod: ${response.status})`);
            }

            return data;
        } catch (err) {
            console.error('API Request Error:', err);
            if (this.showToast) this.showToast(err.message, 'error');
            throw err;
        }
    },
    init: function() {
        try {
            console.log("App Initializing...");
            
            // MATRIX LOGGING: Send all clicks to backend
            window.addEventListener('click', (e) => {
                let target = e.target;
                let elemDesc = target.tagName;
                if (target.id) elemDesc += '#' + target.id;
                if (target.className && typeof target.className === 'string') elemDesc += '.' + target.className.split(' ').join('.');
                if (target.innerText) {
                    let text = target.innerText.substring(0, 30).replace(/\n/g, ' ');
                    if (text) elemDesc += ` ("${text}")`;
                }
                
                let userObj = localStorage.getItem('it_user_data');
                let userName = 'Guest';
                if (userObj) {
                    try { let u = JSON.parse(userObj); userName = u.display_name || u.username || u.name || 'Guest'; } catch(err) { console.error(err); }
                }
                
                fetch('/api/logs/click', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({element: elemDesc, user: userName})
                }).catch(err => {});
            });

            // Global Fetch Interceptor (JWT Auth)
            const originalFetch = window.fetch;
            const self = this;
            window.fetch = async function() {
                let [resource, config] = arguments;
                
                // HttpOnly cookieler otomatik gönderilir, Authorization header eklemeye gerek yok.
                // localStorage'dan token okuma kaldırıldı.
                
                const response = await originalFetch(resource, config);
                
                // 401 hatası gelirse token süresi dolmuş olabilir, refresh dene
                if (response.status === 401 && typeof resource === 'string' && resource.includes('/api/') && !resource.includes('/login') && !resource.includes('/refresh')) {
                    console.warn("401 Unauthorized - Attempting session refresh...");
                    
                    try {
                        const refreshResp = await originalFetch(self.state.API_BASE + '/users/refresh', { method: 'POST' });
                        if (refreshResp.ok) {
                            console.log("Session refreshed successfully. Retrying original request...");
                            return await originalFetch(resource, config);
                        }
                    } catch (err) {
                        console.error("Session refresh failed:", err);
                    }

                    console.error("Session expired. Logging out.");
                    localStorage.removeItem('it_user_data'); // Sadece user info sil, token zaten yok
                    if (self.showLoginOverlay) self.showLoginOverlay();
                    else window.location.reload();
                }
                return response;
            };
            this.checkLoginStatus(); 
            this.setupEventListeners();
            this.setupBatchEventListeners();
            this.setupLoginListeners();
            this.setupSessionTimeout();
            this.setupPwaPrompt();
            // Dashboard refresh
            this.startDashboardRefresh();
        } catch (e) {
            console.error("Critical Init Error:", e);
            this.showLoginOverlay();
        }
    },
    startDashboardRefresh: function() {
        if (this.state.refreshInterval) clearInterval(this.state.refreshInterval);
        if (this.state.keyosInterval) clearInterval(this.state.keyosInterval);

        // 1. Genel İstatistikler (Hızlı Güncelleme - 15 Saniye)
        

        // 2. KeyOS Uyumsuzluk Kontrolü (Yavaş Güncelleme - 5 Dakika)
         
    },
    setupLoginListeners: function() {
        const self = this;
        const u = document.getElementById('login-user');
        const p = document.getElementById('login-pass');
        const trigger = (e) => { if (e.key === 'Enter' || e.keyCode === 13) self.handleLoginButtonClick(); };
        if(u) u.addEventListener('keydown', trigger);
        if(p) p.addEventListener('keydown', trigger);
    },
    setupPwaPrompt: function() {
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.state.deferredPrompt = e;
            const isAndroid = /Android/i.test(navigator.userAgent);
            if (isAndroid) {
                const prompt = document.getElementById('pwa-install-prompt');
                if (prompt) prompt.style.display = 'flex';
            }
        });
        window.addEventListener('appinstalled', () => {
            this.state.deferredPrompt = null;
            const prompt = document.getElementById('pwa-install-prompt');
            if (prompt) prompt.style.display = 'none';
        });
    },
    triggerPwaInstall: async function() {
        const promptEvent = this.state.deferredPrompt;
        if (!promptEvent) return;
        promptEvent.prompt();
        const { outcome } = await promptEvent.userChoice;
        console.log(`PWA User Response: ${outcome}`);
        this.state.deferredPrompt = null;
        const prompt = document.getElementById('pwa-install-prompt');
        if (prompt) prompt.style.display = 'none';
    },
    checkLoginStatus: function() {
        var savedUser = localStorage.getItem('it_user_data');
        var overlay = document.getElementById('login-overlay');
        if (savedUser) {
            try {
                this.state.activeUser = JSON.parse(savedUser);
                if (!this.state.activeUser) throw new Error("Invalid user data");
                this.state.isLoggedIn = true;
                if(overlay) overlay.style.display = 'none';
                document.body.classList.remove('login-required');
                var userNameElem = document.getElementById('active-user-name');
                if(userNameElem) {
                    var name = this.state.activeUser.display_name || this.state.activeUser.name || 'Bilinmiyor';
                    var role = this.state.activeUser.role || '';
                    var icon = role === 'ADMIN' ? '<i class="fas fa-shield-halved" style="color:#00ff88; margin-right:5px;"></i>' : '<i class="fas fa-user" style="color:#00d2ff; margin-right:5px;"></i>';
                    userNameElem.innerHTML = icon + name.toUpperCase() + (role ? ` <span style="opacity:0.6; font-size:0.7rem;">(${role})</span>` : '');
                }
                // Dropdown menü öğelerini yetkiye göre gizle/göster
                var isAdmin = this.state.activeUser.role === 'ADMIN';
                var ids = ['menu-users', 'menu-backup', 'menu-keyos-query', 'menu-cups-query', 'menu-history', 'menu-system-update', 'menu-clear-data', 'btn-device-add', 'menu-admin-reports'];
                for (var i = 0; i < ids.length; i++) {
                    var el = document.getElementById(ids[i]);
                    if(el) el.style.display = isAdmin ? 'block' : 'none';
                }
                
                // Dashboard Health Panel
                var healthPanel = document.getElementById('system-health-panel');
                if(healthPanel) healthPanel.style.display = isAdmin ? 'block' : 'none';
                

                // Admin badge
                if(isAdmin && userNameElem) {
                    userNameElem.innerText = `${name.toUpperCase()} (ADMIN)`;
                    userNameElem.style.borderColor = '#00ff88';
                }
                this.setStateFromRole();
                this.loadMahalList();
                this.renderAll();
                var savedView = localStorage.getItem('active_view') || 'dashboard';
                this.navigateTo(savedView);
                this.setPrinterMainType('PRINTER');
            } catch(e) {
                console.error("Login Check Error:", e);
                localStorage.removeItem('it_user_data');
                this.showLoginOverlay();
            }
        } else {
            this.showLoginOverlay();
        }
    },
    backupDatabase: async function() {
        this.showToast('Veritabanı yedeği alınıyor, lütfen bekleyin...', 'info');
        try {
            const result = await this.apiRequest('/inventory/backup_db', { method: 'POST' });
            if (result.success) {
                this.showToast(result.message || 'Veritabanı yedeği başarıyla kaydedildi.', 'success');
            } else {
                this.showToast('Hata: ' + result.error, 'error');
            }
        } catch (e) {
            console.error('Yedekleme hatası:', e);
        }
    },
    clearAllData: async function() { // GHOST CODE REMOVED

        if (this.state.activeUser.role !== 'ADMIN') {
            return alert('Bu işlem sadece ADMIN yetkisiyle yapılabilir.');
        }
        if (!confirm('âš ï¸ DİKKAT: Tüm envanter, yazıcı, servis, warehouse ve not verileri SİLİNECEKTİR.\n\nKullanıcı hesapları korunacaktır.\n\nDevam etmek istiyor musunuz?')) return;
        if (!confirm('ğŸ”´ SON ONAY: Bu işlem geri alınamaz! Tüm test verileri kalıcı olarak silinecek.\n\nEMİN MİSİNİZ?')) return;
        
        this.showToast('Tüm veriler temizleniyor...', 'info');
        try {
            const result = await this.apiRequest('/inventory/clear_all_data', { method: 'POST' });
            if (result.success) {
                this.showToast(result.message || 'Tüm veriler başarıyla temizlendi!', 'success');
                this.renderAll();
            } else {
                this.showToast('Hata: ' + (result.error || 'Bilinmeyen hata'), 'error');
            }
        } catch (e) {
            console.error('Temizleme hatası:', e);
        }
    },
    manualKeyOSSync: async function() {
        this.showToast('KeyOS MGT senkronizasyonu başlatıldı. Bu işlem birkaç dakika sürebilir...', 'info');
        try {
            const data = await this.apiRequest('/keyos/sync', { method: 'POST' });
            if (data.error) throw new Error(data.error);
            
            this.showToast(data.message || 'KeyOS verileri başarıyla güncellendi.', 'success');
            
            if (data.mismatches && data.mismatches.length > 0) {
                let msg = 'âš ï¸ Hostname Uyuşmazlığı Tespit Edildi:\n\n';
                data.mismatches.forEach(m => {
                    msg += `${m.pc_no}: Sistem=${m.local_hostname} vs KeyOS=${m.keyos_hostname}\n`;
                });
                alert(msg);
            }
            
            this.renderAll();
        } catch (e) {
            console.error(e);
        }
    },
    manualCUPSQuery: async function() {
        this.showToast('CUPS yazıcı durumları sorgulanıyor...', 'info');
        try {
            const data = await this.apiRequest('/printers/printers/query_cups', { method: 'POST' });
            this.showToast(data.message || 'Yazıcı durumları güncellendi.', 'success');
            this.renderAll();
        } catch (e) {
            console.error('CUPS Query Error:', e);
        }
    },
    loadMahalList: async function() {
        try {
            const mahals = await this.apiRequest('/inventory/mahal_list');
            this.state.mahalMap = {};
            const dl = document.getElementById('mahal-datalist');
            const dlName = document.getElementById('mahal-name-datalist');
            if(dl) dl.innerHTML = '';
            if(dlName) dlName.innerHTML = '';
            mahals.forEach(m => {
                this.state.mahalMap[m.location_code] = {
                    name: m.location_name,
                    tower: m.tower,
                    floor: m.floor,
                    phone: m.phone_number
                };
                if(dl) {
                    const opt = document.createElement('option');
                    opt.value = m.location_code;
                    opt.innerText = m.location_name;
                    dl.appendChild(opt);
                }
                if(dlName) {
                    const opt = document.createElement('option');
                    opt.value = m.location_name;
                    opt.innerText = m.location_code;
                    dlName.appendChild(opt);
                }
            });
        } catch(e) { console.error('Mahal listesi yüklenemedi:', e); }
    },
    openMahalImportModal: function() {
        const modal = document.getElementById('mahal-import-modal');
        if (modal) modal.style.display = 'flex';
    },
    executeMahalFileUpload: async function() {
        const fileInput = document.getElementById('mahal-import-file');
        if (!fileInput || !fileInput.files[0]) {
            this.showToast('Lütfen yüklenecek bir Excel dosyası seçin.', 'warning');
            return;
        }

        const btn = document.getElementById('btn-execute-mahal-import');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Yükleniyor...';
        btn.disabled = true;

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        try {
            const resp = await this.apiRequest('/mahal/upload_excel', {
                method: 'POST',
                body: formData
            });
            const result = resp;

            if (result.success) {
                this.showToast(result.message, 'success');
                document.getElementById('mahal-import-modal').style.display = 'none';
                this.loadMahalList(); // Mahal listesini yenile
            } else {
                this.showToast('Yükleme hatası: ' + (result.error || 'Bilinmiyor'), 'error');
            }
        } catch (e) {
            console.error('Upload Error:', e);
            this.showToast('Sunucu bağlantı hatası.', 'error');
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    },
    importMahalExcel: async function() { // GHOST CODE REMOVED

        if (!confirm('Sunucu üzerindeki mahal_phone_number.xlsx dosyasından veriler güncellenecektir. Emin misiniz?')) return;
        
        this.showToast('Excel verileri işleniyor, lütfen bekleyin...', 'info');
        try {
            const resp = await this.apiRequest('/inventory/import_mahal_excel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const result = resp;
            
            if (result.error) throw new Error(result.error);
            
            this.showToast(result.message, 'success');
            // Mahal listesini yeniden yükle ki datalist'ler güncellensin
            this.loadMahalList();
        } catch (e) {
            console.error('Excel Import Error:', e);
            this.showToast('Hata: ' + e.message, 'error');
        }
    },
    setStateFromRole: function() {
        const user = this.state.activeUser;
        if (!user) return;
        const role = user.role || 'VIEWER';
        document.body.classList.toggle('role-admin', role === 'ADMIN');
        document.body.classList.toggle('role-editor', role === 'EDITOR');
        document.body.classList.toggle('role-depot', role === 'DEPOT');
        const isAdmin = role === 'ADMIN';
        const isOther = role === 'OTHER';
        let allowedViews = [];
        if (isAdmin) {
            allowedViews = ['dashboard', 'inventory', 'general-notes', 'areas', 'printers', 'depot', 'docs', 'service', 'logs', 'users', 'admin-reports'];
        } else if (isOther && user.permissions) {
            try {
                allowedViews = JSON.parse(user.permissions);
            } catch(e) { allowedViews = []; }
        } else if (role === 'EDITOR') {
            allowedViews = ['dashboard', 'inventory', 'general-notes', 'areas', 'printers', 'docs', 'service'];
        } else if (role === 'DEPOT') {
            allowedViews = ['depot'];
        } else {
            // VIEWER
            allowedViews = ['dashboard', 'inventory', 'general-notes', 'areas', 'printers', 'service'];
        }
        // Navigasyon linklerini gizle/göster
        document.querySelectorAll('.nav-link').forEach(link => {
            const view = link.getAttribute('data-view');
            link.style.display = allowedViews.includes(view) ? 'block' : 'none';
        });
        // Dropdown menü öelerini gizle/göster
        const navUsers = document.getElementById('menu-users');
        const navLogs = document.getElementById('menu-history');
        const navSync = document.getElementById('menu-sync');
        const navKeyosSync = document.getElementById('menu-keyos-sync');
        const navKeyosReport = document.getElementById('menu-keyos-report');
        if(navUsers) navUsers.style.display = allowedViews.includes('users') ? 'block' : 'none';
        if(navLogs) navLogs.style.display = allowedViews.includes('logs') ? 'block' : 'none';
        if(navSync) navSync.style.display = isAdmin ? 'block' : 'none';
        if(navKeyosSync) navKeyosSync.style.display = isAdmin ? 'block' : 'none';
        if(navKeyosReport) navKeyosReport.style.display = isAdmin ? 'block' : 'none';
        
        const navDepotReport = document.getElementById('menu-depot-report');
        if(navDepotReport) navDepotReport.style.display = (isAdmin || role === 'DEPOT') ? 'block' : 'none';

        const navAdminReports = document.getElementById('menu-admin-reports');
        if(navAdminReports) navAdminReports.style.display = allowedViews.includes('admin-reports') ? 'block' : 'none';
        // Admin-only butonları/alanları göster
        document.querySelectorAll('.admin-only').forEach(el => {
            el.style.display = isAdmin ? 'block' : 'none';
        });
    },
    handleLoginButtonClick: async function() {
        const uInput = document.getElementById('login-user').value;
        const p = document.getElementById('login-pass').value;
        if (!uInput || !p) { this.showToast('Lütfen kullanıcı adı ve ifre girin.', 'warning'); return; }
        // Türkçe karakter dostu küçük harfe çevirme
        const u = uInput.trim(); // DB is case-insensitive
        const btn = document.getElementById('btn-login-submit');
        if(btn) { btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Giriliyor...'; btn.disabled = true; }
        try {
            await this._handleLoginInternal(u, p);
        } finally {
            if(btn) { btn.innerHTML = 'Sisteme Giri Yap'; btn.disabled = false; }
        }
    },
    _handleLoginInternal: async function(u, p) {
        try {
            const response = await this.apiRequest('/users/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: u, password: p })
            });

            console.log("LOGIN RESPONSE:", response);

            // FRONTEND GUARD (AÅAMA 3)
            if (
                !response ||
                response.success !== true ||
                !response.user ||
                typeof response.user !== 'object'
            ) {
                console.error("INVALID LOGIN RESPONSE:", response);
                throw new Error("Kullanıcı bilgisi alınamadı (Geçersiz Schema).");
            }

            const user = response.user;
            this.state.activeUser = user;
            this.currentUser = user;

            localStorage.setItem("token", response.token || "");
            localStorage.setItem("user", JSON.stringify(user));
            localStorage.setItem('it_user_data', JSON.stringify(user));
            localStorage.setItem('active_view', 'dashboard');

            console.log("Login Successful, redirecting...");
            location.reload();
            return true;

        } catch (err) {
            console.error("Login Error (Detailed):", err);
            this.showToast(err.message || "Giriş yapılamadı.", "error");
            throw err;
        }
    },
    showLoginOverlay: function() {
        const overlay = document.getElementById('login-overlay');
        if(overlay) overlay.style.display = 'flex';
        document.body.classList.add('login-required');

        // Zaman asimi mesaji varsa goster
        const timeoutMsg = sessionStorage.getItem('timeout_msg');
        if (timeoutMsg) {
            setTimeout(() => {
                alert(timeoutMsg);
                sessionStorage.removeItem('timeout_msg');
            }, 100);
        }
    },
    triggerSystemUpdate: async function() {
        if (!confirm('Sistemi Git üzerinden güncelleyip yeniden başlatmak istediğinize emin misiniz?\n\nBu işlem sistemi yaklaşık 10 saniye devre dışı bırakacaktır.')) return;
        
        try {
            this.showToast('Güncelleme komutu gönderiliyor...', 'info');
            const resp = await this.apiRequest('/system/git_update', { method: 'POST' });
            if (resp.success) {
                const overlay = document.createElement('div');
                overlay.id = 'update-overlay';
                overlay.style.cssText = 'position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.9); z-index:9999; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#fff; font-family:"Outfit",sans-serif; text-align:center; padding:20px;';
                overlay.innerHTML = `
                    <i class="fas fa-sync-alt fa-spin fa-3x" style="color:#00d2ff; margin-bottom:20px;"></i>
                    <h2 style="margin-bottom:10px;">Sistem Güncelleniyor...</h2>
                    <p style="color:#a0a0a0; font-size:0.9rem;">Lütfen bekleyin, sistem yeniden başlatılıyor. Bu işlem yaklaşık 10-15 saniye sürebilir.</p>
                    <div style="margin-top:20px; width:200px; height:4px; background:#222; border-radius:2px; overflow:hidden;">
                        <div style="height:100%; background:#00d2ff; width:30%; animation:loading 1s infinite alternate;"></div>
                    </div>
                    <style>@keyframes loading { from { transform: translateX(-100%); } to { transform: translateX(300%); } }</style>
                `;
                document.body.appendChild(overlay);

                const checkServer = setInterval(async () => {
                    try {
                        const pingResp = await fetch('/api/system/health');
                        if (pingResp.ok) {
                            clearInterval(checkServer);
                            window.location.reload();
                        }
                    } catch(e) { console.error(e); }
                }, 3000);
            }
        } catch (e) {
            this.showToast('Güncelleme tetiklenemedi: ' + e.message, 'error');
        }
    },

    handleLogout: async function() {
        try {
            await this.apiRequest('/users/logout', { method: 'POST' });
        } catch(e) { console.error(e); }
        localStorage.removeItem('it_user_data');
        location.reload();
    },
    setupSessionTimeout: function() {
        // 5 dk hareketsizlikte logout
        let timeout;
        const resetTimer = () => {
            clearTimeout(timeout);
            // Eer kullanıcı giri yapmamısa veya verisi yoksa iem yapma
            const user = this.state.activeUser;
            if (!user) return; 

            // Eer kullanıcı sadece dashboard yetkisine sahipse süreyi kısıtlama
            if (user.role === 'OTHER') {
                try {
                    const perms = JSON.parse(user.permissions || '[]');
                    if (perms.length === 1 && perms[0] === 'dashboard') {
                        return; // Timeout uygulama
                    }
                } catch(e) { console.error(e); }
            }
            const userTimeout = user.session_timeout;
            if (userTimeout === 0) return; // Sınırsız
            const waitMs = (userTimeout || 5) * 60 * 1000;
            timeout = setTimeout(() => {
                if (this.state.isLoggedIn) {
                    sessionStorage.setItem('timeout_msg', `Oturumunuz ${userTimeout} dakika boyunca işlem yapmadığınız için güvenlik nedeniyle kapatıldı.`);
                    this.handleLogout();
                }
            }, waitMs); 
        };
        // Initial start
        resetTimer();
        document.addEventListener('mousemove', resetTimer);
        document.addEventListener('keypress', resetTimer);
        document.addEventListener('click', resetTimer);
    },
    // PDF Karakter Düzeltme (İ, ,  gibi jspdf'in standart fontta bozduu karakterler için)
    fixTurkishForPDF: function(text) {
        if (!text) return "";
        return text.toString()
            .replace(/İ/g, "I")
            .replace(/ı/g, "i")
            .replace(/Å/g, "S")
            .replace(/ş/g, "s")
            .replace(/Ä/g, "G")
            .replace(/ğ/g, "g");
    },
    renderAll: function() {
        this.loadNoteCounts();
        this.state.inventoryCache = {}; this.loadInventory();
        this.loadAreas();
        this.loadDepot();
        this.loadDashboardStats();
        this.loadGeneralNotes();
    },
    loadNoteCounts: async function() {
        try {
            this.state.noteCounts = await this.apiRequest('/notes/counts/pc');
        } catch(e) {
            console.error('Not sayıları yüklenemedi:', e);
            this.state.noteCounts = {};
        }
    },
    // 
    //  DASHBOARD & STATS
    // 
    loadDashboardStats: async function() {
        try {
            const stats = await this.apiRequest('/dashboard/stats');
            this.renderStats(stats);
            this.renderDashboardChart(stats);
            this.renderStockAlerts(stats.depot_alerts || []);
        } catch (e) {
            console.error("Dashboard yüklenemedi:", e);
            // Fallback: local data üzerinden hesapla
            if (this.state.inventory && Array.isArray(this.state.inventory)) {
                this.renderStatsFromLocal();
            } else {
                this.renderStats({}); // Clear stats
            }
        }
    },
    renderStats: function(stats) {
        if(!stats) return;
        const set = (id, val) => { const el = document.getElementById(id); if(el) el.innerText = val !== undefined ? val : 0; };
        // PC (Nested Structure)
        if(stats.pc) {
            set('stat-pc-on_field', stats.pc.on_field);
            set('stat-pc-ariza', stats.pc.ariza);
            set('stat-pc-warehouse', stats.pc.warehouse);
            set('stat-pc-wait', stats.pc.kayip);
        }
        // Yazıcı
        if(stats.pr) {
            set('stat-pr-kurulu', stats.pr.on_field);
            set('stat-pr-ariza', stats.pr.ariza);
            set('stat-pr-warehouse', stats.pr.warehouse);
            set('stat-pr-kayip', stats.pr.kayip);
        }
        // Barkod Okuyucu
        if(stats.bo) {
            set('stat-bo-toplam', stats.bo.on_field);
            set('stat-bo-warehouse', stats.bo.warehouse);
        }
        // Barkod Yazıcı
        if(stats.by) {
            set('stat-by-toplam', stats.by.on_field);
            set('stat-by-warehouse', stats.by.warehouse);
        }
        // Tarayıcılar
        if(stats.tr_c230) {
            set('stat-tr-c230-on_field', stats.tr_c230.on_field);
            set('stat-tr-c230-warehouse', stats.tr_c230.warehouse);
        }
        if(stats.tr_g2090) {
            set('stat-tr-g2090-on_field', stats.tr_g2090.on_field);
            set('stat-tr-g2090-warehouse', stats.tr_g2090.warehouse);
        }
        if(stats.os) {
            set('stat-os-windows', stats.os.win);
            set('stat-os-keyos', stats.os.keyos);
        }
        // KeyOS Uptime
        if(stats.keyos_uptime) {
            set('stat-k-5dk', stats.keyos_uptime.k5);
            set('stat-k-5-10', stats.keyos_uptime.k5_10);
            set('stat-k-11-29', stats.keyos_uptime.k11_29);
            set('stat-k-30plus', stats.keyos_uptime.k30p);
        }
    },
    renderStatsFromLocal: function() {
        // Dashboard stats are now handled by /api/dashboard/stats endpoint efficiently.
        return;
    },
    toggleDropdown: function(id) {
        var menu = document.querySelector('#' + id + ' .dropdown-menu');
        if (menu) {
            var isOpen = menu.classList.contains('show');
            // Close all first
            document.querySelectorAll('.dropdown-menu').forEach(function(m) { m.classList.remove('show'); });
            if (!isOpen) menu.classList.add('show');
        }
        // Click outside to close
        const closeHandler = (e) => {
            if (!e.target.closest('.custom-dropdown')) {
                document.querySelectorAll('.dropdown-menu').forEach(m => m.classList.remove('show'));
                document.removeEventListener('click', closeHandler);
            }
        };
        setTimeout(() => document.addEventListener('click', closeHandler), 10);
    },
    renderDashboardChart: function(stats) {
        const canvas1 = document.getElementById('dashboard-pie-chart');
        const canvas2 = document.getElementById('dashboard-keyos-chart');
        const canvas3 = document.getElementById('dashboard-printer-chart');
        if (!canvas1 || !canvas2) return;
        if (typeof ChartDataLabels !== 'undefined') {
            Chart.register(ChartDataLabels);
        }
        if (this.state.chart1) this.state.chart1.destroy();
        if (this.state.chart2) this.state.chart2.destroy();
        if (this.state.chart3) this.state.chart3.destroy();
        // 1. Bilgisayar Daılımı (PC-Sahada, PC-Arıza, PC-Depo, PC-Kayıp)
        try {
            const pcData = stats.pc || { on_field:0, ariza:0, warehouse:0, kayip:0 };
            this.state.chart1 = new Chart(canvas1, {
                type: 'pie',
                data: {
                    labels: ['Kurulu', 'Arızalı', 'Depo', 'Kayıp'],
                    datasets: [{
                        data: [
                            pcData.on_field || 0, 
                            pcData.ariza || 0, 
                            pcData.warehouse || 0, 
                            pcData.kayip || 0
                        ],
                        backgroundColor: ['#00ff88', '#ff4b2b', '#00d2ff', '#a0a0a0'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        datalabels: {
                            color: '#fff',
                            font: { weight: 'bold', size: 10 },
                            formatter: (val) => val > 0 ? val : ''
                        }
                    }
                }
            });
        } catch(e) { console.error("Chart1 error:", e); }
        // 2. KeyOS Durum (4 Kademeli)
        try {
            const upData = stats.keyos_uptime || { k5:0, k5_10:0, k11_29:0, k30p:0 };
            // UI text sync
            const el1 = document.getElementById('stat-k-5dk'); if(el1) el1.innerText = upData.k5 || 0;
            const el2 = document.getElementById('stat-k-5-10'); if(el2) el2.innerText = upData.k5_10 || 0;
            const el3 = document.getElementById('stat-k-11-29'); if(el3) el3.innerText = upData.k11_29 || 0;
            const el4 = document.getElementById('stat-k-30plus'); if(el4) el4.innerText = upData.k30p || 0;
            this.state.chart2 = new Chart(canvas2, {
                type: 'doughnut',
                data: {
                    labels: ['5 dk', '5-10 G', '11-30 G', '30 G+'],
                    datasets: [{
                        data: [upData.k5, upData.k5_10, upData.k11_29, upData.k30p],
                        backgroundColor: ['#00ff88', '#00d2ff', '#ffb400', '#ff4b2b'],
                        borderWidth: 0
                    }]
                },
                options: {
                    plugins: { legend: { display: false } },
                    cutout: '75%',
                    responsive: true,
                    maintainAspectRatio: false
                },
                plugins: [{
                    id: 'centerText',
                    beforeDraw: (chart) => {
                        const { ctx, width, height } = chart;
                        ctx.save();
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.fillStyle = '#fff';
                        ctx.font = '0.7rem Outfit';
                        ctx.fillText('5 dk açık', width/2, height/2 - 10);
                        ctx.font = 'bold 1.2rem Outfit';
                        ctx.fillText(upData.k5 || '0', width/2, height/2 + 10);
                        ctx.restore();
                    }
                }]
            });
        } catch(e) { console.error("Chart2 render error:", e); }
        // 3. Yazıcı Daılımı
        if (canvas3) {
            try {
                const prData = stats.pr || { on_field:0, ariza:0, warehouse:0, kayip:0 };
                this.state.chart3 = new Chart(canvas3, {
                    type: 'pie',
                    data: {
                        labels: ['Kurulu', 'Arızalı', 'Depo', 'Kayıp'],
                        datasets: [{
                            data: [
                                prData.on_field || 0, 
                                prData.ariza || 0, 
                                prData.warehouse || 0, 
                                prData.kayip || 0
                            ],
                            backgroundColor: ['#00ff88', '#ff4b2b', '#00d2ff', '#ffb400'],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            datalabels: {
                                color: '#fff',
                                font: { weight: 'bold', size: 10 },
                                formatter: (val) => val > 0 ? val : ''
                            }
                        }
                    }
                });
            } catch(e) { console.error("Chart3 error:", e); }
        }
    },

    renderStockAlerts: function(alerts) {
        // Redundant as per user request to move alerts to Depot view.
        return;
    },
    navigateTo: function(view) {
        if (this.stopLiveConsoleStream) this.stopLiveConsoleStream();
        this.state.view = view;
        localStorage.setItem('active_view', view);
        document.querySelectorAll('.view').forEach(v => v.style.display = 'none');
        const viewEl = document.getElementById(`view-${view}`);
        if(viewEl) viewEl.style.display = 'block';
        document.querySelectorAll('.nav-link').forEach(l => {
            l.classList.toggle('active', l.dataset.view === view);
        });
        const role = (this.state.activeUser && this.state.activeUser.role) ? this.state.activeUser.role : 'GUEST';

        // Depot UI Restrictions
        if (view === 'depot') {
            const btnAdd = document.getElementById('btn-depot-add');
            const btnExport = document.getElementById('btn-depot-export');
            if (btnAdd) btnAdd.style.display = (role === 'ADMIN' || role === 'DEPOT') ? 'block' : 'none';
            if (btnExport) btnExport.style.display = (role === 'ADMIN') ? 'block' : 'none';
            // Default sub-tab for depot
            this.filterDepot('ALERTS');
        }
        
        // Default sub-tabs for other views
        if (view === 'inventory') {
            this.setInvCategory('PC');
        } else if (view === 'kb') {
            this.setKBTab('kodlar');
        } else if (view === 'printers') {
            this.setPrinterMainType('PRINTER');
        } else if (view === 'admin-reports') {
            this.loadAdminReportsCategories();
        }

        // View'a özel veri yükleme (Sadece veri yoksa yükle - Hızlandırma için)
        if (view === 'dashboard') {
            if ((this.state.inventory || []).length === 0) this.loadDashboardStats();
            
            // Eğer canlı mod açıksa interval'i yeniden başlat
            if (this.state.liveMode && !this.liveModeInterval) {
                this.liveModeInterval = setInterval(() => {
                    if (this.state.view === 'dashboard') {
                        this.loadDashboardStats();
                    }
                }, 30000);
            }
        } else {
            // Dashboard dışındaysak intervali tamamen durdur (sunucu ve tarayıcı yormasın)
            if (this.liveModeInterval) {
                clearInterval(this.liveModeInterval);
                this.liveModeInterval = null;
            }
        }
        
        // (Duplicate Fetch Removed) if (view === 'inventory'...) this.state.inventoryCache = {}; this.loadInventory();
        if (view === 'users' && (this.state.users || []).length === 0) this.loadUsers();
        if (view === 'printers' && (this.state.printers || []).length === 0) this.renderPrinters();
        if (view === 'logs' && (this.state.auditLogs || []).length === 0) this.loadAuditLogs();
        if (view === 'service' && (this.state.serviceRecords || []).length === 0) this.loadServiceRecords();
        if (view === 'depot' && (this.state.depot || []).length === 0) this.loadDepot();

        if (view === 'general-notes') this.loadGeneralNotes();
    },
    refreshActiveView: async function() { // GHOST CODE REMOVED

        const view = this.state.view;
        try {
            if (view === 'dashboard') await this.loadDashboardStats();
            else if (view === 'inventory') { this.state.inventoryCache = {}; await this.loadInventory(); }
            else if (view === 'users') await this.loadUsers();
            else if (view === 'printers') await this.renderPrinters();
            else if (view === 'logs') await this.loadAuditLogs();
            else if (view === 'general-notes') await this.loadGeneralNotes();
            else if (view === 'depot') await this.loadDepot();
            else if (view === 'service') await this.loadServiceRecords();
            this.showToast('Görünüm yenilendi.');
        } catch (e) { console.error("Yenileme hatası:", e); }
    },
    syncDatabase: async function() {
        if (this.state.activeUser.role !== 'ADMIN') return;
        const btn = document.querySelector('#menu-sync i');
        if (btn) btn.classList.add('fa-spin');
        try {
            this.showToast('Veritabanı Excel ile senkronize ediliyor...', 'info');
            const resp = await this.apiRequest('/sync', { method: 'POST' });
            const result = resp;
            if (result.error) throw new Error(result.error);
            this.showToast('Senkronizasyon Baarılı! Tüm veriler güncellendi.');
            // Tüm verileri batan yükle
            this.state.inventoryCache = {}; await this.loadInventory();
            await this.loadDashboardStats();
            if (this.state.view === 'depot') await this.loadDepot();
            if (this.state.view === 'service') await this.loadServiceRecords();
        } catch (e) {
            alert('Senkronizasyon Hatası: ' + e.message);
        } finally {
            if (btn) setTimeout(() => btn.classList.remove('fa-spin'), 1000);
        }
    },
    // 
    //  INVENTORY
    // 
    loadInventory: async function() {
        try {
            const cat = this.state.invCategory || 'PC';
            let endpoint = '/inventory/pcs';
            if (cat === 'SK' || cat === 'SIRAMATIK') endpoint = '/inventory/queing_machines';
            else if (cat === 'TABLET') endpoint = '/inventory/tablets';
            else if (cat === 'MONITOR') endpoint = '/inventory/monitors';

            const resp = await this.apiRequest(endpoint);
            const data = Array.isArray(resp) ? resp : (resp.data || []);
            this.state.inventory = data;
            
            if (!this.state.inventoryCache) this.state.inventoryCache = {};
            this.state.inventoryCache[cat] = data; // Save to cache
            
            this.updatePeripheralDatalists();
            this.filterInventory();
            
            // Eğer özel cihazlar yüklendiyse arka planda PC'leri de getir (bağlı PC mahal kodu vs. için)
            if (['MONITOR', 'BARCODE_PRINTER', 'BARCODE_READER', 'SCANNER'].includes(cat)) {
                if (!this.state.inventoryCache['PC']) {
                    this.apiRequest('/inventory/pcs').then(res => {
                        if (res) {
                            this.state.inventoryCache['PC'] = Array.isArray(res) ? res : (res.data || []);
                            if (this.state.invCategory === cat) {
                                this.renderInventory();
                            }
                        }
                    }).catch(e => console.warn("Failed to background load PCs:", e));
                }
            }
        } catch (e) { 
            console.error("Envanter yüklenemedi:", e); 
            this.state.inventory = [];
        }
    },
        updatePeripheralDatalists: function() {
        const byDl = document.getElementById('by-seri-datalist');
        const boDl = document.getElementById('bo-seri-datalist');
        const trDl = document.getElementById('tr-seri-datalist');
        const moDl = document.getElementById('mo-seri-datalist');
        const pcNoDl = document.getElementById('pc-no-datalist');
        
        const bySet = new Set(), boSet = new Set(), trSet = new Set(), moSet = new Set(), pcSet = new Set();
        
        if (this.state.printers && Array.isArray(this.state.printers)) {
            this.state.printers.forEach(p => {
                const dc = (p.device_class || '').toUpperCase();
                if (dc === 'BARCODE_PRINTER' && p.seri) bySet.add(p.seri.trim());
                if (dc === 'BARCODE_READER' && p.seri) boSet.add(p.seri.trim());
                if (dc === 'SCANNER' && p.seri) trSet.add(p.seri.trim());
            });
        }

        if (this.state.allMonitors && Array.isArray(this.state.allMonitors)) {
            this.state.allMonitors.forEach(m => {
                if (m.serial_no) moSet.add(m.serial_no.trim());
            });
        } else if (!this.state.fetchingMonitors) {
            this.state.fetchingMonitors = true;
            this.apiRequest('/inventory/monitors').then(res => {
                this.state.allMonitors = Array.isArray(res) ? res : (res.data || []);
                this.updatePeripheralDatalists();
            }).catch(e => console.error("Monitörler datalist için alınamadı", e));
        }

        if (this.state.inventory && Array.isArray(this.state.inventory)) {
            this.state.inventory.forEach(i => {
                const type = (i.device_type || 'PC').toUpperCase();
                
                if (i.by_seri && i.by_seri.trim() !== "" && i.by_seri !== "---") bySet.add(i.by_seri.trim());
                if (i.bo_seri && i.bo_seri.trim() !== "" && i.bo_seri !== "---") boSet.add(i.bo_seri.trim());
                if (i.tarayici_seri && i.tarayici_seri.trim() !== "" && i.tarayici_seri !== "---") trSet.add(i.tarayici_seri.trim());
                if (i.monitor_seri && i.monitor_seri.trim() !== "" && i.monitor_seri !== "---") moSet.add(i.monitor_seri.trim());
                if (i.monitor2_seri && i.monitor2_seri.trim() !== "" && i.monitor2_seri !== "---") moSet.add(i.monitor2_seri.trim());
                
                if ((type === 'BARKOD YAZICI' || type === 'BARKOD YAZICI') && i.serial_no) bySet.add(i.serial_no.trim());
                if (type === 'BARKOD OKUYUCU' && i.serial_no) boSet.add(i.serial_no.trim());
                if (type === 'TARAYICI' && i.serial_no) trSet.add(i.serial_no.trim());
                if ((type === 'MONITOR' || type === 'MONİTÖR') && i.serial_no) moSet.add(i.serial_no.trim());

                if (i.pc_no && i.pc_no !== '---') {
                    const formatted = isNaN(i.pc_no) ? i.pc_no : `PC-${i.pc_no.toString().padStart(3, '0')}`;
                    pcSet.add(formatted);
                }
            });
        }

        if (byDl) byDl.innerHTML = Array.from(bySet).sort().map(s => `<option value="${s}">`).join('');
        if (boDl) boDl.innerHTML = Array.from(boSet).sort().map(s => `<option value="${s}">`).join('');
        if (trDl) trDl.innerHTML = Array.from(trSet).sort().map(s => `<option value="${s}">`).join('');
        if (moDl) moDl.innerHTML = Array.from(moSet).sort().map(s => `<option value="${s}">`).join('');
        if (pcNoDl) {
            pcNoDl.innerHTML = Array.from(pcSet).sort().map(p => {
                const pc = this.state.inventory.find(x => `PC-${String(x.pc_no).padStart(3,'0')}` === p);
                return `<option value="${p}">${pc ? pc.location_name : ''}</option>`;
            }).join('');
        }
    },
    renderInventory: function(items) {
        const grid = document.getElementById('inventory-grid');
        if(!grid) return;
        if (!items || !items.length) {
            grid.innerHTML = '<p style="opacity:0.4; text-align:center; grid-column:1/-1; padding: 40px;">Envanter verisi bulunamadı.</p>';
            return;
        }
        const nc = this.state.noteCounts || {};
        
        // If it's a MONITOR category, render printer-style cards
        if (this.state.invCategory === 'MONITOR') {
            grid.innerHTML = items.map(p => {
                const status = (p.status || '').toUpperCase();
                const isInstalled = p.mahal && p.mahal.trim() !== "";
                const durumHtml = this.getDurumBadge(status, isInstalled);
                let displayMahal = (p.mahal || 'DEPO').toUpperCase();
                let displayIpValue = p.ip || p.recorded_device_no || p.pc_no || '-';
                let displayIpLabel = "BAĞLI CİHAZ (PC NO / MAHAL)";

                // Bağlı olduğu PC'yi bulma (Barkod yazıcılardaki gibi)
                const pcs = (this.state.inventoryCache && this.state.inventoryCache['PC']) || [];
                const searchNo = (p.recorded_device_no || p.pc_no || "").toUpperCase();
                
                if (searchNo && searchNo !== "NONE" && searchNo !== "NULL" && searchNo !== "---") {
                    const connectedPc = pcs.find(pc => {
                        const pcNo = (pc.pc_no || "").toUpperCase();
                        return pcNo === searchNo || `PC-${pcNo.padStart(3, '0')}` === searchNo || pcNo === searchNo.replace('PC-', '');
                    });

                    if (connectedPc) {
                        displayMahal = (connectedPc.location_code || connectedPc.location_name || p.location_code || 'BİLİNMİYOR').toUpperCase();
                        displayIpValue = connectedPc.pc_no ? `PC-${connectedPc.pc_no.toString().padStart(3, '0')} (${displayMahal})` : `BAĞLI (${displayMahal})`;
                    } else {
                        displayMahal = (p.location_code || searchNo).toUpperCase();
                        displayIpValue = `${searchNo} (${displayMahal})`;
                    }
                } else {
                    displayIpValue = "-";
                }

                const noteInfo = nc[String(p.id)];
                let noteBubble = '';
                if (noteInfo && noteInfo.count > 0) {
                    noteBubble = `<div style="position:absolute; top:-10px; right:-10px; background:var(--accent); color:#000; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:900; font-size:0.7rem; box-shadow:0 0 10px rgba(0,255,136,0.5); z-index:10;">${noteInfo.count}</div>`;
                }

                return `
                <div class="card printer-card-modern fade-in" style="cursor:pointer; min-height: auto;" onclick="app.openDeviceDetail(${p.id}, 'pr', '${p.device_class || 'MONITOR'}')">
                    ${noteBubble}
                    <div class="flex-row mb-3" style="align-items: center; justify-content: space-between;">
                        <div style="color: #38bdf8; font-weight: 900; font-size: 1.3rem; letter-spacing: -0.5px;">${p.pr_no}</div>
                        ${durumHtml}
                    </div>
                    <div class="printer-model-text" style="font-size: 1.1rem; color: #fff; font-weight: 600; margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px; display: flex; align-items: center;">
                        <i class="fas fa-desktop" style="opacity: 0.5; margin-right: 8px;"></i>${p.model || p.name || 'İsimsiz Monitör'}
                        ${p.monitor_type ? `<span style="font-size: 0.75rem; background: rgba(0,255,136,0.15); color: #00ff88; padding: 2px 6px; border-radius: 4px; margin-left: auto;">${p.monitor_type == '1' ? '1. Ekran' : (p.monitor_type == '2' ? '2. Ekran' : p.monitor_type)}</span>` : ''}
                    </div>
                    
                    <div class="printer-grid-info" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;">
                        <div class="info-block">
                            <div class="info-label">${displayIpLabel}</div>
                            <div class="info-value" style="color: #facc15; font-weight: 700;">
                                <i class="fas fa-network-wired" style="opacity:0.5; margin-right:5px; font-size:0.8rem;"></i>${displayIpValue}
                            </div>
                        </div>
                        <div class="info-block" style="text-align: right;">
                            <div class="info-label">SERİ NO</div>
                            <div class="info-value" style="font-family: monospace; letter-spacing: 0.5px;">${p.seri || p.serial_no || '-'}</div>
                        </div>
                    </div>
                </div>
                `;
            }).join('');
            return;
        }

        grid.innerHTML = items.map(i => {
            const pcLabel = this.formatPcLabel(i.pc_no, i.device_type, i.id);
            const durumHtml = this.getDurumBadge(i.status || (i.pending_installation == 1 ? 'BEKLE' : (i.is_faulty == 1 ? 'ARIZALI' : (i.warehouse == 1 ? 'DEPO' : (i.without_location == 1 ? 'KAYIP' : 'KURULU')))), (i.location_code || i.location_code) && (i.location_code || i.location_code) !== '-');
            const osBadge = this.getOSBadge(i.windows == 1 || String(i.windows || "").toUpperCase().includes("WIN"), i.keyos == 1 || String(i.keyos || "").toUpperCase().includes("KEY"), this.isTrue(i.rdp));

            const noteInfo = nc[String(i.id)];
            let noteBubble = '';
            if (noteInfo && noteInfo.count > 0) {
                noteBubble = `<div class="note-bubble-mini blink" style="color: #facc15; border-color: #facc15; background: rgba(250, 204, 21, 0.1);" onclick="event.stopPropagation(); app.openNotesModal(${i.id}, 'pc')" title="${noteInfo.count} Adet Not Var"><i class="fas fa-exclamation-triangle"></i></div>`;
            }

            const countedAt = i.last_counted_at;
            let peripheralsHtml = '';
            if (this.state.countMode) {
                let pList = [];
                const isValid = (val) => val && val.trim() !== '' && val !== '-' && val !== '---' && val.toUpperCase() !== '#N/A';
                
                if (isValid(i.monitor_seri)) pList.push(`<span style="font-size: 0.65rem; color: #00d2ff; font-weight: 700;"><i class="fas fa-desktop"></i> MON1: <span style="color: #f8fafc;">${i.monitor_seri}</span></span>`);
                if (isValid(i.monitor2_seri)) pList.push(`<span style="font-size: 0.65rem; color: #00d2ff; font-weight: 700;"><i class="fas fa-desktop"></i> MON2: <span style="color: #f8fafc;">${i.monitor2_seri}</span></span>`);
                if (isValid(i.by_seri)) pList.push(`<span style="font-size: 0.65rem; color: #00d2ff; font-weight: 700;">BY: <span style="color: #f8fafc;">${i.by_seri}</span></span>`);
                if (isValid(i.bo_seri)) pList.push(`<span style="font-size: 0.65rem; color: #00d2ff; font-weight: 700;">BO: <span style="color: #f8fafc;">${i.bo_seri}</span></span>`);
                if (isValid(i.tarayici_seri)) pList.push(`<span style="font-size: 0.65rem; color: #00d2ff; font-weight: 700;">TARAYICI: <span style="color: #f8fafc;">${i.tarayici_seri}</span></span>`);

                if (pList.length > 0) {
                    peripheralsHtml = `<div class="flex-column" style="margin-top: 5px; margin-bottom: 5px; gap: 2px;">${pList.join('')}</div>`;
                }
            }

            return `
            <div class="card printer-card-modern fade-in ${this.state.countMode && countedAt ? 'counted-card' : ''}" 
                 onclick="app.openDeviceDetail(${i.id}, 'pc')"
                 style="cursor:pointer; min-height: 140px; padding: 12px;">
                
                <!-- BAÅLIK SATIRI: PC NO + DURUM -->
                <div class="flex-row" style="justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px;">
                    <div class="flex-row gap-2" style="align-items: center;">
                        <div style="color: #38bdf8; font-weight: 900; font-size: 1.1rem; letter-spacing: -0.5px; display: flex; align-items: center; gap: 5px;">
                            ${pcLabel}
                            ${i.description && i.description.trim() !== '' ? `<i class="fas fa-exclamation-circle blink-icon" style="color:#ff4b2b; font-size: 1rem;" title="${i.description.replace(/"/g, '&quot;')}"></i>` : ''}
                        </div>
                        ${durumHtml}
                    </div>
                    <div class="flex-row gap-2" style="align-items: center;">
                        ${this.state.invCategory === 'PC' ? `
                        <i class="fas fa-power-off" style="color: #ff4b2b; font-size: 0.85rem; cursor: pointer; opacity: 0.7;" title="Bilgisayarı Kapat" onclick="event.stopPropagation(); app.openRunCommandModal(${i.id}, 'shutdown', '${i.ip}')"></i>
                        <i class="fas fa-rotate-right" style="color: #00d2ff; font-size: 0.85rem; cursor: pointer; opacity: 0.7;" title="Yeniden Başlat" onclick="event.stopPropagation(); app.openRunCommandModal(${i.id}, 'reboot', '${i.ip}')"></i>
                        ` : ''}
                        <i class="fas fa-clock-rotate-left" style="color: #64748b; font-size: 0.85rem; cursor: pointer; opacity: 0.7;" title="Geçmiş" onclick="event.stopPropagation(); app.openHistoryPopup(${i.id}, 'pc', event)"></i>
                    </div>
                </div>

                <!-- İÇERİK 1. SATIR: MAHAL KODU (SOL) & HOSTNAME (SAÄ) -->
                <div class="flex-row mb-2" style="justify-content: space-between; align-items: center;">
                    ${(this.state.invCategory === 'PC' || this.state.invCategory === 'SK' || this.state.invCategory === 'TABLET') ? `
                        <div class="flex-row gap-2" style="align-items: center;">
                            <span style="font-size: 0.75rem; color: #64748b; font-weight: 700;">${i.ip && i.ip !== '-' && String(i.ip).toUpperCase() !== '#N/A' ? i.ip : 'IP YOK'}</span>
                            ${osBadge}
                        </div>
                        <span style="font-size: 0.75rem; color: #38bdf8; font-weight: 800;">${(i.pc_serial || i.serial_no) && (i.pc_serial || i.serial_no) !== '-' && String(i.pc_serial || i.serial_no).toUpperCase() !== '#N/A' ? (i.pc_serial || i.serial_no) : 'SERİ NO YOK'}</span>
                    ` : `
                        <span style="font-size: 0.7rem; color: #64748b; font-weight: 700;">${(i.location_code || i.location_code) && (i.location_code || i.location_code) !== '-' ? (i.location_code || i.location_code) : '---'}</span>
                        <span style="font-size: 0.7rem; color: #38bdf8; font-weight: 800;">${i.hostname && i.hostname !== '-' ? i.hostname : '-'}</span>
                    `}
                </div>

                <!-- İÇERİK 2. SATIR: MAHAL ADI (BİRİM ADI - KUTU İÇİ) -->
                <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 8px; margin-bottom: 10px; min-height: 48px; display: flex; align-items: center;">
                    <div class="flex-column" style="width: 100%;">
                        <span style="font-size: 0.85rem; color: #e2e8f0; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: center;">${(i.location_name || 'BİLİNMİYOR').toUpperCase()}</span>
                        <div class="flex-row" style="justify-content: center; align-items: center; gap: 10px; margin-top: 4px; font-size: 0.65rem;">
                            ${(this.state.invCategory === 'PC' || this.state.invCategory === 'SK' || this.state.invCategory === 'TABLET') ? `
                                <span style="opacity: 0.6;"><i class="fas fa-map-marker-alt"></i> ${i.location_code || i.location_code || '-'}</span>
                                <span style="opacity: 0.6;"><i class="fas fa-phone"></i> ${i.phone || i.phone_number || '-'}</span>
                            ` : `
                                <span><i class="fas fa-layer-group"></i> ${i.tower || '-'}/${i.floor || '-'}</span>
                                <span><i class="fas fa-phone"></i> ${i.phone || i.phone_number || '-'}</span>
                            `}
                        </div>
                    </div>
                </div>

                ${(this.state.invCategory === 'PC' || this.state.invCategory === 'SK' || this.state.invCategory === 'TABLET') ? '' : `
                <!-- İÇERİK 3. SATIR: SERİ NO & IP ADRESİ -->
                <div class="flex-row" style="justify-content: space-between; align-items: flex-end; border-top: 1px solid rgba(255,255,255,0.03); padding-top: 8px;">
                    <div class="flex-column">
                        <span style="font-size: 0.55rem; color: #64748b; font-weight: 800; text-transform: uppercase;">SERİ NO</span>
                        <span style="font-size: 0.75rem; color: #f8fafc; font-weight: 600;">${i.pc_serial || i.serial_no || '-'}</span>
                    </div>
                    <div class="flex-column" style="text-align: right;">
                        <span style="font-size: 0.55rem; color: #38bdf8; font-weight: 800; text-transform: uppercase;">IP ADRESİ</span>
                        <span style="font-size: 0.9rem; color: #f8fafc; font-weight: 700;">${i.ip || '-'}</span>
                    </div>
                </div>
                `}

                ${noteBubble}
                
                ${peripheralsHtml}

                ${this.state.countMode ? `
                <button class="btn ${countedAt ? 'counted' : 'btn-accent'}" style="width:100%; margin-top:10px; padding:8px; font-size:0.7rem;" onclick="event.stopPropagation(); ${countedAt ? `app.undoMarkCounted(${i.id})` : `app.markCounted(${i.id})`}">
                    <i class="fas ${countedAt ? 'fa-undo' : 'fa-check'}"></i> ${countedAt ? 'SAYIMI GERİ AL' : 'SAYILDI OLARAK İÅARETLE'}
                </button>` : ''}
            </div>`;
        }).join('');
    },
    searchInventory: function() { this.filterInventory(); },
    setInvCategory: function(cat) {
        const isChanged = (this.state.invCategory !== (cat || 'PC'));
        this.state.invCategory = cat || 'PC';
        document.querySelectorAll('#device-type-filters .btn-chip').forEach(btn => btn.classList.toggle('active', btn.dataset.category === cat));
        const dd = document.getElementById('search-category-dropdown');
        if (dd) { dd.value = ["BARKOD YAZICI", "BARKOD OKUYUCU", "TARAYICI"].includes(cat) ? cat : ""; }
        
        const addBtn = document.getElementById('btn-device-add');
        if (addBtn) {
            addBtn.style.display = (cat === 'SK' || cat === 'TABLET' || cat === 'MONITOR') ? 'inline-flex' : 'none';
        }
        
        // Cache Logic (Memory Cache by Category)
        if (!this.state.inventoryCache) this.state.inventoryCache = {};
        
        if (isChanged || !this.state.inventoryCache[cat] || this.state.inventoryCache[cat].length === 0) {
            this.loadInventory();
        } else {
            this.state.inventory = this.state.inventoryCache[cat];
            this.updatePeripheralDatalists();
            this.filterInventory();
        }
    },
    openDeviceAddModal: function() {
        const cat = this.state.invCategory;
        if (cat !== 'SK' && cat !== 'TABLET' && cat !== 'MONITOR') return;
        
        // Formu temizle
        document.getElementById('add-pc-no').value = '';
        document.getElementById('add-ip').value = '';
        document.getElementById('add-tower').value = '';
        document.getElementById('add-location_code').value = '';
        document.getElementById('add-location_name').value = '';
        document.getElementById('add-seri').value = '';
        if(document.getElementById('add-assigned_to')) document.getElementById('add-assigned_to').value = '';
        if(document.getElementById('add-phone')) document.getElementById('add-phone').value = '';
        if(document.getElementById('add-title')) document.getElementById('add-title').value = '';
        if(document.getElementById('add-unit')) document.getElementById('add-unit').value = '';
        if(document.getElementById('add-etiket')) document.getElementById('add-etiket').value = '';
        if(document.getElementById('add-model')) document.getElementById('add-model').value = '';
        if(document.getElementById('add-monitor-seri')) document.getElementById('add-monitor-seri').value = '';
        if(document.getElementById('add-connected-pc')) document.getElementById('add-connected-pc').value = '';
        
        document.getElementById('add-windows').checked = false;
        document.getElementById('add-keyos').checked = false;
        document.getElementById('add-on_field').checked = true;
        if(document.getElementById('add-is_faulty')) document.getElementById('add-is_faulty').checked = false;
        if(document.getElementById('add-warehouse')) document.getElementById('add-warehouse').checked = false;
        
        // Modal başlığını ayarla
        const titleText = cat === 'SK' ? 'Sıramatik / Kiosk' : (cat === 'MONITOR' ? 'Monitör' : 'Tablet');
        const titleEl = document.querySelector('#device-add-modal h3');
        if (titleEl) titleEl.innerHTML = `<i class="fas fa-desktop"></i> Yeni ${titleText} Ekle`;

        // Görünürlük ayarları
        document.getElementById('add-pc-no').style.display = 'none';
        
        const tabletFields = document.getElementById('add-tablet-fields');
        if (tabletFields) tabletFields.style.display = (cat === 'TABLET') ? 'flex' : 'none';
        
        const monitorFields = document.getElementById('add-monitor-fields');
        if (monitorFields) monitorFields.style.display = (cat === 'MONITOR') ? 'flex' : 'none';

        if(document.getElementById('lbl-add-windows')) document.getElementById('lbl-add-windows').style.display = (cat === 'MONITOR') ? 'none' : 'block';
        if(document.getElementById('lbl-add-keyos')) document.getElementById('lbl-add-keyos').style.display = (cat === 'MONITOR') ? 'none' : 'block';
        if(document.getElementById('lbl-add-is_faulty')) document.getElementById('lbl-add-is_faulty').style.display = (cat === 'MONITOR') ? 'block' : 'none';
        if(document.getElementById('lbl-add-warehouse')) document.getElementById('lbl-add-warehouse').style.display = (cat === 'MONITOR') ? 'block' : 'none';

        document.getElementById('device-add-modal').style.display = 'flex';
    },
    saveNewDevice: async function() {
        const cat = this.state.invCategory;
        const type = cat === 'TABLET' ? 'TABLET' : (cat === 'SK' ? 'SIRAMATIK' : (cat === 'MONITOR' ? 'MONITOR' : (cat === 'PRINTER' ? 'PRINTER' : 'PC')));
        
        const payload = {
            device_type: type,
            ip: (document.getElementById('add-ip') || {}).value || '',
            tower: (document.getElementById('add-tower') || {}).value || '',
            location_code: (document.getElementById('add-location_code') || {}).value || '',
            location_name: (document.getElementById('add-location_name') || {}).value || '',
            on_field: document.getElementById('add-on_field') && document.getElementById('add-on_field').checked ? 1 : 0,
            windows: document.getElementById('add-windows') && document.getElementById('add-windows').checked ? 1 : 0,
            keyos: document.getElementById('add-keyos') && document.getElementById('add-keyos').checked ? 1 : 0
        };

        if (type === 'PC') {
            payload.pc_no = (document.getElementById('add-pc-no') || {}).value || '';
            payload.pc_serial = (document.getElementById('add-seri') || {}).value || '';
            if (!payload.pc_no && !payload.pc_serial) {
                return alert("En azindan PC Numarasi veya Seri No girmelisiniz.");
            }
        } else if (type === 'PRINTER') {
            payload.envanter = (document.getElementById('add-pc-no') || {}).value || '';
            payload.seri = (document.getElementById('add-seri') || {}).value || '';
            payload.ip = (document.getElementById('add-ip') || {}).value || '';
            payload.mahal = (document.getElementById('add-location_code') || {}).value || '';
            if (!payload.envanter) {
                return alert("Lütfen yazıcı PR Numarası giriniz (örn: PR-001).");
            }
        } else if (type === 'MONITOR') {
            payload.name = (document.getElementById('add-etiket') || {}).value || '';
            payload.model = (document.getElementById('add-model') || {}).value || '';
            payload.serial_no = (document.getElementById('add-monitor-seri') || {}).value || '';
            payload.pc_no = (document.getElementById('add-connected-pc') || {}).value || '';
            payload.is_faulty = document.getElementById('add-is_faulty') && document.getElementById('add-is_faulty').checked ? 1 : 0;
            payload.warehouse = document.getElementById('add-warehouse') && document.getElementById('add-warehouse').checked ? 1 : 0;
            if (!payload.name) {
                return alert("Lütfen monitör etiketi (ismi) giriniz.");
            }
        } else {
            payload.pc_no = (document.getElementById('add-pc-no') || {}).value || '';
            payload.pc_serial = (document.getElementById('add-seri') || {}).value || '-';
            payload.assigned_to = document.getElementById('add-assigned_to') ? document.getElementById('add-assigned_to').value : '';
            payload.phone = document.getElementById('add-phone') ? document.getElementById('add-phone').value : '';
            payload.title = document.getElementById('add-title') ? document.getElementById('add-title').value : '';
            payload.unit = document.getElementById('add-unit') ? document.getElementById('add-unit').value : '';
            
            if (!payload.location_code && !payload.location_name) {
                return alert("Lutfen mahal bilgilerini giriniz.");
            }
        }

        try {
            const resp = await this.apiRequest('/inventory/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (resp.error) throw new Error(resp.error);
            document.getElementById('device-add-modal').style.display = 'none';
            this.showToast('Yeni cihaz basariyla eklendi!');
            this.state.inventoryCache = {}; 
            this.loadInventory();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    setInvBlock: function(block) {
        this.state.invBlock = block || 'ALL';
        this.state.invKat = 'ALL'; // Reset floor when block changes
        document.querySelectorAll('#inventory-filters .btn-chip').forEach(btn => btn.classList.toggle('active', btn.dataset.block === block));
        this.renderKatFilters(block);
        this.filterInventory();
    },
    renderKatFilters: function(block) {
        const container = document.getElementById('floor-filters');
        if (!container) return;
        if (block === 'ALL') {
            container.style.display = 'none';
            return;
        }
        // Find unique floors for the selected block
        const floors = [...new Set(this.state.inventory
            .filter(i => {
                const tower = (i.tower || "").toUpperCase();
                const kod = (i.location_code || i.location_code || "").toUpperCase();
                if (block === 'A') return (kod.startsWith('A.') || tower === 'A');
                if (block === 'B') return (kod.startsWith('B.') || tower === 'B');
                if (block === 'MH') return (kod.startsWith('C.') || tower === 'C' || tower === 'MH');
                return (tower === block || kod.includes(block));
            })
            .map(i => i.floor)
            .filter(k => k && k.trim() !== "")
        )].sort();
        if (floors.length === 0) {
            container.style.display = 'none';
            return;
        }
        container.style.display = 'flex';
        container.innerHTML = `
            <span style="font-size:0.7rem; color:var(--text-secondary); margin-right:10px; align-self:center; font-weight:700;">KAT:</span>
            <button class="btn-chip ${this.state.invKat === 'ALL' ? 'active' : ''}" onclick="app.setInvKat('ALL')">Tümü</button>
            ${floors.map(f => `
                <button class="btn-chip ${this.state.invKat === f ? 'active' : ''}" onclick="app.setInvKat('${f}')">${f}. Kat</button>
            `).join('')}
        `;
    },
    setInvKat: function(floor) {
        this.state.invKat = floor || 'ALL';
        document.querySelectorAll('#floor-filters .btn-chip').forEach(btn => {
            const txt = btn.innerText.replace('. Kat', '').trim();
            btn.classList.toggle('active', (floor === 'ALL' && txt === 'Tümü') || txt === floor);
        });
        this.filterInventory();
    },
    filterInventory: function() {
        const cat = this.state.invCategory || 'PC';
        const block = this.state.invBlock || 'ALL';
        const searchInput = document.getElementById('main-search');
        const query = searchInput ? searchInput.value.toUpperCase() : "";
        let filtered = this.state.inventory.filter(i => {
            // Category
            const type = (i.device_type || 'PC').toUpperCase();
            let catMatch = false;
            if (cat === 'PC') catMatch = (type === 'PC' || type === "");
            else if (cat === 'SK') catMatch = (['SK', 'SIRAMATIK', 'KIOSK'].includes(type));
            else if (cat === 'TABLET') catMatch = (type === 'TABLET');
            else if (cat === 'BARKOD YAZICI') catMatch = (type==='BARKOD YAZICI' || (i.by_seri && i.by_seri.trim() !== ""));
            else if (cat === 'BARKOD OKUYUCU') catMatch = (type==='BARKOD OKUYUCU' || (i.bo_seri && i.bo_seri.trim() !== ""));
            else if (cat === 'TARAYICI') catMatch = (type==='TARAYICI' || (i.tarayici_seri && i.tarayici_seri.trim() !== ""));
            else catMatch = true;
            if (!catMatch) return false;
            // Block
            if (block !== 'ALL') {
                const tower = (i.tower || "").toUpperCase();
                const kod = (i.location_code || i.location_code || "").toUpperCase();
                let blockMatch = false;
                if (block === 'A') blockMatch = (kod.startsWith('A.') || tower === 'A');
                else if (block === 'B') blockMatch = (kod.startsWith('B.') || tower === 'B');
                else if (block === 'MH') blockMatch = (kod.startsWith('C.') || tower === 'C' || tower === 'MH');
                else blockMatch = (tower === block || kod.includes(block));
                if (!blockMatch) return false;
                // Floor filter (only if block is selected)
                if (this.state.invKat && this.state.invKat !== 'ALL') {
                    if (i.floor !== this.state.invKat) return false;
                }
            }
            // Search
            if (query) {
                const osStr = String(i.windows || "").toUpperCase();
                const isWin = i.windows == 1 || i.windows == '1' || i.windows == true || osStr.includes("WIN");
                const isKeyos = i.keyos == 1 || i.keyos == '1' || i.keyos == true;

                // ÖZEL OS FİLTRELEME (WIN / KEYOS)
                if (query === 'WIN' || query === 'WINDOWS') return isWin;
                if (query === 'KEYOS') return isKeyos;

                // Kullanıcı boluk veya "-" ile ayırarak birden fazla kriter girebilir (OR mantıı)
                // ANCAK "PR-092" gibi yazıcı kodlarını bölmemeliyiz.
                const searchTerms = query.split(/\s+/).flatMap(t => {
                    // PR- ile balayanları koru, dierlerini "-" ile böl
                    if (/^PR-\d+/i.test(t)) return [t];
                    return t.split('-');
                }).map(t => t.trim()).filter(t => t !== "");
                if (searchTerms.length > 0) {
                    const matchAny = searchTerms.some(term => {
                        const termUP = term.toUpperCase();
                        const hasDot = term.includes('.');
                        const hasAlpha = /[A-Zİ]/i.test(term);
                        const isNumeric = /^\d+$/.test(term);
                        if (termUP.startsWith('PR')) {
                            // 1. PR- ile balıyorsa: BALI YAZICI araması
                            return (i.bagli_yazicilar || '').toUpperCase().includes(termUP);
                        }
                        else if (hasAlpha && hasDot) {
                            // 2. Harf + Nokta varsa: MAHAL araması (A.07, B.01 vb.)
                            const content = `${i.location_code || i.location_code} ${i.location_name} ${i.mahal}`.toUpperCase();
                            return content.includes(termUP);
                        } 
                        else if (!hasAlpha && hasDot) {
                            // 3. Sadece Sayı + Nokta varsa: IP ADRESİ araması (10.241 vb.)
                            return (i.ip || '').includes(term);
                        } 
                        else if (isNumeric) {
                            // 4. Sadece sayı ise: PC NUMARASI araması (Tam eleme)
                            // "1358" aratınca PC-1358 gelsin ama PC-1360 gelmesin. (ID eşleşmesi kaldırıldı)
                            const pNo = String(i.pc_no || '').replace(/^0+/, '') || '0';
                            const termClean = term.replace(/^0+/, '') || '0';
                            const pcNoMatch = pNo === termClean;
                            return pcNoMatch;
                        } 
                        else if (/^\d+-\d+-\d+$/.test(term)) {
                            // 5. Tireli yapı (Örn: 10-178-1358): Mahal veya Özel Kod araması
                            const fullContent = `${i.location_code || i.location_code} ${i.location_name} ${i.hostname} ${i.pc_serial}`.toUpperCase();
                            return fullContent.includes(termUP);
                        }                        else {
                            // 5. Dier her ey: SERİ NUMARALARI, HOSTNAME ve GENEL (DM4, VJM vb.)
                            const content = `${i.pc_serial} ${i.monitor_seri} ${i.monitor2_seri} ${i.by_seri} ${i.bo_seri} ${i.tarayici_seri} ${i.seri} ${i.serial_no} ${i.hostname} ${i.card_name || ''} ${i.location_name}`.toUpperCase();
                            return content.includes(termUP);
                        }
                    });
                    if (!matchAny) return false;
                }
            }
            return true;
        });
        // DOÄAL SAYISAL SIRALAMA (PC-001, MN-001 gibi sırayla gelmesi için)
        filtered.sort((a, b) => {
            const getSortKey = (item) => {
                if (item.device_class === 'MONITOR' || item.device_type === 'MONITOR') {
                    return String(item.pr_no || item.name || item.id || '').trim().toUpperCase();
                }
                return String(item.pc_no || item.pr_no || item.name || item.id || '').trim().toUpperCase();
            };
            const strA = getSortKey(a);
            const strB = getSortKey(b);
            
            const isMnA = strA.startsWith('MN-');
            const isMnB = strB.startsWith('MN-');
            
            if (isMnA && !isMnB) return -1;
            if (!isMnA && isMnB) return 1;

            return strA.localeCompare(strB, undefined, { numeric: true, sensitivity: 'base' });
        });
        
        this.state.lastFilteredList = filtered;
        this.renderInventory(filtered);

    },
    filterByKat: function(floor, blockFilter) {
        // Chip actives
        document.querySelectorAll('#floor-filters .btn-chip').forEach(btn => {
            btn.classList.toggle('active', btn.innerText.includes(floor || 'TM'));
        });
        let filtered = this.state.inventory.filter(i => {
            const tower = (i.tower || '').toUpperCase();
            const kod = (i.location_code || i.location_code || '').toUpperCase();
            let matchBlock = false;
            if (blockFilter === 'A') matchBlock = kod.startsWith('A.') || tower === 'A';
            else if (blockFilter === 'B') matchBlock = kod.startsWith('B.') || tower === 'B';
            else matchBlock = tower === blockFilter || kod.includes(blockFilter);
            if (!matchBlock) return false;
            if (floor && i.floor !== floor) return false;
            return true;
        });
        // SAYISAL SIRALAMA (PC-001, MN-001 gibi sırayla gelmesi için, numarası olmayanlar en sona)
        filtered.sort((a, b) => {
            const getSortKey = (item) => {
                if (item.device_class === 'MONITOR' || item.device_type === 'MONITOR') {
                    return String(item.pr_no || item.name || item.id || '').trim().toUpperCase();
                }
                return String(item.pc_no || item.pr_no || item.name || item.id || '').trim().toUpperCase();
            };
            const strA = getSortKey(a);
            const strB = getSortKey(b);
            
            const isMnA = strA.startsWith('MN-');
            const isMnB = strB.startsWith('MN-');
            
            if (isMnA && !isMnB) return -1;
            if (!isMnA && isMnB) return 1;
            
            // Ozel kelimeleri en sona at
            const isNoLabel = (s) => s === 'ETİKETSİZ' || s === 'ETKETSZ' || s === 'ETIKETSIZ' || s === '-' || s === 'YOK' || s === '';
            const noA = isNoLabel(strA);
            const noB = isNoLabel(strB);
            
            if (noA && !noB) return 1;
            if (!noA && noB) return -1;
            
            const matchA = strA.match(/\d+/);
            const matchB = strB.match(/\d+/);
            
            const hasNumA = matchA !== null;
            const hasNumB = matchB !== null;
            
            if (hasNumA && hasNumB) {
                return parseInt(matchA[0], 10) - parseInt(matchB[0], 10);
            } else if (hasNumA) {
                return -1;
            } else if (hasNumB) {
                return 1;
            } else {
                return strA.localeCompare(strB, 'tr');
            }
        });
        
        this.state.lastFilteredList = filtered;
        this.renderInventory(filtered);

    },
    // 
    //  PRINTERS
    // 
    renderPrinters: async function() {
        const container = document.getElementById('printers-grid');
        if (!container) return;
        try {
            const [pr, bp, br, sc] = await Promise.all([
                this.apiRequest('/printers/printers/get_all').catch(e => []),
                this.apiRequest('/printers/barcode_printers/get_all').catch(e => []),
                this.apiRequest('/printers/barcode_readers/get_all').catch(e => []),
                this.apiRequest('/printers/scanners/get_all').catch(e => [])
            ]);
            let data = [...(pr || []), ...(bp || []), ...(br || []), ...(sc || [])];
            // Doğal Sıralama (PR-001, PR-010 vs.)
            data.sort((a, b) => {
                const aNo = (a.pr_no || "");
                const bNo = (b.pr_no || "");
                return aNo.localeCompare(bNo, undefined, { numeric: true, sensitivity: 'base' });
            });
            this.state.printers = data;
            this.applyPrinterFilters(); // Filtreleri uygula ve render et
        } catch (e) { console.error("Yazıcılar yüklenemedi:", e); }
    },
    applyPrinterFilters: function() {
        const container = document.getElementById('printers-grid');
        if (!container || !this.state.printers) return;
        const mainType = this.state.printerMainType || 'PRINTER';
        const modelType = this.state.printerModelType || 'ALL';
        const query = (document.getElementById('printer-search').value || "").toUpperCase();
        const isAdmin = this.state.activeUser && ['ADMIN', 'EDITOR'].includes(this.state.activeUser.role);
        
        let filtered = this.state.printers.filter(p => {
            const dClass = p.device_class || 'PRINTER';
            const modelUP = (p.model || "").toUpperCase();

            // 1. Ana Kategori Filtresi
            if (mainType !== 'ALL') {
                if (mainType === 'PRINTER') {
                    if (dClass !== 'PRINTER') return false;
                    // Yazıcı seçiliyken model filtresine bak
                    if (modelType !== 'ALL' && !modelUP.includes(modelType)) return false;
                } else if (mainType === 'BARCODE_PRINTER') {
                    if (dClass !== 'BARCODE_PRINTER' && !modelUP.includes('BARKOD YAZICI')) return false;
                } else if (mainType === 'BARCODE_READER') {
                    if (dClass !== 'BARCODE_READER' && !modelUP.includes('BARKOD OKUYUCU')) return false;
                } else if (mainType === 'SCANNER') {
                    if (dClass !== 'SCANNER' && !modelUP.includes('TARAYICI')) return false;
                }
            }

            // 2. Arama Filtresi
            if (query) {
                const content = `${p.pr_no} ${p.model || p.name} ${p.seri || p.serial_no} ${p.mahal} ${p.ip} ${p.mac}`.toUpperCase();
                if (!content.includes(query)) return false;
            }
            return true;
        });
        container.innerHTML = filtered.map(p => {
            const status = (p.status || '').toUpperCase();
            const prNo = (p.pr_no || p.name || "").toUpperCase();
            const prNoDisplay = p.pr_no || p.name || "İsimsiz";
            const dClass = p.device_class || 'PRINTER';
            const isSpecial = dClass === 'BARCODE_PRINTER' || dClass === 'BARCODE_READER' || dClass === 'SCANNER' || dClass === 'MONITOR';
            
            const isInstalled = p.mahal && p.mahal.trim() !== "";
            const durumHtml = this.getDurumBadge(status, p.mahal && p.mahal.trim() !== "");

            const seri = p.seri || p.serial_no || '-';
            
            // Mahal ve Bağlı Cihaz Bilgisi (Kullanıcı Talebi)
            let displayMahal = (p.mahal || 'DEPO').toUpperCase();
            let displayIpValue = p.ip || '-';
            let displayIpLabel = "IP ADRESİ";

            if (isSpecial) {
                displayIpLabel = "BAÄLI CİHAZ (PC NO)";
                // recorded_device_no üzerinden PC'yi bul
                const connectedPc = this.state.inventory?.find(pc => {
                    const searchNo = (p.recorded_device_no || "").toUpperCase();
                    const pcNo = (pc.pc_no || "").toUpperCase();
                    // "PC-001" vs "001" karşılaştırması için esnek kontrol
                    return pcNo === searchNo || `PC-${pcNo.padStart(3, '0')}` === searchNo || pcNo === searchNo.replace('PC-', '');
                });

                if (connectedPc) {
                    displayMahal = (connectedPc.location_code || 'BİLİNMİYOR').toUpperCase();
                    displayIpValue = connectedPc.pc_no ? `PC-${connectedPc.pc_no.toString().padStart(3, '0')}` : 'BAÄLI';
                } else {
                    displayMahal = (p.recorded_device_no || 'BİLİNMİYOR').toUpperCase();
                    displayIpValue = p.recorded_device_no || '-';
                }
            }

            return `
            <div class="card printer-card-modern fade-in" style="cursor:pointer; min-height: ${isSpecial ? 'auto' : '280px'};" onclick="app.openDeviceDetail(${p.id}, 'pr', '${p.device_class || 'PRINTER'}')">
                <div class="flex-row mb-3" style="align-items: center; justify-content: space-between;">
                    <div style="color: #38bdf8; font-weight: 900; font-size: 1.3rem; letter-spacing: -0.5px;">${prNoDisplay}</div>
                    <div class="flex-row gap-3" style="align-items: center;">
                        ${durumHtml}
                        <div class="flex-row gap-2">
                             <i class="fas fa-history" style="font-size: 1rem; color: #64748b; cursor: pointer;" title="Servis Geçmişi" onclick="event.stopPropagation(); app.openPrinterServiceHistoryModal(${p.id}, '${prNoDisplay}')"></i>
                             ${!isSpecial ? `<i class="fas fa-globe" style="font-size: 1rem; color: #10b981; cursor: pointer;" title="Arayüz & CUPS" onclick="event.stopPropagation(); app.openPrinterInterfaceDual('${p.ip}', '${prNoDisplay}')"></i>` : ''}
                        </div>
                    </div>
                </div>

                <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 10px; padding: 10px; margin-bottom: 12px;">
                    <div class="flex-row mb-2" style="justify-content: space-between; align-items: flex-end;">
                        <div class="flex-column">
                            <span style="font-size: 0.55rem; color: #64748b; font-weight: 800; text-transform: uppercase;">MAHAL</span>
                            <span style="font-size: 0.85rem; color: #e2e8f0; font-weight: 700;">${displayMahal}</span>
                        </div>
                        <div class="flex-column" style="text-align: right;">
                            <span style="font-size: 0.55rem; color: #38bdf8; font-weight: 800; text-transform: uppercase;">MODEL</span>
                            <span style="font-size: 0.85rem; color: #f8fafc; font-weight: 700;">${p.model || p.name || '---'}</span>
                        </div>
                    </div>
                    <div class="flex-row mb-2" style="justify-content: space-between; align-items: flex-end;">
                        <div class="flex-column">
                            <span style="font-size: 0.55rem; color: #64748b; font-weight: 800; text-transform: uppercase;">${displayIpLabel}</span>
                            <span style="font-size: 0.8rem; color: #f8fafc; font-weight: 600;">${displayIpValue}</span>
                        </div>
                    </div>
                </div>


                ${(isAdmin && !isSpecial) ? `
                <div class="flex-row mb-3" style="justify-content: space-around; align-items: center;">
                    <div class="icon-action-container" onclick="event.stopPropagation(); app.runPrinterAction(${p.id}, 'add')">
                        <div class="icon-action-circle" style="width: 36px; height: 36px; font-size: 0.9rem; color: #10b981;"><i class="fas fa-plus"></i></div>
                        <div class="icon-action-label" style="font-size: 0.55rem;">EKLE</div>
                    </div>
                    <div class="icon-action-container" onclick="event.stopPropagation(); app.openBatchModal('add', ${p.id})">
                        <div class="icon-action-circle" style="width: 36px; height: 36px; font-size: 0.9rem; background: rgba(16, 185, 129, 0.1); color: #10b981; border: none;"><i class="fas fa-layer-group"></i></div>
                        <div class="icon-action-label" style="font-size: 0.55rem;">TOPLU</div>
                    </div>
                    <div class="icon-action-container" onclick="event.stopPropagation(); app.runPrinterAction(${p.id}, 'remove')">
                        <div class="icon-action-circle" style="width: 36px; height: 36px; font-size: 0.9rem; color: #ef4444;"><i class="fas fa-minus"></i></div>
                        <div class="icon-action-label" style="font-size: 0.55rem;">KALDIR</div>
                    </div>
                    <div class="icon-action-container" onclick="event.stopPropagation(); app.openBatchModal('remove', ${p.id})">
                        <div class="icon-action-circle" style="width: 36px; height: 36px; font-size: 0.9rem; background: rgba(239, 68, 68, 0.1); color: #ef4444; border: none;"><i class="fas fa-trash-alt"></i></div>
                        <div class="icon-action-label" style="font-size: 0.55rem;">TEMİZLE</div>
                    </div>
                </div>
                
                <button class="btn btn-service-add" style="width: 100%; font-size: 0.75rem; padding: 10px;" onclick="event.stopPropagation(); app.openAddServiceModal(${p.id})">
                    <i class="fas fa-tools" style="margin-right: 6px;"></i> SERVİS KAYDI OLUÅTUR
                </button>
                ` : (isSpecial ? `
                <div style="text-align: center; color: var(--accent); font-size: 0.7rem; font-style: italic; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px;">
                    <i class="fas fa-link"></i> Bilgisayara Bağlı Çevre Birimi
                </div>
                ` : `
                <div style="text-align: center; color: #64748b; font-size: 0.7rem; font-style: italic; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px;">
                    İşlem yetkisi bulunmuyor.
                </div>
                `)}
            </div>`;
        }).join('');
        this.updatePeripheralDatalists();
    },
    deletePeripheralDevice: async function() { // GHOST CODE REMOVED

        if (!confirm('Bu cihazı veritabanından KALICI olarak silmek istediğinize emin misiniz?')) return;
        let endpoint = `/printers/printers/delete/${id}`;
        if (deviceClass === 'BARCODE_PRINTER') endpoint = `/printers/barcode_printers/delete/${id}`;
        else if (deviceClass === 'BARCODE_READER') endpoint = `/printers/barcode_readers/delete/${id}`;
        else if (deviceClass === 'SCANNER') endpoint = `/printers/scanners/delete/${id}`;
        try {
            const resp = await this.apiRequest(endpoint, { method: 'DELETE' });
            const result = resp;
            if (result.success) {
                this.showToast('Cihaz başarıyla silindi.');
                this.renderPrinters();
            } else {
                alert('Hata: ' + result.error);
            }
        } catch (e) {
            console.error("Delete Error:", e);
            alert('Silme işlemi sırasında bir hata oluştu.');
        }
    },
    // â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    // TOPLU YAZICI YÖNETİMİ (BATCH PRINTER MANAGEMENT)
    // â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    
    batchAddPrinters: function() { this.openBatchModal('add'); },
    batchRemovePrinters: function() { this.openBatchModal('remove'); },
    
    openBatchModal: function(type, printerId = null) {
        this.state.batchAction = type;
        const modal = document.getElementById('batch-printer-modal');
        if(!modal) return;
        
        // Auto-fill BIM credentials
        const user = this.state.activeUser || {};
        const bimUserEl = document.getElementById('batch-bim-user');
        const bimPassEl = document.getElementById('batch-bim-pass');
        if (bimUserEl) bimUserEl.value = user.bim_user || user.username || '';
        if (bimPassEl) bimPassEl.value = user.bim_pass || '';
        
        // Update Title
        const titleEl = document.getElementById('batch-modal-title');
        if (titleEl) {
            titleEl.innerHTML = `<i class="fas fa-terminal"></i> ${type === 'add' ? 'Toplu Yazıcı Ekle' : 'Toplu Yazıcı Kaldır'}`;
        }
        
        // Yazıcı Bilgisini Al (Sadece yazıcılar içinde ara)
        const printer = this.state.printers.find(p => p.id == printerId && p.device_class === 'PRINTER');
        const cmdInput = document.getElementById('batch-modal-cmd-display');
        const targetInput = document.getElementById('batch-target-printer');
        
        if(printer) {
            // NORMAL BUTONLARDAKİ MANTIK:
            // Ekleme ise: PR-001/01
            // Kaldırma ise: PR-001
            let cmd = "";
            if (type === 'add') {
                cmd = `${printer.pr_no || ''}/01`;
            } else {
                cmd = `${printer.pr_no || ''}`;
            }
            
            if(cmdInput) cmdInput.value = cmd;
            if(targetInput) targetInput.value = printer.id;
        }

        // Listeyi Sıfırla ve Doldur
        this.renderBatchSelectionList();
        this.updateBatchCounter();
        
        modal.style.display = 'flex';
    },

    setBatchAction: function(type) {
        this.state.batchAction = type;
        const addBtn = document.getElementById('batch-btn-add');
        const remBtn = document.getElementById('batch-btn-remove');
        const execBtn = document.getElementById('btn-batch-execute');
        
        if(addBtn && remBtn) {
            addBtn.className = type === 'add' ? 'btn btn-chip active' : 'btn btn-chip';
            remBtn.className = type === 'remove' ? 'btn btn-chip active' : 'btn btn-chip';
            
            if(type === 'add') {
                addBtn.style.background = 'rgba(0,210,255,0.1)';
                addBtn.style.border = '1px solid var(--accent)';
                remBtn.style.background = '';
                remBtn.style.border = '';
                execBtn.className = 'btn btn-accent';
                execBtn.innerHTML = '<i class="fas fa-play"></i> Toplu Kurulumu Başlat';
            } else {
                remBtn.style.background = 'rgba(255,75,43,0.1)';
                remBtn.style.border = '1px solid #ff4b2b';
                addBtn.style.background = '';
                addBtn.style.border = '';
                execBtn.className = 'btn';
                execBtn.style.background = '#ff4b2b';
                execBtn.style.color = '#fff';
                execBtn.innerHTML = '<i class="fas fa-trash"></i> Toplu Kaldırma Başlat';
            }
        }
        this.updateBatchCounter();
    },

    renderBatchSelectionList: function(filter = '') {
        const listContainer = document.getElementById('batch-selection-list');
        if(!listContainer || !this.state.inventory) return;

        const query = filter.toUpperCase();
        
        const options = this.state.inventory
            .filter(item => {
                const type = (item.device_type || 'PC').toUpperCase();
                const isPC = (type === 'PC' || type === '' || type === 'BİLGİSAYAR');
                if (!isPC) return false;
                
                const searchStr = `${item.pc_no} ${item.hostname} ${item.ip} ${item.location_code} ${item.bagli_yazicilar || ''}`.toUpperCase();
                return !query || searchStr.includes(query);
            })
            .sort((a, b) => {
                // Sadece tirelerden olusan isimleri (---, ----- vb.) tespit et
                const isDash = (s) => !s || s === '' || /^-+$/.test(s);
                const aValid = !isDash(a.pc_no);
                const bValid = !isDash(b.pc_no);
                
                if (aValid && !bValid) return -1;
                if (!aValid && bValid) return 1;
                
                const aVal = String(a.pc_no || 'ZZZ').padStart(5, '0');
                const bVal = String(b.pc_no || 'ZZZ').padStart(5, '0');
                return aVal.localeCompare(bVal);
            })
            .map(item => {
                // KARTLARDAKİ İSİM MANTIÄI:
                let pcLabel = item.pc_no || '---';
                if (pcLabel !== '---' && !isNaN(pcLabel)) pcLabel = `PC-${pcLabel.toString().padStart(3, '0')}`;
                
                // Mahal Kodu + Yazıcı
                const mahalKod = item.location_code || item.location_code || '-';
                const yazicilar = item.bagli_yazicilar || '';
                
                return {
                    id: item.id,
                    label: `<div class="flex-column" style="gap:1px;">
                                <span style="color:#fff; font-weight:700; font-size:0.85rem;">${pcLabel}</span>
                                <div class="flex-row gap-2" style="align-items:center;">
                                    <span style="color:var(--accent); font-size:0.75rem; font-family:monospace;">${item.ip || 'IP Yok'}</span>
                                    <span style="font-size:0.7rem; opacity:0.6; color:#00ff88;">[${mahalKod}]</span>
                                    ${yazicilar ? `<span style="font-size:0.7rem; color:#ffcc00; font-weight:700;"><i class="fas fa-print" style="font-size:0.6rem;"></i> ${yazicilar}</span>` : ''}
                                </div>
                            </div>`,
                    ip: item.ip
                };
            });

        listContainer.innerHTML = options.map(opt => {
            const isChecked = this.state.selectedBatchIds?.has(String(opt.id)) ? 'checked' : '';
            return `
            <div class="flex-row gap-3 dropdown-item" style="border-bottom: 1px solid rgba(255,255,255,0.05); align-items: center; cursor:pointer;" onclick="const chk=document.getElementById('chk-${opt.id}'); chk.checked=!chk.checked; app.updateBatchCounter(); event.stopPropagation();">
                <input type="checkbox" id="chk-${opt.id}" class="batch-chk" data-type="pc" data-val="${opt.id}" onchange="app.updateBatchCounter()" onclick="event.stopPropagation()" style="width:16px; height:16px; accent-color:var(--accent);" ${isChecked}>
                <label for="chk-${opt.id}" style="cursor: pointer; flex: 1; padding: 4px 0;">${opt.label}</label>
            </div>`;
        }).join('');
        
        if (options.length === 0) {
            listContainer.innerHTML = '<p style="padding:15px; color:#888; font-size:0.8rem; text-align:center;">Aranan kriterde Bilgisayar bulunamadı.</p>';
        }
    },

    filterBatchSelection: function() {
        this.updateBatchCounter(); // Mevcut seçimleri Set'e kaydet
        const val = document.getElementById('batch-selection-search').value;
        this.renderBatchSelectionList(val);
        document.getElementById('batch-selection-container').style.display = 'block';
    },

    // Dışarı tıklandığında açılır listeyi kapat
    setupBatchEventListeners: function() {
        document.addEventListener('click', (e) => {
            const container = document.getElementById('batch-selection-container');
            const searchInput = document.getElementById('batch-selection-search');
            if (container && searchInput && !container.contains(e.target) && e.target !== searchInput) {
                container.style.display = 'none';
            }
        });
    },

    selectAllBatch: function(status) {
        document.querySelectorAll('.batch-chk').forEach(chk => chk.checked = status);
        this.updateBatchCounter();
    },

    updateBatchCounter: function() {
        if (!this.state.selectedBatchIds) this.state.selectedBatchIds = new Set();
        const chks = Array.from(document.querySelectorAll('.batch-chk:checked'));
        
        // Mevcut görünür seçili olanları ekle
        chks.forEach(c => this.state.selectedBatchIds.add(String(c.dataset.val)));
        // Mevcut görünür olup seçili OLMAYANLARI Set'ten çıkar (Kullanıcı manuel kaldırmış olabilir)
        Array.from(document.querySelectorAll('.batch-chk:not(:checked)')).forEach(c => this.state.selectedBatchIds.delete(String(c.dataset.val)));

        const selectedIds = Array.from(this.state.selectedBatchIds);
        const btn = document.getElementById('btn-batch-execute');
        const ipDisplay = document.getElementById('batch-target-ips-display');
        
        if(ipDisplay) {
            const displayLines = selectedIds.map(sid => {
                const item = (this.state.inventory || []).find(i => i.id == sid);
                if (!item) return '';
                let pcLabel = item.pc_no || '---';
                if (pcLabel !== '---' && !isNaN(pcLabel)) pcLabel = `PC-${pcLabel.toString().padStart(3, '0')}`;
                const hasPrinter = item.bagli_yazicilar ? `<span style="color:#ffcc00; font-size:0.68rem; margin-left: auto;"><i class="fas fa-print"></i> ${item.bagli_yazicilar}</span>` : '';
                return `<div style="display: flex; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding: 4px 0;">
                    <i class="fas fa-desktop" style="color: var(--accent); margin-right: 8px;"></i>
                    <span style="color: #fff; font-weight: bold; width: 60px;">${pcLabel}</span>
                    <span style="color: var(--accent); font-family: monospace; width: 100px;">${item.ip || 'IP Yok'}</span>
                    <span style="color: #888; font-size: 0.72rem;">[${item.location_code || '-'}]</span>
                    ${hasPrinter}
                </div>`;
            }).filter(Boolean);
            ipDisplay.innerHTML = displayLines.join('');
            ipDisplay.scrollTop = ipDisplay.scrollHeight;
        }

        if (btn) {
            btn.innerHTML = `<i class="fas fa-play"></i> ÇALIÅTIR (${selectedIds.length} CİHAZ)`;
            btn.disabled = selectedIds.length === 0;
        }
    },

    executeBatchPrinterAction: async function() {
        const printerId = document.getElementById('batch-target-printer').value;
        const bimUser = document.getElementById('batch-bim-user').value;
        const bimPass = document.getElementById('batch-bim-pass').value;
        
        const selected = Array.from(document.querySelectorAll('.batch-chk:checked')).map(chk => {
            const item = this.state.inventory.find(i => i.id == chk.dataset.val);
            // Sadece IP kısmını al (Parantez içindeki bilgileri temizle)
            return { id: chk.dataset.val, ip: item ? item.ip : '', name: item ? (item.pc_no || 'Cihaz') : 'Cihaz' };
        });

        if(!printerId || selected.length === 0) {
            this.showToast('Lütfen yazıcı ve en az bir hedef seçin.', 'warning');
            return;
        }

        if(!bimUser || !bimPass) {
            this.showToast('BİM giriş bilgileri eksik.', 'warning');
            return;
        }

        if(!confirm(`${selected.length} cihaz için işlem sırayla başlatılacak. Emin misiniz?`)) return;

        const btn = document.getElementById('btn-batch-execute');
        btn.disabled = true;
        btn.style.opacity = '0.5';
        
        const logArea = document.getElementById('batch-log-area');
        const logContent = document.getElementById('batch-log-content');
        if (logArea && logContent) {
            logArea.style.display = 'block';
            logContent.innerHTML = '';
        }
        
        const appendLog = (msg, isSuccess) => {
            if (!logContent) return;
            const color = isSuccess ? '#00ff88' : '#ff4b2b';
            const icon = isSuccess ? 'fa-check-circle' : 'fa-times-circle';
            logContent.innerHTML += `<div style="display: flex; align-items: flex-start; gap: 8px; margin-bottom: 4px;">
                <i class="fas ${icon}" style="color: ${color}; margin-top: 2px;"></i>
                <span style="color: #ccc;">${msg}</span>
            </div>`;
            logContent.scrollTop = logContent.scrollHeight;
        };

        let successCount = 0;
        let failedTargets = [];

        try {
            for(let i=0; i < selected.length; i++) {
                const target = selected[i];
                const cmdInput = document.getElementById('batch-modal-cmd-display').value;
                const printerName = cmdInput.split('/')[0];
                const actionText = this.state.batchAction === 'add' ? 'tanımlaması yapıldı.' : 'kaldırıldı.';
                const actionTextFail = this.state.batchAction === 'add' ? 'tanımlaması yapılamadı!' : 'kaldırılamadı!';
                
                this.showToast(`(${i+1}/${selected.length}) ${target.name} işleniyor...`, 'info');
                
                const bimFunction = (this.state.batchAction === 'add') ? 'AddPrinter' : 'RemovePrinter';
                const cmd = document.getElementById('batch-modal-cmd-display').value;

                try {
                    const resp = await this.apiRequest('/printers/printers/batch_action', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            action: this.state.batchAction,
                            bim_function: bimFunction,
                            command: cmd,
                            printer_id: printerId,
                            targets: [{ type: 'pc', value: target.id }],
                            user: this.state.activeUser.name,
                            bim_user: bimUser,
                            bim_pass: bimPass
                        })
                    });
                    
                    const res = resp;
                    if(res.success && res.success_count > 0) {
                        successCount++;
                        appendLog(`<b>${target.name}</b> (${target.ip}) cihazına <b>${printerName}</b> ${actionText}`, true);
                    } else {
                        const errReason = res.failed && res.failed.length > 0 ? res.failed[0] : (res.error || 'Bilinmeyen Hata');
                        failedTargets.push(`${target.name} (${errReason})`);
                        appendLog(`<b>${target.name}</b> (${target.ip}) cihazına <b>${printerName}</b> ${actionTextFail} (Hata: ${errReason})`, false);
                    }
                } catch (err) {
                    failedTargets.push(`${target.name} (Bağlantı Hatası)`);
                    appendLog(`<b>${target.name}</b> (${target.ip}) cihazına erişilemedi! (Bağlantı Hatası)`, false);
                }
            }
            
            if (failedTargets.length === 0) {
                this.showToast(`İşlem başarıyla tamamlandı. (${successCount} Cihaz)`, 'success');
            } else {
                const failedList = failedTargets.join('\n');
                alert(`İşlem tamamlandı.\nBaşarılı: ${successCount}\nBaşarısız olanlar:\n${failedList}`);
            }
            
            // document.getElementById('batch-printer-modal').style.display = 'none';
            this.renderPrinters();
            appendLog(`<b>İşlem Bitti:</b> ${successCount} Başarılı, ${failedTargets.length} Başarısız.`, failedTargets.length === 0);
            
        } catch(e) {
            this.showToast('Kritik bir hata oluştu: ' + e.message, 'error');
        } finally {
            btn.disabled = false;
            btn.style.opacity = '1';
        }
    },
    setPrinterMainType: function(type) {
        this.state.printerMainType = type;
        // Eğer Yazıcı seçiliyse model filtrelerini göster, değilse gizle
        const modelFilters = document.getElementById('printer-model-filters-container');
        if (modelFilters) {
            modelFilters.style.display = type === 'PRINTER' ? 'block' : 'none';
        }
        
        document.querySelectorAll('#printer-main-filters .btn-chip').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.ptype === type);
        });
        this.applyPrinterFilters();
    },
    setPrinterModelType: function(model) {
        this.state.printerModelType = model;
        document.querySelectorAll('#printer-model-filters .btn-chip').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.pmodel === model);
        });
        this.applyPrinterFilters();
    },
    searchPrinters: function() { this.applyPrinterFilters(); },
    filterPrinters: function(ptype) { this.setPrinterMainType(ptype); },

    scanAllPrinters: async function() { // GHOST CODE REMOVED

        if(!confirm("Tüm yazıcıların durumunu ve toner seviyesini arka planda güncellemek istediinize emin misiniz? Bu ilem birkaç dakika sürebilir.")) return;
        try {
            const resp = await this.apiRequest('/printers/scan_all', { method: 'POST' });
            const data = resp;
            if(data.success) {
                this.showToast(data.message, 'success');
            } else throw new Error(data.error);
        } catch(e) { this.showToast('Hata: ' + e.message, 'error'); }
    },

    // 
    //  AREAS
    // 
    loadAreas: async function() {
        try {
            const data = await this.apiRequest('/areas/get_all');
            this.state.areas = data;
            this.renderAreas(data);
        } catch (e) { console.error("Alanlar yüklenemedi:", e); }
    },
    renderAreas: function(data) {
        const container = document.getElementById('areas-grid');
        if (!container) return;
        data = data || this.state.areas;
        const isAdmin = this.state.activeUser && this.state.activeUser.role === 'ADMIN';
        container.innerHTML = data.map((area, idx) => `
            <div class="card fade-in ${isAdmin ? 'area-card-admin' : ''}" style="border: 1px solid rgba(255,255,255,0.05); background: linear-gradient(145deg, rgba(20,30,40,0.4) 0%, rgba(10,15,20,0.6) 100%);">
                <div class="flex-between" style="min-height: 50px; margin-bottom: 5px; align-items: center;">
                    <span style="color: #00d2ff; font-weight: 800; font-size: 1.1rem; display: flex; align-items: center; gap: 10px;">
                        <i class="fas fa-folder" style="font-size: 1.3rem;"></i> ${area.name.toUpperCase()}
                    </span>
                    ${isAdmin ? `<i class="fas fa-pencil" style="opacity:0.4; cursor:pointer; font-size: 1.1rem;" onclick="app.openAreaModal(${area.id})" title="Düzenle"></i>` : ''}
                </div>
                <div style="height: 1px; background: rgba(255,255,255,0.08); margin-bottom: 12px; width: 100%;"></div>

                <div class="flex-between mb-3" style="background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.03);">
                    <span style="color: var(--text-secondary); font-size: 0.85rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px;">${area.path || ''}</span>
                    <button class="btn-chip" style="background: rgba(255,255,255,0.1); padding: 4px 12px; font-size: 0.7rem; border-radius: 15px;" onclick="app.copyToClipboard('${(area.path || '').replace(/\\/g, '\\\\')}')">
                         <i class="fas fa-copy"></i> YOL
                    </button>
                </div>

                <div style="font-size: 0.8rem; color: var(--text-secondary); padding: 0 5px;">
                    <div class="flex-between mb-2">
                        <span>Kullanıcı:</span>
                        <div class="flex-row gap-2" style="align-items:center;">
                            <span style="color:#fff; font-weight: 600;">${area.username || 'bilinmiyor'}</span>
                            <i class="fas fa-copy" style="cursor:pointer; opacity: 0.5;" onclick="app.copyToClipboard('${area.username || ''}')"></i>
                        </div>
                    </div>
                    <div class="flex-between" style="margin-bottom: 5px;">
                        <span>Åifre:</span>
                        <div class="flex-row gap-2" style="align-items:center;">
                            <span id="pass-${idx}" data-pass="${(area.password || '').replace(/"/g, '&quot;')}" style="color:var(--accent); font-weight: 700; cursor: pointer;" onclick="this.innerText = this.innerText === '********' ? this.getAttribute('data-pass') : '********';" title="Åifreyi Göster/Gizle">${area.password ? '********' : '-'}</span>
                            <i class="fas fa-copy" style="cursor:pointer; opacity: 0.5;" onclick="app.copyToClipboard('${area.password || ''}')"></i>
                        </div>
                    </div>
                </div>

                <!-- Aksiyon Butonları (Resim 3 Stili) -->
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 15px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 15px;">
                    <div class="area-action-btn" onclick="app.runAreaAction(${area.id}, 'unlock')" title="KİLİT AÇ">
                        <div class="icon-circle" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);"><i class="fas fa-key"></i></div>
                        <span>KİLİT AÇ</span>
                    </div>
                    <div class="area-action-btn" onclick="app.runAreaAction(${area.id}, 'define')" title="TANIMLA" style="color: #00ff88;">
                        <div class="icon-circle" style="background: rgba(0, 255, 136, 0.1); border: 1px solid rgba(0, 255, 136, 0.2);"><i class="fas fa-terminal"></i></div>
                        <span>TANIMLA</span>
                    </div>
                    <div class="area-action-btn" onclick="app.downloadConnectBat(${area.id})" title="WIN BAT" style="color: #00d2ff;">
                        <div class="icon-circle" style="background: rgba(0, 210, 255, 0.1); border: 1px solid rgba(0, 210, 255, 0.2);"><i class="fas fa-windows"></i></div>
                        <span>WIN BAT</span>
                    </div>
                    <div class="area-action-btn" onclick="app.runAreaAction(${area.id}, 'delete')" title="SİL" style="color: #ff4b2b;">
                        <div class="icon-circle" style="background: rgba(255, 75, 43, 0.1); border: 1px solid rgba(255, 75, 43, 0.2);"><i class="fas fa-trash"></i></div>
                        <span>SİL</span>
                    </div>
                </div>
            </div>`).join('');
    },
    searchAreas: function() {
        const query = (document.getElementById('areas-search').value || "").toUpperCase();
        if (!query) return this.renderAreas(this.state.areas);
        const filtered = this.state.areas.filter(a => 
            (a.name || '').toUpperCase().includes(query) || 
            (a.path || '').toUpperCase().includes(query) ||
            (a.birim || '').toUpperCase().includes(query)
        );
        this.renderAreas(filtered);
    },
    openPrinterActionFromArea: function(id) {
        const area = this.state.areas.find(a => a.id == id);
        if (!area) return;
        
        // Kullanıcı "mevcut pc nin ip adresi gelecek" dedi.
        // Bizim elimizde istemcinin (mevcut PC) IP'si genellikle app.state.clientIp'de olabilir (backend'den gelen).
        // Eğer yoksa, bu alandaki IP'yi (server IP) hedef alabiliriz ama kullanıcı "mevcut pc" diyor.
        // İpucunu frontend'den alalım: window.location.hostname veya backend'e soralım.
        
        this.showToast('İstemci IP adresi üzerinden yazıcı işlemleri başlatılıyor...', 'info');
        
        // Modal açmadan önce IP'yi otomatik olarak "Cihazım" IP'si veya client IP olarak belirle
        this.apiRequest('/bim/client_ip')
            .then(data => {
                const myIp = data.ip;
                this.openBatchModal('add', null, myIp); 
            })
            .catch(() => this.openBatchModal('add', null));
    },
    parseNetworkPath: function(path) {
        // \\IP\FOLDER to {ip, folder}
        let p = (path || '').replace(/\\/g, '/');
        p = p.replace(/^\/+/, '');
        const parts = p.split('/');
        return {
            ip: parts[0] || '',
            folder: parts.slice(1).join('/') || ''
        };
    },
    showDefineScript: function(id) {
        const area = this.state.areas.find(a => a.id == id);
        if (!area) return;
        const { ip, folder } = this.parseNetworkPath(area.path);
        const user = area.username || 'USER';
        const pass = area.password || 'PASS';
        const script = `#!/bin/bash
# FSKontrol: Ortak alanın daha önceden fstab'a eklenip eklenmediini kontrol eder
FSKontrol=\`grep ${ip} /etc/fstab | wc -l\`
if [ "$FSKontrol" == "1" ]; then
    echo "FSKontrol: Bu a adresi için ayarlar zaten mevcut."
else
    echo "Ortak alan tanımlanıyor: ${area.name}..."
    apt-get install cifs-utils -y
    mkdir -p /mnt/${folder}
    # Skel Desktop'a link ekle (Yeni kullanıcılar için)
    mkdir -p /etc/skel/Desktop
    ln -sf /mnt/${folder} /etc/skel/Desktop/
    # Anlık Mount
    mount -t cifs //${ip}/${folder} /mnt/${folder} -o username=${user},password='${pass}',noexec,rw,file_mode=0777,dir_mode=0777
    # Credentials Dosyası
    mkdir -p /etc/samba
    echo "username=${user}
password=${pass}" > /etc/samba/.smbcredentials_${folder}
    chmod 600 /etc/samba/.smbcredentials_${folder}
    # fstab Kaydı (Kalıcı hale getirme)
    echo "//${ip}/${folder} /mnt/${folder} cifs nofail,credentials=/etc/samba/.smbcredentials_${folder},noexec,rw,file_mode=0777,dir_mode=0777  0 0" >> /etc/fstab
    # Mevcut kullanıcıların masaüstlerine link ekle
    for UserHome in /home/*; do
        if [ -d "$UserHome/Desktop" ]; then
            ln -sf /mnt/${folder} "$UserHome/Desktop/"
        fi
    done
    echo "FSKontrol: ${area.name} tanımlama ilemi baarıyla bitti."
fi`;
        document.getElementById('script-modal-title').innerHTML = `<i class="fas fa-terminal"></i> ${area.name} - Tanımlama Kodu`;
        document.getElementById('script-modal-content').innerText = script;
        document.getElementById('script-modal').style.display = 'flex';
    },
    showUnlockScript: function(id) {
        const area = this.state.areas.find(a => a.id == id);
        if (!area) return;
        const { ip, folder } = this.parseNetworkPath(area.path);
        const user = area.username || 'USER';
        const pass = area.password || 'PASS';
        const script = `#!/bin/bash
# MountAuto.sh scriptini oluşturur (A koparsa otomatik balamak için)
mkdir -p /KEYDATA/Script
cat <<\\EOF > /KEYDATA/Script/MountAuto_${folder}.sh
#!/bin/bash
MountKontrol=\`mount | grep ${ip} | wc -l\`
if [ "$MountKontrol" == "1" ]; then
    echo "Ortak Alan Balı: ${folder}"
else
    mount -t cifs //${ip}/${folder} /mnt/${folder} -o username=${user},password='${pass}',noexec,rw,file_mode=0777,dir_mode=0777
fi
exit 0
EOF
chmod 755 /KEYDATA/Script/MountAuto_${folder}.sh
# Crontab kontrolü ve ekleme (Her 5 dakikada bir kontrol eder)
CronKontrol=\`cat /etc/crontab | grep "MountAuto_${folder}" | wc -l\`
if [ "$CronKontrol" == "1" ]; then
    echo "Cron: Zaten eklenmi."
else	
    echo "### ${area.name} Otomatik Balantı Kilidi Açıldı ###
*/5 * * * * root /KEYDATA/Script/MountAuto_${folder}.sh" >> /etc/crontab
    echo "### İlgili Ortak Alanın Kilidi Açılmıtır. Kullanıcıya F5 ile yenilemesini söyle! ###"
fi`;
        document.getElementById('script-modal-title').innerHTML = `<i class="fas fa-unlock"></i> ${area.name} - Kilit Açma Kodu`;
        document.getElementById('script-modal-content').innerText = script;
        document.getElementById('script-modal').style.display = 'flex';
    },
    showDeleteScript: function(id) {
        const area = this.state.areas.find(a => a.id == id);
        if (!area) return;
        const { ip, folder } = this.parseNetworkPath(area.path);
        const script = `#!/bin/bash
PaylasimAdi="${folder}"
for path in $(sudo find /home/*/Desktop -name "$PaylasimAdi"); do [ -f "$path" ] && sudo unlink "$path" || ( [ -d "$path" ] && sudo rm -rf "$path" ); done
sed -i "/$PaylasimAdi/d" /etc/fstab
unlink /etc/skel/Desktop/$PaylasimAdi
umount /mnt/$PaylasimAdi
rm -rf /mnt/$PaylasimAdi`;
        document.getElementById('script-modal-title').innerHTML = `<i class="fas fa-trash"></i> ${area.name} - Silme Kodu`;
        document.getElementById('script-modal-content').innerText = script;
        document.getElementById('script-modal').style.display = 'flex';
    },
    runAreaAction: function(id, type) {
        const area = this.state.areas.find(a => a.id == id);
        if (!area) return;
        const { ip, folder } = this.parseNetworkPath(area.path);
        const user = area.username || 'USER';
        const pass = area.password || 'PASS';
        let rawScript = "";
        if (type === 'unlock') {
            rawScript = `mkdir -p /KEYDATA/Script
cat << 'EOF' > /KEYDATA/Script/MountAuto_${folder}.sh
#!/bin/bash
MountKontrol=\`mount | grep ${ip} | wc -l\`
if [ "$MountKontrol" == "1" ]; then
    echo "Bagli"
else
    mount -t cifs //${ip}/${folder} /mnt/${folder} -o username=${user},password='${pass}',noexec,rw,file_mode=0777,dir_mode=0777
fi
EOF
chmod 755 /KEYDATA/Script/MountAuto_${folder}.sh
if ! grep -q "MountAuto_${folder}.sh" /etc/crontab; then
  echo "*/5 * * * * root /KEYDATA/Script/MountAuto_${folder}.sh" >> /etc/crontab
fi`;
        } else if (type === 'define') {
            rawScript = `apt-get install cifs-utils -y
mkdir -p /mnt/${folder}
mkdir -p /etc/samba
echo -e "username=${user}\\npassword=${pass}" > /etc/samba/.smbcredentials_${folder}
chmod 600 /etc/samba/.smbcredentials_${folder}
mount -t cifs //${ip}/${folder} /mnt/${folder} -o credentials=/etc/samba/.smbcredentials_${folder},noexec,rw,file_mode=0777,dir_mode=0777
if ! grep -q "//${ip}/${folder}" /etc/fstab; then
  echo "//${ip}/${folder} /mnt/${folder} cifs nofail,credentials=/etc/samba/.smbcredentials_${folder},noexec,rw,file_mode=0777,dir_mode=0777 0 0" >> /etc/fstab
fi
mkdir -p /etc/skel/Desktop
ln -sf /mnt/${folder} /etc/skel/Desktop/
for UserHome in /home/*; do
  if [ -d "$UserHome/Desktop" ]; then
    ln -sf /mnt/${folder} "$UserHome/Desktop/"
  fi
done`;
        } else if (type === 'delete') {
            rawScript = `umount -l /mnt/${folder}
rm -rf /mnt/${folder}
rm -f /etc/samba/.smbcredentials_${folder}
sed -i "/${folder}/d" /etc/fstab
sed -i "/MountAuto_${folder}/d" /etc/crontab
for path in /home/*/Desktop/${folder}; do
  if [ -L "$path" ]; then rm -f "$path"; fi
done
rm -f /etc/skel/Desktop/${folder}
rm -f /KEYDATA/Script/MountAuto_${folder}.sh`;
        }
        // BİM API'sinin satır atlamaları ve tırnak iaretleriyle (escaping) ilgili sorun yaatmaması için scripti Base64'e çevirip gönderiyoruz.
        const encodedScript = btoa(unescape(encodeURIComponent(rawScript)));
        const script = `echo ${encodedScript} | base64 -d | bash`;
        // Bilgi bankası sistemi gibi istemci IP'sini otomatik algılaması için bo IP gönderiyoruz
        this.openRunCommandModal(null, script, '');
    },
    runPrinterAction: function(id, type) {
        const p = this.state.printers.find(x => x.id == id && x.device_class === 'PRINTER');
        if (!p) return;
        
        let pr_number = (p.pr_no || '').trim().toUpperCase();
        if (pr_number && !pr_number.startsWith('PR-')) {
            pr_number = ''; 
        }

        let cmd = '';
        if (type === 'add') {
            cmd = pr_number ? `${pr_number}/01` : '';
        } else {
            cmd = pr_number ? `${pr_number}` : '';
        }
        const bimFunction = (type === 'add') ? 'AddPrinter' : 'RemovePrinter';
        this.openRunCommandModal(null, cmd, '', bimFunction);
    },
    rebootDevice: async function() { // GHOST CODE REMOVED

        // Tıklanan PC'nin IP adresini dorudan gönder
        this.openRunCommandModal(null, 'reboot', ip);
    },

    updateDepotFilterChips: function() {
        const chips = document.querySelectorAll('#depot-filters .btn-chip');
        chips.forEach(chip => {
            const cat = chip.getAttribute('data-dcat');
            if (cat === this.state.depot_activeFilter) chip.classList.add('active');
            else chip.classList.remove('active');
        });
    },
    loadDepot: async function() {
        try {
            const data = await this.apiRequest('/depot/get_all');
            this.state.depot = data;
            this.renderDepot(data);
        } catch (e) { 
            console.error("Depo yüklenemedi:", e);
            const grid = document.getElementById('depot-grid');
            if (grid) grid.innerHTML = `<p style="color:red; text-align:center; padding:20px;">Veriler yüklenemedi: ${e.message}</p>`;
        }
    },
    renderDepot: function(items) {
        const grid = document.getElementById('depot-grid');
        if (!grid) return;
        items = items || this.state.depot;
        // Her zaman alfabetik sırala
        items.sort((a, b) => (a.name || "").localeCompare(b.name || "", 'tr'));
        if (!items.length) {
            grid.innerHTML = '<p style="opacity:0.4; text-align:center; grid-column:1/-1;">Depoda henüz ürün yok. + Yeni ürün butonuyla ekleyin.</p>';
            return;
        }
        grid.innerHTML = items.map(item => {
            const ratio = item.critical_stock > 0 ? (item.current_stock / item.critical_stock) : 999;
            let stockClass = 'stock-ok', stockIcon = 'fa-check-circle', stockText = 'Yeterli';
            if (item.current_stock === 0) {
                stockClass = 'stock-critical'; stockIcon = 'fa-circle-xmark'; stockText = 'Stokta Yok!';
            } else if (ratio <= 1) {
                stockClass = 'stock-warning'; stockIcon = 'fa-triangle-exclamation'; stockText = 'Kritik Seviye!';
            }
            const catNormalized = (item.category || "").toUpperCase().trim();
            const catClass = catNormalized === 'SARF MALZEME' ? 'cat-sarf' :
                            catNormalized === 'YEDEK PARÇA' ? 'cat-yedek' :
                            catNormalized === 'ÇEVRE BİRİMİ' ? 'cat-cevre' : 
                            catNormalized === 'GIDA' ? 'cat-gida' : 'cat-kablo';
            const barWidth = Math.min(100, (item.current_stock / Math.max(item.critical_stock * 2, 1)) * 100);
            const barColor = ratio > 1 ? '#00ff88' : (item.current_stock === 0 ? '#ff4b2b' : '#ffb400');

            return `
            <div class="card depot-card fade-in" style="cursor:pointer; border-left: 4px solid ${barColor};" onclick="app.openEditDepotItem(${item.id})">
                <div class="flex-between mb-2">
                    <span class="category-badge ${catClass}">${item.category || 'Belirsiz'}</span>
                    <div class="stock-indicator ${stockClass}" style="margin:0; font-size:0.7rem; padding: 2px 8px;">
                        <i class="fas ${stockIcon}"></i> ${stockText}
                    </div>
                </div>
                
                <div style="font-size: 1.05rem; font-weight: 700; color: #fff; margin-bottom: 8px; min-height: 2.4em; line-height:1.2; display: flex; align-items: center;">${item.name}</div>
                
                <div class="flex-between" style="font-size: 0.85rem; background: rgba(255,255,255,0.03); padding: 8px; border-radius: 6px; margin-bottom: 8px;">
                    <div class="flex-column">
                        <span style="opacity:0.5; font-size:0.65rem;">DEPO STOK</span>
                        <strong style="color:#fff; font-size:1.1rem;">${item.current_stock} <small style="font-weight:400; font-size:0.7rem; opacity:0.6;">${item.unit}</small></strong>
                    </div>
                    <div class="flex-column" style="text-align:right;">
                        <span style="opacity:0.5; font-size:0.65rem;">KRİTİK SINIR</span>
                        <strong style="color:var(--accent);">${item.critical_stock}</strong>
                    </div>
                </div>

                <div class="stock-bar" style="height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; margin-bottom: 12px;">
                    <div class="stock-bar-fill" style="width: ${barWidth}%; background: ${barColor}; height: 100%;"></div>
                </div>

                <div class="flex-row gap-2 mb-3" style="font-size: 0.7rem; opacity: 0.8;">
                    <div class="flex-column" style="flex:1; align-items:center; background: rgba(0,0,0,0.15); padding: 5px; border-radius: 4px;">
                        <span style="opacity:0.6; font-size: 0.55rem;">Saha</span>
                        <strong style="color:var(--accent);">${item.saha_count || 0}</strong>
                    </div>
                    <div class="flex-column" style="flex:1; align-items:center; background: rgba(0,0,0,0.15); padding: 5px; border-radius: 4px;">
                        <span style="opacity:0.6; font-size: 0.55rem;">Arızalı</span>
                        <strong style="color:#ffb400;">${item.arizali_count || 0}</strong>
                    </div>
                    <div class="flex-column" style="flex:1; align-items:center; background: rgba(0,0,0,0.15); padding: 5px; border-radius: 4px;">
                        <span style="opacity:0.6; font-size: 0.55rem;">Kayıp</span>
                        <strong style="color:#ff4b2b;">${item.kayip_count || 0}</strong>
                    </div>
                </div>

                <div class="flex-row gap-2" style="border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px;">
                    <button class="btn btn-secondary" style="flex:1; padding: 6px; font-size: 0.75rem; background: rgba(0,210,255,0.05); border-color: rgba(0,210,255,0.2); color: var(--accent);" onclick="event.stopPropagation(); app.openDepotTransaction(${item.id}, '${item.name.replace(/'/g, "\\'")}', 'in')">
                        <i class="fas fa-arrow-down"></i> GİRİÅ
                    </button>
                    <button class="btn btn-secondary" style="flex:1; padding: 6px; font-size: 0.75rem; background: rgba(255,180,0,0.05); border-color: rgba(255,180,0,0.2); color: #ffb400;" onclick="event.stopPropagation(); app.openDepotTransaction(${item.id}, '${item.name.replace(/'/g, "\\'")}', 'out')">
                        <i class="fas fa-arrow-up"></i> ÇIKIÅ
                    </button>
                    <button class="btn btn-chip" style="padding: 6px; width: 35px; justify-content:center;" onclick="event.stopPropagation(); app.openEditDepotItem(${item.id})" title="Düzenle">
                        <i class="fas fa-cog"></i>
                    </button>
                </div>
            </div>`;
        }).join('');
    },
    searchDepot: function() {
        const query = (document.getElementById('depot-search').value || '').toLocaleUpperCase('tr-TR');
        const items = this.state.depot || [];
        const filtered = items.filter(d =>
            (d.name || '').toLocaleUpperCase('tr-TR').includes(query) ||
            (d.category || '').toLocaleUpperCase('tr-TR').includes(query) ||
            (d.description || '').toLocaleUpperCase('tr-TR').includes(query)
        );
        this.renderDepot(filtered);
    },
    filterDepot: function(cat) {
        this.state.depot_activeFilter = cat; 
        document.querySelectorAll('#depot-filters .btn-chip').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-dcat') === cat);
        });
        const items = this.state.depot || [];
        if (cat === 'ALL') {
            this.renderDepot(items);
        } else if (cat === 'ALERTS' || cat === 'CRITICAL') {
            const alerts = items.filter(d => (parseInt(d.current_stock) || 0) <= (parseInt(d.critical_stock) || 0));
            this.renderDepot(alerts);
        } else {
            // Tam esleme (Case-insensitive)
            const target = cat.toUpperCase().trim();
            this.renderDepot(items.filter(d => (d.category || "").toUpperCase().trim() === target));
        }
    },
    openAddDepotModal: function() {
        this.state.editingDepotOrigin = 'depot';
        document.getElementById('depot-add-form').reset();
        document.getElementById('depot-item-id').value = '';
        document.getElementById('depot-unit').value = 'Adet';
        document.getElementById('depot-saha').value = 0;
        document.getElementById('depot-is_faulty').value = 0;
        document.getElementById('depot-kayip').value = 0;
        document.getElementById('depot-asset-fields').style.display = 'none';
        
        const deleteBtn = document.getElementById('btn-depot-delete');
        if (deleteBtn) deleteBtn.style.display = 'none';
        
        document.getElementById('depot-add-modal').style.display = 'flex';
    },
    handleDepotCategoryChange: function(val) {
        val = val || document.getElementById('depot-category').value;
        const fields = document.getElementById('depot-asset-fields');
        if (!fields) return;
        // Varlık alanlarını göster/gizle (Asset vs Consumable)
        const isConsumable = ['SARF MALZEME', 'OFİS / GİDA', 'OFİS / GIDA'].includes(val.toUpperCase().trim());
        fields.style.display = 'block'; // Her zaman acık kalsın ama icerik degissin
        // Label'ları güncelle
        const labels = fields.querySelectorAll('label');
        if (labels.length >= 4) {
            labels[1].innerText = isConsumable ? 'GEÇEN HAFTA' : 'SAHADA';
            labels[2].innerText = isConsumable ? 'DAÄITILAN' : 'ARIZALI';
            labels[3].innerText = isConsumable ? 'KALAN' : 'KAYIP';
            // 3. inputu gizle (Gıda/Sarf için gereksiz dendi)
            const input3 = document.getElementById('depot-kayip');
            if (input3 && input3.parentElement) {
                input3.parentElement.style.display = isConsumable ? 'none' : 'block';
            }
        }
    },
    openEditDepotItem: function(id) {
        const item = this.state.depot.find(d => d.id == id);
        if (!item) return;
        this.state.editingDepotOrigin = item.table_origin || 'depot';
        
        const titleEl = document.getElementById('depot-add-modal-title') || document.getElementById('depot-modal-title');
        if(titleEl) titleEl.innerText = 'Ürün Düzenle';
        document.getElementById('depot-item-id').value = item.id;
        document.getElementById('depot-name').value = item.name || '';
        document.getElementById('depot-current').value = item.current_stock || 0;
        document.getElementById('depot-critical').value = item.critical_stock || 0;
        document.getElementById('depot-unit').value = item.unit || 'Adet';
        document.getElementById('depot-desc').value = item.description || '';
        document.getElementById('depot-saha').value = item.saha_count || item.field_stock || 0;
        document.getElementById('depot-is_faulty').value = item.arizali_count || item.faulty_stock || 0;
        document.getElementById('depot-kayip').value = item.kayip_count || item.lost_stock || 0;
        // Kategori seçimi (case-insensitive)
        const catSelect = document.getElementById('depot-category');
        const itemCat = (item.category || "").trim().toUpperCase();
        let found = false;
        for (let i = 0; i < catSelect.options.length; i++) {
            if (catSelect.options[i].value.trim().toUpperCase() === itemCat) {
                catSelect.selectedIndex = i;
                found = true;
                break;
            }
        }
        if(!found && item.category) {
             const opt = new Option(item.category, item.category);
             catSelect.add(opt);
             catSelect.value = item.category;
        }
        this.handleDepotCategoryChange(item.category);

        // Silme butonunu sadece adminlere ve duzenleme modunda goster
        const deleteBtn = document.getElementById('btn-depot-delete');
        const isAdmin = this.state.activeUser && this.state.activeUser.role === 'ADMIN';
        if (deleteBtn) deleteBtn.style.display = (id && isAdmin) ? 'block' : 'none';

        document.getElementById('depot-add-modal').style.display = 'flex';
    },
    syncDepotsFromExcel: async function() { // GHOST CODE REMOVED

        if(!confirm('DİKKAT: Veritabanındaki güncel warehouse bilgileri Excel üzerinden batan oluşturulacaktır. Onaylıyor musunuz?')) return;
        const btn = document.getElementById('btn-depot-sync');
        if(btn) { btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Aktüalize Ediliyor...'; btn.disabled = true; }
        try {
            const resp = await this.apiRequest('/depot/sync_from_excel', { method: 'POST' });
            const result = resp;
            if(result.error) throw new Error(result.error);
            this.showToast(result.message || 'Baarıyla aktarıldı');
            this.loadDepot();
            this.loadDashboardStats();
        } catch(e) {
            alert('Hata: ' + e.message);
        } finally {
            if(btn) { btn.innerHTML = '<i class="fas fa-file-excel"></i> Excel Aktüalize'; btn.disabled = false; }
        }
    },
    syncPrintersFromExcel: async function() {
        if(this.state.activeUser.role !== 'ADMIN') return alert('Sadece ADMIN bu ilemi yapabilir.');
        if(!confirm('DİKKAT: Yazıcı listesi yazıcılar.xlsx ile senkronize edilecek ve mevcut servis durumları Excel\'e kaydedilecektir. Onaylıyor musunuz?')) return;
        const btn = document.getElementById('btn-printer-sync');
        if(btn) { btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Eitleniyor...'; btn.disabled = true; }
        try {
            const resp = await this.apiRequest('/printers/sync_from_excel', { method: 'POST' });
            const result = resp;
            if(result.error) throw new Error(result.error);
            this.showToast(result.message || 'Baarıyla eitlendi');
            this.renderPrinters();
            this.loadDashboardStats();
        } catch(e) {
            alert('Hata: ' + e.message);
        } finally {
            if(btn) { btn.innerHTML = '<i class="fas fa-file-excel"></i> Excel Sync'; btn.disabled = false; }
        }
    },
    generateDepotWeeklyReport: async function() {
        try {
            this.showToast('Rapor hazırlanıyor...', 'info');
            const resp = await this.apiRequest('/depot/weekly_report');
            const data = resp;
            if(data.error) throw new Error(data.error);
            if(!data || !data.items) {
                throw new Error("Sunucudan rapor verisi boş veya hatalı döndü. (Lütfen arka plan uygulamanızı yeniden başlatın)");
            }
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            // Logo Ekleme (Opsiyonel - Eer tarayıcıda yüklüyse)
            try {
                const logoLeft = "logo/ht_left.png";
                doc.addImage(logoLeft, 'PNG', 10, 10, 30, 15);
                const logoRight = "logo/ht_right.png";
                doc.addImage(logoRight, 'PNG', 170, 10, 30, 15);
            } catch(e) { console.warn("Rapor logoları eklenemedi."); }
            doc.setFontSize(18);
            doc.setTextColor(40);
            doc.text("HAFTALIK DEPO ENVANTER RAPORU", 105, 25, null, null, "center");
            doc.setFontSize(10);
            const dateStr = new Date().toLocaleDateString('tr-TR');
            doc.text(`Rapor Tarihi: ${dateStr}`, 105, 32, null, null, "center");
            doc.line(10, 35, 200, 35);
            // 1. MEVCUT DURUM TABLOSU
            doc.setFontSize(12);
            doc.setTextColor(6, 182, 212); // Accent color
            doc.text("Mevcut Stok Durumu (Kritik ve Aktif rünler)", 14, 45);
            const tableRows = [];
            data.items.forEach(item => {
                if (item.current_stock <= item.critical_stock || item.current_stock > 0) {
                    tableRows.push([
                        this.fixTurkishForPDF(item.name || ''), 
                        this.fixTurkishForPDF(item.category || ''), 
                        `${item.current_stock} ${this.fixTurkishForPDF(item.unit)}`, 
                        item.critical_stock
                    ]);
                }
            });
            doc.autoTable({
                startY: 50,
                head: [['Urun Adi', 'Kategori', 'Mevcut Stok', 'Kritik Sinir']],
                body: tableRows,
                theme: 'striped',
                headStyles: { fillColor: [6, 182, 212] },
                styles: { fontSize: 9, cellPadding: 2 },
                columnStyles: {
                    0: { cellWidth: 80 }, 
                    1: { cellWidth: 45 }, 
                    2: { cellWidth: 35, halign: 'center' },
                    3: { cellWidth: 30, halign: 'center' }
                }
            });
            // 2. HAREKETLER TABLOSU
            let nextY = doc.lastAutoTable.finalY + 15;
            if (nextY > 250) { doc.addPage(); nextY = 20; }
            doc.setFontSize(12);
            doc.setTextColor(244, 63, 94); // Danger/Rose color
            doc.text("Son 7 Günlük Stok Hareketleri", 14, nextY);
            const transRows = [];
            data.transactions.forEach(t => {
                const tDate = new Date(t.created_at).toLocaleString('tr-TR');
                const ttype = t.transaction_type === 'in' ? 'Giri (+)' : 'ıkı (-)';
                transRows.push([
                    tDate, 
                    this.fixTurkishForPDF(t.item_category || ''), 
                    this.fixTurkishForPDF(t.item_name || ''), 
                    this.fixTurkishForPDF(ttype), 
                    t.quantity, 
                    this.fixTurkishForPDF(t.user_name || '')
                ]);
            });
            if(transRows.length === 0) {
                transRows.push([{content: 'Son 7 günde herhangi bir stok hareketi kaydedilmedi.', colSpan: 5, styles: {halign: 'center'}}]);
            }
            doc.autoTable({
                startY: nextY + 5,
                head: [['Tarih', 'Kategori', 'Urun Adi', 'Islem', 'Miktar', 'Personel']],
                body: transRows,
                theme: 'grid',
                headStyles: { fillColor: [244, 63, 94] },
                styles: { fontSize: 8, cellPadding: 2 },
                columnStyles: {
                    1: { cellWidth: 30 }, 
                    2: { cellWidth: 60 }  
                }
            });
            doc.save(`IT_Haftalik_Depo_Raporu_${dateStr.replace(/\./g,'_')}.pdf`);
            this.showToast('Haftalık rapor baarıyla indirildi.', 'success');
        } catch(e) {
            console.error(e);
            alert('Rapor oluşturulamadı! Hata detayı: ' + e.message);
        }
    },
    generateWeeklyInventoryReport: async function() {
        try {
            this.showToast('Haftalık envanter raporu hazırlanıyor...', 'info');
            const resp = await this.apiRequest('/inventory/weekly_location_report');
            const data = resp;
            if(!data || !data.success) {
                throw new Error((data && data.error) || "Sunucudan veri alınamadı.");
            }
            const items = data.items || [];
            if(items.length === 0) {
                alert('Son 7 günde mahal değişikliği yapılmış herhangi bir cihaz bulunmamaktadır.');
                this.showToast('Değişiklik bulunamadı.', 'warning');
                return;
            }

            const { jsPDF } = window.jspdf;
            const doc = new jsPDF('l', 'mm', 'a4'); // Landscape format is better for wide tables
            
            // Add Logos
            try {
                const logoLeft = "logo/ht_left.png";
                doc.addImage(logoLeft, 'PNG', 10, 10, 30, 15);
                const logoRight = "logo/ht_right.png";
                doc.addImage(logoRight, 'PNG', 255, 10, 30, 15);
            } catch(e) { console.warn("Rapor logoları eklenemedi."); }

            doc.setFontSize(18);
            doc.setTextColor(40);
            doc.text("HAFTALIK MAHAL DEGISIKLIGI ENVANTER RAPORU", 148, 22, null, null, "center");
            
            doc.setFontSize(10);
            const dateStr = new Date().toLocaleDateString('tr-TR');
            doc.text(`Rapor Tarihi: ${dateStr}  |  Son 7 Günlük Kayıtlar`, 148, 29, null, null, "center");
            doc.line(10, 32, 285, 32);

            const tableRows = [];
            items.forEach(item => {
                tableRows.push([
                    item.timestamp || '',
                    this.fixTurkishForPDF(item.device_type || ''),
                    this.fixTurkishForPDF(item.record_label || ''),
                    this.fixTurkishForPDF(item.old_value || ''),
                    this.fixTurkishForPDF(item.old_location_name || ''),
                    this.fixTurkishForPDF(item.new_value || ''),
                    this.fixTurkishForPDF(item.new_location_name || ''),
                    this.fixTurkishForPDF(item.display_name || item.changed_by || '')
                ]);
            });

            doc.autoTable({
                startY: 40,
                head: [['Tarih', 'Cihaz Tipi', 'Cihaz Adi/No', 'Eski Kod', 'Eski Mahal Adi', 'Yeni Kod', 'Yeni Mahal Adi', 'Degistiren']],
                body: tableRows,
                theme: 'striped',
                headStyles: { fillColor: [6, 182, 212] }, // Cyan accent
                styles: { fontSize: 8, cellPadding: 2 },
                columnStyles: {
                    0: { cellWidth: 32 }, // Date
                    1: { cellWidth: 28 }, // Type
                    2: { cellWidth: 28 }, // Label
                    3: { cellWidth: 20 }, // Old Code
                    4: { cellWidth: 55 }, // Old Name
                    5: { cellWidth: 20 }, // New Code
                    6: { cellWidth: 55 }, // New Name
                    7: { cellWidth: 32 }  // Changed by
                }
            });

            doc.save(`IT_Mahal_Degisiklikleri_Raporu_${dateStr.replace(/\./g,'_')}.pdf`);
            this.showToast('Haftalık envanter raporu başarıyla indirildi.', 'success');
        } catch(e) {
            console.error(e);
            alert('Rapor oluşturulamadı! Hata detayı: ' + e.message);
        }
    },
    saveDepotItem: async function() {
        const id = document.getElementById('depot-item-id').value;
        const cat = document.getElementById('depot-category').value;
        const name = document.getElementById('depot-name').value;
        if (!cat || !name) return alert('Kategori ve ürün adı gereklidir.');
        try {
            const url = id ? `${this.state.API_BASE}/depot/update/${id}` : `${this.state.API_BASE}/depot/add`;
            const method = id ? 'PUT' : 'POST';
            const resp = await this.apiRequest(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: cat,
                    name: name,
                    current_stock: parseInt(document.getElementById('depot-current').value) || 0,
                    critical_stock: parseInt(document.getElementById('depot-critical').value) || 5,
                    unit: document.getElementById('depot-unit').value || 'Adet',
                    description: document.getElementById('depot-desc').value || '',
                    field_stock: parseInt(document.getElementById('depot-saha').value) || 0,
                    faulty_stock: parseInt(document.getElementById('depot-is_faulty').value) || 0,
                    lost_stock: parseInt(document.getElementById('depot-kayip').value) || 0,
                    table_type: this.state.editingDepotOrigin || 'depot'
                })
            });
            const result = resp;
            if (result.error) throw new Error(result.error);
            document.getElementById('depot-add-modal').style.display = 'none';
            this.showToast(id ? 'Ürün başarıyla güncellendi!' : 'Ürün depoya eklendi!');
            await this.loadDepot();
            if (this.state.depot_activeFilter) {
                this.filterDepot(this.state.depot_activeFilter);
            }
            this.loadDashboardStats();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    deleteDepotItemFromModal: function() {
        const id = document.getElementById('depot-item-id').value;
        if (id) {
            this.deleteDepotItem(id);
            document.getElementById('depot-add-modal').style.display = 'none';
        }
    },
    openDepotTransaction: function(id, name, mode = 'in') {
        const item = this.state.depot.find(d => d.id == id);
        this.state.editingDepotOrigin = item ? (item.table_origin || 'depot') : 'depot';
        
        document.getElementById('depot-trans-title').innerText = `Stok İşlemi: ${name}`;
        document.getElementById('trans-item-id').value = id;
        document.getElementById('trans-quantity').value = 1;
        document.getElementById('trans-note').value = '';
        this.setTransType(mode);
        const sel = document.getElementById('trans-type-selection');
        if (sel) sel.style.display = mode ? 'none' : 'flex';
        document.getElementById('depot-transaction-modal').style.display = 'flex';
    },
    setTransType: function(type) {
        document.getElementById('trans-type').value = type;
        document.getElementById('trans-type-in').classList.toggle('active', type === 'in');
        document.getElementById('trans-type-out').classList.toggle('active', type === 'out');
        const reasonCont = document.getElementById('trans-reason-container');
        if (reasonCont) reasonCont.style.display = (type === 'out') ? 'block' : 'none';
    },
    executeDepotTransaction: async function() {
        const itemId = document.getElementById('trans-item-id').value;
        const qty = parseInt(document.getElementById('trans-quantity').value);
        const type = document.getElementById('trans-type').value;
        const reason = document.getElementById('trans-reason').value;
        let note = document.getElementById('trans-note').value;
        if (type === 'out' && reason) {
            note = `[${reason}] ${note}`;
        }
        if (!qty || qty <= 0) return alert('Geçerli bir miktar girin.');
        try {
            const resp = await this.apiRequest('/depot/transaction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    depot_item_id: parseInt(itemId),
                    type: type,
                    quantity: qty,
                    note: note,
                    user_name: this.state.activeUser.name,
                    user_id: this.state.activeUser.key,
                    table_type: this.state.editingDepotOrigin || 'depot'
                })
            });
            const result = resp;
            if (result.error) throw new Error(result.error);
            document.getElementById('depot-transaction-modal').style.display = 'none';
            this.showToast(`Stok ${type === 'in' ? 'girişi' : 'çıkışı'} yapıldı! Yeni stok: ${result.new_stock}`);
            await this.loadDepot();
            if (this.state.depot_activeFilter) {
                this.filterDepot(this.state.depot_activeFilter);
            }
            this.loadDashboardStats();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    openDepotAssign: function(id, name) {
        const item = this.state.depot.find(d => d.id == id);
        this.state.editingDepotOrigin = item ? (item.table_origin || 'depot') : 'depot';
        
        document.getElementById('depot-assign-title').innerText = `Cihaza Ata: ${name}`;
        document.getElementById('assign-item-id').value = id;
        document.getElementById('assign-quantity').value = 1;
        document.getElementById('assign-device-id').value = '';
        document.getElementById('depot-assign-modal').style.display = 'flex';
    },
    executeDepotAssign: async function() {
        const itemId = document.getElementById('assign-item-id').value;
        const qty = parseInt(document.getElementById('assign-quantity').value);
        const deviceId = document.getElementById('assign-device-id').value;
        const deviceType = document.getElementById('assign-device-type').value;
        if (!deviceId) return alert('Cihaz ID girin.');
        if (!qty || qty <= 0) return alert('Geçerli bir miktar girin.');
        try {
            const resp = await this.apiRequest('/depot/transaction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    depot_item_id: parseInt(itemId),
                    type: 'out',
                    quantity: qty,
                    device_id: parseInt(deviceId),
                    device_type: deviceType,
                    user_name: this.state.activeUser.name,
                    user_id: this.state.activeUser.key,
                    note: `Cihaz ${deviceType.toUpperCase()}-${deviceId} için atandı`,
                    table_type: this.state.editingDepotOrigin || 'depot'
                })
            });
            const result = resp;
            if (result.error) throw new Error(result.error);
            document.getElementById('depot-assign-modal').style.display = 'none';
            this.showToast(`Malzeme cihaza atandı ve teknik not oluşturuldu!`);
            await this.loadDepot();
            if (this.state.depot_activeFilter) {
                this.filterDepot(this.state.depot_activeFilter);
            }
            this.loadDashboardStats();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    deleteDepotItem: async function(id) {
        const item = this.state.depot.find(d => d.id == id);
        const origin = item ? (item.table_origin || 'depot') : 'depot';
        if (!confirm('Bu ürünü silmek istediğinize emin misiniz?')) return;
        try {
            const resp = await this.apiRequest(`/depot/delete/${id}?table_type=${origin}`, { method: 'DELETE' });
            const result = resp;
            if (result.error) throw new Error(result.error);
            this.showToast('Ürün silindi.');
            this.loadDepot();
            this.loadDashboardStats();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    deleteDepotItem: async function(id) {
        if (!confirm('Bu ürünü silmek istediinize emin misiniz?')) return;
        try {
            const resp = await this.apiRequest(`/depot/delete/${id}?table_type=${this.state.currentDepotTab}`, { method: 'DELETE' });
            const result = resp;
            if (result.error) throw new Error(result.error);
            this.showToast('rün silindi.');
            this.loadDepot();
            this.loadDashboardStats();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    // 
    //  DEVICE DETAIL & EDIT MODAL
    // 
    openDeviceDetail: async function(id, type, deviceClass) {
        try {
            // Herkes detayları görebilsin (VIEWER dahil)
        this.state.editingId = id;
        this.state.editingType = type;
        this.state.editingDeviceClass = deviceClass || null;
        // Find item data
        let item = null;
        if (type === 'pc') {
            item = this.state.inventory.find(i => i.id == id);
            if (item && !item.tower && item.location_code && item.location_code.includes('.')) item.tower = item.location_code.split('.')[0];
            if (item && !item.floor && item.location_code && item.location_code.includes('.')) item.floor = item.location_code.split('.')[1];
        } else if (type === 'pr') {
            // device_class ile filtreleyerek ID çakışmasını önle
            if (deviceClass === 'MONITOR') {
                item = (this.state.inventory || []).find(p => p.id == id && p.device_class === deviceClass);
            } else if (deviceClass) {
                item = (this.state.printers || []).find(p => p.id == id && p.device_class === deviceClass);
            }
            if (!item && deviceClass !== 'MONITOR') {
                item = (this.state.printers || []).find(p => p.id == id);
            }
        }
        if (!item) {
            alert('Cihaz bulunamadı (ID: ' + id + ')');
            return;
        }
        // Set title
        const title = document.getElementById('device-detail-title');
        if (type === 'pc') {
            let pcLabel = `ID: ${id}`;
            if (item.pc_no) {
                const pcStr = item.pc_no.toString().trim();
                const isNum = !isNaN(pcStr) && pcStr !== '' && pcStr !== '---';
                if (isNum) pcLabel = `PC-${pcStr.padStart(3, '0')}`;
                else pcLabel = pcStr.toUpperCase();
            }
            title.innerText = `${pcLabel} Detay`;
        } else {
            if (deviceClass === 'MONITOR') {
                title.innerText = `Monitör: ${item.pr_no || item.name || 'Detay'}`;
            } else {
                title.innerText = `Yazıcı: ${item.pr_no || item.model || 'Detay'}`;
            }
        }
        // Load edit form
        this.loadEditForm(item, type);
        // Render History Button (Image references "Düzenleme geçmii")
        const historyBtn = document.getElementById('btn-show-history');
        if (historyBtn) {
            historyBtn.onclick = () => this.openHistoryModal(id, type);
        }
            // İlk veri durumunu kaydet (Deiiklik kontrolü için)
            setTimeout(() => {
                this.state.initialFormData = this.getFormState();
            }, 100);
            document.getElementById('device-detail-modal').style.display = 'flex';
        } catch (e) {
            console.error("openDeviceDetail hatası:", e);
            this.showToast("Cihaz detayı açılamadı: " + e.message, 'error');
        }
    },
    fetchKeyOSData: async function(serial) {
        try {
            const resp = await this.apiRequest('/keyos/check/' + serial);
            const data = resp;
            if (data.success) {
                // UI'daki alanları güncelle (Eer bo ise doldur veya karılatır)
                const ipInput = document.getElementById('edit-ip');
                const printersInput = document.getElementById('edit-bagli_yazicilar');
                const hostnameInput = document.getElementById('edit-hostname');
                if (ipInput && !ipInput.value) ipInput.value = data.ip || '';
                if (printersInput) printersInput.value = data.printers || '';
                // Hostname uyumazlıını vurgula
                if (hostnameInput && data.hostname) {
                    const invHostname = (hostnameInput.value || '').trim().toUpperCase();
                    const keyosHostname = (data.hostname || '').trim().toUpperCase();
                    if (invHostname !== keyosHostname) {
                        hostnameInput.style.color = '#ff4b2b';
                        hostnameInput.title = `KeyOS Hostname: ${data.hostname}`;
                        this.showToast(`Uyarı: Hostname uyumazlıı! KeyOS: ${data.hostname}`, 'warning');
                    } else {
                        hostnameInput.style.color = 'var(--accent)';
                        hostnameInput.title = '';
                    }
                }
            }
        } catch (e) { console.warn("KeyOS verisi çekilemedi:", e); }
    },
    openHistoryModal: async function(id, type) {
        const modal = document.getElementById('history-modal');
        const list = document.getElementById('history-list');
        if (!modal || !list) return;
        modal.style.display = 'flex';
        list.innerHTML = '<div style="text-align:center; padding:50px;"><i class="fas fa-spinner fa-spin fa-2x"></i><br>Geçmi yükleniyor...</div>';
        try {
            let table = 'pcs';
            if (this.state.invCategory === 'TABLET') table = 'tablets';
            if (this.state.invCategory === 'MONITOR') table = 'monitors';
            if (type !== 'pc') table = type;
            const resp = await this.apiRequest(`/logs/get_record_history/${table}/${id}`);
            const logs = resp;
            if (!logs.length) {
                list.innerHTML = '<div style="text-align:center; padding:50px; opacity:0.5;">Bu cihaz için henüz bir deiiklik kaydı bulunmuyor.</div>';
                return;
            }
            // Group by date and user to simulate the visual in Image 1
            list.innerHTML = logs.map(l => {
                const date = new Date(l.created_at).toLocaleString('tr-TR');
                return `
                <div class="history-item fade-in">
                    <div class="history-user-info">
                        <div class="history-avatar">${l.display_name ? l.display_name[0].toUpperCase() : 'U'}</div>
                        <div class="history-meta">
                            <span class="history-username">${l.display_name || 'Bilinmeyen Kullanıcı'}</span>
                            <span class="history-date">${date}</span>
                        </div>
                    </div>
                    <div class="history-change">
                        <span class="history-field">${l.field_name.toUpperCase()}:</span>
                        ${(!l.old_value || l.old_value === 'None') ? 
                            `<span class="history-new">Eklendi: "${l.new_value}"</span>` : 
                            ((!l.new_value || l.new_value === 'None') ? 
                                `<span class="history-old">Silindi: "${l.old_value}"</span>` :
                                `<span class="history-old">${l.old_value}</span> <i class="fas fa-arrow-right" style="font-size:0.7rem; opacity:0.3;"></i> <span class="history-new">${l.new_value}</span>`
                            )
                        }
                    </div>
                </div>`;
            }).join('');
        } catch (e) {
            list.innerHTML = '<div style="color:#ff4b2b; text-align:center; padding:20px;">Geçmi yüklenemedi.</div>';
        }
    },
    closeDeviceDetail: function() {
        document.getElementById('device-detail-modal').style.display = 'none';
        this.state.editingId = null;
        this.state.editingType = null;
        this.state.initialFormData = null;
    },
    getFormState: function() {
        const state = {};
        const container = document.getElementById('edit-form-content');
        if (!container) return state;
        const inputs = container.querySelectorAll('input, textarea');
        inputs.forEach(el => {
            if (el.type === 'checkbox' || el.type === 'radio') {
                if (el.checked) state[el.id || el.name] = el.value || 'checked';
            } else {
                state[el.id] = el.value;
            }
        });
        return JSON.stringify(state);
    },
    closeDeviceDetailWithCheck: function(event) {
        // Eer dıarı tıklandıysa kontrol et
        if (event && event.target.id !== 'device-detail-modal') return;
        const currentState = this.getFormState();
        if (this.state.initialFormData && this.state.initialFormData !== currentState) {
            const save = confirm("Deiiklik yaptınız. Kaydetmek istiyor musunuz?\n\n[Tamam]: Kaydet ve Kapat\n[İptal]: Kaydetmeden Kapat");
            if (save) {
                this.saveEdit();
                return;
            }
        }
        this.closeDeviceDetail();
    },
    openNotesModal: function(id, type) {
        this.state.editingId = id;
        this.state.editingType = type;
        document.getElementById('device-notes-title').innerHTML = `<i class="fas fa-clock-rotate-left"></i> ${type.toUpperCase()}-${id} Notları`;
        this.loadNotes(id, type);
        document.getElementById('device-notes-modal').style.display = 'flex';
    },
    closeNotesModal: function() {
        document.getElementById('device-notes-modal').style.display = 'none';
        this.state.editingId = null;
        this.state.editingType = null;
    },
    loadEditForm: function(item, type) {
        const container = document.getElementById('edit-form-content');
        if (!container) return;
        const isAdmin = this.state.activeUser && this.state.activeUser.role === 'ADMIN';
        if (type === 'pc') {
            const devType = (item.device_type || 'PC').toUpperCase();
            if (devType === 'TABLET') {
                container.innerHTML = `
                <div class="edit-form-grid" style="gap: 12px; padding: 0;">
                    <!-- Row 1: Cihaz No, Mahal, Adi -->
                    <div class="form-row form-row-3">
                        <div class="form-group">
                            <label>CİHAZ NO (Örn: 1, 2)</label>
                            <input type="search" class="search-bar" id="edit-pc_no" value="${item.pc_no || ''}">
                        </div>
                        <div class="form-group">
                            <label>MAHAL KODU</label>
                            <input type="search" class="search-bar" id="edit-location_code" value="${item.location_code || ''}" list="mahal-datalist" onchange="app.handleMahalSelection(this.value, 'code')">
                        </div>
                        <div class="form-group">
                            <label>MAHAL ADI</label>
                            <input type="search" class="search-bar" id="edit-location_name" value="${item.location_name || ''}" list="mahal-name-datalist" onchange="app.handleMahalSelection(this.value, 'name')">
                        </div>
                    </div>
                    <!-- Row 2: Kule/Kat -->
                    <div class="form-row form-row-2">
                        <div class="form-group" style="display:none;">
                            <label>KULE / KAT</label>
                            <div class="flex-row gap-2">
                                <input type="search" class="search-bar" id="edit-tower" value="${item.tower || ''}" style="flex:1; opacity:0.6;" readonly>
                                <input type="search" class="search-bar" id="edit-floor" value="${item.floor || ''}" style="flex:1; opacity:0.6;" readonly>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>IP ADRESİ</label>
                            <input type="search" class="search-bar" id="edit-ip" value="${item.ip || ''}">
                        </div>
                    </div>
                    <!-- Row 3: MAC & Telefon -->
                    <div class="form-row form-row-2">
                        <div class="form-group">
                            <label>MAC ADRESİ</label>
                            <input type="search" class="search-bar" id="edit-mac" value="${item.mac || ''}">
                        </div>
                        <div class="form-group">
                            <label>TELEFON (Tablet)</label>
                            <input type="search" class="search-bar" id="edit-phone" value="${item.phone || ''}">
                        </div>
                    </div>
                    <!-- Row 4: Zimmet & Unvan -->
                    <div class="form-row form-row-2">
                        <div class="form-group">
                            <label>ZİMMETLENEN KİÅİ / SORUMLU</label>
                            <input type="search" class="search-bar" id="edit-assigned_to" value="${item.assigned_to || ''}">
                        </div>
                        <div class="form-group">
                            <label>UNVAN</label>
                            <input type="search" class="search-bar" id="edit-title" value="${item.title || ''}">
                        </div>
                    </div>
                    <!-- Row 5: Birim & Açıklama -->
                    <div class="form-row form-row-2">
                        <div class="form-group">
                            <label>BİRİM</label>
                            <input type="search" class="search-bar" id="edit-unit" value="${item.unit || ''}">
                        </div>
                        <div class="form-group">
                            <label>AÇIKLAMA NOTU (Kısa)</label>
                            <input type="search" class="search-bar" id="edit-aciklama_short" value="" placeholder="Kısa not...">
                        </div>
                    </div>
                    <!-- Status Checkboxes -->
                    <div class="flex-column gap-2" style="border-top:1px solid rgba(255,255,255,0.05); padding-top:10px;">
                        <div class="flex-row gap-2" style="align-items:center; flex-wrap:wrap;">
                            <label class="check-container" style="font-size:0.7rem;">Sahada
                                <input type="checkbox" id="edit-on_field" ${this.isTrue(item.on_field) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-on_field')">
                                <span class="checkmark"></span>
                            </label>
                            <label class="check-container" style="font-size:0.7rem;">Depoda
                                <input type="checkbox" id="edit-warehouse" ${this.isTrue(item.warehouse) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-warehouse')">
                                <span class="checkmark"></span>
                            </label>
                            <label class="check-container" style="font-size:0.7rem;">Arızalı
                                <input type="checkbox" id="edit-is_faulty" ${this.isTrue(item.is_faulty) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-is_faulty')">
                                <span class="checkmark"></span>
                            </label>
                            <label class="check-container" style="font-size:0.7rem;">Kayıp
                                <input type="checkbox" id="edit-without_location" ${this.isTrue(item.without_location) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-without_location')">
                                <span class="checkmark"></span>
                            </label>

                        </div>
                    </div>
                </div>
                ${this.loadEditFormFooter('pc')}`;
            } else if (devType === 'SIRAMATIK' || devType === 'KIOSK') {
                container.innerHTML = `
                <div class="edit-form-grid" style="gap: 12px; padding: 0;">
                    <!-- Row 1: Cihaz No, Mahal, Adi -->
                    <div class="form-row form-row-3">
                        <div class="form-group">
                            <label>CİHAZ NO (Örn: 1, 2)</label>
                            <input type="search" class="search-bar" id="edit-pc_no" value="${item.pc_no || ''}">
                        </div>
                        <div class="form-group">
                            <label>MAHAL KODU</label>
                            <input type="search" class="search-bar" id="edit-location_code" value="${item.location_code || ''}" list="mahal-datalist" onchange="app.handleMahalSelection(this.value, 'code')">
                        </div>
                        <div class="form-group">
                            <label>MAHAL ADI</label>
                            <input type="search" class="search-bar" id="edit-location_name" value="${item.location_name || ''}" list="mahal-name-datalist" onchange="app.handleMahalSelection(this.value, 'name')">
                        </div>
                    </div>
                    <!-- Row 2: Kule/Kat -->
                    <div class="form-row form-row-2">
                        <div class="form-group" style="display:none;">
                            <label>KULE / KAT</label>
                            <div class="flex-row gap-2">
                                <input type="search" class="search-bar" id="edit-tower" value="${item.tower || ''}" style="flex:1; opacity:0.6;" readonly>
                                <input type="search" class="search-bar" id="edit-floor" value="${item.floor || ''}" style="flex:1; opacity:0.6;" readonly>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>IP ADRESİ</label>
                            <input type="search" class="search-bar" id="edit-ip" value="${item.ip || ''}">
                        </div>
                    </div>
                    <!-- Row 3: MAC & Seri No -->
                    <div class="form-row form-row-2">
                        <div class="form-group">
                            <label>MAC ADRESİ</label>
                            <input type="search" class="search-bar" id="edit-mac" value="${item.mac || ''}">
                        </div>
                        <div class="form-group">
                            <label>SERİ NO</label>
                            <input type="search" class="search-bar" id="edit-serial_no" value="${item.seri || item.serial_no || item.serial || ''}">
                        </div>
                    </div>
                    <!-- Status Checkboxes -->
                    <div class="flex-column gap-2" style="border-top:1px solid rgba(255,255,255,0.05); padding-top:10px;">
                        <div class="flex-row gap-2" style="align-items:center; flex-wrap:wrap;">
                            <label class="check-container" style="font-size:0.7rem;">Sahada
                                <input type="checkbox" id="edit-on_field" ${this.isTrue(item.on_field) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-on_field')">
                                <span class="checkmark"></span>
                            </label>
                            <label class="check-container" style="font-size:0.7rem;">Depoda
                                <input type="checkbox" id="edit-warehouse" ${this.isTrue(item.warehouse) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-warehouse')">
                                <span class="checkmark"></span>
                            </label>
                            <label class="check-container" style="font-size:0.7rem;">Arızalı
                                <input type="checkbox" id="edit-is_faulty" ${this.isTrue(item.is_faulty) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-is_faulty')">
                                <span class="checkmark"></span>
                            </label>

                        </div>
                    </div>
                </div>
                ${this.loadEditFormFooter('pc')}`;
            } else {
                                // DEFAULT PC
                container.innerHTML = `
                <div class="edit-form-grid" style="gap: 12px; padding: 0;">
                    <!-- Row 1: Mahal Kodu, Mahal Adi, Hostname -->
                    <div class="form-row form-row-3">
                        <div class="form-group">
                            <label>MAHAL KODU</label>
                            <input type="search" class="search-bar" id="edit-location_code" value="${item.location_code || ''}" list="mahal-datalist" onchange="app.handleMahalSelection(this.value, 'code')">
                        </div>
                        <div class="form-group">
                            <label>MAHAL ADI</label>
                            <input type="search" class="search-bar" id="edit-location_name" value="${item.location_name || ''}" readonly style="background:rgba(255,255,255,0.02); color:#64748b;">
                        </div>
                        <div class="form-group">
                            <label>HOSTNAME</label>
                            <input type="search" class="search-bar" id="edit-hostname" value="${item.hostname || ''}" readonly style="background:rgba(255,255,255,0.02); color:var(--accent); font-weight:700;">
                        </div>
                    </div>

                    <!-- Row 3: IP, PC Seri, Yazıcılar -->
                    <div class="form-row form-row-3">
                        <div class="form-group">
                            <label>IP ADRESİ</label>
                            <input type="search" class="search-bar" id="edit-ip" value="${item.ip || ''}" readonly style="background:rgba(255,255,255,0.02); color:#64748b;">
                        </div>
                        <div class="form-group">
                            <label>PC SERİ NO</label>
                            <input type="search" class="search-bar" id="edit-pc_serial" value="${item.pc_serial || ''}" readonly style="background:rgba(255,255,255,0.02); color:#64748b;">
                        </div>
                        <div class="form-group">
                            <label>BAÄLI YAZICILAR</label>
                            <input type="search" class="search-bar" id="edit-bagli_yazicilar" value="${item.bagli_yazicilar || ''}" readonly style="background:rgba(255,255,255,0.02); color:#64748b;">
                        </div>
                    </div>
                    <!-- Row 4: Barkod, Tarayıcı -->
                    <div class="form-row form-row-3">
                        <div class="form-group">
                            <label>BARKOD YAZICI SERİ</label>
                            <input type="search" class="search-bar" id="edit-by_seri" list="by-seri-datalist" value="${item.by_seri || ''}">
                        </div>
                        <div class="form-group">
                            <label>BARKOD OKUYUCU SERİ</label>
                            <input type="search" class="search-bar" id="edit-bo_seri" list="bo-seri-datalist" value="${item.bo_seri || ''}">
                        </div>
                        <div class="form-group">
                            <label>TARAYICI SERİ NO</label>
                            <input type="search" class="search-bar" id="edit-tarayici_seri" list="tr-seri-datalist" value="${item.tarayici_seri || ''}">
                        </div>
                    </div>
                    <!-- Row 5: Monitor & Monitor2 -->
                    <div class="form-row form-row-2">
                        <div class="form-group">
                            <label>MONİTÖR SERİ</label>
                            <input type="search" class="search-bar" id="edit-monitor_seri" list="mo-seri-datalist" value="${item.monitor_seri || ''}">
                        </div>
                        <div class="form-group">
                            <label>2. MONİTÖR SERİ</label>
                            <input type="search" class="search-bar" id="edit-monitor2_seri" list="mo-seri-datalist" value="${item.monitor2_seri || ''}">
                        </div>
                    </div>
                    <!-- Row 6: Açıklama -->
                    <div class="form-group">
                        <label>AÇIKLAMA</label>
                        <textarea class="search-bar" id="edit-description" style="min-height:80px; height:80px; resize:none; width:100%; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.02); color:#fff; border-radius:4px; padding:8px;">${item.description || ''}</textarea>
                    </div>
                    <div id="duplicate-warning" style="display:none; color:#ff4b2b; font-size:0.7rem; font-weight:700; background:rgba(255,75,43,0.1); padding:5px 10px; border-radius:4px; text-align:center; margin-top:5px;">
                        <i class="fas fa-exclamation-triangle"></i> DİKKAT: <span id="duplicate-warning-text"></span>
                    </div>
                    <!-- Bottom Status Bar -->
                    <div class="flex-column gap-2" style="border-top:1px solid rgba(255,255,255,0.05); padding-top:10px;">
                        <div class="flex-row gap-2" style="align-items:center; flex-wrap:wrap;">
                            <label class="check-container" style="font-size:0.7rem;">Sahada
                                <input type="checkbox" id="edit-on_field" ${this.isTrue(item.on_field) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-on_field')">
                                <span class="checkmark"></span>
                            </label>
                            <label class="check-container" style="font-size:0.7rem;">Depoda
                                <input type="checkbox" id="edit-warehouse" ${this.isTrue(item.warehouse) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-warehouse')">
                                <span class="checkmark"></span>
                            </label>
                            <label class="check-container" style="font-size:0.7rem;">Arızalı
                                <input type="checkbox" id="edit-is_faulty" ${this.isTrue(item.is_faulty) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-is_faulty')">
                                <span class="checkmark"></span>
                            </label>
                            <label class="check-container" style="font-size:0.7rem;">Kayıp
                                <input type="checkbox" id="edit-without_location" ${this.isTrue(item.without_location) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-without_location')">
                                <span class="checkmark"></span>
                            </label>
                            <label class="check-container" style="font-size:0.7rem; color:var(--accent); font-weight:700;">KURULUM BEKLİYOR
                                <input type="checkbox" id="edit-pending_installation" ${item.pending_installation === 1 ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-pending_installation')">
                                <span class="checkmark"></span>
                            </label>
                        </div>
                        <div class="flex-row gap-2" style="justify-content: flex-start; align-items:center;">
                             <label class="check-container" style="font-size:0.75rem;">Windows
                                <input type="checkbox" id="edit-windows" ${this.isTrue(item.windows) ? 'checked' : ''} onclick="app.handleExclusiveCheck('os', 'edit-windows')">
                                <span class="checkmark"></span>
                            </label>
                             <label class="check-container" style="font-size:0.75rem;">Keyos
                                <input type="checkbox" id="edit-keyos" ${this.isTrue(item.keyos) ? 'checked' : ''} onclick="app.handleExclusiveCheck('os', 'edit-keyos'); app.handleKeyOSChange();">
                                <span class="checkmark"></span>
                            </label>
                            <div id="rdp-wrapper" style="opacity: ${this.isTrue(item.keyos) ? '1' : '0.3'}; pointer-events: ${this.isTrue(item.keyos) ? 'auto' : 'none'}; border-left: 1px solid rgba(255,255,255,0.1); padding-left: 10px; margin-left: 5px;">
                                <label class="check-container" style="font-size:0.75rem; color:#facc15;">RDP
                                    <input type="checkbox" id="edit-rdp" ${this.isTrue(item.rdp) ? 'checked' : ''} ${this.isTrue(item.keyos) ? '' : 'disabled'} onchange="app.handleRDPChange()">
                                    <span class="checkmark" style="border-color:#facc15;"></span>
                                </label>
                                <div id="rdp-details" style="display: ${this.isTrue(item.rdp) ? 'flex' : 'none'}; flex-direction: column; gap: 5px; margin-top: 5px;">
                                    <input type="search" id="edit-rdp_address" class="search-bar" placeholder="RDP Adresi (IP/Hostname)" value="${item.rdp_address || ''}" style="padding: 4px; font-size: 0.75rem;">
                                    <input type="search" id="edit-rdp_reason" class="search-bar" placeholder="RDP AYlma Nedeni" value="${item.rdp_reason || ''}" style="padding: 4px; font-size: 0.75rem;">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                ${this.loadEditFormFooter('pc')}`;
            }
        } else {
            const dClass = item.device_class || 'PRINTER';
            const isPrinter = dClass === 'PRINTER';
            const isSpecial = dClass === 'BARCODE_PRINTER' || dClass === 'BARCODE_READER' || dClass === 'SCANNER' || dClass === 'MONITOR';
            
            const idLabel = isPrinter ? 'PR NUMARASI' : (dClass === 'MONITOR' ? 'ETİKET / İSİM' : 'CİHAZ ADI (NAME)');
            const modelLabel = 'MODEL';
            const mahalLabel = isSpecial ? 'BAÄLI OLDUÄU PC (MAHAL)' : (isPrinter ? 'MAHAL ADI / KODU' : 'MAHAL');
            const ipLabel = isSpecial ? 'BAĞLI OLDUĞU PC NO' : 'IP ADRESİ';

            let initialSpecialIp = isSpecial ? (item.pc_no || item.location_code || '') : (item.ip || '');
            let initialSpecialMahal = item.location_code || '';
            if (isSpecial && initialSpecialIp) {
                const pcs = (this.state.inventoryCache && this.state.inventoryCache['PC']) || [];
                const searchNo = initialSpecialIp.toUpperCase();
                const pc = pcs.find(i => {
                    const pcNo = (i.pc_no || "").toString().toUpperCase();
                    return pcNo === searchNo || `PC-${pcNo.padStart(3, '0')}` === searchNo || pcNo === searchNo.replace('PC-', '');
                });
                if (pc) {
                    initialSpecialMahal = pc.location_code || pc.location_code || pc.mahal || pc.location_name || initialSpecialMahal;
                }
            }

            container.innerHTML = `
                <div class="edit-form-grid">
                    <div class="form-row form-row-2">
                        <div class="form-group">
                            <label>${idLabel}</label>
                            <input type="search" class="search-bar" id="edit-pr_no" value="${item.pr_no || item.name || ''}" ${dClass === 'MONITOR' ? '' : 'readonly style="background:rgba(255,255,255,0.02); color:#64748b;"'}>
                        </div>
                        <div class="form-group">
                            <label>${modelLabel}</label>
                            <input type="search" class="search-bar" id="edit-model" value="${item.model || ''}" readonly style="background:rgba(255,255,255,0.02); color:#64748b;">
                        </div>
                    </div>
                    <!-- 2. Satır: MAHAL VE IP -->
                    <div class="form-row form-row-2">
                        <div class="form-group">
                            <label>${mahalLabel}</label>
                            <input type="search" class="search-bar" id="edit-mahal" value="${isSpecial ? initialSpecialMahal : (item.mahal || item.location_code || '')}" ${(isSpecial && dClass !== 'MONITOR') ? 'readonly style="background:rgba(255,255,255,0.02); color:#64748b;"' : (dClass === 'MONITOR' && isSpecial) ? 'list="mahal-datalist" placeholder="Mahal Kodu veya PC-XXX"' : ''}>
                        </div>
                        <div class="form-group">
                            <label>${ipLabel}</label>
                            <input type="search" class="search-bar" id="edit-ip" value="${initialSpecialIp}" ${isSpecial ? 'list="pc-no-datalist" placeholder="PC-XXX Seçiniz"' : 'readonly style="background:rgba(255,255,255,0.02); color:#64748b;"'} oninput="${isSpecial ? 'app.autoUpdateSpecialMahal(this.value)' : ''}">
                        </div>
                    </div>
                    <!-- 3. Satır: SERİ VE MAC -->
                    <div class="form-row form-row-2">
                        <div class="form-group">
                            <label>SERİ NO</label>
                            <input type="search" class="search-bar" id="edit-seri" value="${item.seri || item.serial_no || item.serial || ''}" readonly style="background:rgba(255,255,255,0.02); color:#64748b;">
                        </div>
                        ${(!isSpecial) ? `
                        <div class="form-group">
                            <label>MAC ADRESİ</label>
                            <input type="search" class="search-bar" id="edit-mac" value="${item.mac || ''}" readonly style="background:rgba(255,255,255,0.02); color:#64748b;">
                        </div>
                        ` : (dClass === 'MONITOR' ? `
                        <div class="form-group">
                            <label>MONİTÖR TİPİ</label>
                            <div class="flex-row gap-2 mt-2">
                                <label class="check-container" style="flex:1">1. Monitör
                                    <input type="radio" name="monitor-type" value="1" ${item.monitor_type == '1' || item.monitor_type === '1. Monitör' || !item.monitor_type ? 'checked' : ''}>
                                    <span class="checkmark" style="border-radius:50%;"></span>
                                </label>
                                <label class="check-container" style="flex:1">2. Monitör
                                    <input type="radio" name="monitor-type" value="2" ${item.monitor_type == '2' || item.monitor_type === '2. Monitör' ? 'checked' : ''}>
                                    <span class="checkmark" style="border-radius:50%;"></span>
                                </label>
                            </div>
                        </div>
                        ` : '')}
                    </div>

                    <div class="form-group mt-2">
                        <label>Durum</label>
                        <div class="flex-row gap-2">
                            ${(() => {
                                let isKurulu = false, isArizali = false, isDepoda = false, isServiste = false, isKayip = false;
                                if (['MONITOR', 'BARCODE_PRINTER', 'BARCODE_READER', 'SCANNER'].includes(dClass)) {
                                    isKurulu = this.isTrue(item.on_field);
                                    isArizali = this.isTrue(item.is_faulty);
                                    isDepoda = this.isTrue(item.warehouse);
                                    isKayip = this.isTrue(item.without_location);
                                    if (!isKurulu && !isArizali && !isDepoda && !isKayip) isKurulu = true;
                                } else {
                                    const st = (item.status || '').toUpperCase();
                                    isKurulu = (!st || st === 'KURULU');
                                    isArizali = (st === 'ARIZALI');
                                    isDepoda = (st === 'DEPODA');
                                    isServiste = (st === 'SERVİSTE' || st === 'SERVISTE');
                                    isKayip = (st === 'KAYIP');
                                }
                                return `
                            <label class="check-container" style="flex:1">Kurulu
                                <input type="radio" name="printer-status" id="edit-status-kurulu" ${isKurulu ? 'checked' : ''} value="Kurulu">
                                <span class="checkmark" style="border-radius:50%;"></span>
                            </label>
                            <label class="check-container" style="flex:1">Arızalı
                                <input type="radio" name="printer-status" id="edit-status-is_faulty" ${isArizali ? 'checked' : ''} value="Arızalı">
                                <span class="checkmark" style="border-radius:50%;"></span>
                            </label>
                            <label class="check-container" style="flex:1">Depoda
                                <input type="radio" name="printer-status" id="edit-status-warehouse" ${isDepoda ? 'checked' : ''} value="Depoda">
                                <span class="checkmark" style="border-radius:50%;"></span>
                            </label>
                            ${isPrinter ? `
                            <label class="check-container" style="flex:1">Serviste
                                <input type="radio" name="printer-status" id="edit-status-serviste" ${isServiste ? 'checked' : ''} value="Serviste">
                                <span class="checkmark" style="border-radius:50%;"></span>
                            </label>` : ''}
                            <label class="check-container" style="flex:1">Kayıp
                                <input type="radio" name="printer-status" id="edit-status-kayip" ${isKayip ? 'checked' : ''} value="Kayıp">
                                <span class="checkmark" style="border-radius:50%;"></span>
                            </label>
                                `;
                            })()}
                        </div>
                    </div>
                </div>
                </div>
                ${this.loadEditFormFooter('pr')}`;
        }
    },
    autoUpdateSpecialMahal: function(pcNo) {
        if (!pcNo || pcNo.length < 1) return;
        const pcs = (this.state.inventoryCache && this.state.inventoryCache['PC']) || [];
        const s = pcNo.toUpperCase();
        const pc = pcs.find(i => {
            const p = (i.pc_no || "").toString().toUpperCase();
            return p === s || `PC-${p.padStart(3, '0')}` === s || p === s.replace('PC-', '');
        });
        if (pc) {
            const mahalEl = document.getElementById('edit-mahal');
            if (mahalEl) mahalEl.value = pc.location_code || pc.location_name || pc.mahal || '';
        }
    },
    handleMahalSelection: function(val, triggerType) {
        let info = null;
        let code = val;
        if (triggerType === 'name') {
            // İsime göre kodu bul
            for (const [k, v] of Object.entries(this.state.mahalMap)) {
                if (v.name === val) {
                    info = v;
                    code = k;
                    break;
                }
            }
        } else {
            // Koda göre ismi bul
            info = this.state.mahalMap[val];
        }
        if (!info) return;
        const setVal = (id, val) => {
            const editEl = document.getElementById('edit-' + id);
            if (editEl && editEl.offsetParent !== null) editEl.value = val;
            const addEl = document.getElementById('add-' + id);
            if (addEl && addEl.offsetParent !== null) addEl.value = val;
        };
        setVal('location_code', code);
        setVal('location_name', info.name);
        setVal('tower', info.tower);
        setVal('floor', info.floor);
        setVal('phone_number', info.phone);
    },
    handleAddExclusiveCheck: function(currentId) {
        const list = ['add-on_field', 'add-warehouse', 'add-is_faulty'];
        const currentEl = document.getElementById(currentId);
        if (!currentEl || !currentEl.checked) return;
        list.forEach(item => {
            const el = document.getElementById(item);
            if (el && item !== currentId) el.checked = false;
        });
    },
    handleExclusiveCheck: function(group, currentId) {
        let targets = [];
        if (group === 'status') {
            targets = ['edit-on_field', 'edit-warehouse', 'edit-is_faulty', 'edit-without_location'];
        } else if (group === 'os') {
            targets = ['edit-windows', 'edit-keyos'];
        }
        const currentEl = document.getElementById(currentId);
        if (!currentEl || !currentEl.checked) return;
        targets.forEach(id => {
            if (id !== currentId) {
                const el = document.getElementById(id);
                if (el) el.checked = false;
            }
        });
    },
    handleKeyOSChange: function() {
        const checkKeyOS = document.getElementById('edit-keyos');
        const rdpWrapper = document.getElementById('rdp-wrapper');
        const rdpCheck = document.getElementById('edit-rdp');
        
        if (checkKeyOS && rdpWrapper && rdpCheck) {
            if (checkKeyOS.checked) {
                rdpWrapper.style.opacity = '1';
                rdpWrapper.style.pointerEvents = 'auto';
                rdpCheck.disabled = false;
            } else {
                rdpWrapper.style.opacity = '0.3';
                rdpWrapper.style.pointerEvents = 'none';
                rdpCheck.checked = false;
                rdpCheck.disabled = true;
                this.handleRDPChange(); // hide rdp details
            }
        }
    },
    handleRDPChange: function() {
        const rdpCheck = document.getElementById('edit-rdp');
        const rdpDetails = document.getElementById('rdp-details');
        if (rdpCheck && rdpDetails) {
            rdpDetails.style.display = rdpCheck.checked ? 'flex' : 'none';
        }
    },
    saveEdit: async function() {
        if(!['ADMIN', 'EDITOR'].includes(this.state.activeUser.role)) {
            return this.showToast('Düzenleme yetkiniz bulunmamaktadır!', 'warning');
        }
        const id = this.state.editingId;
        const type = this.state.editingType;
        if (!id) return;
        try {
            const payload = { 
                id: id,
                changed_by: this.state.activeUser.username || this.state.activeUser.key || 'system',
                display_name: this.state.activeUser.display_name || this.state.activeUser.name || 'Sistem'
            };
            if (type === 'pc') {
                const item = this.state.inventory.find(i => i.id == id);
                payload.pc_no = item ? item.pc_no : '';
                const devType = (item ? item.device_type : 'PC').toUpperCase();
                payload.device_type = devType;

                let fields = [];
                let checks = [];

                if (devType === 'TABLET') {
                    fields = ['location_code', 'location_name', 'ip', 'mac', 'phone', 'assigned_to', 'title', 'unit'];
                    checks = ['on_field', 'warehouse', 'is_faulty', 'without_location', 'pending_installation'];
                } else if (devType === 'SIRAMATIK' || devType === 'KIOSK') {
                    fields = ['location_code', 'location_name', 'ip', 'mac', 'serial_no'];
                    checks = ['on_field', 'warehouse', 'is_faulty', 'without_location', 'pending_installation'];
                } else if (['BARCODE_PRINTER', 'BARCODE_READER', 'SCANNER', 'MONITOR'].includes(devType)) {
                    fields = ['name', 'location_code', 'location_name', 'ip', 'pc_no', 'serial_no', 'mac', 'monitor_type', 'model'];
                    checks = ['on_field', 'warehouse', 'is_faulty', 'without_location', 'pending_installation'];
                } else {
                    fields = ['tower', 'floor', 'location_code', 'location_name', 'ip', 'description', 'pc_serial', 'monitor_seri', 'monitor2_seri', 'mac', 'assigned_to', 'bagli_yazicilar', 'by_seri', 'bo_seri', 'tarayici_seri', 'rdp_address', 'rdp_reason'];
                    checks = ['on_field', 'warehouse', 'is_faulty', 'without_location', 'windows', 'keyos', 'rdp', 'pending_installation'];
                }

                
                fields.forEach(k => {
                    const el = document.getElementById('edit-' + k);
                    if(el) payload[k] = el.value;
                });

                // BARCODE AUTO-REGISTER FLOW (AÅAMA 4) - only for default PC
                if (devType !== 'TABLET' && devType !== 'SIRAMATIK' && devType !== 'KIOSK') {
                    const peripherals = [
                        { key: 'by_seri', type: 'BARCODE_PRINTER', label: 'Barkod Yazıcı' },
                        { key: 'bo_seri', type: 'BARCODE_READER', label: 'Barkod Okuyucu' },
                        { key: 'tarayici_seri', type: 'SCANNER', label: 'Tarayıcı' }
                    ];
                    
                    for (const p of peripherals) {
                        const serial = payload[p.key];
                        if (serial && serial.trim() !== "" && serial !== '---') {
                            const check = await this.apiRequest('/printers/printers/check_serial', {
                                method: 'POST',
                                body: JSON.stringify({ serial: serial.trim() })
                            });
                            if (check.success && !check.exists) {
                                if (confirm(`${p.label} için girilen seri numarası (${serial}) kayıtlı değil.\n\nYeni cihaz olarak kaydetmek ister misiniz?`)) {
                                    await this.apiRequest('/inventory/update', {
                                        method: 'POST',
                                        body: JSON.stringify({
                                            serial: serial.trim(),
                                            device_type: p.type,
                                            pc_no: payload.pc_no,
                                            is_new: true
                                        })
                                    });
                                } else {
                                    this.showToast('Kaydetme işlemi iptal edildi.', 'warning');
                                    return; 
                                }
                            } else if (check.success && check.exists) {
                                const mapT = {'barcode_printers': 'Barkod Yazıcı', 'barcode_readers': 'Barkod Okuyucu', 'scanners': 'Tarayıcı'};
                                let tblMatch = false;
                                if (p.type === 'BARCODE_PRINTER' && check.table === 'barcode_printers') tblMatch = true;
                                else if (p.type === 'BARCODE_READER' && check.table === 'barcode_readers') tblMatch = true;
                                else if (p.type === 'SCANNER' && check.table === 'scanners') tblMatch = true;
                                
                                if (!tblMatch && mapT[check.table]) {
                                    const tableToKey = {
                                        'barcode_printers': 'by_seri',
                                        'barcode_readers': 'bo_seri',
                                        'scanners': 'tarayici_seri'
                                    };
                                    const targetKey = tableToKey[check.table];
                                    
                                    alert(`SİSTEM UYARISI: Girdiğiniz seri numarası (${serial}), sistemde bir "${mapT[check.table]}" olarak algılandı.\n\nOtomatik Düzeltme: Değer "${p.label}" alanından alınıp doğru olan "${mapT[check.table]}" alanına taşındı ve kaydetme işlemine devam ediliyor.`);
                                    
                                    // Move data in payload
                                    payload[targetKey] = serial;
                                    payload[p.key] = '';
                                    
                                    // Update UI visibly
                                    const srcEl = document.getElementById('edit-' + p.key);
                                    if(srcEl) srcEl.value = '';
                                    const tgtEl = document.getElementById('edit-' + targetKey);
                                    if(tgtEl) tgtEl.value = serial;
                                }
                            }
                        }
                    }
                }

                checks.forEach(k => {
                    const el = document.getElementById('edit-' + k);
                    if(el) payload[k] = el.checked ? 1 : 0;
                });
                let data;
                let forceUpdate = false;
                while (true) {
                    payload.force_update = forceUpdate;
                    data = await this.apiRequest('/inventory/update', {
                        method: 'POST',
                        body: JSON.stringify(payload)
                    });
                    
                    if (data && data.requires_confirmation) {
                        if (confirm(data.confirm_message)) {
                            forceUpdate = true;
                            continue; // Retry with force_update
                        } else {
                            this.showToast('Güncelleme iptal edildi.', 'warning');
                            return; // User cancelled
                        }
                    }
                    break; // Success
                }
            } else if (type === 'pr') {
                // Mevcut yazıcı durumunu kontrol et (device_class ile doğru cihazı bul)
                const editDC = this.state.editingDeviceClass;
                let currentPrinter = null;
                if (editDC === 'MONITOR') {
                    currentPrinter = (this.state.inventory || []).find(p => p.id == id && p.device_class === editDC);
                } else if (editDC) {
                    currentPrinter = (this.state.printers || []).find(p => p.id == id && p.device_class === editDC);
                }
                if (!currentPrinter && editDC !== 'MONITOR') {
                    currentPrinter = (this.state.printers || []).find(p => p.id == id);
                }
                if (!currentPrinter) throw new Error("Cihaz bulunamadı.");
                
                payload.device_class = currentPrinter.device_class || 'PRINTER';
                
                if (editDC === 'MONITOR') {
                    const selectedMonitorTypeEl = document.querySelector('input[name="monitor-type"]:checked');
                    if (selectedMonitorTypeEl) {
                        payload.monitor_type = selectedMonitorTypeEl.value;
                    }
                }
                ['pr_no', 'model', 'ip', 'seri', 'mac', 'mahal'].forEach(k => {
                    const el = document.getElementById('edit-' + k);
                    if(el) payload[k] = el.value;
                });
                const selectedStatusEl = document.querySelector('input[name="printer-status"]:checked');
                const selectedStatus = selectedStatusEl ? selectedStatusEl.value : '';
                
                if (selectedStatus) {
                    if (['MONITOR', 'BARCODE_PRINTER', 'BARCODE_READER', 'SCANNER'].includes(payload.device_class)) {
                        // Ozel cihazlar status'u boolean olarak tutar, status kolonu PC numarasını tutar
                        payload.on_field = selectedStatus === 'Kurulu' ? 1 : 0;
                        payload.is_faulty = selectedStatus === 'Arızalı' ? 1 : 0;
                        payload.warehouse = selectedStatus === 'Depoda' ? 1 : 0;
                        payload.without_location = selectedStatus === 'Kayıp' ? 1 : 0;
                    } else {
                        // Yazıcılar doğrudan status stringini tutar
                        payload.status = selectedStatus;
                    }
                }

                // YENİ GÜVENLİK: Servis tablosunda açık kaydı (Dönü tarihi olmayan) var mı?
                const openServiceRecord = this.state_service.raw.find(s => 
                    s.pr_no === payload.pr_no && (!s.return_date || s.return_date.trim() === "" || s.return_date === "-")
                );

                if (openServiceRecord && selectedStatus === 'Kurulu') {
                    alert("yazıcının kapanmamış servis işlem kaydı var depocunuz ile iletişime geçin");
                    return;
                }

                // Eski koruma mantığı (Yedek olarak)
                const currentStatus = currentPrinter.status || '';
                if ((currentStatus === 'Arızalı' || currentStatus === 'Serviste') && selectedStatus === 'Kurulu' && !openServiceRecord) {
                    alert("UYARI: Bu yazıcının açık bir servis kaydı bulunmaktadır.\n\nYazıcıyı 'Kurulu' olarak işaretleyebilmek için depocunun servis kaydını kapatması (Depoya çekmesi) gerekmektedir.");
                    return;
                }
                let result;
                let endpoint = '/printers/printers/update';
                
                if (['MONITOR', 'BARCODE_PRINTER', 'BARCODE_READER', 'SCANNER'].includes(payload.device_class)) {
                    endpoint = '/inventory/update';
                    payload.device_type = payload.device_class;
                    if (payload.pr_no) payload.name = payload.pr_no;
                    if (payload.seri) payload.serial_no = payload.seri;
                    
                    // ÖZEL CİHAZLAR: edit-ip PC numarasını tutar, edit-mahal ise Mahal kodunu tutar.
                    payload.pc_no = payload.ip;
                    payload.recorded_device_no = payload.ip;
                    payload.location_code = payload.mahal;

                    // ANAYASA: Monitorlerin bağlı olduğu PC numarası status kolonunda saklanır.
                    if (payload.device_class === 'MONITOR') {
                        payload.status = payload.ip;
                    }
                }

                let forceUpdatePr = false;
                while (true) {
                    payload.force_update = forceUpdatePr;
                    result = await this.apiRequest(endpoint, {
                        method: 'POST',
                        body: JSON.stringify(payload)
                    });

                    if (result && result.requires_confirmation) {
                        if (confirm(result.confirm_message)) {
                            forceUpdatePr = true;
                            continue;
                        } else {
                            this.showToast('Güncelleme iptal edildi.', 'warning');
                            return;
                        }
                    }
                    break;
                }
                
                // CUPS Update integration for Printers
                if (endpoint === '/printers/printers/update' && payload.pr_no && payload.mahal) {
                    try {
                        this.showToast('Veritabanı güncellendi. CUPS Mahallesi senkronize ediliyor...', 'info');
                        const cupsResp = await this.apiRequest('/printers/printers/cups/modify_location', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ pr_no: payload.pr_no, location: payload.mahal })
                        });
                        if (!cupsResp.success) {
                            console.warn('CUPS Update failed:', cupsResp.error);
                            this.showToast('CUPS güncellenirken hata: ' + (cupsResp.error || 'Bilinmeyen hata'), 'warning');
                        }
                    } catch (e) {
                        console.error('CUPS Update error:', e);
                        this.showToast('CUPS güncellenemedi: ' + e.message, 'warning');
                    }
                }

                this.state.inventoryCache = {}; await this.loadInventory(); // Reload all to refresh printer state
                this.renderPrinters(this.state.printers);
            }
            this.closeDeviceDetail();
            this.showToast('Cihaz bilgileri güncellendi!');
            this.state.inventoryCache = {}; this.loadInventory();
            this.loadDashboardStats();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    checkPrinterStatus: async function(ip, printerId) {
        if (!ip) return;
        // Detay modaldaki alan (yazıcı detayı açıkken)
        const detailArea = document.getElementById('printer-live-status-area');
        // Kart üzerindeki inline alan
        const cardArea = printerId ? document.getElementById('printer-status-' + printerId) : null;
        const targetArea = detailArea || cardArea;
        if (cardArea) {
            cardArea.style.display = 'block';
            cardArea.innerHTML = '<div style="text-align:center;"><i class="fas fa-spinner fa-spin"></i> Sorgulanıyor...</div>';
        }
        if (detailArea) {
            detailArea.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sorgulanıyor...';
        }
        try {
            const data = await this.apiRequest('/printers/status/' + ip);
            if (data.success) {
                // Toner yüzdesini çıkar
                let tonerPercent = 0;
                let tonerText = data.toner_level || 'Bilinmiyor';
                const match = tonerText.match(/(\d+)/);
                if (match) tonerPercent = parseInt(match[1]);
                // Toner bar rengi
                let barColor = '#00ff88';
                if (tonerPercent <= 10) barColor = '#ff4b2b';
                else if (tonerPercent <= 30) barColor = '#ffb400';
                // Durum rengi
                let statusColor = '#00ff88';
                const statusLower = (data.device_status || '').toLowerCase();
                if (statusLower.includes('drum') || statusLower.includes('hata') || statusLower.includes('error') || statusLower.includes('deitir')) {
                    statusColor = '#ff4b2b';
                } else if (statusLower.includes('uyku') || statusLower.includes('sleep')) {
                    statusColor = '#ffb400';
                }
                const html = `
                    <div style="font-weight:700; color:${statusColor}; margin-bottom:5px; font-size:0.8rem;">
                        <i class="fas fa-circle" style="font-size:0.5rem;"></i> ${data.device_status}
                    </div>
                    <div style="font-size:0.7rem; opacity:0.7; margin-bottom:3px;">Toner: ${tonerText}</div>
                    <div style="background:rgba(255,255,255,0.1); border-radius:4px; height:8px; overflow:hidden;">
                        <div style="width:${tonerPercent}%; height:100%; background:${barColor}; border-radius:4px; transition:width 0.5s;"></div>
                    </div>
                `;
                if (cardArea) { cardArea.style.display = 'block'; cardArea.innerHTML = html; }
                if (detailArea) detailArea.innerHTML = html;
            } else {
                const errHtml = `<span style="color:#ff4b2b"><i class="fas fa-exclamation-triangle"></i> ${data.error || 'Cihaza ulaılamadı.'}</span>`;
                if (cardArea) { cardArea.style.display = 'block'; cardArea.innerHTML = errHtml; }
                if (detailArea) detailArea.innerHTML = errHtml;
            }
        } catch (e) {
            const errMsg = `<span style="color:#ff4b2b">Sorgulama baarısız: ${e.message}</span>`;
            if (cardArea) { cardArea.style.display = 'block'; cardArea.innerHTML = errMsg; }
            if (detailArea) detailArea.innerHTML = errMsg;
        }
    },
    syncServiceRecordsFromExcel: async function() {
        if (!confirm("database/servise_giden_yazıcılar.xlsx dosyasındaki kayıtlar içeri aktarılacak. Emin misiniz?")) return;
        try {
            this.showToast('Senkronizasyon baladı...', 'info');
            const resp = await this.apiRequest('/service/sync_from_excel', { method: 'POST' });
            const result = resp;
            if (result.error) throw new Error(result.error);
            this.showToast(result.message);
            this.loadServiceRecords();
            this.loadDashboardStats();
            this.renderPrinters(); // Yazıcı durumları deimi olabilir
        } catch (e) {
            alert('Senkronizasyon hatası: ' + e.message);
        }
    },
    loadEditFormFooter: function(type) {
        let item = null;
        if (type === 'pc') {
            item = this.state.inventory.find(i => i.id == this.state.editingId);
        } else {
            const editDC = this.state.editingDeviceClass;
            if (editDC === 'MONITOR') {
                item = (this.state.inventory || []).find(p => p.id == this.state.editingId && p.device_class === editDC);
            } else if (editDC) {
                item = (this.state.printers || []).find(p => p.id == this.state.editingId && p.device_class === editDC);
            }
            if (!item && editDC !== 'MONITOR') {
                item = (this.state.printers || []).find(p => p.id == this.state.editingId);
            }
        }
            
        if (!item) return '';

        if (type === 'pr') {
            const dClass = item.device_class || 'PRINTER';
            const isSpecial = dClass === 'BARCODE_PRINTER' || dClass === 'BARCODE_READER' || dClass === 'SCANNER' || dClass === 'MONITOR';
            return `
            <div class="flex-row gap-2 mt-4">
                <button class="btn btn-secondary" style="flex: 1;" onclick="app.closeDeviceDetail()">İptal</button>
                <button class="btn btn-accent" style="flex: 1;" onclick="app.saveEdit()">Güncelle</button>
            </div>`;
        }
        
        return `
        <div class="flex-row gap-2 mt-4">
            <button class="btn btn-secondary" style="flex: 1;" onclick="app.closeDeviceDetail()">İptal</button>
            <button class="btn btn-accent" style="flex: 1;" onclick="app.saveEdit()">Güncelle</button>
        </div>`;
    },
    // 
    //  TECHNICAL NOTES
    // 
    loadNotes: async function(deviceId, deviceType) {
        const timeline = document.getElementById('notes-timeline');
        if (!timeline) return;
        timeline.innerHTML = '<div style="text-align:center; padding:20px;"><i class="fas fa-spinner fa-spin"></i> Notlar yükleniyor...</div>';
        try {
            const resp = await this.apiRequest(`/notes/get/${deviceType}/${deviceId}`);
            const notes = resp;
            this.renderNotes(notes);
        } catch (e) {
            timeline.innerHTML = '<div class="timeline-empty"><i class="fas fa-plug"></i> Backend balantısı kurulamadı.</div>';
        }
    },
    renderNotes: function(notes) {
        const timeline = document.getElementById('notes-timeline');
        if (!timeline) return;
        if (!notes || notes.length === 0) {
            timeline.innerHTML = `
                <div class="timeline-empty">
                    <i class="fas fa-clipboard" style="font-size: 2rem; display:block; margin-bottom:10px;"></i>
                    Henüz teknik not eklenmedi.<br>Yukarıdan ilk notu ekleyin.
                </div>`;
            return;
        }
        const currentUser = this.state.activeUser;
        timeline.innerHTML = '<div class="timeline">' + notes.map(n => {
            const date = n.created_at ? new Date(n.created_at).toLocaleString('tr-TR') : '-';
            // Sadece notu ekleyen veya ADMIN düzenleyebilir.
            // Sahibi belli olmayan eski notları sadece ADMIN düzenleyebilir.
            const canEdit = currentUser.role === 'ADMIN' || (n.user_id && currentUser.key === n.user_id);
            const canDelete = canEdit; 
            const images = (n.images || []).map(img =>
                `<img src="${this.state.API_BASE.replace('/api', '')}/uploads/notes/${img.filename}" class="timeline-image" alt="Not Görseli" onclick="window.open(this.src)">`
            ).join('');
            return `
            <div class="timeline-item fade-in" id="note-item-${n.id}">
                <div class="flex-between">
                    <span class="timeline-date"><i class="fas fa-calendar"></i> ${date}</span>
                    <span class="timeline-user"><i class="fas fa-user"></i> ${n.user_name || 'Bilinmiyor'}</span>
                </div>
                <div id="note-display-${n.id}">
                    ${n.title ? `<div class="timeline-title">${n.title}</div>` : ''}
                    <div class="timeline-content">${n.content || ''}</div>
                </div>
                ${images}
                ${(canEdit || canDelete) ? `
                <div class="timeline-actions">
                    ${canEdit ? `<button class="btn btn-chip btn-sm" onclick="app.editNote(${n.id})"><i class="fas fa-edit"></i> Düzenle</button>` : ''}
                    ${canDelete ? `<button class="btn btn-danger btn-sm" onclick="app.deleteNote(${n.id})"><i class="fas fa-trash"></i> Sil</button>` : ''}
                </div>` : ''}
            </div>`;
        }).join('') + '</div>';
    },
    editNote: function(noteId) {
        // Not içeriini bul
        const display = document.getElementById(`note-display-${noteId}`);
        const titleEl = display.querySelector('.timeline-title');
        const contentEl = display.querySelector('.timeline-content');
        const oldTitle = titleEl ? titleEl.innerText : '';
        const oldContent = contentEl ? contentEl.innerText : '';
        display.innerHTML = `
            <div class="note-edit-box" style="margin-top:10px;">
                <input type="search" id="edit-note-title-${noteId}" class="input-modern mb-2" value="${oldTitle}" placeholder="Balık" style="width:100%;">
                <textarea id="edit-note-content-${noteId}" class="input-modern" style="width:100%; height:80px; min-height:80px;" placeholder="İçerik">${oldContent}</textarea>
                <div class="flex-row gap-2 mt-2">
                    <button class="btn btn-accent btn-sm" onclick="app.saveNoteEdit(${noteId})">Kaydet</button>
                    <button class="btn btn-secondary btn-sm" onclick="app.loadNotes(app.state.editingId, app.state.editingType)">İptal</button>
                </div>
            </div>
        `;
    },
    saveNoteEdit: async function(noteId) {
        const title = document.getElementById(`edit-note-title-${noteId}`).value;
        const content = document.getElementById(`edit-note-content-${noteId}`).value;
        try {
            const resp = await this.apiRequest(`/notes/update/${noteId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title, content,
                    user_id: this.state.activeUser.key,
                    role: this.state.activeUser.role
                })
            });
            const result = resp;
            if (result.error) throw new Error(result.error);
            this.showToast('Not güncellendi!');
            this.loadNotes(this.state.editingId, this.state.editingType);
        } catch (e) { alert('Hata: ' + e.message); }
    },
    addNote: async function() {
        const title = document.getElementById('note-title').value;
        const content = document.getElementById('note-content').value;
        const imageInput = document.getElementById('note-image');
        if (!title && !content) return alert('Balık veya içerik yazın.');
        const formData = new FormData();
        formData.append('device_id', this.state.editingId);
        formData.append('device_type', this.state.editingType);
        formData.append('title', title);
        formData.append('content', content);
        formData.append('user_id', this.state.activeUser.key);
        formData.append('user_name', this.state.activeUser.name);
        if (imageInput.files.length > 0) {
            formData.append('image', imageInput.files[0]);
        }
        try {
            const resp = await this.apiRequest('/notes/add', {
                method: 'POST',
                body: formData
            });
            const result = resp;
            if (result.error) throw new Error(result.error);
            // Formu temizle
            document.getElementById('note-title').value = '';
            document.getElementById('note-content').value = '';
            imageInput.value = '';
            this.showToast('Teknik not eklendi!');
            this.loadNotes(this.state.editingId, this.state.editingType);
        } catch (e) { alert('Hata: ' + e.message); }
    },
    deleteNote: async function(noteId) {
        if (!confirm('Bu notu silmek istediinize emin misiniz?')) return;
        try {
            const resp = await this.apiRequest(`/notes/delete/${noteId}?user_id=${this.state.activeUser.key}&role=${this.state.activeUser.role}`, { method: 'DELETE' });
            const result = resp;
            if (result.error) throw new Error(result.error);
            this.showToast('Not silindi.');
            this.loadNotes(this.state.editingId, this.state.editingType);
        } catch (e) { alert('Hata: ' + e.message); }
    },
    // 
    //  GENERAL NOTES (BİLGİ BANKASI)
    // 
    loadGeneralNotes: async function() {
        const grid = document.getElementById('general-notes-grid');
        if (!grid) return;
        try {
            const data = await this.apiRequest(`/notes/kb/${this.state_kb.tab}`);
            this.state_kb.raw = data;
            this.renderGeneralNotes(data);
        } catch (e) {
            grid.innerHTML = '<p>Bağlantı hatası.</p>';
        }
    },
    syncKBFromExcel: async function() {
        if (!confirm("database/bilgi_bankasi.xlsx dosyasındaki veriler Bilgi Bankası'na aktarılacak. Mevcut aynı balıklı kayıtlar güncellenecektir. Emin misiniz?")) return;
        try {
            this.showToast('Bilgi Bankası senkronize ediliyor...', 'info');
            const resp = await this.apiRequest('/notes/kb/sync_from_excel', { method: 'POST' });
            const result = resp;
            if (result.error) throw new Error(result.error);
            this.showToast(result.message);
            this.loadGeneralNotes();
        } catch (e) {
            alert('Senkronizasyon hatası: ' + e.message);
        }
    },
    setKBTab: function(tab) {
        this.state_kb.tab = tab;
        document.querySelectorAll('#view-general-notes .btn-chip').forEach(btn => {
            btn.classList.toggle('active', btn.id === `kb-tab-${tab}`);
        });
        if (tab === 'indir') {
            this.loadDownloads();
        } else {
            this.loadGeneralNotes();
        }
    },
    loadDownloads: async function() {
        const grid = document.getElementById('general-notes-grid');
        if (grid) grid.innerHTML = '<div style="text-align:center; padding:50px;"><i class="fas fa-spinner fa-spin fa-2x"></i></div>';
        try {
            const resp = await this.apiRequest('/downloads/list');
            this.renderDownloads(resp.files || []);
        } catch (e) {
            if (grid) grid.innerHTML = `<div style="color:red; text-align:center; padding:30px;">Dosyalar yüklenemedi.</div>`;
        }
    },
    renderDownloads: function(files) {
        const grid = document.getElementById('general-notes-grid');
        if (!grid) return;
        if (!files || files.length === 0) {
            grid.innerHTML = '<div style="text-align:center; padding:30px; opacity:0.5;">Klasörde henüz dosya bulunamadı.</div>';
            return;
        }
        grid.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; width: 100%;">
                ${files.map(f => {
                    const isBat = f.name.toLowerCase().endsWith('.bat');
                    const icon = isBat ? 'fa-terminal' : 'fa-file-arrow-down';
                    return `
                    <div class="card" style="padding: 15px; display: flex; align-items: center; gap: 15px; cursor: pointer;" onclick="window.location.href='${this.state.API_BASE}/downloads/get/${encodeURIComponent(f.name)}'">
                        <div style="width: 45px; height: 45px; background: rgba(255,255,255,0.05); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: var(--accent);">
                            <i class="fas ${icon} fa-xl"></i>
                        </div>
                        <div style="flex: 1; overflow: hidden;">
                            <div style="font-weight: 600; font-size: 0.9rem;" title="${f.name}">${f.name}</div>
                            <div style="font-size: 0.7rem; opacity: 0.5;">${f.size} | ${f.date}</div>
                        </div>
                    </div>`;
                }).join('')}
            </div>`;
    },
    renderGeneralNotes: function(data) {
        const grid = document.getElementById('general-notes-grid');
        if (!grid) return;
        if (!data || data.length === 0) {
            grid.innerHTML = '<div style="text-align:center; padding:30px; opacity:0.5;">Bu kategoride henüz bilgi bulunamadı.</div>';
            return;
        }
        grid.innerHTML = data.map((n, idx) => {
            const date = n.created_at ? (isNaN(new Date(n.created_at)) ? n.created_at : new Date(n.created_at).toLocaleDateString('tr-TR')) : '-';
            const isKodlar = this.state_kb.tab === 'kodlar';
            const isAdmin = this.state.activeUser && this.state.activeUser.role === 'ADMIN';
            let contentHtml = '';
            if (isKodlar || true) {
                let userControlHtml = '';
                if (n.requires_user && Number(n.requires_user) === 1) {
                    userControlHtml = `
                    <div class="kb-user-control mb-2">
                        <div class="flex-row gap-2">
                            <input type="text" id="kb-user-input-${n.id}" class="search-bar" style="height:35px; font-size:0.8rem;" placeholder="Kullanıcı Adı Girin (r: mehmet)">
                            <button class="btn btn-accent btn-sm" onclick="app.applyKBUserPlaceholder(${n.id})">Uygula</button>
                        </div>
                    </div>`;
                }
                let displayContent = n.content;
                let isMulti = false;
                try {
                    if (n.content.startsWith('{')) {
                        const parsed = JSON.parse(n.content);
                        if (parsed.type === 'multi') {
                            displayContent = parsed.commands.map((c, i) => `[KOMUT ${i+1}]\n${c}`).join('\n\n');
                            isMulti = true;
                        }
                    }
                } catch(e) { console.error(e); }

                contentHtml = `
                    ${userControlHtml}
                    <div class="kb-code-container" style="${isMulti ? 'border-left: 4px solid #ff4b2b;' : ''}">
                        <div class="kb-code-block">
                            <pre id="kb-pre-${n.id}">${displayContent.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
                        </div>
                        <div class="kb-action-sidebar" style="display: flex; flex-direction: row; gap: 5px; align-items: center; justify-content: flex-end; margin-top: 5px;">
                            <i class="fas fa-edit kb-mini-icon" onclick="app.editKBEntry(${n.id})" title="Düzenle" style="color: #ffcc00; font-size: 1.1rem; cursor:pointer;"></i>
                            <i class="fas fa-copy kb-mini-icon" onclick="app.copyToClipboard(document.getElementById('kb-pre-${n.id}').innerText)" title="Kopyala" style="font-size: 1.1rem; cursor:pointer;"></i>
                            ${isKodlar ? `
                            <i class="fas fa-play-circle kb-mini-icon" onclick="app.openRunCommandModal(${n.id})" title="${isMulti ? 'Sıralı Komutları Çalıtır' : 'Çalıtır'}" style="color: ${isMulti ? '#ff4b2b' : 'var(--accent)'}; font-size: 1.4rem; cursor:pointer;"></i>
                            ` : ''}
                        </div>
                    </div>`;
            }
            return `
            <div class="kb-card" id="kb-card-${n.id}">
                <div class="kb-header" onclick="app.toggleKB(${n.id})">
                    <div class="kb-title">${n.title || 'İsimsiz Bilgi'}</div>
                    <i class="fas fa-chevron-down kb-icon"></i>
                </div>
                <div class="kb-content">
                    <div id="kb-body-${n.id}" class="kb-body">
                        ${contentHtml}
                        ${n.image_path ? `<img src="${this.state.API_BASE.replace('/api', '')}/uploads/notes/${n.image_path}" class="timeline-image" style="max-height:300px;" onclick="window.open(this.src)">` : ''}
                    </div>
                    <div class="kb-footer">
                        ${date !== '-' ? `<span>${date}</span>` : ''}
                        ${n.user_name ? `<span><i class="fas fa-user-edit"></i> ${n.user_name.toUpperCase()}</span>` : ''}
                    </div>
                </div>
            </div>`;
        }).join('');
    },
    editKBEntry: function(id) {
        this.openKBModal(id);
    },
    saveKBItem: async function() {
        const editId = document.getElementById('kb-edit-id').value;
        const title = document.getElementById('kb-title').value;
        const type = document.getElementById('kb-type').value;
        const imageFile = document.getElementById('kb-image').files[0];
        const isMulti = document.getElementById('kb-multi-command').checked;
        
        let content = "";
        if (isMulti) {
            const inputs = document.querySelectorAll('.multi-command-input');
            const commands = Array.from(inputs).map(inp => inp.value.trim()).filter(v => v);
            if (commands.length < 2) return alert('Lütfen en az 2 komut giriniz.');
            content = JSON.stringify({ type: 'multi', commands: commands, delay: 60000 });
        } else {
            content = document.getElementById('kb-content').value;
            if (type !== 'indir' && !content) return alert('Lütfen içerik giriniz.');
        }

        if (!title) return alert('Lütfen bir başlık giriniz.');
        if (type === 'indir' && !editId && !imageFile) return alert('Lütfen yüklenecek dosyayı seçiniz.');
        
        try {
            this.showToast('Bilgi kaydediliyor...', 'info');
            const formData = new FormData();
            formData.append('device_type', type);
            formData.append('type', type);
            formData.append('title', title);
            formData.append('content', content);
            formData.append('requires_user', document.getElementById('kb-requires-user').checked ? 1 : 0);
            formData.append('user_id', this.state.activeUser.key);
            formData.append('user_name', this.state.activeUser.display_name || this.state.activeUser.username || this.state.activeUser.name || 'Sistem');
            formData.append('role', this.state.activeUser.role);
            if (imageFile) formData.append('image', imageFile);
            
            let url = this.state.API_BASE + '/notes/kb/add';
            if (editId) url = `${this.state.API_BASE}/notes/kb/update/${editId}`;
            
            const resp = await this.apiRequest(url, { method: 'POST', body: formData });
            const result = resp;
            if (result.error) throw new Error(result.error);
            
            this.showToast(editId ? 'Kayıt güncellendi!' : 'Yeni bilgi eklendi!');
            this.closeKBModal();
            this.loadGeneralNotes();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    handleMultiCommandToggle: function(checked) {
        const config = document.getElementById('kb-multi-config');
        const normalContent = document.getElementById('kb-content').parentElement;
        if (checked) {
            config.style.display = 'block';
            normalContent.style.display = 'none';
            this.generateMultiInputs(document.getElementById('kb-multi-count').value);
        } else {
            config.style.display = 'none';
            normalContent.style.display = 'block';
        }
    },
    generateMultiInputs: function(count) {
        const container = document.getElementById('kb-multi-inputs');
        container.innerHTML = '';
        for (let i = 1; i <= count; i++) {
            container.innerHTML += `
                <div class="form-group">
                    <label style="font-size:0.65rem; color:var(--accent);">KOMUT #${i}</label>
                    <textarea class="search-bar multi-command-input" placeholder="Komut giriniz..." style="min-height:60px; font-family:monospace;"></textarea>
                </div>`;
        }
    },
    applyKBUserPlaceholder: function(id) {
        const username = document.getElementById(`kb-user-input-${id}`).value.trim();
        if(!username) return alert('Lütfen bir kullanıcı adı girin.');
        const n = this.state_kb.raw.find(item => item.id == id);
        if(!n) return;
        // <kullanici_adi> yer tutucusunu deitir
        const newContent = n.content.replace(/<kullanici_adi>/g, username);
        // Ekranda gösterilen pre içeriini güncelle
        document.getElementById(`kb-pre-${id}`).innerText = newContent;
        this.showToast('Komut kullanıcı adına göre düzenlendi. imdi kopyalayabilirsiniz.');
    },
    openRunCommandModal: async function(id, customScript = null, targetIp = null, bimFunction = 'RunCommand') {
        let preContent = "";
        if (customScript) {
            preContent = customScript;
        } else if (id) {
            const item = this.state_kb.raw.find(n => n.id == id);
            preContent = item ? item.content : "";
        }
        
        // Modal Başlığını Dinamik Olarak Ayarla
        let titleText = ">_ Uzaktan Komut Çalıştır";
        if (bimFunction === 'AddPrinter') titleText = ">_ Uzaktan Yazıcı Ekle";
        if (bimFunction === 'RemovePrinter') titleText = ">_ Uzaktan Yazıcı Kaldır";
        if (customScript && customScript === 'reboot') titleText = ">_ Bilgisayarı Yeniden Başlat";
        if (customScript && customScript === 'shutdown') titleText = ">_ Bilgisayarı Kapat";
        
        const titleEl = document.querySelector('#run-command-modal h3');
        if (titleEl) {
            titleEl.innerHTML = `<i class="fas fa-terminal"></i> ${titleText}`;
        }

        document.getElementById('run-command-id').value = id || '';
        document.getElementById('run-command-func').value = bimFunction;
        document.getElementById('run-command-text').value = preContent;
        const ipInput = document.getElementById('run-command-ip');
        ipInput.value = targetIp || '';
        ipInput.placeholder = targetIp ? targetIp : 'IP Adresi Alınıyor...';
        document.getElementById('run-command-modal').style.display = 'flex';
        if (!targetIp) {
            try {
                const resp = await this.apiRequest('/bim/client_ip');
                const data = resp;
                if (data && data.ip) {
                    ipInput.value = data.ip;
                }
            } catch(e) {
                console.error("IP alinmadi", e);
            }
        }
        ipInput.placeholder = 'IP Adresi Giriniz';
        // Profilde kayıtlı BİM bilgilerini otomatik doldur
        const user = this.state.activeUser || {};
        document.getElementById('run-command-bim-user').value = user.bim_user || user.username || '';
        document.getElementById('run-command-bim-pass').value = user.bim_pass || '';
    },
    executeRunCommand: async function() {
        const ip = document.getElementById('run-command-ip').value.trim();
        const rawCommand = document.getElementById('run-command-text').value.trim();
        const bimFunction = document.getElementById('run-command-func').value || 'RunCommand';
        const bimUser = document.getElementById('run-command-bim-user').value.trim();
        const bimPass = document.getElementById('run-command-bim-pass').value.trim();
        const btn = document.getElementById('btn-execute-run');

        if (!ip) return alert('Lütfen komutun çalıtırılacaı IP adresini giriniz.');
        if (!bimUser) return alert('Lütfen BİM kullanıcı adınızı giriniz.');
        if (!bimPass) return alert('Lütfen BİM ifrenizi giriniz.');
        if (!rawCommand) return alert('alıtırılacak komut bulunamadı.');

        let commands = [rawCommand];
        let delayMs = 0;

        // Çoklu komut kontrolü (JSON)
        try {
            if (rawCommand.startsWith('{')) {
                const parsed = JSON.parse(rawCommand);
                if (parsed.type === 'multi') {
                    commands = parsed.commands;
                    delayMs = parsed.delay || 60000;
                }
            }
        } catch(e) { console.error(e); }

        const originalText = btn.innerHTML;
        btn.disabled = true;

        try {
            for (let i = 0; i < commands.length; i++) {
                const cmd = commands[i];
                btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Komut ${i+1}/${commands.length} Gönderiliyor...`;
                
                const resp = await this.apiRequest('/bim/run_command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ip: ip,
                        command: cmd,
                        username: bimUser,
                        password: bimPass,
                        function: bimFunction
                    })
                });
                const result = resp;
                if (result.error) throw new Error(result.error || 'Beklenmeyen hata');

                this.showToast(`Komut ${i+1} iletildi: ${result.result || 'OK'}`);

                // Eer sonraki komut varsa ve delay tanımlıysa bekle
                if (i < commands.length - 1 && delayMs > 0) {
                    let secondsLeft = delayMs / 1000;
                    while (secondsLeft > 0) {
                        btn.innerHTML = `<i class="fas fa-clock"></i> Bekleniyor... (${secondsLeft}s)`;
                        await new Promise(r => setTimeout(r, 1000));
                        secondsLeft--;
                    }
                }
            }
            this.showToast('Tüm komutlar sırayla iletildi.');
            document.getElementById('run-command-modal').style.display = 'none';
        } catch (e) {
            alert('Hata: ' + e.message);
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    },
    deleteKBEntryFromModal: function() {
        const id = document.getElementById('kb-edit-id').value;
        if (!id) return;
        this.deleteKBEntry(id);
        this.closeKBModal();
    },
    deleteKBEntry: async function(id) {
        if (!confirm('Bu bilgiyi silmek istediinize emin misiniz?')) return;
        try {
            const resp = await this.apiRequest(`/notes/kb/delete/${id}?user_id=${this.state.activeUser.key}&role=${this.state.activeUser.role}`, {
                method: 'DELETE'
            });
            const result = resp;
            if (result.error) throw new Error(result.error);
            this.showToast('Kayıt silindi.');
            this.loadGeneralNotes();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    toggleKB: function(id) {
        const card = document.getElementById(`kb-card-${id}`);
        const isActive = card.classList.contains('active');
        // Dierlerini kapat (Opsiyonel: Sadece tıklananı açmak için)
        document.querySelectorAll('.kb-card').forEach(c => c.classList.remove('active'));
        if (!isActive) {
            card.classList.add('active');
        }
    },
    searchKB: function() {
        const query = document.getElementById('kb-search').value.toUpperCase();
        const filtered = this.state_kb.raw.filter(n => 
            (n.title || '').toUpperCase().includes(query) || 
            (n.content || '').toUpperCase().includes(query)
        );
        this.renderGeneralNotes(filtered);
    },
    openKBModal: function(id = null) {
        const isAdmin = this.state.activeUser.role === 'ADMIN';
        document.getElementById('kb-modal').style.display = 'flex';
        document.getElementById('kb-modal-title').innerHTML = id ? '<i class="fas fa-edit"></i> Bilgiyi Düzenle' : '<i class="fas fa-pen-to-square"></i> Yeni Bilgi / Not Ekle';
        document.getElementById('kb-edit-id').value = id || '';
        document.getElementById('kb-title').value = '';
        document.getElementById('kb-content').value = '';
        document.getElementById('kb-type').value = this.state_kb.tab || 'kodlar';
        document.getElementById('kb-requires-user').checked = false;
        document.getElementById('kb-multi-command').checked = false;
        this.handleMultiCommandToggle(false);
        document.getElementById('kb-btn-delete').style.display = id ? 'block' : 'none';
        document.getElementById('kb-image').value = '';
        
        if (id) {
            const item = this.state_kb.raw.find(x => x.id == id);
            if (item) {
                document.getElementById('kb-title').value = item.title || '';
                document.getElementById('kb-type').value = item.type || 'kodlar';
                document.getElementById('kb-requires-user').checked = item.requires_user == 1;
                
                // Çoklu komut kontrolü
                if (item.content && item.content.startsWith('{"type":"multi"')) {
                    try {
                        const parsed = JSON.parse(item.content);
                        document.getElementById('kb-multi-command').checked = true;
                        this.handleMultiCommandToggle(true);
                        document.getElementById('kb-multi-count').value = parsed.commands.length;
                        this.generateMultiInputs(parsed.commands.length);
                        const inputs = document.querySelectorAll('.multi-command-input');
                        parsed.commands.forEach((cmd, idx) => {
                            if (inputs[idx]) inputs[idx].value = cmd;
                        });
                    } catch(e) {
                        document.getElementById('kb-content').value = item.content;
                    }
                } else {
                    document.getElementById('kb-content').value = item.content || '';
                }
            }
        }

        const optIndir = document.querySelector('#kb-type option[value="indir"]');
        if (optIndir) {
            optIndir.style.display = isAdmin ? 'block' : 'none';
            optIndir.disabled = !isAdmin;
        }
        document.getElementById('kb-title').focus();
    },
    closeKBModal: function() {
        document.getElementById('kb-modal').style.display = 'none';
    },
    handleKBTypeChange: function(type) {
        const fileLabel = document.getElementById('kb-file-label') || { innerHTML: "" };
        const fileInput = document.getElementById('kb-image');
        const contentContainer = document.getElementById('kb-content').parentElement;
        const contentLabel = contentContainer ? contentContainer.querySelector('label') : null;
        
        if (type === 'indir') {
            fileLabel.innerHTML = '<i class="fas fa-file-export"></i> DOSYA YÜKLE (Gerekli İndirmeler)';
            fileInput.removeAttribute('accept');
            if (contentLabel) contentLabel.innerText = 'DOSYA AÇIKLAMASI / NOTLAR';
            const uploadArea = document.getElementById('kb-image').closest('.form-group');
            if (uploadArea) uploadArea.style.display = (this.state.activeUser.role === 'ADMIN') ? 'block' : 'none';
        } else {
            fileLabel.innerHTML = 'RESİM (Opsiyonel)';
            fileInput.setAttribute('accept', 'image/*');
            if (contentLabel) contentLabel.innerText = 'İÇERİK / KOMUTLAR / NOTLAR';
            const uploadArea = document.getElementById('kb-image').closest('.form-group');
            if (uploadArea) uploadArea.style.display = 'block';
        }
    },
    openDocModal: function(type) {
        const modalId = `doc-modal-${type}`;
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex';
        } else {
            // Generic fallback for placeholders
            const genericModal = document.getElementById('doc-modal-generic');
            const titles = {
                'sla-sehven': 'SLA Sehven Tutanaı',
                'barcode-manual': 'Manuel Barkod',
                'barcode-55x45': 'Manuel Barkod (55x45)',
                'barcode-100x100': 'Manuel Barkod (100x100)'
            };
            document.getElementById('generic-modal-title').innerText = titles[type] || 'Form Taslaı';
            genericModal.style.display = 'flex';
        }
    },
    closeDocModal: function(type) {
        const modalId = type === 'generic' ? 'doc-modal-generic' : `doc-modal-${type}`;
        const modal = document.getElementById(modalId);
        if (modal) modal.style.display = 'none';
    },
    // 
    //  SERVICE OPERATIONS
    // 
    loadServiceRecords: async function() {
        const tbody = document.getElementById('service-table-body');
        if (!tbody) return;
        try {
            const resp = await this.apiRequest('/service/get_all');
            const data = resp;
            if (data.error) {
                console.error("Service API Error:", data.error);
                tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:#ff4b2b; padding:20px;">Hata: ${data.error}</td></tr>`;
                return;
            }
            this.state_service.raw = Array.isArray(data) ? data : [];
            this.state_service.filtered = this.state_service.raw;
            this.renderServiceTable(this.state_service.filtered);
        } catch (e) {
            console.error("Service Load Error:", e);
            tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; color:red; padding:20px;">Yükleme Hatası (Sunucu Erişimi)!</td></tr>';
        }
    },
    renderServiceTable: function(items) {
        const tbody = document.getElementById('service-table-body');
        if (!tbody) return;
        
        if (!items || items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:20px; opacity:0.5;">Kayıt bulunamadı.</td></tr>';
            return;
        }

        tbody.innerHTML = items.map(r => {
            // İkame Yazıcı Mantığı
            let ikameHtml = '<span style="opacity:0.6;">Verilmedi</span>';
            if (r.substitute_pr_no && r.substitute_pr_no.trim() !== "" && r.substitute_pr_no !== "-") {
                ikameHtml = `<span style="color:#00ff88;"><i class="fas fa-check"></i> Verildi (${r.substitute_pr_no})</span>`;
            }

            // Durum Badge Rengi
            let statusClass = "is_faulty"; // Default (Kırmızı)
            let statusText = (r.status || 'BELİRSİZ').trim().toLocaleUpperCase('tr-TR');
            
            if (statusText === 'SERVİSTE' || statusText === 'SERVİS' || statusText === 'SERVISTE') {
                statusClass = "kurulum"; // Turkuaz (Mevcut CSS: status-kurulum)
                statusText = "SERVİSTE";
            } else if (statusText === 'TAMAMLANDI' || statusText === 'TESLİM EDİLDİ' || statusText === 'DEPODA') {
                statusClass = "on_field"; // Yeşil
                statusText = "TAMAMLANDI";
            } else if (statusText === 'ARIZALI' || statusText === 'ARIZALI') {
                statusClass = "is_faulty"; // Kırmızı
                statusText = "ARIZALI";
            }

            return `
            <tr onclick="app.openServiceEditModal(${r.id})" style="border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.2s; cursor: pointer;" onmouseover="this.style.background='rgba(0,210,255,0.05)'" onmouseout="this.style.background='transparent'">
                <td style="padding: 6px 10px; white-space: nowrap; width: 70px;"><span style="color:var(--accent); font-weight:700;">${r.pr_no || '-'}</span></td>
                <td style="padding: 6px 10px; color: #ffb400; font-weight: 600; white-space: nowrap; width: 100px;">${r.sla_no || '-'}</td>
                <td style="padding: 6px 10px; font-size:0.75rem; font-weight:600; color: #fff; white-space: nowrap; width: 120px;">${r.mahal || '-'}</td>
                <td style="padding: 6px 10px; color: #00d2ff; font-weight: 500; white-space: nowrap; font-size: 0.75rem; width: 85px;">${this.formatDate(r.acquisition_date)}</td>
                <td style="padding: 6px 10px; color: #fff; opacity: 0.6; white-space: nowrap; font-size: 0.75rem; width: 85px;">${this.formatDate(r.sent_date)}</td>
                <td style="padding: 6px 10px; color: #fff; opacity: 0.6; white-space: nowrap; font-size: 0.75rem; width: 85px;">${this.formatDate(r.return_date)}</td>
                <td style="padding: 6px 10px; word-break: break-word; font-style:italic; opacity:0.8; font-size:0.8rem; color: #fff; line-height: 1.2;">${r.fault_description || r.fault_desc || '-'}</td>
                <td style="padding: 6px 10px; font-size: 0.75rem; white-space: nowrap; width: 130px; text-align: left;">${ikameHtml}</td>
                <td style="padding: 6px 10px; font-size: 0.75rem; color: var(--text-secondary); width: 110px; white-space: nowrap;">
                    <i class="fas fa-user-edit" style="opacity:0.5;"></i> ${r.user_name ? r.user_name.toUpperCase() : '-'}
                </td>
                <td style="padding: 6px 10px; text-align: right; width: 110px;">
                    <span class="status-badge status-${statusClass}" style="min-width:100px; text-align:center; font-weight: 800; border-radius: 4px;">${statusText}</span>
                </td>
            </tr>`;
        }).join('');
    },
    openAddServiceModal: function(printer_id = null) {
        try {
            const isAdmin = this.state.activeUser && (this.state.activeUser.role === 'ADMIN' || this.state.activeUser.role === 'EDITOR');
            // Formu sıfırla
            const modalTitle = document.getElementById('service-modal-title');
            if(modalTitle) modalTitle.innerHTML = '<i class="fas fa-tools"></i> Yeni Servis Kaydı';
            const editId = document.getElementById('service-edit-id');
            if(editId) editId.value = '';
            const printerIdEl = document.getElementById('service-printer-id');
            if(printerIdEl) printerIdEl.value = printer_id || '';
            // Alanları temizle
            const fields = [
                'service-pr-no', 'service-seri', 'service-mac', 'service-model', 
                'service-mahal', 'service-acq-place', 'service-acq-date', 
                'service-sent-date', 'service-return-date', 'service-substitute-pr-no',
                'service-fault-desc'
            ];
            fields.forEach(id => {
                const el = document.getElementById(id);
                if(el) el.value = '';
            });
            // Admin koruması
            const adminFields = ['service-pr-no', 'service-seri', 'service-mac', 'service-model'];
            adminFields.forEach(id => {
                const el = document.getElementById(id);
                if(el) el.readOnly = !!(printer_id && !isAdmin);
            });
            // Event Listeners - onchange kullan (datalist seçimi için)
            const prInput = document.getElementById('service-pr-no');
            const subInput = document.getElementById('service-substitute-pr-no');
            if(prInput) {
                prInput.oninput = null;
                prInput.onchange = () => this.handlePrinterSelection('service-pr-no', false);
            }
            if(subInput) {
                subInput.oninput = null;
                subInput.onchange = () => this.handlePrinterSelection('service-substitute-pr-no', true);
            }
            const now = new Date().toISOString().split('T')[0];
            const acqDate = document.getElementById('service-acq-date');
            if(acqDate) acqDate.value = now;
            const statusEl = document.getElementById('service-status');
            if(statusEl) statusEl.value = 'Serviste';
            // Durum otomatik güncelleme dinleyicileri
            const retDate = document.getElementById('service-return-date');
            if(retDate) {
                retDate.onchange = (e) => {
                    if(e.target.value && statusEl) statusEl.value = 'Depoda';
                };
            }
            const ikameCheck = document.getElementById('service-has-substitute');
            if(ikameCheck) {
                ikameCheck.checked = false;
                const subContainer = document.getElementById('service-substitute-container');
                if(subContainer) {
                    subContainer.style.display = 'none';
                    ikameCheck.onchange = (e) => {
                        subContainer.style.display = e.target.checked ? 'block' : 'none';
                    };
                }
            }
            // Eger printer_id varsa bilgileri doldur
            if (printer_id && this.state.printers) {
                const p = this.state.printers.find(x => x.id == printer_id);
                if (p) {
                    if(document.getElementById('service-pr-no')) document.getElementById('service-pr-no').value = p.pr_no || p.name || '';
                    if(document.getElementById('service-seri')) document.getElementById('service-seri').value = p.seri || p.serial_no || p.serial || '';
                    if(document.getElementById('service-mac')) document.getElementById('service-mac').value = p.mac || '';
                    if(document.getElementById('service-model')) document.getElementById('service-model').value = p.model || '';
                    
                    let pcMahal = p.mahal || p.location_code || p.location || '';
                    if (p.device_class !== 'PRINTER' && p.pc_no) {
                        const pcs = (this.state.inventoryCache && this.state.inventoryCache['PC']) || this.state.inventory || [];
                        const pc = pcs.find(i => {
                            const searchNo = p.pc_no.toUpperCase();
                            const pcNo = (i.pc_no || "").toUpperCase();
                            return pcNo === searchNo || `PC-${pcNo.padStart(3, '0')}` === searchNo || pcNo === searchNo.replace('PC-', '');
                        });
                        if (pc) {
                            pcMahal = pc.location_code || pc.location_code || pc.mahal || pc.location_name || pcMahal;
                        }
                    }
                    if(document.getElementById('service-mahal')) document.getElementById('service-mahal').value = pcMahal;
                    if(document.getElementById('service-acq-place')) document.getElementById('service-acq-place').value = pcMahal;
                }
            }
            this.updatePrinterDatalist();
            const modal = document.getElementById('service-modal');
            if(modal) modal.style.display = 'flex';
        } catch (err) {
            console.error("Servis modal hatası:", err);
            alert("Servis kaydı formu açılırken bir hata oluştu: " + err.message);
        }
    },
    openServiceEditModal: async function(id) {
        const record = this.state_service.raw.find(s => s.id == id);
        if (!record) return;

        const role = this.state.activeUser ? this.state.activeUser.role : '';
        if (role !== 'ADMIN' && role !== 'DEPOT') {
            alert("Servis kaydı üzerinde sadece Admin ve Depocu işlem yapabilir.");
            return;
        }
        
        const hasReturnDate = record.return_date && record.return_date.trim() !== '' && record.return_date !== '-';
        if (hasReturnDate && role !== 'ADMIN') {
            alert("Geldiği tarih bilgisi girilmiş kapalı kayıtları sadece Admin düzenleyebilir.");
            return;
        }
        
        // Modal balıı
        const title = document.getElementById('service-modal-title');
        if (title) title.innerHTML = `<i class="fas fa-edit"></i> Servis Kaydı Düzenle [${record.pr_no}]`;
        
        // ID set et
        const editIdInput = document.getElementById('service-edit-id');
        if (editIdInput) editIdInput.value = id;

        // Alanları doldur
        const fields = {
            'service-printer-id': record.printer_id,
            'service-pr-no': record.pr_no,
            'service-seri': record.seri,
            'service-mac': record.mac,
            'service-model': record.model,
            'service-mahal': record.mahal,
            'service-acq-place': record.acq_place,
            'service-acq-date': app.formatDateForInput(record.acquisition_date),
            'service-sent-date': app.formatDateForInput(record.sent_date),
            'service-return-date': app.formatDateForInput(record.return_date),
            'service-status': record.status,
            'service-substitute-pr-no': record.substitute_pr_no,
            'service-fault-desc': record.fault_description || record.fault_desc || ''
        };

        for (const [fid, val] of Object.entries(fields)) {
            const el = document.getElementById(fid);
            if (el) {
                el.value = val || '';
                el.readOnly = false; // Tıklayınca düzenlenebilir olması için
            }
        }

        // İkame yazıcı kontrolü
        const ikameCheck = document.getElementById('service-has-substitute');
        if (ikameCheck) {
            ikameCheck.checked = !!record.has_substitute;
            const subContainer = document.getElementById('service-substitute-container');
            if (subContainer) subContainer.style.display = record.has_substitute ? 'block' : 'none';
        }

        // Silme butonunu adminlere göster
        const deleteBtn = document.getElementById('btn-service-delete');
        if (deleteBtn) {
            deleteBtn.style.display = (this.state.activeUser && this.state.activeUser.role === 'ADMIN') ? 'block' : 'none';
        }

        const modal = document.getElementById('service-modal');
        if (modal) modal.style.display = 'flex';
    },
    updateCupsLocation: async function(pr_no, mahal) {
        if (!pr_no) return alert('PR No bulunamadı!');
        
        const currentMahalInput = document.getElementById('edit-mahal');
        if (currentMahalInput && currentMahalInput.value) {
            mahal = currentMahalInput.value;
        }

        if (!confirm(`${pr_no} no'lu yazıcının CUPS üzerindeki mahal bilgisini [${mahal}] olarak güncellemek istiyor musunuz?`)) return;
        
        try {
            this.showToast('CUPS güncelleniyor, lütfen bekleyin...', 'info');
            const resp = await this.apiRequest('/printers/printers/cups/modify_location', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pr_no: pr_no, location: mahal })
            });
            const result = resp;
            if (result.success) {
                this.showToast('CUPS Mahal başarıyla güncellendi.');
            } else {
                throw new Error(result.error || 'Bilinmeyen bir hata oluştu.');
            }
        } catch (e) {
            alert('CUPS Hatası: ' + e.message);
        }
    },
    updatePrinterDatalist: function() {
        // HTML'de id="printer-pr-datalist" olarak tanımlandı
        const dl = document.getElementById('printer-pr-datalist');
        if (!dl || !this.state.printers) return;
        dl.innerHTML = this.state.printers
            .sort((a, b) => (a.pr_no || '').localeCompare(b.pr_no || ''))
            .map(p => `<option value="${p.pr_no}">${p.pr_no} - ${p.model || ''} (${p.mahal || 'Depo'})</option>`)
            .join('');
    },
    handlePrinterSelection: function(inputId, isSubstitute) {
        const inputEl = document.getElementById(inputId);
        if (!inputEl || !this.state.printers) return;
        const val = inputEl.value.trim().toUpperCase();
        if (!val) return;
        // Tam eleme önce dene, sonra kısmi eleme
        let p = this.state.printers.find(x => (x.pr_no || '').toUpperCase() === val);
        if (!p) p = this.state.printers.find(x => (x.pr_no || '').toUpperCase().includes(val));
        if (!p) return;
        if (isSubstitute) {
            const status = (p.status || '').toLowerCase();
            const isSahada = status.includes('kurulu');
            if (status.includes('serviste') || isSahada) {
                alert(`UYARI: ${p.pr_no} numaralı yazıcı u an [${isSahada ? 'SAHADA KURULU' : 'SERVİSTE'}] durumundadır.\n\nLütfen depodaki (bota) bir yazıcıyı seçiniz!`);
                inputEl.value = '';
                return;
            }
        } else {
            // Ana PR No seçildiyse diğer alanları doldur
            const idEl = document.getElementById('service-printer-id');
            const modelEl = document.getElementById('service-model');
            const seriEl = document.getElementById('service-seri');
            const macEl = document.getElementById('service-mac');
            const mahalEl = document.getElementById('service-mahal');
            const acqDateEl = document.getElementById('service-acq-date');
            // PR No'yu düzeltilmiş haliyle yaz
            inputEl.value = p.pr_no || val;
            if(idEl) idEl.value = p.id || '';
            if(modelEl) modelEl.value = p.model || '';
            if(seriEl) seriEl.value = p.seri || '';
            if(macEl) macEl.value = p.mac || '';
            if(mahalEl) mahalEl.value = p.mahal || '';
            if(acqDateEl && p.acquisition_date) {
                acqDateEl.value = this.formatDateForInput(p.acquisition_date);
            }
        }
    },
    deleteServiceRecordFromModal: function() {
        const id = document.getElementById('service-edit-id').value;
        if (id) {
            this.deleteServiceRecord(id);
            document.getElementById('service-modal').style.display = 'none';
        }
    },
    saveServiceRecord: async function() {
        const editId = document.getElementById('service-edit-id').value;
        const prNoVal = document.getElementById('service-pr-no').value;
        const returnDateVal = document.getElementById('service-return-date').value;

        // YENİ GÜVENLİK: Mükerrer kayıt engeli (Sadece yeni kayıt eklerken)
        if (!editId && prNoVal) {
            const activeRecord = this.state_service.raw.find(s => 
                s.pr_no === prNoVal && (!s.return_date || s.return_date.trim() === "" || s.return_date === "-")
            );
            if (activeRecord) {
                alert(`HATA: ${prNoVal} için zaten açık bir servis kaydı bulunuyor! Önceki kayıt sonuçlanmadan yenisi açılamaz.`);
                return;
            }
        }

        const printerIdVal = document.getElementById('service-printer-id').value;
        const payload = {
            printer_id: printerIdVal ? parseInt(printerIdVal) : null,
            pr_no: prNoVal,
            seri: document.getElementById('service-seri').value,
            mac: document.getElementById('service-mac').value,
            model: document.getElementById('service-model').value,
            mahal: document.getElementById('service-mahal').value,
            acq_place: document.getElementById('service-acq-place').value,
            acquisition_date: document.getElementById('service-acq-date').value,
            sent_date: document.getElementById('service-sent-date').value,
            return_date: returnDateVal,
            status: document.getElementById('service-status').value,
            fault_description: document.getElementById('service-fault-desc').value,
            has_substitute: document.getElementById('service-has-substitute').checked,
            substitute_pr_no: document.getElementById('service-substitute-pr-no').value,
            user_name: this.state.activeUser.username
        };

        try {
            const url = editId ? `${this.state.API_BASE}/service/update/${editId}` : `${this.state.API_BASE}/service/add`;
            const method = editId ? 'PUT' : 'POST';
            
            const resp = await this.apiRequest(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = resp;
            if (result.error) throw new Error(result.error);

            document.getElementById('service-modal').style.display = 'none';
            this.showToast('Servis kaydı başarıyla kaydedildi!');
            
            // --- AKILLI OTOMASYON ---
            // 1. İkame işaretlenirse yazıcının mahalini DEPO yap
            if (payload.has_substitute) {
                this.showToast('İkame verildi: Yazıcı mahali DEPO olarak güncelleniyor...', 'info');
                await this.apiRequest('/printers/printers/cups/update_mahal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pr_no: payload.pr_no, mahal: 'DEPO' })
                });

                // CUPS SYNC (AÅAMA 4)
                if (payload.substitute_pr_no) {
                    this.showToast('CUPS lokasyonu güncelleniyor...', 'info');
                    try {
await this.apiRequest('/printers/printers/cups/modify_location', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ 
                                pr_no: payload.substitute_pr_no, 
                                location: payload.mahal 
                            })
                        });
                        this.showToast('CUPS lokasyonu başarıyla senkronize edildi.', 'success');
                    } catch (cupsErr) {
                        console.error("CUPS Sync Error:", cupsErr);
                        this.showToast('CUPS senkronizasyonu başarısız, ancak SQL kaydı tamamlandı.', 'warning');
                    }
                }
            } else {
                const newMahal = payload.mahal.startsWith("SERVİSTE-") ? payload.mahal : "SERVİSTE-" + payload.mahal;
                this.showToast("İkame verilmedi: Yazıcı mahali " + newMahal + " olarak güncelleniyor...", 'info');
                await this.apiRequest('/printers/printers/cups/update_mahal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pr_no: payload.pr_no, mahal: newMahal })
                });
                try {
                    await this.apiRequest('/printers/printers/cups/modify_location', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ pr_no: payload.pr_no, location: newMahal })
                    });
                } catch(e) { console.error(e); }
            }

            // 2. Her durumda yazıcıyı CUPS üzerinden durdur (Pause/Reject)
            try {
                this.showToast('CUPS Durduruluyor (Pause/Reject)...', 'info');
                await this.apiRequest('/printers/printers/cups/pause', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pr_no: payload.pr_no, reason: 'Servis/Arıza' })
                });
            } catch (cupsErr) { console.warn('CUPS Otomasyon Hatası:', cupsErr); }

            // 3. Otomatik Yazıcı Değişimi (PC bazlı)
            if (payload.has_substitute && payload.substitute_pr_no) {
                this.handleAutomaticPrinterSwap(payload.pr_no, payload.substitute_pr_no);
            }

            this.loadServiceRecords();
            this.renderPrinters(); 
            this.loadDashboardStats();
            this.state.inventoryCache = {}; this.loadInventory(); 
            this.navigateTo('service');
        } catch (e) { alert('Hata: ' + e.message); }
    },
    handleAutomaticPrinterSwap: async function(oldPrNo, newPrNo) {
        try {
            this.showToast(`${oldPrNo} -> ${newPrNo} otomatik değişimi başlatılıyor...`, 'info');
            
            // 1. Hedef PC'leri bul (Bağlı yazıcılarda eski PR No olanlar)
            const targets = this.state.inventory.filter(item => 
                (item.bagli_yazicilar || '').toUpperCase().includes(oldPrNo.toUpperCase())
            );
            
            if (targets.length === 0) {
                console.log("Otomatik değişim: Değişim yapılacak PC bulunamadı.");
                return;
            }
            
            const ips = targets.map(t => t.ip).filter(ip => ip && ip.trim());
            if (ips.length === 0) {
                this.showToast("Hedef bilgisayarların IP adresleri bulunamadı.", "warning");
                return;
            }
            
            // 2. BİM bilgilerini al
            const bimUser = this.state.activeUser.bim_user;
            const bimPass = this.state.activeUser.bim_pass;
            
            if (!bimUser || !bimPass) {
                this.showToast("BİM şifresi kayıtlı değil! Otomatik değişim yapılamadı. Lütfen profil ayarlarından kaydedin.", "error");
                return;
            }
            
            // Backend'in beklediği hedefler dizisini oluştur (targets: [{value: pc_id}])
            const backendTargets = targets.map(t => ({ type: 'pc', value: t.id }));
            
            // 3. Eski Yazıcıyı Kaldır
            const remResp = await this.apiRequest('/printers/printers/batch_action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'remove',
                    bim_function: 'RemovePrinter',
                    command: oldPrNo,
                    printer_id: null,
                    targets: backendTargets,
                    user: this.state.activeUser.username || 'system',
                    bim_user: bimUser,
                    bim_pass: bimPass
                })
            });
            
            // 4. İkame Yazıcıyı Kur
            const addResp = await this.apiRequest('/printers/printers/batch_action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'add',
                    bim_function: 'AddPrinter',
                    command: `${newPrNo}/01`,
                    printer_id: null,
                    targets: backendTargets,
                    user: this.state.activeUser.username || 'system',
                    bim_user: bimUser,
                    bim_pass: bimPass
                })
            });
            
            let errMsg = [];
            if (remResp.failed && remResp.failed.length > 0) errMsg.push('Kaldırma Hataları: ' + remResp.failed.join(', '));
            if (addResp.failed && addResp.failed.length > 0) errMsg.push('Ekleme Hataları: ' + addResp.failed.join(', '));
            
            if (errMsg.length > 0) {
                this.showToast(`Değişim tamamlandı ancak bazı hatalar var:\n${errMsg.join('\n')}`, 'warning');
            } else {
                this.showToast(`Otomatik değişim ${ips.length} PC için başarıyla tetiklendi.`, 'success');
            }
        } catch (e) {
            console.error("Otomatik değişim hatası:", e);
            this.showToast("Otomatik değişim sırasında bir hata oluştu.", "error");
        }
    },
    openPrinterInterfaceDual: function(ip, pr_no) {
        if(!ip || ip === '-') {
            alert('Yazıcı IP adresi tanımlı değil.');
            return;
        }
        // Printer Web Interface
        window.open('http://' + ip, '_blank');
        // CUPS Interface
        window.open('https://print01.kocaelish.com:49631/printers/' + pr_no, '_blank');
    },
    deleteServiceRecord: async function(id) {
        if (!confirm('Bu servis kaydını silmek istediinize emin misiniz?')) return;
        try {
            await this.apiRequest(`/service/delete/${id}`, { method: 'DELETE' });
            this.showToast('Kayıt silindi.');
            this.loadServiceRecords();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    filterServiceRecords: function() {
        const query = document.getElementById('service-search').value.toUpperCase();
        const status = document.getElementById('service-filter-status').value;
        const filtered = this.state_service.raw.filter(s => {
            const matchesQuery = (s.pr_no || '').toUpperCase().includes(query) || 
                                (s.seri || '').toUpperCase().includes(query) || 
                                (s.mahal || '').toUpperCase().includes(query);
            const matchesStatus = status === 'ALL' || s.status === status;
            return matchesQuery && matchesStatus;
        });
        this.renderServiceTable(filtered);
    },
    downloadServiceDeliveryForm: function() {
        const url = `${this.state.API_BASE}/service/export_form`;
        const a = document.createElement('a');
        a.href = url;
        a.download = `Servis_Teslim_Formu_${new Date().toLocaleDateString('tr-TR').replace(/\./g,'_')}.xlsx`;
        a.click();
        this.showToast('Excel formu hazırlanıyor ve indiriliyor...');
    },
    downloadServicePDF: function() {
        const url = `${this.state.API_BASE}/service/export_pdf`;
        window.open(url, '_blank');
        this.showToast('PDF teslim formu hazırlanıyor...');
    },
    // 
    //  DOCUMENTS (PDF)
    // 
    sendPDFRequest: async function(payload, type, isFormData = false) {
        try {
            const options = {
                method: 'POST',
                body: isFormData ? payload : JSON.stringify(payload)
            };
            if (!isFormData) {
                options.headers = { 'Content-Type': 'application/json' };
            }
            const response = await this.apiRequest('/documents/generate_tutanak', {
                ...options
            });
            if (!response.ok) {
                const errData = response;
                throw new Error(errData.error || 'Backend hatası');
            }
            // --- CUPS CHECK ---
            if (response.headers.get('Content-Type').includes('application/json')) {
                const res = response;
                if (res.success) {
                    this.showToast('<i class="fas fa-print"></i> ' + res.message);
                    return;
                }
            }
            // Dosya tipini kontrol et (PDF mi XLSX mi?)
            const disposition = response.headers.get('Content-Disposition');
            const contentType = response.headers.get('Content-Type') || '';
            let isExcel = contentType.includes('spreadsheet') || (disposition && disposition.includes('.xlsx'));
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            if (isExcel) {
                // Excel dosyasını indir - kullanıcı açıp yazdıracak
                const a = document.createElement('a');
                a.href = url;
                a.download = `Tutanak_${type}_${new Date().toLocaleDateString('tr-TR')}.xlsx`;
                a.click();
                this.showToast('Doldurulmu Excel ablonu indiriliyor. Açıp yazdırabilirsiniz.');
            } else {
                // PDF'i dorudan yazdır
                this.directPrint(url);
                this.showToast('Yazdırma penceresi açılıyor...');
            }
        } catch (e) { alert('Hata: ' + e.message); }
    },
    generateZimmetPDF: async function(format = 'pdf') {
        if (this.state.zimmetDevices.length === 0) return alert('Lütfen en az bir cihaz ekleyin.');
        const staff = document.getElementById('zimmet-staff-name').value;
        const alan = document.getElementById('zimmet-teslim-alan').value;
        const veren = document.getElementById('zimmet-teslim-eden').value;
        if (!staff || !alan || !veren) {
            return alert('Lütfen personel adı ve teslim alan/eden bilgilerini doldurun.');
        }
        this.sendPDFRequest({
            type: 'ZIMMET',
            mahal: 'Zimmet',
            data: {
                format: format,
                staff: staff,
                devices: this.state.zimmetDevices,
                alan: alan,
                veren: veren
            }
        }, 'ZIMMET');
    },
    openAddDeviceToZimmet: function() {
        document.getElementById('zimmet-device-modal').style.display = 'flex';
    },
    addDeviceToZimmet: function() {
        this.state.zimmetDevices.push({
            adet: document.getElementById('zd-adet').value,
            tip: document.getElementById('zd-tip').value || '-',
            marka: document.getElementById('zd-marka').value || '-',
            model: document.getElementById('zd-model').value || '-',
            seri: document.getElementById('zd-seri').value || '-'
        });
        document.getElementById('zimmet-device-modal').style.display = 'none';
        this.renderZimmetList();
    },
    renderZimmetList: function() {
        const list = document.getElementById('zimmet-device-list');
        if (!list) return;
        list.innerHTML = this.state.zimmetDevices.map((d, i) => `
            <div class="device-item">
                <span>${d.adet}x ${d.tip} (${d.seri})</span>
                <i class="fas fa-times" onclick="app.removeDeviceFromZimmet(${i})" style="color:red; cursor:pointer;"></i>
            </div>`).join('');
    },
    removeDeviceFromZimmet: function(i) {
        this.state.zimmetDevices.splice(i, 1);
        this.renderZimmetList();
    },
    toggleOtherHT: function() {
        const otherField = document.getElementById('ht-other-text');
        const checkbox = document.getElementById('ht-check-other');
        if (otherField && checkbox) {
            otherField.style.display = checkbox.checked ? 'block' : 'none';
        }
    },
    // 
    //  EVENT LISTENERS & NAVIGATION
    // 
    setupEventListeners: function() {
        // Global Modal Kapatma Mantıı (ESC ve Dıarı Tıklama)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const activeModal = document.querySelector('.modal-backdrop[style*="display: flex"]');
                if (activeModal) {
                    const id = activeModal.id;
                    if (id.startsWith('doc-modal-')) {
                        this.closeDocModal(id.replace('doc-modal-', ''));
                    } else if (id === 'device-add-modal') {
                        activeModal.style.display = 'none';
                    } else {
                        activeModal.style.display = 'none';
                    }
                }
            }
        });
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-backdrop')) {
                const id = e.target.id;
                if (id === 'login-overlay') return; // Login overlay dıarı tıklanarak kapanmaz
                if (id.startsWith('doc-modal-')) {
                    this.closeDocModal(id.replace('doc-modal-', ''));
                } else {
                    e.target.style.display = 'none';
                }
            }
        });
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                const view = e.target.dataset.view;
                this.navigateTo(view);
                // Lazy-load printers when tab is clicked
                if (view === 'printers' && !this.state.printers.length) {
                    this.renderPrinters();
                }
                // Load service records when tab is clicked
                if (view === 'service') {
                    this.loadServiceRecords();
                }
            });
        });
    },
    // 
    //  UTILITIES & MODALS
    // 

    openAreaModal: function(id) {
        let area = { id: '', name: '', path: '', username: '', password: '' };
        if (id) {
            area = this.state.areas.find(a => a.id == id) || area;
            document.getElementById('area-title').innerHTML = `<i class="fas fa-edit"></i> Alanı Düzenle`;
        } else {
            document.getElementById('area-title').innerHTML = `<i class="fas fa-plus"></i> Yeni Ortak Alan`;
        }
        document.getElementById('area-id').value = area.id;
        document.getElementById('area-name').value = area.name;
        document.getElementById('area-path').value = area.path;
        document.getElementById('area-username').value = area.username;
        document.getElementById('area-pass').value = area.password;
        // Admin ise silme butonunu göster
        const isAdmin = this.state.activeUser && this.state.activeUser.role === 'ADMIN';
        const deleteBtn = document.getElementById('btn-area-delete');
        if (deleteBtn) deleteBtn.style.display = (id && isAdmin) ? 'block' : 'none';
        document.getElementById('area-modal').style.display = 'flex';
    },
    deleteAreaFromModal: function() {
        const id = document.getElementById('area-id').value;
        if (id) {
            this.deleteArea(id);
        }
    },
    deleteArea: async function(id) {
        if (!confirm('Bu ortak alan kaydını sistemden silmek istediinize emin misiniz?')) return;
        try {
            const resp = await this.apiRequest('/areas/delete/' + id, { method: 'DELETE' });
            const result = resp;
            if (result.error) throw new Error(result.error);
            document.getElementById('area-modal').style.display = 'none';
            this.showToast('Ortak alan kaydı silindi.');
            this.loadAreas();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    saveArea: async function() {
        const payload = {
            id: document.getElementById('area-id').value,
            name: document.getElementById('area-name').value,
            path: document.getElementById('area-path').value,
            username: document.getElementById('area-username').value,
            password: document.getElementById('area-pass').value
        };
        if (!payload.name) return alert("A Adı zorunludur.");
        const endpoint = payload.id ? `/areas/update/${payload.id}` : '/areas/add';
        const method = payload.id ? 'PUT' : 'POST';
        try {
            const resp = await this.apiRequest(endpoint, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = resp;
            if (result.error) throw new Error(result.error);
            document.getElementById('area-modal').style.display = 'none';
            this.showToast('Ortak alan kaydedildi!');
            this.loadAreas();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    normalizeFaultyStatus: function(item) {
        if (!item) return false;
        let val = item.is_faulty !== undefined ? item.is_faulty : item.is_faulty;
        return this.isTrue(val) || item.status === 'ARIZALI' || item.status === 'Arızalı';
    },
    isTrue: function(v) {
        return v && v !== '' && v !== '0' && v !== 0;
    },
    copyToClipboard: function(text) {
        if (!text) return;
        // Modern Clipboard API
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(() => {
                this.showToast('Kopyalandı!');
            }).catch(err => {
                this.copyFallback(text);
            });
        } else {
            this.copyFallback(text);
        }
    },
    copyFallback: function(text) {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            this.showToast('Kopyalandı!');
        } catch (err) {
            console.error('Kopyalama hatası:', err);
        }
        document.body.removeChild(textArea);
    },
    togglePass: function(idx, pwd) {
        const el = document.getElementById(`pass-${idx}`);
        if(el.innerText === '********') el.innerText = pwd;
        else el.innerText = '********';
    },
    showQR: function(id) {
        alert('QR Code ID: ' + id);
    },
    showToast: function(message, type = 'success') {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        let icon = 'fa-check-circle';
        if (type === 'error') icon = 'fa-exclamation-circle';
        else if (type === 'warning') icon = 'fa-exclamation-triangle';
        else if (type === 'info') icon = 'fa-info-circle';
        toast.innerHTML = `<i class="fas ${icon}"></i> <span>${message}</span>`;
        document.body.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('show'));
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 400);
        }, 3500);
    },
    // 
    //  USER MANAGEMENT
    // 
    loadUsers: async function() {
        const tbody = document.getElementById('users-table-body');
        if (!tbody) return;
        try {
            const resp = await this.apiRequest('/users/get_all');
            const users = resp;
            tbody.innerHTML = users.map(u => {
                const created = u.created_at ? u.created_at : '-';
                const lastLog = u.last_login ? u.last_login : '-';
                return `
                <tr>
                    <td style="font-weight:600;">${u.username}</td>
                    <td>${u.display_name}</td>
                    <td><span class="role-badge" style="background: rgba(255,255,255,0.2);">${u.role}</span></td>
                    <td style="font-size:0.75rem; opacity:0.6;">${created}</td>
                    <td style="font-size:0.75rem; color:var(--accent);">${lastLog}</td>
                    <td style="text-align: right;">
                        <div class="flex-row gap-2" style="justify-content: flex-end;">
                            <button class="btn-chip" onclick="app.openEditUserModal(${u.id}, '${u.username}', '${u.display_name}', '${u.role}', ${u.permissions ? `'${u.permissions}'` : 'null'})"><i class="fas fa-edit"></i></button>
                            <button class="btn-chip" onclick="app.deleteUser(${u.id})" style="color:#ff4b2b;"><i class="fas fa-trash"></i></button>
                        </div>
                    </td>
                </tr>`;
            }).join('');
        } catch(e) { console.error('Kullanıcılar yüklenemedi:', e); }
    },
    openAddUserModal: function() {
        document.getElementById('user-modal-title').innerHTML = '<i class="fas fa-user-plus"></i> Yeni Kullanıcı';
        document.getElementById('user-edit-id').value = '';
        document.getElementById('user-username').value = '';
        document.getElementById('user-username').disabled = false;
        document.getElementById('user-displayname').value = '';
        document.getElementById('user-password').value = '';
        document.getElementById('user-password').placeholder = 'Şifre';
        document.getElementById('user-role').value = 'EDITOR';
        this.handleUserRoleChange('EDITOR');
        
        // Temizlik: Önceki düzenlemelerden kalan özel yetkileri sıfırla
        const container = document.getElementById('user-permissions-container');
        if (container) {
            container.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
        }
        
        document.getElementById('user-modal').style.display = 'flex';
    },
    handleUserRoleChange: function(role) {
        const container = document.getElementById('user-permissions-container');
        if (role === 'OTHER') {
            container.style.display = 'block';
        } else {
            container.style.display = 'none';
        }
    },
    openEditUserModal: function(id, username, displayName, role, permissions) {
        document.getElementById('user-modal-title').innerHTML = '<i class="fas fa-user-edit"></i> Kullanıcı Düzenle';
        document.getElementById('user-edit-id').value = id;
        document.getElementById('user-username').value = username;
        document.getElementById('user-username').disabled = true;
        document.getElementById('user-displayname').value = displayName;
        document.getElementById('user-password').value = '';
        document.getElementById('user-password').placeholder = 'Yeni ifre (bo bırakılırsa deimez)';
        document.getElementById('user-role').value = role;
        this.handleUserRoleChange(role);
        // Checkboxları doldur
        const container = document.getElementById('user-permissions-container');
        const checks = container.querySelectorAll('input[type="checkbox"]');
        let allowed = [];
        try { allowed = permissions ? JSON.parse(permissions) : []; } catch(e) { console.error(e); }
        checks.forEach(cb => {
            cb.checked = allowed.includes(cb.value);
        });
        document.getElementById('user-modal').style.display = 'flex';
    },
    saveUser: async function() {
        const editId = document.getElementById('user-edit-id').value;
        const username = document.getElementById('user-username').value;
        const displayName = document.getElementById('user-displayname').value;
        const password = document.getElementById('user-password').value;
        const role = document.getElementById('user-role').value;
        if (!displayName) return alert('Görünen ad zorunludur.');
        try {
            let permissions = null;
            if (role === 'OTHER') {
                const container = document.getElementById('user-permissions-container');
                const checks = container.querySelectorAll('input[type="checkbox"]:checked');
                permissions = JSON.stringify(Array.from(checks).map(c => c.value));
            }
            let resp;
            if (editId) {
                // Güncelle
                const payload = { display_name: displayName, role: role, permissions: permissions };
                if (password) payload.password = password;
                resp = await this.apiRequest('/users/update/' + editId, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } else {
                // Yeni ekle
                if (!username || !password) return alert('Kullanıcı adı ve ifre zorunludur.');
                resp = await this.apiRequest('/users/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password, display_name: displayName, role, permissions })
                });
            }
            const result = resp;
            if (result.error) throw new Error(result.error);
            document.getElementById('user-modal').style.display = 'none';
            this.showToast(editId ? 'Kullanıcı güncellendi!' : 'Kullanıcı eklendi!');
            this.loadUsers();
        } catch(e) { alert('Hata: ' + e.message); }
    },
    deleteUser: async function(id) {
        if (!confirm('Bu kullanıcıyı silmek istediinize emin misiniz?')) return;
        try {
            const resp = await this.apiRequest('/users/delete/' + id, { method: 'DELETE' });
            const result = resp;
            if (result.error) throw new Error(result.error);
            this.showToast('Kullanıcı silindi.');
            this.loadUsers();
        } catch(e) { alert('Hata: ' + e.message); }
    },
    loadAdminReportsCategories: async function() {
        try {
            const resp = await this.apiRequest('/admin/reports/categories');
            const select = document.getElementById('admin-reports-category-filter');
            if (select && resp.success) {
                select.innerHTML = '<option value="">Tüm Kategoriler</option>';
                resp.categories.forEach(cat => {
                    select.innerHTML += `<option value="${cat.id}">${cat.name}</option>`;
                });
            }
            this.loadAdminReportsList();
        } catch(e) {
            console.error("Kategoriler yüklenirken hata oluştu:", e);
        }
    },
    loadAdminReportsList: async function() {
        try {
            const listDiv = document.getElementById('admin-reports-file-list');
            if (!listDiv) return;
            
            listDiv.innerHTML = '<div style="text-align: center; opacity: 0.5; padding: 30px;"><i class="fas fa-spinner fa-spin"></i> Raporlar yükleniyor...</div>';
            
            const category = document.getElementById('admin-reports-category-filter').value;
            const resp = await this.apiRequest(`/admin/reports/list?category=${category}`);
            
            if (!resp.success || !resp.items || resp.items.length === 0) {
                listDiv.innerHTML = '<div style="text-align: center; opacity: 0.5; padding: 30px;">Gösterilecek rapor veya log bulunmamaktadır.</div>';
                return;
            }
            
            listDiv.innerHTML = '';
            resp.items.forEach(file => {
                const sizeKB = (file.size / 1024).toFixed(1);
                const fileIcon = file.type === 'md' ? 'fa-file-markdown' : 'fa-file-lines';
                const iconColor = file.type === 'log' ? '#ffb400' : (file.type === 'md' ? '#00d2ff' : '#ccc');
                
                const itemHtml = `
                    <div class="admin-report-item" style="display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 8px 12px; cursor: pointer; transition: all 0.2s;" 
                         onclick="app.selectAdminReport('${file.file_id}', '${file.file_name}')" id="report-${file.file_id}">
                        <div style="display: flex; align-items: center; gap: 10px; overflow: hidden; width: 80%;">
                            <i class="fas ${fileIcon}" style="color: ${iconColor};"></i>
                            <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                <span style="font-weight: 600; font-size: 0.85rem; color: #eee; display: block;">${file.file_name}</span>
                                <span style="font-size: 0.7rem; color: var(--text-secondary);">${file.modified_at}</span>
                            </div>
                        </div>
                        <span style="font-size: 0.75rem; color: #888;">${sizeKB} KB</span>
                    </div>
                `;
                listDiv.innerHTML += itemHtml;
            });
        } catch(e) {
            console.error("Rapor listesi yüklenirken hata oluştu:", e);
        }
    },
    state_admin_reports: {
        selected_file_id: null,
        selected_file_name: ''
    },
    selectAdminReport: function(file_id, file_name) {
        this.stopLiveConsoleStream();
        document.querySelectorAll('.admin-report-item').forEach(el => {
            el.style.background = 'rgba(255,255,255,0.02)';
            el.style.borderColor = 'rgba(255,255,255,0.05)';
        });
        
        const selectedEl = document.getElementById(`report-${file_id}`);
        if (selectedEl) {
            selectedEl.style.background = 'rgba(0, 210, 255, 0.08)';
            selectedEl.style.borderColor = 'var(--accent)';
        }
        
        this.state_admin_reports.selected_file_id = file_id;
        this.state_admin_reports.selected_file_name = file_name;
        
        const actionsToolbar = document.getElementById('admin-reports-viewer-actions');
        if (actionsToolbar) actionsToolbar.style.display = 'flex';
        
        this.viewAdminReportTail();
    },
    viewAdminReportTail: async function() {
        const file_id = this.state_admin_reports.selected_file_id;
        const file_name = this.state_admin_reports.selected_file_name;
        if (!file_id) return;
        
        const titleEl = document.getElementById('admin-reports-viewer-title');
        const contentEl = document.getElementById('admin-reports-viewer-content');
        if (titleEl) titleEl.innerText = file_name;
        if (contentEl) contentEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Dosya okunuyor...';
        
        try {
            const lines = document.getElementById('admin-reports-tail-lines').value;
            const resp = await this.apiRequest(`/admin/reports/tail?file_id=${file_id}&lines=${lines}`);
            if (contentEl) {
                if (resp.success) {
                    contentEl.textContent = resp.content || '(Boş)';
                } else {
                    contentEl.textContent = "Hata: " + (resp.error || "Dosya okunamadı.");
                }
            }
        } catch(e) {
            if (contentEl) contentEl.textContent = "Bağlantı Hatası: " + e.message;
        }
    },
    viewAdminReportFull: async function() {
        const file_id = this.state_admin_reports.selected_file_id;
        const file_name = this.state_admin_reports.selected_file_name;
        if (!file_id) return;
        
        const titleEl = document.getElementById('admin-reports-viewer-title');
        const contentEl = document.getElementById('admin-reports-viewer-content');
        if (titleEl) titleEl.innerText = `${file_name} (Tam Görünüm)`;
        if (contentEl) contentEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Dosyanın tamamı yükleniyor...';
        
        try {
            const resp = await this.apiRequest(`/admin/reports/view?file_id=${file_id}`);
            if (contentEl) {
                if (resp.success) {
                    contentEl.textContent = resp.content || '(Boş)';
                } else {
                    contentEl.textContent = "Hata: " + (resp.error || "Büyük dosyalar doğrudan yüklenemez, lütfen 'tail' özelliğini kullanın.");
                }
            }
        } catch(e) {
            if (contentEl) contentEl.textContent = "Bağlantı Hatası: " + e.message;
        }
    },
    toggleLiveConsoleStream: function() {
        if (this.state_admin_reports.live_stream_interval) {
            this.stopLiveConsoleStream();
        } else {
            this.startLiveConsoleStream();
        }
    },
    startLiveConsoleStream: function() {
        this.stopLiveConsoleStream(); // Temiz bir başlangıç
        
        const btn = document.getElementById('btn-admin-reports-live-console');
        if (btn) btn.classList.add('btn-live-active');
        
        // Canlı akış sırasında normal dosya seçeneklerini gizle (tam dosya indirme/tail limitleri)
        const actionsToolbar = document.getElementById('admin-reports-viewer-actions');
        if (actionsToolbar) actionsToolbar.style.display = 'none';
        
        // Pulsing dot ve başlık güncelleme
        const titleEl = document.getElementById('admin-reports-viewer-title');
        if (titleEl) {
            titleEl.innerHTML = '<span class="live-pulse">●</span> Canlı Sunucu Konsolu';
        }
        
        // Soldaki dosya listesinden seçili olanların stilini temizle
        document.querySelectorAll('.admin-report-item').forEach(el => {
            el.style.background = 'rgba(255,255,255,0.02)';
            el.style.borderColor = 'rgba(255,255,255,0.05)';
        });
        
        const liveFileId = 'bG9ncy9zZXJ2ZXJfY29uc29sZS5sb2c='; // Base64 encoding of 'logs/server_console.log'
        this.state_admin_reports.selected_file_id = liveFileId;
        this.state_admin_reports.selected_file_name = 'server_console.log';
        
        const contentEl = document.getElementById('admin-reports-viewer-content');
        if (contentEl) {
            contentEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Canlı sunucu konsoluna bağlanılıyor...';
        }
        
        const fetchLiveConsole = async () => {
            try {
                // Son 500 satırı getir
                const resp = await this.apiRequest(`/admin/reports/tail?file_id=${liveFileId}&lines=500`);
                if (contentEl) {
                    if (resp.success) {
                        contentEl.textContent = resp.content || '(Konsol çıktısı boş)';
                        // Otomatik olarak en aşağı kaydır (Real-time cmd terminal hissi)
                        contentEl.scrollTop = contentEl.scrollHeight;
                    } else {
                        contentEl.textContent = "Hata: " + (resp.error || "Konsol çıktısı yüklenemedi.");
                    }
                }
            } catch (e) {
                if (contentEl) contentEl.textContent = "Konsol Bağlantı Hatası: " + e.message;
            }
        };
        
        // İlk veriyi hemen çek
        fetchLiveConsole();
        
        // 2 saniyede bir canlandır
        this.state_admin_reports.live_stream_interval = setInterval(fetchLiveConsole, 2000);
    },
    stopLiveConsoleStream: function() {
        if (this.state_admin_reports.live_stream_interval) {
            clearInterval(this.state_admin_reports.live_stream_interval);
            this.state_admin_reports.live_stream_interval = null;
        }
        
        const btn = document.getElementById('btn-admin-reports-live-console');
        if (btn) btn.classList.remove('btn-live-active');
        
        // Eğer hala canlı sunucu başlığı aktifse temizle
        const titleEl = document.getElementById('admin-reports-viewer-title');
        if (titleEl && titleEl.innerHTML.includes('Canlı Sunucu Konsolu')) {
            titleEl.innerText = 'Seçilen Rapor Dosyası';
            
            const contentEl = document.getElementById('admin-reports-viewer-content');
            if (contentEl) {
                contentEl.innerText = 'Log dosyası görüntülemek için soldan bir dosya seçin.';
            }
        }
    },
    // 
    //  AUDIT LOGS
    // 
    loadAuditLogs: async function() {
        const tbody = document.getElementById('logs-tbody');
        if (!tbody) return;
        const userEl = document.getElementById('log-filter-user');
        const tableEl = document.getElementById('log-filter-table');
        const user = userEl ? userEl.value : '';
        const table = tableEl ? tableEl.value : '';
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; opacity:0.5; padding:20px;"><i class="fas fa-spinner fa-spin"></i> Yükleniyor...</td></tr>';
        try {
            const resp = await this.apiRequest(`/logs/get_all?user=${user}&table=${table}`);
            const data = resp;
            this.state.auditLogs = data;
            if (userEl && userEl.options.length <= 1) {
                const users = [...new Set(data.map(l => l.changed_by).filter(Boolean))];
                users.forEach(u => {
                    const opt = document.createElement('option');
                    opt.value = u; opt.text = u;
                    userEl.add(opt);
                });
            }
            if (!data.length) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; opacity:0.5; padding:30px;"><i class="fas fa-check-circle" style="color:#00ff88;"></i> İşlem geçmişi temiz.</td></tr>';
                return;
            }
            const fieldNameMap = {
                'is_faulty': 'Arızalı Durumu',
                'sahada': 'Saha Durumu',
                'mahal': 'Mahal / Lokasyon',
                'ip': 'IP Adresi',
                'seri': 'Seri No',
                'model': 'Model',
                'pr_no': 'PR Numarası',
                'rdp': 'Uzak Masaüstü',
                'location_code': 'Lokasyon Kodu',
                'scanner_serial': 'Tarayıcı Seri No',
                'by_serial': 'Eski Seri No',
                'status': 'Durum',
                'personnel': 'Personel',
                'brand': 'Marka',
                'mac': 'MAC Adresi',
                'is_deleted': 'Silinme Durumu',
                'category': 'Kategori',
                'current_stock': 'Mevcut Stok',
                'critical_stock': 'Kritik Stok'
            };

            tbody.innerHTML = data.map(l => {
                const date = l.timestamp ? l.timestamp.replace('T', ' ').split('.')[0] : '-';
                const cleanOld = (l.old_value || '-').replace('Sahada Kurulu', 'KURULU');
                const cleanNew = (l.new_value || '-').replace('Sahada Kurulu', 'KURULU');
                const friendlyFieldName = fieldNameMap[l.field_name] || l.field_name;
                return `
                <tr>
                    <td style="font-size:0.75rem; white-space:nowrap;">${date}</td>
                    <td><span class="badge" style="background:rgba(0,186,255,0.1); color:var(--accent);">${l.display_name || l.changed_by}</span></td>
                    <td style="font-size:0.75rem;">${l.client_ip || '-'}</td>
                    <td style="font-weight:600;">${l.record_label || l.record_id}</td>
                    <td style="color:var(--text-secondary);">${friendlyFieldName}</td>
                    <td style="color:#ff4b2b; text-decoration:line-through; font-size:0.8rem; opacity:0.7;">${cleanOld}</td>
                    <td style="color:#00ff88; font-weight:600;">${cleanNew}</td>
                </tr>`;
            }).join('');
        } catch (e) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:#ff4b2b;">Yükleme hatası.</td></tr>';
        }
    },
    clearAllLogs: async function() {
        if (!confirm('DİKKAT: Tüm ilem geçmii (audit log) kalıcı olarak silinecektir. Onaylıyor musunuz?')) return;
        try {
            const resp = await this.apiRequest('/logs/clear_all', { method: 'DELETE' });
            const result = resp;
            if (result.error) throw new Error(result.error);
            this.showToast(result.message || 'Geçmi temizlendi.');
            // Listeyi sıfırla
            const tbody = document.getElementById('logs-tbody');
            if (tbody) tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; opacity:0.5; padding:30px;"><i class="fas fa-check-circle" style="color:#00ff88;"></i> İşlem geçmişi temiz.</td></tr>';
            // Kullanıcı filtresini de sıfırla
            const userEl = document.getElementById('log-filter-user');
            if (userEl) { while(userEl.options.length > 1) userEl.remove(1); }
        } catch (e) { alert('Hata: ' + e.message); }
    },
    clearDepotTransactions: async function() {
        if (!confirm('DİKKAT: Tüm stok hareketleri (warehouse geçmii) kalıcı olarak silinecektir. Onaylıyor musunuz?')) return;
        try {
            const resp = await this.apiRequest('/depot/clear_transactions', { method: 'DELETE' });
            const result = resp;
            if (result.error) throw new Error(result.error);
            this.showToast(result.message || 'Depo geçmii temizlendi.');
            this.loadDepot();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    // 
    //  INVENTORY COUNTING MODE
    // 
    toggleCountMode: function() {
        if (!['ADMIN', 'EDITOR'].includes(this.state.activeUser.role)) {
            return alert('Sayım modunu sadece Admin ve Editörler kullanabilir.');
        }
        this.state.countMode = !this.state.countMode;
        const controls = document.getElementById('count-mode-controls');
        const btn = document.getElementById('btn-count-mode');
        if (this.state.countMode) {
            controls.style.display = 'block';
            btn.classList.add('active');
            btn.style.background = 'linear-gradient(135deg, #b829ff, #00d2ff)';
            btn.style.color = '#fff';
            btn.style.borderColor = 'transparent';
            btn.style.boxShadow = '0 0 15px rgba(184, 41, 255, 0.5), inset 0 0 5px rgba(255,255,255,0.2)';
            // Sıralama butonlarını ekle
            controls.innerHTML = `
                <div class="flex-between" style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid var(--accent); margin-bottom: 20px;">
                    <span style="font-size: 0.85rem; font-weight: 600;"><i class="fas fa-list-ol"></i> SAYIM SIRALAMASI:</span>
                    <div class="flex-row gap-2">
                        <button class="btn-chip" onclick="app.sortInventory('location_code')">MAHAL KODUNA GRE</button>
                        <button class="btn-chip" onclick="app.sortInventory('floor')">KATA GRE</button>
                        <button class="btn btn-secondary" onclick="app.resetCount()" style="padding: 2px 10px; font-size: 0.7rem; border-color: #ff4b2b; color: #ff4b2b;">
                            <i class="fas fa-undo"></i> Sayımı Sıfırla
                        </button>
                    </div>
                </div>
            `;
            this.showToast('Sayım modu aktif! Cihazları iaretleyin.');
        } else {
            controls.style.display = 'none';
            btn.classList.remove('active');
            btn.style.background = '';
            btn.style.color = '';
            btn.style.borderColor = '';
            btn.style.boxShadow = '';
        }
        this.filterInventory();
    },
    sortInventory: function(by) {
        if (!this.state.countMode) return;
        const sorted = [...this.state.lastFilteredList].sort((a, b) => {
            const valA = (a[by] || '').toString();
            const valB = (b[by] || '').toString();
            return valA.localeCompare(valB, 'tr', { numeric: true });
        });
        this.state.lastFilteredList = sorted;
        this.renderInventory(sorted);
        this.showToast(`Sıralandı: ${by === 'floor' ? 'Kat' : 'Mahal Kodu'}`);
    },
    markCounted: async function(id) {
        if (!this.state.countMode) return;
        try {
            const resp = await this.apiRequest('/inventory/count', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: id,
                    counted_by: this.state.activeUser.display_name || this.state.activeUser.name
                })
            });
            const result = resp;
            if (result.error) throw new Error(result.error);
            // Yerelde güncelle
            const item = this.state.inventory.find(i => i.id == id);
            if (item) {
                item.last_counted_at = new Date().toISOString();
                item.counted_by = this.state.activeUser.display_name || this.state.activeUser.name;
            }
            this.renderInventory(this.state.lastFilteredList.length > 0 ? this.state.lastFilteredList : this.state.inventory);
            this.showToast('Cihaz sayıldı.');
        } catch (e) { alert('Hata: ' + e.message); }
    },
    toggleLiveMode: function() {
        this.state.liveMode = !this.state.liveMode;
        const btn = document.getElementById('btn-live-mode');
        
        if (this.state.liveMode) {
            btn.classList.add('active');
            // Dashboard'dayken her 30 saniyede bir verileri yenile
            this.liveModeInterval = setInterval(() => {
                if (this.state.view === 'dashboard') {
                    this.loadDashboardStats();
                }
            }, 30000);
            this.showToast('Canlı Veri Modu Aktif (30 sn yenileme)');
            this.loadDashboardStats(); 
        } else {
            btn.classList.remove('active');
            if (this.liveModeInterval) {
                clearInterval(this.liveModeInterval);
                this.liveModeInterval = null;
            }
            this.showToast('Canlı Veri Modu Kapatıldı');
        }
    },
    resetCount: async function() {
        if (!confirm('TM sayım verileri sıfırlanacak! Yeni bir sayım dönemine balamak istediinize emin misiniz?')) return;
        try {
            const resp = await this.apiRequest('/inventory/count/reset', { method: 'POST' });
            const result = resp;
            if (result.error) throw new Error(result.error);
            this.state.inventory.forEach(i => {
                i.last_counted_at = null;
                i.counted_by = null;
            });
            this.renderInventory(this.state.inventory);
            this.showToast('Tüm sayım verileri sıfırlandı.');
        } catch (e) { alert('Hata: ' + e.message); }
    },
    // 
    //  HISTORY CAROUSEL LOGIC
    // 
    setStateFromRole: function() {
        if (!this.state.activeUser) return;
        const isAdmin = this.state.activeUser.role === 'ADMIN';
        const logNav = document.getElementById('nav-logs');
        if (logNav) logNav.style.display = isAdmin ? 'block' : 'none';
        const userNav = document.getElementById('nav-users');
        if (userNav) userNav.style.display = isAdmin ? 'block' : 'none';
        const userMenuBtn = document.getElementById('menu-users');
        if (userMenuBtn) userMenuBtn.style.display = isAdmin ? 'block' : 'none';
        const keyosSyncBtn = document.getElementById('menu-keyos-sync');
        if (keyosSyncBtn) keyosSyncBtn.style.display = isAdmin ? 'block' : 'none';
        const keyosReportBtn = document.getElementById('menu-keyos-report');
        if (keyosReportBtn) keyosReportBtn.style.display = isAdmin ? 'block' : 'none';
    },
    closeHistoryModal: function() {
        document.getElementById('history-modal').style.display = 'none';
    },
    moveHistory: function(dir) {
        const next = this.state.currentHistoryIndex + dir;
        if (next >= 0 && next < this.state.historyItems.length) {
            this.state.currentHistoryIndex = next;
            this.renderHistoryCarousel();
        }
    },
    renderHistoryCarousel: function() {
        const container = document.getElementById('history-carousel-content');
        const items = this.state.historyItems;
        if (!items || items.length === 0) {
            container.innerHTML = '<div style="padding:40px; text-align:center; width:100%; opacity:0.5;">Bu ürün için henüz bir deiiklik kaydı bulunmuyor.</div>';
            document.getElementById('carousel-dots').innerHTML = '';
            return;
        }
        container.innerHTML = items.map((item, idx) => {
            const dateStr = item.created_at ? (isNaN(new Date(item.created_at)) ? item.created_at : new Date(item.created_at).toLocaleString('tr-TR')) : '-';
            const offset = (idx - this.state.currentHistoryIndex) * 100;
            return `
            <div class="history-card" style="position: absolute; left: 0; width: 100%; transform: translateX(${offset}%); transition: transform 0.5s ease; ${idx === this.state.currentHistoryIndex ? 'opacity:1; visibility:visible;' : 'opacity:0; visibility:hidden;'}">
                <div class="field-name">${item.field_name || 'Bilinmeyen Alan'}</div>
                <div class="change-vals">
                    <div class="old-val">${item.old_value || '-'}</div>
                    <div class="arrow-icon"><i class="fas fa-arrow-right"></i></div>
                    <div class="new-val">${item.new_value || '-'}</div>
                </div>
                <div class="meta" style="margin-top: 20px;">
                    <span><i class="fas fa-user-edit"></i> ${item.display_name || item.changed_by}</span>
                    <span><i class="fas fa-calendar-day"></i> ${dateStr.split(' ')[0]}</span>
                </div>
            </div>`;
        }).join('');
    },
    setHistoryIndex: function(idx) {
        this.state.currentHistoryIndex = idx;
        this.renderHistoryPopup();
    },
    openHistoryPopup: async function(id, type, event) {
        event.stopPropagation();
        const popup = document.getElementById('history-popup');
        const icon = event.currentTarget;
        const rect = icon.getBoundingClientRect();
        // Dier popup'ları kapat ve temizle
        popup.style.display = 'none';
        popup.innerHTML = '<div style="text-align:center;"><i class="fas fa-spinner fa-spin"></i></div>';
        // Pozisyonu belirle
        popup.style.top = `${window.scrollY + rect.bottom + 10}px`;
        popup.style.left = `${window.scrollX + rect.left - 240}px`;
        popup.style.display = 'block';
        try {
            let table = 'pcs';
            if (this.state.invCategory === 'TABLET') table = 'tablets';
            if (this.state.invCategory === 'MONITOR') table = 'monitors';
            if (type !== 'pc') table = type;
            const resp = await this.apiRequest(`/logs/get_record_history/${table}/${id}`);
            const logs = resp;
            this.state.historyItems = logs;
            this.state.currentHistoryIndex = 0;
            if (!logs || logs.length === 0) {
                popup.innerHTML = '<div style="font-size:0.8rem; opacity:0.5; padding:10px;">Henüz geçmi kaydı yok.</div>';
            } else {
                this.renderHistoryPopup();
            }
            // Dıarı tıklayınca kapatma
            const closeHandler = (e) => {
                if (!popup.contains(e.target) && e.target !== icon) {
                    popup.style.display = 'none';
                    document.removeEventListener('click', closeHandler);
                }
            };
            setTimeout(() => document.addEventListener('click', closeHandler), 10);
        } catch (e) {
            popup.innerHTML = '<div style="color:red; font-size:0.75rem;">Hata!</div>';
        }
    },
    renderHistoryPopup: function() {
        const popup = document.getElementById('history-popup');
        const items = this.state.historyItems;
        const idx = this.state.currentHistoryIndex;
        const item = items[idx];
        if (!item) return;
        const date = item.created_at ? (isNaN(new Date(item.created_at)) ? item.created_at : new Date(item.created_at).toLocaleString('tr-TR')) : '-';
        const avatar = item.display_name ? item.display_name[0].toUpperCase() : 'U';
        popup.innerHTML = `
            <div class="hp-header">
                <div class="hp-title">Düzenleme Geçmişi (${idx + 1}/${items.length})</div>
                <div class="hp-nav">
                    <button class="hp-nav-btn" ${idx === 0 ? 'disabled' : ''} onclick="app.navigateHistory(-1, event)" title="Daha Yeni"><i class="fas fa-chevron-left"></i></button>
                    <button class="hp-nav-btn" ${idx === items.length - 1 ? 'disabled' : ''} onclick="app.navigateHistory(1, event)" title="Daha Eski"><i class="fas fa-chevron-right"></i></button>
                </div>
            </div>
            <div class="hp-user-info">
                <div class="hp-avatar">${avatar}</div>
                <div class="hp-user-details">
                    <span class="hp-username">${username}</span>
                    <span class="hp-date">${date}</span>
                </div>
            </div>
            <div class="hp-change-box">
                <span class="hp-field">${fieldName}</span>
                <div class="hp-values">
                    ${(!item.old_value || item.old_value === '-' || item.old_value === 'None') ? 
                        `Eklenen: "${item.new_value}"` : 
                        `<span class="hp-old">${item.old_value}</span> <i class="fas fa-arrow-right" style="opacity:0.3; margin:0 4px;"></i> <span class="hp-new">${item.new_value}</span>`
                    }
                </div>
            </div>
        `;
    },
    navigateHistory: function(step, event) {
        if (event) event.stopPropagation();
        // Step logic: 1 is older (index increases), -1 is newer (index decreases)
        const nextIdx = this.state.currentHistoryIndex + step;
        if (nextIdx >= 0 && nextIdx < this.state.historyItems.length) {
            this.state.currentHistoryIndex = nextIdx;
            this.renderHistoryPopup();
        }
    },
    loadMahalList: async function() {
        const dl = document.getElementById('mahal-datalist');
        try {
            const resp = await this.apiRequest('/inventory/mahal_list');
            const data = resp;
            this.state.mahalMap = {};
            let optionsHtml = '';
            data.forEach(m => {
                this.state.mahalMap[m.location_code] = {
                    name: m.location_name,
                    phone: m.phone_number,
                    tower: (m.location_code && m.location_code.includes('.')) ? m.location_code.split('.')[0] : '',
                    floor: (m.location_code && m.location_code.includes('.')) ? m.location_code.split('.')[1] : ''
                };
                optionsHtml += `<option value="${m.location_code}">${m.location_name}</option>`;
            });
            if (dl) dl.innerHTML = optionsHtml;
        } catch (e) { console.error("Mahal listesi yüklenemedi:", e); }
    },
    downloadConnectBat: function(areaId) {
        const area = this.state.areas.find(a => a.id == areaId);
        if (!area) return;
        const setupContent = `
@echo off
set "AreaName=${area.name}"
echo [%AreaName%] Ortak Alan Kurulumu Baslatiliyor...
:: 1. Klasör oluştur
if not exist "C:\\OrtakAlan" mkdir "C:\\OrtakAlan"
:: 2. Kalıcı BAT dosyasını oluştur (C:\\OrtakAlan)
(
echo @echo off
echo set "DriveLetter=Z:"
echo set "RemotePath=${area.path}"
echo set "Username=${area.username}"
echo set "Password=${area.password}"
echo set "AreaName=${area.name}"
echo net use %%DriveLetter%% /delete /y ^>nul 2^>^&1
echo net use %%DriveLetter%% "%%RemotePath%%" /user:%%Username%% %%Password%% /persistent:yes
echo powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%%USERPROFILE%%\\\\Desktop\\\\%%AreaName%%.lnk');$s.TargetPath='%%DriveLetter%%';$s.Save()"
) > "C:\\OrtakAlan\\${area.name}.bat"
:: 3. Masaüstüne kopyala (Hem BAT dosyasını hem Kısayolu)
copy /y "C:\\OrtakAlan\\${area.name}.bat" "%USERPROFILE%\\Desktop\\${area.name}.bat" >nul
:: 4. Kayıt Defterine ekle
reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "OrtakAlan_${area.name}" /t REG_SZ /d "C:\\OrtakAlan\\${area.name}.bat" /f >nul
:: 5. alıtır
start "" "%USERPROFILE%\\Desktop\\${area.name}.bat"
echo Kurulum Tamamlandıi. Masaustunde hem BAT dosyaniz hem de Surucu kisayolunuz hazir.
timeout /t 2 >nul
(goto) 2>nul & del "%~f0"
`.trim();
        const blob = new Blob([setupContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `KURULUM_${area.name}.bat`;
        document.body.appendChild(a);
        a.click();
    },
    undoMarkCounted: async function(id) {
        if (!confirm('Bu sayımı iptal etmek istediinize emin misiniz?')) return;
        try {
            const resp = await this.apiRequest('/inventory/count/undo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id })
            });
            const result = resp;
            if (result.error) throw new Error(result.error);
            // Yerelde güncelle
            const item = this.state.inventory.find(i => i.id == id);
            if (item) {
                item.last_counted_at = null;
                item.counted_by = null;
            }
            this.renderInventory(this.state.lastFilteredList.length > 0 ? this.state.lastFilteredList : this.state.inventory);
            this.showToast('Sayım geri alındı.');
        } catch (e) { alert('Hata: ' + e.message); }
    },
    handleExclusiveCheck: function(group, id) {
        if (group === 'status') {
            const list = ['edit-on_field', 'edit-warehouse', 'edit-is_faulty', 'edit-without_location', 'edit-pending_installation'];
            list.forEach(item => { 
                const el = document.getElementById(item);
                if (el && item !== id) el.checked = false; 
            });
        } else if (group === 'os') {
            const list = ['edit-windows', 'edit-keyos'];
            list.forEach(item => { 
                const el = document.getElementById(item);
                if (el && item !== id) el.checked = false; 
            });
        }
    },
    validateDuplicateSerials: function(input) {
        const val = input.value.trim().toUpperCase();
        if (!val || val === '' || val === '---') {
            const warnEl = document.getElementById('duplicate-warning');
            if (warnEl) warnEl.style.display = 'none';
            return true;
        }
        const fieldMap = { 
            'edit-by_seri':'by_seri', 
            'edit-bo_seri':'bo_seri', 
            'edit-tarayici_seri':'tarayici_seri',
            'edit-monitor_seri':'monitor_seri',
            'edit-monitor2_seri':'monitor2_seri'
        };
        const currentId = this.state.editingId;
        // Inventory listesinde bu seri no'ye sahip BAKA bir cihaz var mı bak (BYK/KK HARF DUYARSIZ)
        const duplicate = this.state.inventory.find(i => 
            i.id != currentId && (
                (i.by_seri && i.by_seri.trim().toUpperCase() === val) || 
                (i.bo_seri && i.bo_seri.trim().toUpperCase() === val) || 
                (i.tarayici_seri && i.tarayici_seri.trim().toUpperCase() === val) ||
                (i.monitor_seri && i.monitor_seri.trim().toUpperCase() === val) ||
                (i.monitor2_seri && i.monitor2_seri.trim().toUpperCase() === val)
            )
        );
        const warnEl = document.getElementById('duplicate-warning');
        const warnText = document.getElementById('duplicate-warning-text');
        const btnSave = document.getElementById('btn-save-device');
        if (duplicate) {
            const pcLabel = duplicate.pc_no ? `PC-${duplicate.pc_no}` : `ID:${duplicate.id}`;
            if (warnText) warnText.innerText = `Bu seri numarası (${val}) zaten ${pcLabel} (${duplicate.location_name || ''}) cihazında kayıtlı! Lütfen düzeltin.`;
            if (warnEl) warnEl.style.display = 'block';
            if (btnSave) {
                btnSave.disabled = true;
                btnSave.style.opacity = '0.5';
                btnSave.style.cursor = 'not-allowed';
            }
            input.style.borderColor = '#ff4b2b';
            input.style.boxShadow = '0 0 10px rgba(255,75,43,0.3)';
            return false;
        } else {
            if (warnEl) warnEl.style.display = 'none';
            if (btnSave) {
                btnSave.disabled = false;
                btnSave.style.opacity = '1';
                btnSave.style.cursor = 'pointer';
            }
            input.style.borderColor = 'rgba(255,255,255,0.1)';
            input.style.boxShadow = 'none';
            return true;
        }
    },
    openPrinterServiceHistoryModal: async function(printerId, prNo) {
        const modal = document.getElementById('printer-service-history-modal');
        const container = document.getElementById('printer-service-history-list');
        const title = document.getElementById('printer-service-history-title');
        if (!modal || !container) return;
        title.innerHTML = `<i class="fas fa-list-check"></i> [${prNo}] Yazıcı Servis Kayıtları`;
        modal.style.display = 'flex';
        container.innerHTML = '<div style="text-align:center; padding:50px;"><i class="fas fa-spinner fa-spin fa-2x"></i></div>';
        try {
            // we filter from existing raw service records or fetch
            if (this.state_service.raw.length === 0) await this.loadServiceRecords();
            // Filter by printer_id AND pr_no (some records might only have pr_no)
            const printerObj = this.state.printers.find(p => p.id == printerId);
            const pr_no = printerObj ? printerObj.pr_no : null;
            const records = this.state_service.raw.filter(s => s.printer_id == printerId || (pr_no && s.pr_no === pr_no));
            // Sort by sent_date descending (newest first)
            records.sort((a,b) => (b.sent_date || '').localeCompare(a.sent_date || ''));
            if (records.length === 0) {
                container.innerHTML = '<div style="padding:40px; text-align:center; opacity:0.5;">Bu yazıcı için servis kaydı bulunamadı.</div>';
                return;
            }
            container.innerHTML = `
                <table style="width:100%; border-collapse: collapse; font-size: 0.85rem;">
                    <thead>
                        <tr style="border-bottom: 2px solid rgba(255,255,255,0.1); text-align:left;">
                            <th style="padding:10px;">Gidi Tarihi</th>
                            <th style="padding:10px;">Dönü Tarihi</th>
                            <th style="padding:10px;">Arıza Açıklaması</th>
                            <th style="padding:10px;">Durum</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${records.map(function(r) { return `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <td style="padding:10px; white-space:nowrap;">${app.formatDate(r.sent_date)}</td>
                                <td style="padding:10px; white-space:nowrap;">${app.formatDate(r.return_date)}</td>
                                <td style="padding:10px;">${r.fault_description || '-'}</td>
                                <td style="padding:10px;"><span class="status-badge ${r.status === 'Serviste' ? 'status-ariza' : 'status-on_field'}">${r.status}</span></td>
                            </tr>
                        `; }).join('')}
                    </tbody>
                </table>
                <div style="margin-top:20px; font-weight:700; color:var(--accent);">Toplam Servis Sayısı: ${records.length}</div>
            `;
        } catch (e) {
            container.innerHTML = '<div style="color:red; text-align:center;">Kayıtlar yüklenemedi.</div>';
        }
    },
    // 
    //  KEYOS INTEGRATION
    // 
    checkKeyOSMismatches: async function() {
        const container = document.getElementById('keyos-alerts-container');
        const list = document.getElementById('keyos-mismatch-list');
        if (!container || !list) return;
        try {
            const resp = await this.apiRequest('/keyos/check_all_mismatches');
            const data = resp;
            if (data.success && data.mismatches && data.mismatches.length > 0) {
                container.style.display = 'block';
                list.innerHTML = data.mismatches.map(m => `
                    <div class="flex-between" style="background: rgba(255,255,255,0.02); padding: 8px 12px; border-radius: 8px; border-left: 3px solid #ff4b2b; margin-bottom: 5px;">
                        <div class="flex-column">
                            <span style="font-weight:700; color:#fff; font-size:0.85rem;">PC-${m.pc_no.toString().padStart(3,'0')} Hostname Uyumazlıı</span>
                            <span style="font-size:0.7rem; opacity:0.6;">Envanter: ${m.inv_hostname || '-'} | KeyOS: ${m.keyos_hostname || '-'}</span>
                        </div>
                        <button class="btn-chip" style="color:var(--accent);" onclick="app.openDeviceDetail(${m.id}, 'pc')"><i class="fas fa-eye"></i> İncele</button>
                    </div>
                `).join('');
            } else {
                container.style.display = 'none';
            }
        } catch (e) { console.error("KeyOS mismatch check failed:", e); }
    },
    openKeyOSEditModal: function() {
        const item = this.state.inventory.find(i => i.id == this.state.editingId);
        if (!item) return;
        document.getElementById('keyos-edit-hostname').value = item.hostname || '';
        document.getElementById('keyos-sys-hostname').value = item.hostname || ''; 
        document.getElementById('keyos-edit-mahal').value = item.location_code || '';
        // Initial format check
        this.formatKeyOSMahal(document.getElementById('keyos-edit-mahal'));
        document.getElementById('keyos-edit-modal').style.display = 'flex';
    },
    formatKeyOSMahal: function(input) {
        if (!input.value) return;
        // Mahaller KeyOS'ta nokta yerine tire ile tutulur
        input.value = input.value.replace(/\./g, '-').toUpperCase();
    },
    executeKeyOSUpdate: async function() {
        const btn = document.getElementById('btn-execute-keyos-update');
        const user = document.getElementById('keyos-admin-user').value;
        const pass = document.getElementById('keyos-admin-pass').value;
        const hostname = document.getElementById('keyos-edit-hostname').value;
        const placeId = document.getElementById('keyos-edit-mahal').value;
        const item = this.state.inventory.find(i => i.id == this.state.editingId);
        if (!item || !item.pc_serial) return alert('Seri numarası bulunamadı.');
        if (!user || !pass) return alert('KeyOS yetkili kullanıcı adı ve ifre gereklidir.');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Güncelleniyor...';
        try {
            const resp = await this.apiRequest('/keyos/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    serial: item.pc_serial,
                    hostname: hostname,
                    placeId: placeId,
                    keyos_user: user,
                    keyos_pass: pass
                })
            });
            const result = resp;
            if (result.success) {
                this.showToast('KeyOS baarıyla güncellendi.');
                document.getElementById('keyos-edit-modal').style.display = 'none';
                this.checkKeyOSMismatches(); // Refresh alerts
            } else {
                throw new Error(result.error || 'Bilinmeyen bir hata oluştu.');
            }
        } catch (e) {
            alert('KeyOS Güncelleme Hatası: ' + e.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-save"></i> KeyOS\'u Güncelle';
        }
    },
    // 
    //  MANUAL KEYOS SYNC
    // 
    manualKeyOSSync: async function() {
        if (this.state.activeUser.role !== 'ADMIN') return;
        const btn = document.getElementById('menu-keyos-sync');
        const icon = btn ? btn.querySelector('i') : null;
        if (icon) icon.classList.add('fa-spin');
        try {
            this.showToast('KeyOS MGT ile senkronizasyon balatıldı. Lütfen bekleyin (bu işlem 2-3 dakika sürebilir)...', 'info');
            const resp = await this.apiRequest('/keyos/manual_sync', { method: 'POST' });
            const result = resp;
            if (result.error) throw new Error(result.error);
            this.showToast(`Senkronizasyon Başarılı! Rapor yükleniyor...`);
            this.showKeyOSReportModal();
            this.checkKeyOSMismatches();
        } catch (e) {
            alert('Senkronizasyon Hatası: ' + e.message);
        } finally {
            if (icon) setTimeout(() => icon.classList.remove('fa-spin'), 1000);
        }
    },
    showKeyOSReportModal: async function() {
        try {
            const resp = await this.apiRequest('/keyos/last_report', { method: 'GET' });
            if (!resp.success) {
                alert('Rapor bulunamadı: ' + (resp.message || resp.error));
                return;
            }
            this.keyosReports = resp.reports || [];
            if (this.keyosReports.length === 0) {
                alert('Henüz rapor oluşturulmamış.');
                return;
            }
            
            const sel = document.getElementById('keyos-report-selector');
            if (sel) {
                sel.innerHTML = '';
                this.keyosReports.forEach((rep, idx) => {
                    const opt = document.createElement('option');
                    opt.value = idx;
                    opt.textContent = rep.timestamp + (idx === 0 ? ' (En Son)' : ' (Önceki)');
                    sel.appendChild(opt);
                });
            }
            
            this.renderKeyOSReportFromIndex(0);
            this.switchKeyOSTab('success');
            this.navigateTo('keyos-report');
        } catch (e) {
            console.error(e);
            alert('Rapor yüklenemedi!');
        }
    },

    renderKeyOSReportFromIndex: function(index) {
        if (!this.keyosReports || !this.keyosReports[index]) return;
        const data = this.keyosReports[index];
        
        document.getElementById('keyos-stat-success').textContent = data.updated_count || 0;
        document.getElementById('keyos-stat-failed').textContent = data.failed_count || 0;
        document.getElementById('keyos-stat-mismatch').textContent = data.mismatch_count || 0;
        
        const succTbody = document.getElementById('keyos-table-success');
        let succHtml = '';
        (data.successful || []).forEach(r => {
            succHtml += `<tr><td>${r.pc_no}</td><td>${r.serial}</td><td>${r.ip}</td><td>${r.mac}</td><td>${r.printers}</td></tr>`;
        });
        succTbody.innerHTML = succHtml;

        const failTbody = document.getElementById('keyos-table-failed');
        let failHtml = '';
        (data.failed || []).forEach(r => {
            failHtml += `<tr><td>${r.pc_no}</td><td>${r.serial}</td><td>Bulunamadı / Bağlantı Koptu</td></tr>`;
        });
        failTbody.innerHTML = failHtml;

        const misTbody = document.getElementById('keyos-table-mismatch');
        let misHtml = '';
        (data.mismatches || []).forEach(r => {
            misHtml += `<tr><td>${r.pc_no}</td><td style="color:#ff4b2b;">${r.local_hostname}</td><td style="color:#00ff88;">${r.keyos_hostname}</td></tr>`;
        });
        misTbody.innerHTML = misHtml;
    },

    switchKeyOSTab: function(tabName) {
        document.getElementById('keyos-tab-success').style.display = tabName === 'success' ? 'block' : 'none';
        document.getElementById('keyos-tab-failed').style.display = tabName === 'failed' ? 'block' : 'none';
        document.getElementById('keyos-tab-mismatch').style.display = tabName === 'mismatch' ? 'block' : 'none';
    },

    exportKeyosReportToExcel: async function() {
        if (!this.keyosReports || this.keyosReports.length === 0) {
            alert('Dışa aktarılacak rapor bulunamadı.');
            return;
        }
        
        try {
            const sel = document.getElementById('keyos-report-selector');
            const idx = sel && sel.value ? parseInt(sel.value) : 0;
            const data = this.keyosReports[idx];
            
            if (!data) return;

            // ExcelJS kütüphanesini kullanarak gerçek bir .xlsx dosyası oluşturalım
            const wb = new ExcelJS.Workbook();
            
            // 1. Başarılı Sekmesi
            const wsSuccess = wb.addWorksheet('Başarılı Güncellemeler');
            wsSuccess.columns = [
                { header: 'Kodu', key: 'pc_no', width: 15 },
                { header: 'Seri No', key: 'serial', width: 20 },
                { header: 'IP Adresi', key: 'ip', width: 15 },
                { header: 'MAC', key: 'mac', width: 20 },
                { header: 'Yazıcılar', key: 'printers', width: 35 }
            ];
            (data.successful || []).forEach(r => wsSuccess.addRow(r));
            wsSuccess.getRow(1).font = { bold: true };

            // 2. Hatalı Sekmesi
            const wsFailed = wb.addWorksheet('Hatalı (Bulunamayan)');
            wsFailed.columns = [
                { header: 'Kodu', key: 'pc_no', width: 15 },
                { header: 'Seri No', key: 'serial', width: 20 },
                { header: 'Durum', key: 'durum', width: 40 }
            ];
            (data.failed || []).forEach(r => {
                wsFailed.addRow({ pc_no: r.pc_no, serial: r.serial, durum: 'Bulunamadı / Bağlantı Koptu' });
            });
            wsFailed.getRow(1).font = { bold: true };

            // 3. Uyuşmazlık Sekmesi
            const wsMismatch = wb.addWorksheet('İsim Uyuşmazlığı');
            wsMismatch.columns = [
                { header: 'Kodu', key: 'pc_no', width: 15 },
                { header: 'Lokal Hostname', key: 'local_hostname', width: 30 },
                { header: 'KeyOS Hostname', key: 'keyos_hostname', width: 30 }
            ];
            (data.mismatches || []).forEach(r => wsMismatch.addRow(r));
            wsMismatch.getRow(1).font = { bold: true };

            const buffer = await wb.xlsx.writeBuffer();
            const dateStr = new Date().toISOString().split('T')[0];
            saveAs(new Blob([buffer], { type: 'application/octet-stream' }), `KeyOS_Rapor_${dateStr}.xlsx`);
            this.showToast('Excel raporu başarıyla oluşturuldu ve indiriliyor.', 'success');
        } catch (e) {
            console.error(e);
            alert('Excel dışa aktarılırken bir hata oluştu: ' + e.message);
        }
    },
    // 
    //  İZİN İSTEK FORMU GENERATION
    // 
    calculateIzinSuresi: function() {
        const bas = document.getElementById('izin-baslangic').value;
        const bit = document.getElementById('izin-bitis').value;
        if (!bas || !bit) return;
        const d1 = new Date(bas);
        const d2 = new Date(bit);
        const diffTime = Math.abs(d2 - d1);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
        document.getElementById('izin-sure-gun').value = diffDays > 0 ? diffDays : 0;
        document.getElementById('izin-sure-saat').value = "0"; // Varsayılan tam gün
    },
    generateIzinFormu: async function(format = 'pdf') {
        const payload = {
            format: format,
            ad_soyad: document.getElementById('izin-ad-soyad').value,
            sicil: document.getElementById('izin-sicil').value,
            bolum: document.getElementById('izin-bolum').value,
            gorev: document.getElementById('izin-gorev').value,
            sebep: document.getElementById('izin-sebep').value,
            baslangic: document.getElementById('izin-baslangic').value,
            bas_saat: document.getElementById('izin-bas-saat').value,
            bitis: document.getElementById('izin-bitis').value,
            bit_saat: document.getElementById('izin-bit-saat').value,
            isbasi: document.getElementById('izin-isbasi').value,
            isbasi_saat: document.getElementById('izin-isbasi-saat').value,
            tur: document.getElementById('izin-tur').value,
            sure_gun: document.getElementById('izin-sure-gun').value,
            sure_saat: document.getElementById('izin-sure-saat').value,
            talep_eden_ad: document.getElementById('izin-talep-eden').value,
            takim_lideri_ad: document.getElementById('izin-takim-lideri').value,
            bolum_muduru_ad: document.getElementById('izin-bolum-muduru').value,
            ik_ad: document.getElementById('izin-ik').value
        };
        if (!payload.ad_soyad || !payload.bolum || !payload.sicil || !payload.sebep || !payload.baslangic || !payload.bitis || !payload.isbasi || !payload.talep_eden_ad || !payload.takim_lideri_ad || !payload.bolum_muduru_ad || !payload.ik_ad) {
            return alert('Lütfen imza alanları dahil tüm zorunlu alanları doldurun.');
        }
        this.sendPDFRequest({
            type: 'IZIN',
            mahal: payload.ad_soyad.replace(/\s/g, '_'),
            format: format,
            data: payload
        }, 'IZIN');
    },
    generateBarcodePDF: async function(size) {
        const type = size === '55x45' ? 'BC55' : 'BC100';
        const prefix = size === '55x45' ? 'bc55' : 'bc100';
        const payload = {
            text: document.getElementById(`${prefix}-text`).value,
            subtext: size === '55x45' ? document.getElementById('bc55-subtext').value : '',
            desc: size === '100x100' ? document.getElementById('bc100-desc').value : '',
            count: document.getElementById(`${prefix}-count`).value || 1
        };
        if (!payload.text) return alert('Barkod metni zorunludur.');
        try {
            this.showToast('Barkod hazırlanıyor...', 'info');
            const resp = await this.apiRequest('/documents/generate_tutanak', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: type,
                    mahal: 'Barkod',
                    data: payload
                })
            });
            if (!resp.ok) throw new Error('Sunucu hatası');
            const blob = await resp.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Barkod_${size}_${payload.text}.pdf`;
            a.click();
            this.showToast('Barkod baarıyla oluşturuldu.');
        } catch (e) { alert('Hata: ' + e.message); }
    },
    openDocModal: function(type) {
        const modal = document.getElementById(`doc-modal-${type}`);
        if (modal) {
            modal.style.display = 'flex';
            // Formun ilk halini kaydet (Deiiklik kontrolü için)
            const form = modal.querySelector('form');
            if (form) {
                const data = new FormData(form);
                this.state.initialFormData = JSON.stringify(Object.fromEntries(data));
            }
        }
    },
    closeDocModal: function(type) {
        const modal = document.getElementById(`doc-modal-${type}`);
        if (!modal) return;
        const form = modal.querySelector('form');
        if (form) {
            const currentData = JSON.stringify(Object.fromEntries(new FormData(form)));
            // Eer formda deiiklik varsa sor (İptal hariç)
            if (this.state.initialFormData && currentData !== this.state.initialFormData) {
                if (!confirm('Yapılan deiiklikler silinecek. Kapatmak istediinize emin misiniz?')) {
                    return;
                }
            }
            form.reset(); // Formu sıfırla
            // Custom reset logic (pre-filled fields)
            if (type === 'izin-istek') {
                document.getElementById('izin-bolum-muduru').value = "MURAT COKUN";
                document.getElementById('izin-ik').value = "PINAR ENDOAN";
            }
        }
        modal.style.display = 'none';
        this.state.initialFormData = null;
    },
    toggleOtherHT: function() {
        const check = document.getElementById('ht-check-other');
        const text = document.getElementById('ht-other-text');
        if (check && text) text.style.display = check.checked ? 'block' : 'none';
    },
    generateHTPDF: async function(format = 'pdf') {
        const actualFormat = (format === 'pdf') ? 'excel' : format;
        const checkboxes = document.querySelectorAll('#ht-equipment-list input[type="checkbox"]:checked');
        const equipment = Array.from(checkboxes).map(cb => cb.value);
        if (document.getElementById('ht-check-other').checked) {
            const otherVal = document.getElementById('ht-other-text').value;
            if (otherVal) equipment.push(otherVal);
        }
        const payload = {
            sla: document.getElementById('ht-sla').value,
            equipment: equipment,
            model: document.getElementById('ht-model').value,
            seri: document.getElementById('ht-seri').value,
            tespitEden: document.getElementById('ht-tespit-eden').value,
            tespitUnvan: document.getElementById('ht-tespit-unvan').value,
            teslimEden: document.getElementById('ht-teslim-eden').value,
            userUnvan: document.getElementById('ht-user-unvan').value,
            birimSorumlusu: document.getElementById('ht-birim-sorumlusu').value,
            birimUnvan: document.getElementById('ht-birim-unvan').value,
            desc: document.getElementById('ht-description').value
        };
        if (equipment.length === 0 || !payload.sla || !payload.tespitEden || !payload.teslimEden || !payload.birimSorumlusu || !payload.desc) {
            return alert('Lütfen ürün tipi seçin ve tüm alanları (SLA No, Tespit Eden, Teslim Eden, Birim Sorumlusu, Açıklama) doldurun.');
        }
        try {
            this.showToast('Hazırlanıyor...', 'info');
            // Photo handling
            const photoInput = document.getElementById('ht-photo');
            if (photoInput && photoInput.files[0]) {
                const formData = new FormData();
                formData.append('type', 'HT');
                formData.append('mahal', 'Hasar_Tespit');
                formData.append('format', actualFormat);
                formData.append('data', JSON.stringify(payload));
                formData.append('photo', photoInput.files[0]);
                this.sendPDFRequest(formData, 'HT', true);
            } else {
                this.sendPDFRequest({
                    type: 'HT',
                    mahal: 'Hasar_Tespit',
                    format: actualFormat,
                    data: payload
                }, 'HT');
            }
        } catch (e) { alert('Hata: ' + e.message); }
    },
    generateSLAPDF: async function(format = 'pdf') {
        const actualFormat = (format === 'pdf') ? 'excel' : format;
        const payload = {
            ticket: document.getElementById('sla-ticket-no').value,
            cihaz: document.getElementById('sla-cihaz').value,
            aciklama: document.getElementById('sla-aciklama').value,
            personel: document.getElementById('sla-personel').value,
            onaylayan: document.getElementById('sla-onaylayan').value
        };
        if (!payload.ticket || !payload.cihaz || !payload.aciklama || !payload.personel || !payload.onaylayan) {
            return alert('Lütfen tüm alanları doldurun.');
        }
        try {
            this.showToast('SLA tutanaı hazırlanıyor...', 'info');
            this.sendPDFRequest({
                type: 'SLA',
                mahal: 'SLA',
                format: actualFormat,
                data: payload
            }, 'SLA');
        } catch (e) { alert('Hata: ' + e.message); }
    },
    generateBarcodePDF: async function(size) {
        let payload = {};
        let type = '';
        if (size === '55x45') {
            payload = { 
                text: document.getElementById('bc55-text').value,
                subtext: document.getElementById('bc55-subtext').value,
                count: document.getElementById('bc55-count').value
            };
            type = 'BC55';
        } else if (size === '100x100') {
            payload = {
                text: document.getElementById('bc100-text').value,
                desc: document.getElementById('bc100-desc').value,
                count: document.getElementById('bc100-count').value
            };
            type = 'BC100';
        } else {
            payload = {
                text: document.getElementById('bc-manual-text').value,
                subtext: document.getElementById('bc-manual-subtext').value,
                count: document.getElementById('bc-manual-count').value
            };
            type = 'BC55'; // Default to 55x45 for manual if not specified
        }
        if (!payload.text) return alert('Lütfen barkod metnini girin.');
        try {
            this.showToast('Barkod oluşturuluyor...', 'info');
            const resp = await this.apiRequest('/documents/generate_tutanak', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: type, mahal: 'Barkod', data: payload })
            });
            await this._handleHTResponse(resp);
        } catch (e) { alert('Hata: ' + e.message); }
    },
    printBarcode: function(size) {
        let text = "", subtext = "", width = "", height = "", count = 1, frameStyle = 'solid';
        if (size === '55x45') {
            text = document.getElementById('bc55-text').value;
            subtext = document.getElementById('bc55-subtext').value;
            count = parseInt(document.getElementById('bc55-count').value) || 1;
            frameStyle = document.getElementById('bc55-style')?.value || 'solid';
            width = "55mm";
            height = "45mm";
        } else if (size === '100x100') {
            text = document.getElementById('bc100-text').value;
            subtext = document.getElementById('bc100-desc').value;
            count = parseInt(document.getElementById('bc100-count').value) || 1;
            frameStyle = document.getElementById('bc100-style')?.value || 'solid';
            width = "100mm";
            height = "100mm";
        } else {
             text = document.getElementById('bc-manual-text').value;
             subtext = document.getElementById('bc-manual-subtext').value;
             count = parseInt(document.getElementById('bc-manual-count').value) || 1;
             width = "55mm";
             height = "45mm";
        }
        if (!text) return alert('Lütfen barkod metnini girin.');
        // Dinamik font boyutu (55x45 için 6 satır kuralı)
        let fontSizeMain = size === '100x100' ? '32pt' : '18pt';
        let fontSizeSub = size === '100x100' ? '16pt' : '10pt';
        if (size === '55x45' || size === 'manual') {
            const lines = (subtext ? subtext.split('\n').length : 0) + (text.length > 15 ? 2 : 1);
            const totalChars = (text.length + (subtext ? subtext.length : 0));
            if (lines > 6 || totalChars > 110) {
                fontSizeMain = '13pt';
                fontSizeSub = '8pt';
            } else if (lines > 4 || totalChars > 70) {
                fontSizeMain = '15pt';
                fontSizeSub = '9pt';
            }
        }
        let borderCSS = '1px solid #000';
        if (frameStyle === 'dotted') borderCSS = '1px dashed #000';
        else if (frameStyle === 'none') borderCSS = 'none';
        else if (frameStyle === 'double') borderCSS = '3px double #000';
        else if (frameStyle === 'rounded') borderCSS = '1.5px solid #000';
        const printWin = window.open('', '_blank', 'width=800,height=600');
        const labelsHtml = Array(count).fill().map(() => `
            <div class="label-page">
                <div class="main-text">${text}</div>
                ${subtext ? `<div class="sub-text">${subtext.replace(/\n/g, '<br>')}</div>` : ''}
            </div>
        `).join('');
        printWin.document.write(`
            <html>
            <head>
                <title>Barkod Yazdır - ${size}</title>
                <style>
                    @page { 
                        size: ${width} ${height}; 
                        margin: 0; 
                    }
                    @media print {
                        body { margin: 0; padding: 0; }
                        .label-page { page-break-after: always; }
                    }
                    body { 
                        margin: 0; 
                        padding: 0; 
                        font-family: 'Segoe UI', Arial, sans-serif; 
                        -webkit-print-color-adjust: exact;
                    }
                    .label-page {
                        width: ${width};
                        height: ${height};
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        text-align: center;
                        box-sizing: border-box;
                        padding: 3mm;
                        padding-bottom: 8mm; /* Alt kısım kesilmesin diye daha fazla boluk */
                        overflow: hidden;
                        border: ${borderCSS};
                        border-radius: ${frameStyle === 'rounded' ? '4mm' : '0'};
                        margin: 0;
                        transform: scale(0.88); /* Daha güvenli bir ölçek */
                        transform-origin: center;
                    }
                    .main-text { 
                        font-size: ${fontSizeMain}; 
                        font-weight: 900; 
                        margin-bottom: 5px; 
                        word-break: break-all;
                        line-height: 1.1;
                    }
                    .sub-text { 
                        font-size: ${fontSizeSub}; 
                        color: #000; 
                        opacity: 0.9;
                        word-break: break-word;
                        line-height: 1.2;
                    }
                </style>
                </style>
            </head>
            <body>
                ${labelsHtml}
                <script>
                    window.onload = function() {
                        window.print();
                        setTimeout(() => { window.close(); }, 500);
                    };
                </script>
            </body>
            </html>
        `);
        printWin.document.close();
    },
    _handleHTResponse: async function(resp) {
        if (!resp.ok) {
            const err = resp.catch(() => ({error: 'Sunucu hatası'}));
            throw new Error(err.error || 'Sunucu hatası');
        }
        const contentType = resp.headers.get('content-type');
        const blob = await resp.blob();
        const url = window.URL.createObjectURL(blob);
        if (contentType && (contentType.includes('word') || contentType.includes('excel') || contentType.includes('officedocument'))) {
            // İndirme ilemi
            const a = document.createElement('a');
            a.href = url;
            // Dosya adını Content-Disposition'dan almaya çalıalım
            const disposition = resp.headers.get('Content-Disposition');
            let filename = 'dokuman';
            if (disposition && disposition.indexOf('filename=') !== -1) {
                filename = disposition.split('filename=')[1].replace(/"/g, '');
            } else {
                filename = contentType.includes('word') ? 'tutanak.docx' : 'rapor.xlsx';
            }
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            this.showToast('Dosya indirildi.', 'success');
        } else {
            // PDF Yazdırma ilemi
            this.directPrint(url);
            this.showToast('İlem tamamlandı, yazdırma penceresi açılıyor.');
        }
        // Modalları kapat
        ['hasar-tespit', 'zimmet', 'izin-istek', 'sla-sehven', 'barcode-55x45', 'barcode-100x100', 'barcode-manual'].forEach(id => this.closeDocModal(id));
    },

    // =========================================================================
    //  PHASE 4 - HELPER FUNCTIONS (INLINE HTML REDUCTION)
    // =========================================================================
    getDurumBadge: function(status, isInstalled) {
        let text = "KURULU", css = "on_field";
        const s = (status || '').toUpperCase();
        if (s.includes("BEKLE")) { text = "BEKLEMEDE"; css = "kurulum"; }
        else if (s.includes("ARIZALI")) { text = "ARIZALI"; css = "is_faulty"; }
        else if (s.includes("DEPODA") || s.includes("DEPO")) { text = "DEPODA"; css = "warehouse"; }
        else if (s.includes("KAYIP")) { text = "KAYIP"; css = "is_faulty"; }
        else if (s.includes("SERVİSTE") || s.includes("SERVIS")) { text = "SERVİSTE"; css = "servis"; }
        else if (isInstalled) { text = "KURULU"; css = "on_field"; }
        return `<span class="status-badge status-${css}">${text}</span>`;
    },
    getOSBadge: function(isWin, isKey, isRdp) {
        let html = '';
        if(isWin) html += '<span style="background:#0078d4; color:white; font-size:0.5rem; font-weight:800; padding:1px 6px; border-radius:4px; margin-right:4px;">WIN</span>';
        if(isKey) html += '<span style="background:#ff4b2b; color:white; font-size:0.5rem; font-weight:800; padding:1px 6px; border-radius:4px; margin-right:4px;">KEYOS</span>';
        if(isRdp) html += '<span style="background:#3b82f6; color:white; font-size:0.5rem; font-weight:800; padding:1px 6px; border-radius:4px; margin-right:4px;">RDP</span>';
        return html;
    },
    formatPcLabel: function(pcNo, deviceType, id) {
        const isValid = pcNo && pcNo !== '---' && String(pcNo).trim() !== '';
        const isNumeric = isValid && !isNaN(pcNo);
        
        if (deviceType === 'TABLET') {
            if (isValid) return isNumeric ? `TBL-${pcNo.toString().padStart(2, '0')}` : pcNo;
            return `TBL-${String(id).padStart(3, '0')}`;
        }
        if (['SIRAMATIK', 'KIOSK', 'SK'].includes(deviceType)) {
            if (isValid) return isNumeric ? `SK-${pcNo.toString().padStart(2, '0')}` : pcNo;
            return `SK-${String(id).padStart(3, '0')}`;
        }
        if (deviceType === 'BARKOD YAZICI') return `BY-${String(id).padStart(3, '0')}`;
        if (deviceType === 'BARKOD OKUYUCU') return `BO-${String(id).padStart(3, '0')}`;
        if (deviceType === 'TARAYICI') return `TR-${String(id).padStart(3, '0')}`;
        if (isValid) return isNumeric ? `PC-${pcNo.toString().padStart(3, '0')}` : pcNo;
        return pcNo || `ID-${id}`;
    },
    normalizeFaultyStatus: function(item) {
        if (!item) return item;
        const faulty = item.is_faulty || item.is_faulty || item['is_faulty'] || item['ar\u0131zal\u0131'] || item['ar\u00c4\u00b1zal\u00c4\u00b1'];
        const isTrue = (v) => v === true || v === 1 || v === "1" || String(v).toLowerCase() === "true";
        item.is_faulty = isTrue(faulty) ? 1 : 0;
        item.is_faulty = item.is_faulty;
        return item;
    }
};
// Merge without overwriting existing critical functions like handleLogin
for (var key in appData) {
    if (appData.hasOwnProperty(key)) {
        app[key] = appData[key];
    }
}
//  POST-MERGE: Additional app functions 
app.directPrint = function(url) {
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.src = url;
    document.body.appendChild(iframe);
    iframe.onload = function() {
        setTimeout(() => {
            iframe.contentWindow.focus();
            iframe.contentWindow.print();
        }, 500);
    };
};
app.openProfileSettingsModal = function() {
    const user = app.state.activeUser;
    if (!user) return;
    document.getElementById('profile-keyos-user').value = user.keyos_user || '';
    document.getElementById('profile-keyos-pass').value = ''; 
    document.getElementById('profile-bim-user').value = user.bim_user || '';
    document.getElementById('profile-bim-pass').value = '';
    document.getElementById('profile-current-pass').value = '';
    document.getElementById('profile-new-pass').value = '';
    document.getElementById('profile-session-timeout').value = user.session_timeout !== undefined ? user.session_timeout : 5;
    document.getElementById('profile-settings-modal').style.display = 'flex';
};
app.saveProfileSettings = async function() {
    const user = app.state.activeUser;
    const currentPass = document.getElementById('profile-current-pass').value;
    const newPass = document.getElementById('profile-new-pass').value;
    
    try {
        // 1. Şifre Değişikliği (Eğer yeni şifre girilmişse)
        if (newPass) {
            if (!currentPass) throw new Error("Şifre değiştirmek için mevcut şifrenizi girmelisiniz!");
            app.showToast('Şifre güncelleniyor...', 'info');
            const pwResp = await app.apiRequest('/users/change_password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_password: currentPass, new_password: newPass })
            });
        }

        // 2. Profil Bilgileri (KeyOS, BIM, Timeout)
        const payload = {
            id: user.id,
            keyos_user: document.getElementById('profile-keyos-user').value,
            keyos_pass: document.getElementById('profile-keyos-pass').value,
            bim_user: document.getElementById('profile-bim-user').value,
            bim_pass: document.getElementById('profile-bim-pass').value || user.bim_pass,
            session_timeout: parseInt(document.getElementById('profile-session-timeout').value)
        };

        app.showToast('Ayarlar kaydediliyor...', 'info');
        const result = await app.apiRequest('/users/update_profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        app.showToast('Profil ayarları başarıyla güncellendi.');
        document.getElementById('profile-settings-modal').style.display = 'none';
        
        // Local state güncelle
        app.state.activeUser.keyos_user = payload.keyos_user;
        app.state.activeUser.bim_user = payload.bim_user;
        app.state.activeUser.bim_pass = payload.bim_pass; // NEW
        app.state.activeUser.session_timeout = payload.session_timeout;
        localStorage.setItem('it_user_data', JSON.stringify(app.state.activeUser));
    } catch (e) { 
        console.error(e);
        alert(e.message); 
    }
};
app.clearSearch = function(id) {
    const el = document.getElementById(id);
    if (el) {
        el.value = '';
        // İlgili filtreleme fonksiyonunu tetikle
        if (id === 'main-search') this.filterInventory();
        else if (id === 'printer-search') this.searchPrinters();
        else if (id === 'depot-search') this.searchDepot();
        else if (id === 'area-search') this.searchAreas();
        else if (id === 'kb-search') this.searchKB();
    }
};

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• DEVOPS & SYSTEM HEALTH â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

app.refreshSystemHealth = async function() {
    try {
        const data = await this.apiRequest('/devops/health');
        
        const apiEl = document.getElementById('health-api-status');
        const dbEl = document.getElementById('health-db-status');
        const backupEl = document.getElementById('health-last-backup');
        const errorEl = document.getElementById('health-error-rate');
        const queueEl = document.getElementById('health-queue-status');
        
        if(apiEl) {
            apiEl.innerText = data.api;
            apiEl.style.color = data.api === 'Healthy' ? '#00ff88' : '#ff4b2b';
        }
        if(dbEl) {
            dbEl.innerText = data.database;
            dbEl.style.color = data.database === 'Healthy' ? '#00ff88' : '#ff4b2b';
        }
        if(backupEl) {
            backupEl.innerText = data.last_backup || 'Yedek yok';
        }
        if(errorEl) {
            errorEl.innerText = data.error_rate || '0%';
        }
        if(queueEl) {
            queueEl.innerText = data.queue_status || 'Normal';
        }
    } catch (e) {
        console.error("Health refresh error:", e);
    }
};

app.openDevOpsModal = function() {
    document.getElementById('devops-modal').style.display = 'flex';
    document.getElementById('devops-status-box').style.display = 'none';
};

app.runSystemUpdate = async function() {
    if(!confirm("Sistem güncellenecektir. Bu işlem sırasında kısa süreli kesinti yaşanabilir. Devam edilsin mi?")) return;
    
    const outputEl = document.getElementById('devops-pipeline-output');
    const statusBox = document.getElementById('devops-status-box');
    
    statusBox.style.display = 'block';
    outputEl.innerHTML = '<div style="color: #00ff88;">> Pipeline başlatıldı...</div>';
    
    try {
        const result = await this.apiRequest('/devops/deploy', { method: 'POST' });
        
        result.steps.forEach(step => {
            outputEl.innerHTML += `<div>> ${step}</div>`;
        });
        
        if(result.status === 'Success') {
            outputEl.innerHTML += `<div style="color: #00ff88; font-weight: bold; margin-top: 10px;">> GÜNCELLEME BAÅARILI!</div>`;
            this.showToast('Sistem başarıyla güncellendi. Sayfa yenileniyor...', 'success');
            setTimeout(() => location.reload(), 3000);
        } else {
            outputEl.innerHTML += `<div style="color: #ff4b2b; font-weight: bold; margin-top: 10px;">> HATA: ${result.final_result}</div>`;
            if(result.details) {
                outputEl.innerHTML += `<pre style="font-size: 0.65rem; color: #ff6b6b;">${JSON.stringify(result.details, null, 2)}</pre>`;
            }
        }
    } catch (e) {
        outputEl.innerHTML += `<div style="color: #ff4b2b;">> KRİTİK HATA: ${e.message}</div>`;
    }
};

app.runSystemCleanup = async function() {
    try {
        const res = await this.apiRequest('/devops/cleanup', { method: 'POST' });
        this.showToast(`${res.cleared_count} gereksiz dosya karantinaya alındı.`, 'success');
        if(res.details && res.details.length > 0) {
            console.table(res.details);
        }
    } catch (e) {
        this.showToast('Temizlik hatası: ' + e.message, 'error');
    }
};

app.runSystemRollback = async function() {
    if(!confirm("Sistemi son stabil sürüme geri döndürmek istediğinize emin misiniz? Bu işlem mevcut dosyaların üzerine yazacaktır.")) return;
    
    try {
        this.showToast('Rollback başlatıldı, lütfen bekleyin...', 'info');
        const res = await this.apiRequest('/devops/rollback', { method: 'POST' });
        if(res.success) {
            this.showToast(res.message, 'success');
            setTimeout(() => location.reload(), 2000);
        } else {
            this.showToast('Rollback hatası: ' + res.error, 'error');
        }
    } catch (e) {
        this.showToast('Kritik Hata: ' + e.message, 'error');
    }
};

app.runSelfHealing = async function() {
    try {
        this.showToast('Sistem analizi başlatıldı...', 'info');
        const res = await this.apiRequest('/devops/self_healing', { method: 'POST' });
        if(res.status === 'Intervened') {
            this.showToast('Müdahale edildi: ' + res.actions.join(', '), 'success');
        } else if(res.status === 'Healthy') {
            this.showToast('Sistem sağlıklı, müdahale gerekmedi.', 'success');
        } else {
            this.showToast('Analiz tamamlandı: ' + res.status, 'info');
        }
    } catch (e) {
        this.showToast('Onarım hatası: ' + e.message, 'error');
    }
};

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• SAFE DATA ARCHIVE â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

app.archiveAllData = function() {
    if(!confirm("DİKKAT: Tüm aktif kayıtlar (Cihazlar, Yazıcılar, Notlar) arşive taşınacaktır. Canlı listeden kaldırılacaktır. Devam edilsin mi?")) return;
    
    // Rastgele 4 haneli onay kodu üret
    const code = Math.floor(1000 + Math.random() * 9000).toString();
    this.state.archiveConfirmCode = code;
    
    const modal = document.getElementById('archive-modal');
    const label = document.getElementById('archive-confirm-label');
    const input = document.getElementById('archive-confirm-code');
    const confirmBtn = modal.querySelector('.btn-accent');
    
    label.innerText = code;
    input.value = '';
    input.disabled = true;
    confirmBtn.disabled = true;
    confirmBtn.innerText = 'BEKLEYİN (3s)';
    
    modal.style.display = 'flex';
    
    // 3 Saniye Delay (Yanlışlıkla tıklamayı önlemek için)
    let count = 3;
    const timer = setInterval(() => {
        count--;
        if(count <= 0) {
            clearInterval(timer);
            input.disabled = false;
            confirmBtn.disabled = false;
            confirmBtn.innerText = 'ARÅİVLE';
            input.focus();
        } else {
            confirmBtn.innerText = `BEKLEYİN (${count}s)`;
        }
    }, 1000);
};

app.confirmArchiveData = async function() {
    const input = document.getElementById('archive-confirm-code').value;
    if(input !== this.state.archiveConfirmCode) {
        this.showToast('Onay kodu hatalı!', 'error');
        return;
    }
    
    this.showToast('Veriler arşivleniyor...', 'info');
    try {
        // Not: Backend'de /api/inventory/clear_all_data endpoint'ini soft delete'e çevirmeliyiz.
        // Veya yeni bir endpoint: /api/inventory/archive_all
        const result = await this.apiRequest('/inventory/clear_all_data', { method: 'POST' });
        this.showToast('Veriler başarıyla arşivlendi.', 'success');
        document.getElementById('archive-modal').style.display = 'none';
        this.loadDashboardStats();
    } catch (e) {
        this.showToast('Arşivleme hatası: ' + e.message, 'error');
    }
};

app.init();
window.app = app;
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./sw.js')
            .then(reg => console.log('PWA Service Worker kayıtlı!', reg))
            .catch(err => console.log('PWA kaydı başarısız: ', err));
    });
}


// ==========================================
// BAT APPS FONKSIYONLARI
// ==========================================
app.openBatAppsModal = function() {
    document.getElementById('bat-apps-modal').style.display = 'flex';
    app.loadBatApps();
};

app.loadBatApps = async function() {
    const listDiv = document.getElementById('bat-apps-list');
    listDiv.innerHTML = '<div style="color:var(--text-secondary); text-align:center;">Yükleniyor...</div>';
    try {
        const resp = await app.apiRequest('/bat_apps/list');
        if (resp.error) throw new Error(resp.error);
        
        if (resp.length === 0) {
            listDiv.innerHTML = '<div style="color:var(--text-secondary); text-align:center;">Gösterilecek dosya bulunamadı.</div>';
            return;
        }
        
        let html = '';
        resp.forEach(f => {
            html += `
                <div class="flex-between" style="background: rgba(255,255,255,0.03); padding: 10px 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <div class="flex-row gap-2" style="align-items:center;">
                        <i class="fas fa-file-code" style="color: #00ff88; font-size: 1.2rem;"></i>
                        <div>
                            <div style="color: #fff; font-size: 0.9rem; font-weight: 600;">${f.name}</div>
                            <div style="color: var(--text-secondary); font-size: 0.75rem;">Boyut: ${f.size}</div>
                        </div>
                    </div>
                    <button class="btn btn-accent" style="padding: 5px 15px; font-size: 0.8rem;" onclick="app.downloadBatApp('${f.name}')">
                        <i class="fas fa-download"></i> İndir
                    </button>
                </div>
            `;
        });
        listDiv.innerHTML = html;
    } catch (e) {
        listDiv.innerHTML = `<div style="color:#ff4b2b; text-align:center;">Hata: ${e.message}</div>`;
    }
};

app.downloadBatApp = function(filename) {
    window.open(app.state.API_BASE + '/bat_apps/download/' + encodeURIComponent(filename), '_blank');
};

