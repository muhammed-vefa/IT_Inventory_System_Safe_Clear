var app = window.app || {};
var appData = {
    state: {
        API_BASE: (window.location.origin || '') + '/api',
        isLoggedIn: false,
        activeUser: null,
        chart: null,
        view: 'inventory',
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
        depot_activeFilter: 'ALL'
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
    // Date formatter DD.MM.YYYY
    formatDate: function(dateStr) {
        if (!dateStr || dateStr === '-' || dateStr === 'None') return '-';
        try {
            const d = dateStr.split(' ')[0];
            const parts = d.split('-');
            if (parts.length === 3 && parts[0].length === 4) {
                return `${parts[2]}.${parts[1]}.${parts[0]}`;
            }
            return d;
        } catch(e) { return dateStr; }
    },
    showLoginOverlay: function() {
        var overlay = document.getElementById('login-overlay');
        if (overlay) overlay.style.display = 'flex';
        document.body.classList.add('login-required');
    },
    init: function() {
        try {
            console.log("App Initializing...");
            // Global Fetch Interceptor (JWT Auth)
            const originalFetch = window.fetch;
            window.fetch = async function() {
                let [resource, config] = arguments;
                const userDataStr = localStorage.getItem('it_user_data');
                let token = null;
                if (userDataStr) {
                    try { token = JSON.parse(userDataStr).token; } catch(e) {}
                }
                // Sadece kendi API'mize giden isteklere token ekle
                if (token && typeof resource === 'string' && resource.includes('/api/')) {
                    config = config || {};
                    config.headers = config.headers || {};
                    // FormData ise Content-Type dokunma, sadece auth ekle
                    config.headers['Authorization'] = 'Bearer ' + token;
                }
                const response = await originalFetch(resource, config);
                // 401 hatası gelirse token patlamı demektir, çıkı yap
                if (response.status === 401 && typeof resource === 'string' && resource.includes('/api/') && !resource.includes('/login')) {
                    console.error("401 Unauthorized - Token expired or invalid");
                    localStorage.removeItem('it_user_data');
                    if (app && app.showLoginOverlay) {
                        app.showLoginOverlay();
                    } else {
                        window.location.reload();
                    }
                }
                return response;
            };
            this.checkLoginStatus(); 
            this.setupEventListeners();
            this.setupBatchEventListeners();
            this.setupLoginListeners();
            this.setupSessionTimeout();
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
        this.state.refreshInterval = setInterval(() => {
            if (this.state.view === 'dashboard') {
                this.loadDashboardStats();
            }
        }, 15000);

        // 2. KeyOS Uyumsuzluk Kontrolü (Yavaş Güncelleme - 5 Dakika)
        this.state.keyosInterval = setInterval(() => {
            if (this.state.view === 'dashboard') {
                this.checkKeyOSMismatches();
            }
        }, 300000); 
    },
    setupLoginListeners: function() {
        const self = this;
        const u = document.getElementById('login-user');
        const p = document.getElementById('login-pass');
        const trigger = (e) => { if (e.key === 'Enter' || e.keyCode === 13) self.handleLoginButtonClick(); };
        if(u) u.addEventListener('keydown', trigger);
        if(p) p.addEventListener('keydown', trigger);
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
                    userNameElem.innerText = name.toUpperCase();
                }
                // Dropdown menü öelerini yetkiye göre gizle/göster
                var isAdmin = this.state.activeUser.role === 'ADMIN';
                var ids = ['menu-users', 'menu-sync', 'menu-printer-sync', 'menu-depot-sync', 'menu-kb-sync', 'menu-keyos-sync', 'menu-history', 'btn-inventory-add'];
                for (var i = 0; i < ids.length; i++) {
                    var el = document.getElementById(ids[i]);
                    if(el) el.style.display = isAdmin ? 'block' : 'none';
                }
                this.setStateFromRole();
                this.loadMahalList();
                this.renderAll();
            } catch(e) {
                console.error("Login Check Error:", e);
                localStorage.removeItem('it_user_data');
                this.showLoginOverlay();
            }
        } else {
            this.showLoginOverlay();
        }
    },
    loadMahalList: async function() {
        try {
            const resp = await fetch(this.state.API_BASE + '/inventory/mahals');
            const mahals = await resp.json();
            this.state.mahalMap = {};
            const dl = document.getElementById('mahal-datalist');
            const dlName = document.getElementById('mahal-name-datalist');
            if(dl) dl.innerHTML = '';
            if(dlName) dlName.innerHTML = '';
            mahals.forEach(m => {
                this.state.mahalMap[m.mahal_kodu] = {
                    name: m.mahal_adi,
                    kule: m.kule,
                    kat: m.kat,
                    phone: m.telefon
                };
                if(dl) {
                    const opt = document.createElement('option');
                    opt.value = m.mahal_kodu;
                    opt.innerText = m.mahal_adi;
                    dl.appendChild(opt);
                }
                if(dlName) {
                    const opt = document.createElement('option');
                    opt.value = m.mahal_adi;
                    opt.innerText = m.mahal_kodu;
                    dlName.appendChild(opt);
                }
            });
        } catch(e) { console.error('Mahal listesi yüklenemedi:', e); }
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
            allowedViews = ['dashboard', 'inventory', 'general-notes', 'areas', 'printers', 'depot', 'docs', 'service', 'logs', 'users'];
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
        if(navUsers) navUsers.style.display = allowedViews.includes('users') ? 'block' : 'none';
        if(navLogs) navLogs.style.display = allowedViews.includes('logs') ? 'block' : 'none';
        if(navSync) navSync.style.display = isAdmin ? 'block' : 'none';
        if(navKeyosSync) navKeyosSync.style.display = isAdmin ? 'block' : 'none';
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
        const u = uInput.replace(/I/g, 'ı').replace(/İ/g, 'i').toLowerCase();
        const btn = document.getElementById('btn-login-submit');
        if(btn) { btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Giriliyor...'; btn.disabled = true; }
        try {
            await this._handleLoginInternal(u, p);
        } finally {
            if(btn) { btn.innerHTML = 'Sisteme Giri Yap'; btn.disabled = false; }
        }
    },
    _handleLoginInternal: async function(u, p) {
        console.log("Internal login attempt...");
        try {
            const resp = await fetch(this.state.API_BASE + '/users/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: u, password: p })
            });
            const result = await resp.json();
            if (result.error) {
                alert('Giri Baarısız: ' + result.error);
                return;
            }
            // JWT auth bilgisini de kaydet
            const userData = {
                id: result.user.id,
                username: result.user.username,
                display_name: result.user.display_name,
                role: result.user.role,
                permissions: result.user.permissions,
                bim_user: result.user.bim_user,
                bim_pass: result.user.bim_pass,
                keyos_user: result.user.keyos_user,
                keyos_pass: result.user.keyos_pass,
                token: result.token
            };
            localStorage.setItem('it_user_data', JSON.stringify(userData));
            location.reload();
        } catch(e) {
            // Fallback: eski hardcoded login
            const fallbackUsers = {
                'admin': { pass: '123', name: 'Sistem Admin', role: 'ADMIN' },
                'vefa': { pass: '123', name: 'M. Vefa', role: 'ADMIN' },
                'destek': { pass: '123', name: 'Saha Destek', role: 'EDITOR' }
            };
            if(fallbackUsers[u] && fallbackUsers[u].pass === p) {
                const userData = { key: u, name: fallbackUsers[u].name, display_name: fallbackUsers[u].name, role: fallbackUsers[u].role, username: u };
                localStorage.setItem('it_user_data', JSON.stringify(userData));
                location.reload();
            } else {
                alert('Giri Baarısız!');
            }
        }
    },
    showLoginOverlay: function() {
        const overlay = document.getElementById('login-overlay');
        if(overlay) overlay.style.display = 'flex';
        document.body.classList.add('login-required');
    },
    handleLogout: function() {
        localStorage.removeItem('it_user_data');
        location.reload();
    },
    setupSessionTimeout: function() {
        // 5 dk hareketsizlikte logout
        let timeout;
        const resetTimer = () => {
            clearTimeout(timeout);
            // Eer kullanıcı sadece dashboard yetkisine sahipse süreyi kısıtlama
            const user = this.state.activeUser;
            if (user && user.role === 'OTHER') {
                try {
                    const perms = JSON.parse(user.permissions || '[]');
                    if (perms.length === 1 && perms[0] === 'dashboard') {
                        return; // Timeout uygulama
                    }
                } catch(e) {}
            }
            const userTimeout = this.state.activeUser.session_timeout;
            if (userTimeout === 0) return; // Sınırsız
            const waitMs = (userTimeout || 5) * 60 * 1000;
            timeout = setTimeout(() => {
                if (this.state.isLoggedIn) {
                    alert(`Oturumunuz ${userTimeout} dakika boyunca ilem yapmadıınız için güvenlik nedeniyle kapatıldı.`);
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
            .replace(/Ş/g, "S")
            .replace(/ş/g, "s")
            .replace(/Ğ/g, "G")
            .replace(/ğ/g, "g");
    },
    renderAll: function() {
        this.loadNoteCounts();
        this.loadInventory();
        this.loadAreas();
        this.loadDepot();
        this.loadDashboardStats();
        this.loadGeneralNotes();
    },
    loadNoteCounts: async function() {
        try {
            const resp = await fetch(this.state.API_BASE + '/notes/counts/pc');
            this.state.noteCounts = await resp.json();
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
            const resp = await fetch(this.state.API_BASE + '/dashboard/stats');
            const stats = await resp.json();
            this.renderStats(stats);
            this.renderDashboardChart(stats);
            this.renderStockAlerts(stats.depot_alerts || []);
        } catch (e) {
            console.error("Dashboard yüklenemedi:", e);
            // Fallback: local data üzerinden hesapla
            this.renderStatsFromLocal();
        }
    },
    renderStats: function(stats) {
        if(!stats) return;
        const set = (id, val) => { const el = document.getElementById(id); if(el) el.innerText = val !== undefined ? val : 0; };
        // PC (Nested Structure)
        if(stats.pc) {
            set('stat-pc-sahada', stats.pc.sahada);
            set('stat-pc-ariza', stats.pc.ariza);
            set('stat-pc-depo', stats.pc.depo);
            set('stat-pc-wait', stats.pc.kayip);
        }
        // Yazıcı
        if(stats.pr) {
            set('stat-pr-kurulu', stats.pr.sahada);
            set('stat-pr-ariza', stats.pr.ariza);
            set('stat-pr-depo', stats.pr.depo);
            set('stat-pr-kayip', stats.pr.kayip);
        }
        // Barkod
        set('stat-bo-toplam', stats.bo);
        set('stat-by-toplam', stats.by);
        // Tarayıcılar
        if(stats.tr_c230) {
            set('stat-tr-c230-sahada', stats.tr_c230.sahada);
            set('stat-tr-c230-depo', stats.tr_c230.depo);
        }
        if(stats.tr_g2090) {
            set('stat-tr-g2090-sahada', stats.tr_g2090.sahada);
            set('stat-tr-g2090-depo', stats.tr_g2090.depo);
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
        const inv = this.state.inventory;
        if (!inv.length) return;
        const set = (id, val) => { const el = document.getElementById(id); if(el) el.innerText = val; };
        const isTrue = (v) => v && v !== '' && v !== '0';
        const pcs = inv.filter(i => (i.device_type || '').toUpperCase() === 'PC' || !i.device_type);
        set('stat-pc-sahada', pcs.filter(i => isTrue(i.sahada)).length);
        set('stat-pc-ariza', pcs.filter(i => isTrue(i.arizali)).length);
        set('stat-pc-depo', pcs.filter(i => isTrue(i.depo)).length);
        set('stat-pc-wait', pcs.filter(i => isTrue(i.mahalsiz)).length);
        set('stat-os-windows', inv.filter(i => isTrue(i.windows)).length);
        set('stat-os-keyos', inv.filter(i => isTrue(i.keyos)).length);
        set('stat-bo-toplam', inv.filter(i => i.bo_seri && i.bo_seri !== '').length);
        set('stat-by-toplam', inv.filter(i => i.by_seri && i.by_seri !== '').length);
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
            const pcData = stats.pc || { sahada:0, ariza:0, depo:0, kayip:0 };
            this.state.chart1 = new Chart(canvas1, {
                type: 'pie',
                data: {
                    labels: ['Kurulu', 'Arızalı', 'Depo', 'Kayıp'],
                    datasets: [{
                        data: [
                            pcData.sahada || 0, 
                            pcData.ariza || 0, 
                            pcData.depo || 0, 
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
                const prData = stats.pr || { sahada:0, ariza:0, depo:0, kayip:0 };
                this.state.chart3 = new Chart(canvas3, {
                    type: 'pie',
                    data: {
                        labels: ['Kurulu', 'Arızalı', 'Depo', 'Kayıp'],
                        datasets: [{
                            data: [
                                prData.sahada || 0, 
                                prData.ariza || 0, 
                                prData.depo || 0, 
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
    updatePeripheralDatalists: function() {
        const categories = {
            'bo-seri-datalist': 'Barkod Okuyucu',
            'by-seri-datalist': 'Barkod Yazıcı',
            'tr-seri-datalist': 'Tarayıcı',
            'pr-seri-datalist': 'Yazıcı'
        };
        for (const [id, modelFilter] of Object.entries(categories)) {
            const dl = document.getElementById(id);
            if (!dl) continue;
            const seriList = (this.state.printers || [])
                .filter(p => (p.model || '').includes(modelFilter))
                .map(p => `<option value="${p.seri}">${p.model} (${p.mahal || 'Depo'})</option>`)
                .join('');
            dl.innerHTML = seriList;
        }
    },
    renderStockAlerts: function(alerts) {
        // Redundant as per user request to move alerts to Depot view.
        return;
    },
    navigateTo: function(view) {
        this.state.view = view;
        document.querySelectorAll('.view').forEach(v => v.style.display = 'none');
        const viewEl = document.getElementById(`view-${view}`);
        if(viewEl) viewEl.style.display = 'block';
        document.querySelectorAll('.nav-link').forEach(l => {
            l.classList.toggle('active', l.dataset.view === view);
        });
        const role = (this.state.activeUser && this.state.activeUser.role) ? this.state.activeUser.role : 'GUEST';
        // MagicInfo UI Restrictions
        const miWindows = document.querySelectorAll('.magicinfo-window, #magicinfo-side-panel');
        miWindows.forEach(win => {
            win.style.display = (view === 'magicinfo') ? 'block' : 'none';
        });
        // Depot UI Restrictions
        if (view === 'depot') {
            const btnAdd = document.getElementById('btn-depot-add');
            const btnExport = document.getElementById('btn-depot-export');
            if (btnAdd) btnAdd.style.display = (role === 'ADMIN' || role === 'DEPOT') ? 'block' : 'none';
            if (btnExport) btnExport.style.display = (role === 'ADMIN') ? 'block' : 'none';
        }
        // View'a özel veri yükleme (Sadece veri yoksa yükle - Hızlandırma için)
        if (view === 'dashboard' && (this.state.inventory || []).length === 0) this.loadDashboardStats();
        if (view === 'inventory' && (this.state.inventory || []).length === 0) this.loadInventory();
        if (view === 'users' && (this.state.users || []).length === 0) this.loadUsers();
        if (view === 'printers' && (this.state.printers || []).length === 0) this.renderPrinters();
        if (view === 'logs' && (this.state.auditLogs || []).length === 0) this.loadAuditLogs();
        if (view === 'service' && (this.state.serviceRecords || []).length === 0) this.loadServiceRecords();
        if (view === 'depot' && (this.state.depot || []).length === 0) this.loadDepot();
        if (view === 'magicinfo' && (this.state.magicinfo || []).length === 0) this.loadMagicInfo();
        if (view === 'general-notes') this.loadGeneralNotes();
    },
    refreshActiveView: async function() {
        const view = this.state.view;
        try {
            if (view === 'dashboard') await this.loadDashboardStats();
            else if (view === 'inventory') await this.loadInventory();
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
            const resp = await fetch(this.state.API_BASE + '/sync', { method: 'POST' });
            const result = await resp.json();
            if (result.error) throw new Error(result.error);
            this.showToast('Senkronizasyon Baarılı! Tüm veriler güncellendi.');
            // Tüm verileri batan yükle
            await this.loadInventory();
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
            const response = await fetch(this.state.API_BASE + '/inventory/get_all');
            const data = await response.json();
            this.state.inventory = data;
            this.updatePeripheralDatalists();
            this.filterInventory();
            this.renderStatsFromLocal();
        } catch (e) { console.error("Envanter yüklenemedi:", e); }
    },
    updatePeripheralDatalists: function() {
        const byDl = document.getElementById('by-seri-datalist');
        const boDl = document.getElementById('bo-seri-datalist');
        const trDl = document.getElementById('tr-seri-datalist');
        if (!byDl || !boDl || !trDl) return;
        const bySet = new Set(), boSet = new Set(), trSet = new Set();
        this.state.inventory.forEach(i => {
            if (i.by_seri && i.by_seri.trim() !== "" && i.by_seri !== "---") bySet.add(i.by_seri.trim());
            if (i.bo_seri && i.bo_seri.trim() !== "" && i.bo_seri !== "---") boSet.add(i.bo_seri.trim());
            if (i.tarayici_seri && i.tarayici_seri.trim() !== "" && i.tarayici_seri !== "---") trSet.add(i.tarayici_seri.trim());
        });
        byDl.innerHTML = Array.from(bySet).sort().map(s => `<option value="${s}">`).join('');
        boDl.innerHTML = Array.from(boSet).sort().map(s => `<option value="${s}">`).join('');
        trDl.innerHTML = Array.from(trSet).sort().map(s => `<option value="${s}">`).join('');
    },
    renderInventory: function(items) {
        const grid = document.getElementById('inventory-grid');
        if(!grid) return;
        if (!items || !items.length) {
            grid.innerHTML = '<p style="opacity:0.4; text-align:center; grid-column:1/-1;">Envanter verisi bulunamadı.</p>';
            return;
        }
        const isTrue = (v) => v && v !== '' && v !== '0' && v !== 0;
        const nc = this.state.noteCounts || {};
        grid.innerHTML = items.map(i => {
            const countedAt = i.last_counted_at || null;
            // UI Labeling
            let pcLabel = i.pc_no || '---';
            let isPC = true;
            if (i.device_type === 'TABLET') { pcLabel = i.card_name || `TBL-${String(i.id).padStart(3,'0')}`; isPC = false; }
            else if (['SIRAMATIK', 'KIOSK', 'SK'].includes(i.device_type)) { pcLabel = i.card_name || `(S-K)-${String(i.id).padStart(3,'0')}`; isPC = false; }
            else if (pcLabel !== '---' && !isNaN(pcLabel)) pcLabel = `PC-${pcLabel.toString().padStart(3, '0')}`;
            let durumText = "Bilinmiyor", durumClass = "sahada";
            const s = (v) => v && v !== '0' && v !== 0 && v !== "";
            if(i.kurulum_bekliyor == 1 || (i.status || "").includes("BEKLE")) { durumText = "KURULUM BEKLİYOR"; durumClass = "kurulum"; }
            else if(s(i.sahada) || (i.status === "KURULU")) { durumText = "KURULU"; durumClass = "sahada"; }
            else if(s(i.depo) || (i.status === "DEPODA")) { durumText = "DEPO"; durumClass = "depoda"; }
            else if(s(i.arizali) || (i.status === "ARIZALI")) { durumText = "ARIZALI"; durumClass = "arizali"; }
            else if(s(i.mahalsiz) || (i.status === "KAYIP")) { durumText = "KAYIP"; durumClass = "arizali"; }
            let osBadge = "";
            if(s(i.windows)) osBadge = '<span style="background:#0078d4; color:white; font-size:0.65rem; font-weight:800; padding:2px 8px; border-radius:4px; margin-right:4px; text-shadow: 0 1px 2px rgba(0,0,0,0.3);">WIN</span>';
            if(s(i.keyos)) osBadge = '<span style="background:#ff4b2b; color:white; font-size:0.65rem; font-weight:800; padding:2px 8px; border-radius:4px; margin-right:4px; text-shadow: 0 1px 2px rgba(0,0,0,0.3);">KEYOS</span>';
            const noteInfo = nc[String(i.id)];
            let noteBubble = '';
            if (noteInfo && noteInfo.count > 0) {
                const safeTitle = (noteInfo.last_title || 'Not').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                const safeContent = (noteInfo.last_content || '').replace(/'/g, "\\'").replace(/"/g, '&quot;').replace(/\n/g, ' ');
                noteBubble = `
                <div class="note-bubble" onclick="event.stopPropagation(); app.openNotesModal(${i.id}, 'pc')">
                    <i class="fas fa-comment-dots"></i>
                    <span class="note-count">${noteInfo.count}</span>
                    <div class="note-tooltip">
                        <div class="note-tooltip-title">${safeTitle}</div>
                        <div class="note-tooltip-content">${safeContent}</div>
                    </div>
                </div>`;
            }
            let descBubble = (i.aciklama && i.aciklama.trim() !== "") ? `
                <div class="desc-bubble blink-icon" onclick="event.stopPropagation()"><i class="fas fa-exclamation-circle" style="color:#ffb400;"></i></div>` : "";
            let countBadge = countedAt ? `<div style="font-size:0.6rem; color:#00ff88; margin-top:4px;"><i class="fas fa-check-circle"></i> Sayıldı: ${new Date(countedAt).toLocaleDateString('tr-TR')}</div>` : "";
            return `
            <div class="card card-compact ${this.state.countMode && countedAt ? 'counted-card' : ''}" 
                 onclick="${this.state.countMode ? `app.markCounted(${i.id})` : `app.openDeviceDetail(${i.id}, 'pc')`}"
                 style="cursor:pointer">
                <div class="flex-between mb-1">
                    <span style="color:var(--accent); font-size:1.1rem; font-weight:800">${pcLabel}</span>
                    <div class="flex-row gap-2" style="align-items:center;">
                        ${descBubble} ${noteBubble} ${osBadge}
                        ${isPC ? `<i class="fas fa-shield-halved" style="cursor:pointer; font-size:0.9rem; color:#ff4b2b; opacity:0.6;" title="KeyOS'tan Sorgula" onclick="event.stopPropagation(); app.fetchKeyOSData('${i.pc_seri}')"></i>` : ''}
                        <i class="fas fa-clock-rotate-left history-icon-btn" onclick="app.openHistoryPopup(${i.id}, 'pc', event)"></i>
                        <span class="status-badge status-${durumClass}">${durumText}</span>
                    </div>
                </div>
                <div class="flex-between" style="font-size:0.75rem; color:var(--text-secondary); line-height:1.2; margin-top: 5px; margin-bottom: 2px;">
                    <span>Kod: ${i.mahal_kodu || '-'}</span>
                    <span style="color:var(--accent); font-weight:800;">${i.hostname || ''}</span>
                </div>
                <div style="font-size:1rem; font-weight:700; color:#fff; margin-bottom:10px;">${i.card_name || i.mahal_adi || '-'}</div>
                <div class="card-info" style="border-top:1px solid rgba(255,255,255,0.05); padding-top:8px; display:grid; grid-template-columns:1fr 1fr; gap:5px;">
                    <div class="info-item"><span>IP</span><div class="flex-row gap-1" style="align-items:center;">${i.ip || '-'}${i.ip ? ` <i class="fas fa-power-off" style="cursor:pointer; color:#ff4b2b; font-size:0.8rem; margin-left:5px;" title="Yeniden Balat" onclick="event.stopPropagation(); app.rebootDevice('${i.ip}')"></i>` : ''}</div></div>
                    <div class="info-item"><span>SERİ NO</span>${i.pc_seri || '-'}</div>
                    ${i.bagli_yazicilar ? `<div class="info-item" style="grid-column: 1 / -1; border-top: 1px dashed rgba(255,255,255,0.05); padding-top: 5px;"><span>YAZICILAR</span>${i.bagli_yazicilar}</div>` : ''}
                </div>
                ${(i.by_seri || i.bo_seri || i.tarayici_seri) ? `
                <div style="font-size:0.65rem; color:var(--accent); margin-top:8px; border-top:1px dashed rgba(0,210,255,0.1); padding-top:5px;">
                    ${i.by_seri ? `<div>BY: ${i.by_seri}</div>` : ''}
                    ${i.bo_seri ? `<div>BO: ${i.bo_seri}</div>` : ''}
                    ${i.tarayici_seri ? `<div>TR: ${i.tarayici_seri}</div>` : ''}
                </div>` : ''}
                ${i.aciklama ? `
                <div style="font-size:0.75rem; color:#ffb400; margin-top:8px; border-top:1px solid rgba(255,255,255,0.05); padding-top:5px; font-weight:500;">
                    <i class="fas fa-info-circle"></i> ${i.aciklama}
                </div>` : ''}
                ${countBadge}
                ${this.state.countMode ? `
                <button class="btn ${countedAt ? 'counted' : 'btn-accent'}" style="width:100%; margin-top:10px; padding:5px; font-size:0.75rem;" onclick="event.stopPropagation(); ${countedAt ? `app.undoMarkCounted(${i.id})` : `app.markCounted(${i.id})`}">
                    <i class="fas ${countedAt ? 'fa-undo' : 'fa-check'}"></i> ${countedAt ? 'GERİ AL' : 'SAYILDI'}
                </button>` : ''}
            </div>`;
        }).join('');
    },
    searchInventory: function() { this.filterInventory(); },
    setInvCategory: function(cat) {
        this.state.invCategory = cat || 'PC';
        document.querySelectorAll('#device-type-filters .btn-chip').forEach(btn => btn.classList.toggle('active', btn.dataset.category === cat));
        const dd = document.getElementById('search-category-dropdown');
        if (dd) { dd.value = ["BARKOD YAZICI", "BARKOD OKUYUCU", "TARAYICI"].includes(cat) ? cat : ""; }
        // Show "Yeni Ekle" button ONLY for SK and TABLET
        const addBtn = document.getElementById('btn-device-add');
        if (addBtn) {
            addBtn.style.display = (cat === 'SK' || cat === 'TABLET') ? 'inline-flex' : 'none';
        }
        this.filterInventory();
    },
    openDeviceAddModal: function() {
        const cat = this.state.invCategory;
        if (cat !== 'SK' && cat !== 'TABLET') return; // Sadece bu modlarda çalısın
        // Formu temizle
        document.getElementById('add-pc-no').value = '';
        document.getElementById('add-ip').value = '';
        document.getElementById('add-kule').value = '';
        document.getElementById('add-mahal-kodu').value = '';
        document.getElementById('add-mahal-adi').value = '';
        document.getElementById('add-seri').value = '';
        if(document.getElementById('add-assigned_to')) document.getElementById('add-assigned_to').value = '';
        if(document.getElementById('add-phone')) document.getElementById('add-phone').value = '';
        if(document.getElementById('add-title')) document.getElementById('add-title').value = '';
        if(document.getElementById('add-unit')) document.getElementById('add-unit').value = '';
        // Sadece basit cihazlar eklenecei için varsayılan alanları ayarla
        document.getElementById('add-windows').checked = false;
        document.getElementById('add-keyos').checked = false;
        document.getElementById('add-sahada').checked = true;
        // PC NO alanını gizle (Sıramatik/Tablet'te yok)
        document.getElementById('add-pc-no').style.display = 'none';
        // Tablet alanlarını göster/gizle
        const tabletFields = document.getElementById('add-tablet-fields');
        if (tabletFields) {
            tabletFields.style.display = (cat === 'TABLET') ? 'flex' : 'none';
        }
        // Modal balıını ayarla
        const titleText = cat === 'SK' ? 'Sıramatik / Kiosk' : 'Tablet';
        const titleEl = document.querySelector('#device-add-modal h3');
        if (titleEl) titleEl.innerHTML = `<i class="fas fa-desktop"></i> Yeni ${titleText} Ekle`;
        document.getElementById('device-add-modal').style.display = 'flex';
    },
    saveNewDevice: async function() {
        // Bu özellik Sıramatik/Kiosk/Tablet eklemek için özelletirilmitir
        const cat = this.state.invCategory;
        const type = cat === 'TABLET' ? 'TABLET' : 'SIRAMATIK'; 
        const ip = document.getElementById('add-ip').value;
        const kule = document.getElementById('add-kule').value;
        const mahal_kodu = document.getElementById('add-mahal-kodu').value;
        const mahal_adi = document.getElementById('add-mahal-adi').value;
        const seri = document.getElementById('add-seri').value || '-';
        if (!mahal_kodu && !mahal_adi) return alert("Lütfen mahal bilgilerini giriniz.");
        try {
            const resp = await fetch(this.state.API_BASE + '/inventory/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    device_type: type,
                    ip: ip,
                    kule: kule,
                    mahal_kodu: mahal_kodu,
                    mahal_adi: mahal_adi,
                    pc_seri: seri,
                    sahada: document.getElementById('add-sahada').checked ? 1 : 0,
                    windows: document.getElementById('add-windows').checked ? 1 : 0,
                    keyos: document.getElementById('add-keyos').checked ? 1 : 0,
                    assigned_to: document.getElementById('add-assigned_to') ? document.getElementById('add-assigned_to').value : '',
                    phone: document.getElementById('add-phone') ? document.getElementById('add-phone').value : '',
                    title: document.getElementById('add-title') ? document.getElementById('add-title').value : '',
                    unit: document.getElementById('add-unit') ? document.getElementById('add-unit').value : ''
                })
            });
            const result = await resp.json();
            if (result.error) throw new Error(result.error);
            this.showToast("Cihaz baarıyla eklendi!");
            document.getElementById('device-add-modal').style.display = 'none';
            this.loadInventory();
        } catch (e) {
            alert("Hata: " + e.message);
        }
    },
    setInvBlock: function(block) {
        this.state.invBlock = block || 'ALL';
        this.state.invKat = 'ALL'; // Reset floor when block changes
        document.querySelectorAll('#inventory-filters .btn-chip').forEach(btn => btn.classList.toggle('active', btn.dataset.block === block));
        this.renderKatFilters(block);
        this.filterInventory();
    },
    renderKatFilters: function(block) {
        const container = document.getElementById('kat-filters');
        if (!container) return;
        if (block === 'ALL') {
            container.style.display = 'none';
            return;
        }
        // Find unique floors for the selected block
        const floors = [...new Set(this.state.inventory
            .filter(i => {
                const kule = (i.kule || "").toUpperCase();
                const kod = (i.mahal_kodu || "").toUpperCase();
                if (block === 'A') return (kod.startsWith('A.') || kule === 'A');
                if (block === 'B') return (kod.startsWith('B.') || kule === 'B');
                if (block === 'MH') return (kod.startsWith('C.') || kule === 'C' || kule === 'MH');
                return (kule === block || kod.includes(block));
            })
            .map(i => i.kat)
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
    setInvKat: function(kat) {
        this.state.invKat = kat || 'ALL';
        document.querySelectorAll('#kat-filters .btn-chip').forEach(btn => {
            const txt = btn.innerText.replace('. Kat', '').trim();
            btn.classList.toggle('active', (kat === 'ALL' && txt === 'Tümü') || txt === kat);
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
                const kule = (i.kule || "").toUpperCase();
                const kod = (i.mahal_kodu || "").toUpperCase();
                let blockMatch = false;
                if (block === 'A') blockMatch = (kod.startsWith('A.') || kule === 'A');
                else if (block === 'B') blockMatch = (kod.startsWith('B.') || kule === 'B');
                else if (block === 'MH') blockMatch = (kod.startsWith('C.') || kule === 'C' || kule === 'MH');
                else blockMatch = (kule === block || kod.includes(block));
                if (!blockMatch) return false;
                // Floor filter (only if block is selected)
                if (this.state.invKat && this.state.invKat !== 'ALL') {
                    if (i.kat !== this.state.invKat) return false;
                }
            }
            // Search
            if (query) {
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
                            const content = `${i.mahal_kodu} ${i.mahal_adi}`.toUpperCase();
                            return content.includes(termUP);
                        } 
                        else if (!hasAlpha && hasDot) {
                            // 3. Sadece Sayı + Nokta varsa: IP ADRESİ araması (10.241 vb.)
                            return (i.ip || '').includes(term);
                        } 
                        else if (isNumeric) {
                            // 4. Sadece sayı ise: PC NUMARASI veya ID araması (Tam eleme)
                            const pNo = String(i.pc_no || '').replace(/^0+/, '') || '0';
                            const termClean = term.replace(/^0+/, '') || '0';
                            return pNo === termClean || String(i.id) === term;
                        } 
                        else {
                            // 5. Dier her ey: SERİ NUMARALARI, HOSTNAME ve GENEL (DM4, VJM vb.)
                            const content = `${i.pc_seri} ${i.monitor_seri} ${i.monitor2_seri} ${i.by_seri} ${i.bo_seri} ${i.tarayici_seri} ${i.hostname} ${i.card_name || ''} ${i.mahal_adi}`.toUpperCase();
                            return content.includes(termUP);
                        }
                    });
                    if (!matchAny) return false;
                }
            }
            return true;
        });
        this.state.lastFilteredList = filtered;
        this.renderInventory(filtered);
    },
    filterByKat: function(kat, blockFilter) {
        // Chip actives
        document.querySelectorAll('#kat-filters .btn-chip').forEach(btn => {
            btn.classList.toggle('active', btn.innerText.includes(kat || 'TM'));
        });
        let filtered = this.state.inventory.filter(i => {
            const kule = (i.kule || '').toUpperCase();
            const kod = (i.mahal_kodu || '').toUpperCase();
            let matchBlock = false;
            if (blockFilter === 'A') matchBlock = kod.startsWith('A.') || kule === 'A';
            else if (blockFilter === 'B') matchBlock = kod.startsWith('B.') || kule === 'B';
            else matchBlock = kule === blockFilter || kod.includes(blockFilter);
            if (!matchBlock) return false;
            if (kat && i.kat !== kat) return false;
            return true;
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
            const resp = await fetch(this.state.API_BASE + '/printers/get_all');
            const data = await resp.json();
            this.state.printers = data;
            const isAdmin = ['ADMIN', 'EDITOR'].includes(this.state.activeUser.role);
            this.state.printers = data;
            this.applyPrinterFilters(); // Filtreleri uygula ve render et
        } catch (e) { console.error("Yazıcılar yüklenemedi:", e); }
    },
    applyPrinterFilters: function() {
        const container = document.getElementById('printers-grid');
        if (!container || !this.state.printers) return;
        const ptype = this.state.printerType || 'ALL';
        const query = (document.getElementById('printer-search').value || "").toUpperCase();
        const isAdmin = ['ADMIN', 'EDITOR'].includes(this.state.activeUser.role);
        let filtered = this.state.printers.filter(p => {
            // 1. Kategori Filtresi
            if (ptype !== 'ALL') {
                const model = (p.model || "").toUpperCase();
                if (ptype === 'BY') { if (!model.includes('BARKOD YAZICI')) return false; }
                else if (ptype === 'BO') { if (!model.includes('BARKOD OKUYUCU')) return false; }
                else if (ptype === 'TR') { if (!model.includes('TARAYICI')) return false; }
                else { if (!model.includes(ptype)) return false; }
            }
            // 2. Arama Filtresi (oklu terim destekli)
            if (query) {
                const searchTerms = query.split('-').map(t => t.trim()).filter(t => t !== "");
                if (searchTerms.length > 0) {
                    return searchTerms.some(term => {
                        const termUP = term.toUpperCase();
                        const hasDot = term.includes('.');
                        const isNumeric = /^\d+$/.test(term);
                        if (isNumeric && !hasDot) {
                            // Sadece sayı ise PR NO veya IP sonu araması
                            return (p.pr_no || '').includes(term) || (p.ip || '').endsWith(term);
                        } else if (hasDot) {
                            // Nokta varsa IP araması
                            const content = `${p.pr_no} ${p.model} ${p.seri} ${p.mahal} ${p.mac}`.toUpperCase();
                            return content.includes(termUP);
                        } else {
                            // Genel metin araması
                            const content = `${p.pr_no} ${p.model} ${p.seri} ${p.mahal} ${p.mac}`.toUpperCase();
                            return content.includes(termUP);
                        }
                    });
                }
            }
            return true;
        });
        container.innerHTML = filtered.map(p => {
            const status = (p.status || '').toUpperCase();
            const isInstalled = p.mahal && p.mahal.trim() !== "";
            let durumText = "DEPODA";
            let durumClass = "depo";
            if (status.includes('SERVİSTE') || status.includes('SERVIS')) {
                durumText = "SERVİSTE";
                durumClass = "servis";
            } else if (status.includes('ARIZALI')) {
                durumText = "ARIZALI";
                durumClass = "arizali";
            } else if (status.includes('KURULU') || isInstalled) {
                durumText = "KURULU";
                durumClass = "sahada";
            }

            return `
            <div class="card fade-in" style="cursor:pointer;" onclick="app.openDeviceDetail(${p.id}, 'pr')">
                <div class="flex-between mb-2">
                    <span style="background:rgba(0,186,255,0.2); color:var(--accent); padding:4px 10px; border-radius:20px; font-size:1.1rem; font-weight:800;">${p.pr_no || 'Yazıcı'}</span>
                    <div class="flex-row gap-2" style="align-items:center;">
                        <span class="status-badge status-${durumClass}" style="font-size:0.65rem; padding:2px 8px;">${durumText}</span>
                        <i class="fas fa-list-check" style="cursor:pointer; font-size:0.9rem; opacity:0.6; color:var(--accent);" title="Servis Geçmişi" onclick="event.stopPropagation(); app.openPrinterServiceHistoryModal(${p.id}, '${p.pr_no}')"></i>
                        <i class="fas fa-globe" style="cursor:pointer; font-size:0.9rem; opacity:0.6; color:var(--accent);" title="Arayüz" onclick="event.stopPropagation(); window.open('http://${p.ip}', '_blank')"></i>
                        ${isAdmin ? `<i class="fas fa-tools" style="cursor:pointer; font-size:0.8rem; opacity:0.7; color:var(--accent);" title="Servis" onclick="event.stopPropagation(); app.openAddServiceModal(${p.id})"></i>` : ''}
                    </div>
                </div>

                ${isAdmin ? `
                <div class="flex-row mb-2" style="justify-content: flex-end; padding-right: 5px; align-items: center; gap: 6px;">
                    <!-- Sorgulama -->
                    <div class="icon-circle-bg" style="background: #00d2ff; color: #000;" onclick="event.stopPropagation(); app.checkPrinterStatus('${p.ip}', ${p.id})" title="Durum Sorgula">
                        <i class="fas fa-satellite-dish"></i>
                    </div>
                    
                    <!-- Tekli Ekle -->
                    <div class="icon-circle-bg" style="background: rgba(0, 255, 136, 0.2); color: #00ff88; border: 1px solid #00ff88;" onclick="event.stopPropagation(); app.runPrinterAction(${p.id}, 'add')" title="Tekli Ekle">
                        <i class="fas fa-plus"></i>
                    </div>
                    
                    <!-- Toplu Ekle (Batch) -->
                    <div class="icon-circle-bg" style="background: #00ff88; color: #000; box-shadow: 0 0 15px rgba(0,255,136,0.3);" onclick="event.stopPropagation(); app.openBatchModal('add', ${p.id})" title="Toplu Kurulum (++)">
                        <i class="fas fa-layer-group"></i>
                    </div>

                    <!-- Tekli Kaldır -->
                    <div class="icon-circle-bg" style="background: rgba(255, 75, 43, 0.2); color: #ff4b2b; border: 1px solid #ff4b2b;" onclick="event.stopPropagation(); app.runPrinterAction(${p.id}, 'remove')" title="Tekli Kaldır">
                        <i class="fas fa-minus"></i>
                    </div>
                    
                    <!-- Toplu Kaldır (Batch) -->
                    <div class="icon-circle-bg" style="background: #ff4b2b; color: #fff; box-shadow: 0 0 15px rgba(255,75,43,0.3);" onclick="event.stopPropagation(); app.openBatchModal('remove', ${p.id})" title="Toplu Kaldır (--)">
                        <i class="fas fa-layer-group"></i>
                    </div>
                </div>
                ` : ''}

                <div class="flex-column">
                    <div style="font-size: 0.7rem; color: var(--accent); font-weight: 700; text-transform: uppercase; margin-bottom: 2px;">${p.mahal || 'Mahal Bilgisi Yok'}</div>
                    <div style="font-size: 1.1rem; font-weight: 600; color:#fff; margin-bottom: 5px;">${p.model || 'LaserJet'}</div>
                    <div class="text-secondary" style="font-size: 0.8rem; opacity: 0.8;">IP: ${p.ip || '-'}</div>
                    <div class="text-secondary" style="font-size: 0.7rem; opacity:0.6;">MAC: ${p.mac || '-'} | Seri: ${p.seri || '-'}</div>
                    <div id="printer-status-${p.id}" class="printer-inline-status" style="display:none; margin-top:8px; padding:8px 10px; background:rgba(0,0,0,0.3); border-radius:6px; border:1px solid rgba(0,210,255,0.1); font-size:0.75rem;"></div>
                </div>
            </div>`;
        }).join('');
        this.updatePeripheralDatalists();
    },
    // ══════════════════════════════════════════════════════════════
    // TOPLU YAZICI YÖNETİMİ (BATCH PRINTER MANAGEMENT)
    // ══════════════════════════════════════════════════════════════
    
    batchAddPrinters: function() { this.openBatchModal('add'); },
    batchRemovePrinters: function() { this.openBatchModal('remove'); },
    
    openBatchModal: function(type, printerId = null) {
        this.state.batchAction = type;
        const modal = document.getElementById('batch-printer-modal');
        if(!modal) return;
        
        // Yazıcı Bilgisini Al
        const printer = this.state.printers.find(p => p.id == printerId);
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
                
                const searchStr = `${item.pc_no} ${item.hostname} ${item.ip} ${item.mahal_kodu}`.toUpperCase();
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
                // KARTLARDAKİ İSİM MANTIĞI:
                let pcLabel = item.pc_no || '---';
                if (pcLabel !== '---' && !isNaN(pcLabel)) pcLabel = `PC-${pcLabel.toString().padStart(3, '0')}`;
                
                // Mahal Kodu
                const mahalKod = item.mahal_kodu || item.mahal || '-';
                
                return {
                    id: item.id,
                    label: `<div class="flex-column" style="gap:1px;">
                                <span style="color:#fff; font-weight:700; font-size:0.85rem;">${pcLabel}</span>
                                <div class="flex-row gap-2" style="align-items:center;">
                                    <span style="color:var(--accent); font-size:0.75rem; font-family:monospace;">${item.ip || 'IP Yok'}</span>
                                    <span style="font-size:0.7rem; opacity:0.6; color:#00ff88;">[${mahalKod}]</span>
                                </div>
                            </div>`,
                    ip: item.ip
                };
            });

        listContainer.innerHTML = options.map(opt => `
            <div class="flex-row gap-3 dropdown-item" style="border-bottom: 1px solid rgba(255,255,255,0.05); align-items: center; cursor:pointer;" onclick="const chk=document.getElementById('chk-${opt.id}'); chk.checked=!chk.checked; app.updateBatchCounter(); event.stopPropagation();">
                <input type="checkbox" id="chk-${opt.id}" class="batch-chk" data-type="pc" data-val="${opt.id}" onchange="app.updateBatchCounter()" onclick="event.stopPropagation()" style="width:16px; height:16px; accent-color:var(--accent);">
                <label for="chk-${opt.id}" style="cursor: pointer; flex: 1; padding: 4px 0;">${opt.label}</label>
            </div>
        `).join('');
        
        if (options.length === 0) {
            listContainer.innerHTML = '<p style="padding:15px; color:#888; font-size:0.8rem; text-align:center;">Aranan kriterde Bilgisayar bulunamadı.</p>';
        }
    },

    filterBatchSelection: function() {
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
        const selected = Array.from(document.querySelectorAll('.batch-chk:checked'));
        const btn = document.getElementById('btn-batch-execute');
        const ipDisplay = document.getElementById('batch-target-ips-display');
        
        // IP Adreslerini Textarea'ya yaz (Detaylı Bilgiyle)
        if(ipDisplay) {
            const displayLines = selected.map(chk => {
                const item = this.state.inventory.find(i => i.id == chk.dataset.val);
                if (!item) return '';
                let pcLabel = item.pc_no || '---';
                if (pcLabel !== '---' && !isNaN(pcLabel)) pcLabel = `PC-${pcLabel.toString().padStart(3, '0')}`;
                return `${item.ip || 'IP Yok'} (${pcLabel} / ${item.mahal_kodu || '-'})`;
            }).filter(Boolean);
            ipDisplay.value = displayLines.join('\n');
        }

        if(btn) {
            btn.innerHTML = `<i class="fas fa-play"></i> ÇALIŞTIR (${selected.length} CİHAZ)`;
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

        let successCount = 0;
        let failedTargets = [];

        try {
            for(let i=0; i < selected.length; i++) {
                const target = selected[i];
                this.showToast(`(${i+1}/${selected.length}) ${target.name} kuruluyor...`, 'info');
                
                const bimFunction = (this.state.batchAction === 'add') ? 'AddPrinter' : 'RemovePrinter';
                const cmd = document.getElementById('batch-modal-cmd-display').value;

                try {
                    const resp = await fetch(this.state.API_BASE + '/printers/batch_action', {
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
                    
                    const res = await resp.json();
                    if(res.success) {
                        successCount++;
                    } else {
                        failedTargets.push(`${target.name} (${res.error || 'Bilinmeyen Hata'})`);
                    }
                } catch (err) {
                    failedTargets.push(`${target.name} (Bağlantı Hatası)`);
                }
            }
            
            if (failedTargets.length === 0) {
                this.showToast(`İşlem başarıyla tamamlandı. (${successCount} Cihaz)`, 'success');
            } else {
                const failedList = failedTargets.join('\n');
                alert(`İşlem tamamlandı.\nBaşarılı: ${successCount}\nBaşarısız olanlar:\n${failedList}`);
            }
            
            document.getElementById('batch-printer-modal').style.display = 'none';
            this.renderPrinters();
            
        } catch(e) {
            this.showToast('Kritik bir hata oluştu: ' + e.message, 'error');
        } finally {
            btn.disabled = false;
            btn.style.opacity = '1';
        }
    },
    searchPrinters: function() { this.applyPrinterFilters(); },
    filterPrinters: function(ptype) {
        this.state.printerType = ptype;
        document.querySelectorAll('#printer-filters .btn-chip').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.ptype === ptype);
        });
        this.applyPrinterFilters();
    },
    // 
    //  MAGICINFO
    // 
    loadMagicInfo: async function() {
        const container = document.getElementById('magicinfo-grid');
        if (container) container.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding:50px; color:#fff; opacity:0.6;"><i class="fas fa-spinner fa-spin fa-2x mb-3"></i><br>Cihaz listesi yükleniyor...</div>';
        try {
            const response = await fetch(this.state.API_BASE + '/magicinfo/get_all');
            const data = await response.json();
            if (response.ok) {
                this.state.magicinfo = Array.isArray(data) ? data : [];
                this.state.magicinfoServerFilter = 'ALL';
                this.state.magicinfoBlockFilter = 'ALL';
                this.renderMagicInfo();
                if (this.state.magicinfo.length === 0) {
                    if (container) container.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding:50px; color:#fff; opacity:0.6;"><i class="fas fa-exclamation-triangle fa-2x mb-3"></i><br>Hiç cihaz bulunamadı. magicinfo.xls dosyasını kontrol edin.</div>';
                }
            } else {
                throw new Error(data.error || 'Sunucu hatası');
            }
        } catch (e) {
            console.error("MagicInfo verileri yüklenemedi:", e);
            if (container) container.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding:50px; color:#ff4b2b;"><i class="fas fa-times-circle fa-2x mb-3"></i><br>Hata: ${e.message}</div>`;
        }
    },
    renderMagicInfo: function() {
        const container = document.getElementById('magicinfo-grid');
        if (!container) return;
        let data = this.state.magicinfo || [];
        const query = (document.getElementById('magicinfo-search')?.value || "").toUpperCase();
        const serverFilter = this.state.magicinfoServerFilter || 'ALL';
        const showScreenshot = document.getElementById('magicinfo-screenshot-toggle')?.checked || false;
        const filtered = data.filter(d => {
            if (serverFilter !== 'ALL' && d.server !== serverFilter) return false;
            const blockFilter = this.state.magicinfoBlockFilter || 'ALL';
            if (blockFilter !== 'ALL') {
                if (!d.name.startsWith(blockFilter + '-')) return false;
            }
            if (query) {
                const q = `${d.name} ${d.ip} ${d.mac} ${d.location}`.toUpperCase();
                return q.includes(query);
            }
            return true;
        });
        // CSS for magicinfo cards
        container.style.display = 'grid';
        container.style.gridTemplateColumns = 'repeat(auto-fill, minmax(200px, 1fr))';
        container.style.gap = '15px';
        container.innerHTML = filtered.map(d => {
            const screenshotUrl = showScreenshot && d.ip ? `${this.state.API_BASE}/magicinfo/screenshot?ip=${d.ip}` : 'logo/keydata.png';
            // Performans Optimizasyonu: Lazy Loading
            // src yerine data-src kullanarak sadece ekrana gelince yüklenmesini salayacaız
            const imgHtml = showScreenshot 
                ? `<img data-src="${screenshotUrl}" src="logo/keydata.png" alt="${d.name}" class="lazy-screenshot" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='logo/keydata.png'; this.style.objectFit='contain'; this.style.padding='20px';">`
                : `<img src="logo/keydata.png" alt="${d.name}" style="width: 100%; height: 100%; object-fit: contain; padding:20px;">`;
            const screenshotHtml = `<div style="height: 130px; background: #c5c5c5; display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative; border-bottom: 2px solid #5a9bd4;">
                ${imgHtml}
                ${!showScreenshot ? `<div style="position:absolute; background:rgba(0,0,0,0.6); color:#fff; padding:4px 8px; border-radius:4px; font-size:0.75rem; font-weight:bold;">Görüntü Kapalı</div>` : ''}
            </div>`;
            return `
            <div class="card fade-in" style="padding: 0; overflow: hidden; border: 1px solid #7eaadb; display: flex; flex-direction: column; cursor: pointer; background: #89c4f4; border-radius: 4px;" onclick="app.showMagicInfoControls('${d.ip}', '${d.name}', ${d.id})">
                <!-- st Kısım: Ekran Görüntüsü -->
                ${screenshotHtml}
                <!-- Alt Kısım: Mavi Bar ve İsim -->
                <div style="padding: 10px; display: flex; flex-direction: column; gap: 15px; position: relative;">
                    <span style="font-weight: 700; font-size: 0.95rem; color: #ffffff; text-shadow: 0px 1px 2px rgba(0,0,0,0.2);">${d.name || '-'}</span>
                    <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div style="display: flex; gap: 4px;">
                            <span style="background: #00d2ff; color: #fff; font-size: 0.7rem; font-weight: 800; padding: 2px 6px; border-radius: 2px;">S6</span>
                            <span style="background: #00d2ff; color: #fff; font-size: 0.7rem; font-weight: 800; padding: 2px 6px; border-radius: 2px;">P</span>
                        </div>
                        <!-- Sa alttaki (i) butonu -> Düzenleme ekranını açar -->
                        <div style="background: #ffffff; color: #89c4f4; width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-family: serif; font-size: 1rem; box-shadow: 0px 1px 3px rgba(0,0,0,0.2); z-index: 10;" 
                             title="Düzenle: ${d.ip} | MAC: ${d.mac}" 
                             onclick="event.stopPropagation(); app.openEditMagicInfoModal(${d.id})">
                             <i class="fas fa-info" style="font-size:0.8rem;"></i>
                        </div>
                    </div>
                </div>
            </div>`;
        }).join('');
        // Observer balat (Görüntüleri sadece ekrana gelince yükler)
        if (showScreenshot) {
            this.initLazyLoading();
        }
    },
    initLazyLoading: function() {
        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        obs.unobserve(img);
                    }
                }
            });
        }, { threshold: 0.1 });
        document.querySelectorAll('.lazy-screenshot').forEach(img => observer.observe(img));
    },
    showMagicInfoControls: function(ip, name, id) {
        // Kontrol butonlarını bir modal veya alert ile göster (Hızlı Kontrol)
        const modalHtml = `
            <div class="modal-overlay" id="magicinfo-control-modal" style="display:flex;">
                <div class="modal-content fade-in" style="max-width:400px; text-align:center;">
                    <div class="modal-header">
                        <h3 style="color:var(--accent);">${name} - Hızlı Kontrol</h3>
                        <i class="fas fa-times close-btn" onclick="document.getElementById('magicinfo-control-modal').remove()"></i>
                    </div>
                    <div class="modal-body" style="display:flex; flex-direction:column; gap:10px;">
                        <button class="btn btn-secondary" onclick="app.runMagicInfoAction('${ip}', 'POWER_ON'); document.getElementById('magicinfo-control-modal').remove();">
                            <i class="fas fa-power-off" style="color: #00ff88;"></i> Açık (Power On)
                        </button>
                        <button class="btn btn-secondary" onclick="app.runMagicInfoAction('${ip}', 'POWER_OFF'); document.getElementById('magicinfo-control-modal').remove();">
                            <i class="fas fa-power-off" style="color: #ff4b2b;"></i> Kapalı (Power Off)
                        </button>
                        <button class="btn btn-secondary" onclick="app.runMagicInfoAction('${ip}', 'REBOOT'); document.getElementById('magicinfo-control-modal').remove();">
                            <i class="fas fa-rotate-right" style="color: #00d2ff;"></i> Yeniden Balat
                        </button>
                        <button class="btn btn-secondary" onclick="app.runMagicInfoAction('${ip}', 'SOURCE_MAGICINFO'); document.getElementById('magicinfo-control-modal').remove();">
                            <i class="fas fa-display" style="color: #ffb400;"></i> Kaynak Deitir (MagicInfo)
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    },
    filterMagicInfoByBlock: function(block) {
        this.state.magicinfoBlockFilter = block;
        document.querySelectorAll('#magicinfo-block-filters .btn-chip').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.block === block);
        });
        this.renderMagicInfo();
    },
    openEditMagicInfoModal: function(id) {
        const d = this.state.magicinfo.find(x => x.id === id);
        if(!d) return;
        document.getElementById('edit-magicinfo-id').value = d.id;
        document.getElementById('edit-magicinfo-name').value = d.name;
        document.getElementById('edit-magicinfo-location').value = d.location;
        document.getElementById('edit-magicinfo-server').value = d.server;
        document.getElementById('magicinfo-edit-modal').style.display = 'flex';
    },
    saveMagicInfoChanges: async function() {
        const payload = {
            id: document.getElementById('edit-magicinfo-id').value,
            name: document.getElementById('edit-magicinfo-name').value,
            location: document.getElementById('edit-magicinfo-location').value,
            server: document.getElementById('edit-magicinfo-server').value
        };
        try {
            const resp = await fetch(this.state.API_BASE + '/magicinfo/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const res = await resp.json();
            if(res.success) {
                this.showToast('Deiiklikler kaydedildi.', 'success');
                document.getElementById('magicinfo-edit-modal').style.display = 'none';
                this.loadMagicInfo();
            } else throw new Error(res.error);
        } catch(e) { alert('Hata: ' + e.message); }
    },
    searchMagicInfo: function() {
        this.renderMagicInfo();
    },
    filterMagicInfo: function(server) {
        this.state.magicinfoServerFilter = server;
        document.querySelectorAll('#magicinfo-filters .btn-chip').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.server === server);
        });
        this.renderMagicInfo();
    },
    scanAllPrinters: async function() {
        if(!confirm("Tüm yazıcıların durumunu ve toner seviyesini arka planda güncellemek istediinize emin misiniz? Bu ilem birkaç dakika sürebilir.")) return;
        try {
            const resp = await fetch(this.state.API_BASE + '/printers/scan_all', { method: 'POST' });
            const data = await resp.json();
            if(data.success) {
                this.showToast(data.message, 'success');
            } else throw new Error(data.error);
        } catch(e) { this.showToast('Hata: ' + e.message, 'error'); }
    },
    runMagicInfoAction: async function(ip, action) {
        if(!ip || ip === '-') {
            this.showToast('Geçerli bir IP adresi yok!', 'error');
            return;
        }
        if(!confirm(`[${ip}] için ${action} komutu gönderilsin mi?`)) return;
        this.showToast('Komut sunucuya iletiliyor...', 'info');
        try {
            const resp = await fetch(this.state.API_BASE + '/magicinfo/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip, action })
            });
            const res = await resp.json();
            if(res.success) {
                this.showToast(res.message, 'success');
            } else {
                this.showToast(res.error || 'Komut baarısız!', 'error');
            }
        } catch(e) {
            this.showToast('Balantı hatası.', 'error');
        }
    },
    // 
    //  AREAS
    // 
    loadAreas: async function() {
        try {
            const response = await fetch(this.state.API_BASE + '/areas/get_all');
            const data = await response.json();
            this.state.areas = data;
            this.renderAreas(data);
        } catch (e) { console.error("Alanlar yüklenemedi:", e); }
    },
    renderAreas: function(data) {
        const container = document.getElementById('areas-grid');
        if (!container) return;
        data = data || this.state.areas;
        const isAdmin = this.state.activeUser.role === 'ADMIN';
        container.innerHTML = data.map((area, idx) => `
            <div class="card fade-in ${isAdmin ? 'area-card-admin' : ''}">
                <div class="flex-between" style="margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px;">
                    <span style="color: var(--accent); font-weight: 700; font-size: 1.1rem;"><i class="fas fa-folder"></i> ${area.name}</span>
                    ${isAdmin ? `<i class="fas fa-gears" style="opacity:0.3; cursor:pointer;" onclick="app.openAreaModal(${area.id})" title="Düzenle"></i>` : ''}
                </div>
                <div class="flex-between" style="padding: 5px 0; margin-bottom:8px; gap: 10px;">
                    <span style="display: block; color: var(--text-secondary); word-break: break-all; font-size: 0.85rem;">${area.path || ''}</span>
                    <button class="btn-chip" style="padding: 4px 8px; font-size: 0.7rem; flex-shrink: 0;" onclick="app.copyToClipboard('${(area.path || '').replace(/\\/g, '\\\\')}')">
                         <i class="fas fa-copy"></i> YOL
                    </button>
                </div>
                <div style="font-size: 0.75rem; color: var(--text-secondary);">
                    <div class="flex-between mb-2">
                        <span>Kullanıcı:</span>
                        <div class="flex-row gap-2">
                            <span style="color:#fff;">${area.user || ''}</span>
                            <i class="fas fa-copy" style="cursor:pointer; font-size:0.7rem;" onclick="app.copyToClipboard('${area.user || ''}')"></i>
                        </div>
                    </div>
                    <div class="flex-between mb-3">
                        <span>ifre:</span>
                        <div class="flex-row gap-2">
                            <span id="pass-${idx}" onclick="app.togglePass(${idx}, '${area.password || ''}')" style="cursor:pointer; color:var(--accent);">${area.password ? '********' : '-'}</span>
                            <i class="fas fa-copy" style="cursor:pointer; font-size:0.7rem;" onclick="app.copyToClipboard('${area.password || ''}')"></i>
                        </div>
                    </div>
                </div>
                <!-- Aksiyon Butonları (KİLİT A, TANIMLA, SİL, WIN BAT) -->
                <div class="flex-row gap-2" style="margin-top: 15px; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 12px;">
                    <button class="btn-chip" style="flex:1; font-size:0.65rem; background: rgba(0, 210, 255, 0.1);" onclick="event.stopPropagation(); app.runAreaAction(${area.id}, 'unlock')">
                        <i class="fas fa-key"></i> KİLİT A
                    </button>
                    <button class="btn-chip" style="flex:1; font-size:0.65rem; background: rgba(0, 255, 136, 0.1); color:#00ff88;" onclick="event.stopPropagation(); app.runAreaAction(${area.id}, 'define')">
                        <i class="fas fa-terminal"></i> TANIMLA
                    </button>
                    <button class="btn-chip" style="flex:1; font-size:0.65rem; background: rgba(0, 120, 215, 0.2); color:#0078d7; border: 1px solid rgba(0, 120, 215, 0.3);" onclick="app.downloadConnectBat(${area.id})">
                        <i class="fas fa-windows"></i> WIN BAT
                    </button>
                    <button class="btn-chip" style="flex:1; font-size:0.65rem; background: rgba(255, 75, 43, 0.1); color:#ff4b2b;" onclick="event.stopPropagation(); app.runAreaAction(${area.id}, 'delete')">
                        <i class="fas fa-trash"></i> SİL
                    </button>
                </div>
            </div>`).join('');
    },
    searchAreas: function() {
        const query = document.getElementById('area-search').value.toUpperCase();
        this.renderAreas(this.state.areas.filter(a =>
            (a.name || '').toUpperCase().includes(query) ||
            (a.path || '').toUpperCase().includes(query)
        ));
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
        const user = area.user || 'USER';
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
        const user = area.user || 'USER';
        const pass = area.password || 'PASS';
        const script = `#!/bin/bash
# MountAuto.sh scriptini oluturur (A koparsa otomatik balamak için)
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
        const user = area.user || 'USER';
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
        const p = this.state.printers.find(x => x.id == id);
        if (!p) return;
        let cmd = "";
        if (type === 'add') {
            cmd = `${p.pr_no || ''}/01`;
        } else {
            cmd = `${p.pr_no || ''}`;
        }
        const bimFunction = (type === 'add') ? 'AddPrinter' : 'RemovePrinter';
        // Kullanıcının istei: IP adresi mevcut bilgisayarın IP'si (client_ip) olarak gelsin.
        // openRunCommandModal içinde targetIp bo gelirse otomatik olarak istemci IP'sini çeker.
        this.openRunCommandModal(null, cmd, '', bimFunction);
    },
    rebootDevice: function(ip) {
        // Tıklanan PC'nin IP adresini dorudan gönder
        this.openRunCommandModal(null, 'reboot', ip);
    },
    // 
    //  DEPOT (DEPO YNETİMİ)
    // 
    loadDepot: async function() {
        try {
            const resp = await fetch(this.state.API_BASE + '/depot/get_all');
            const data = await resp.json();
            if (data.error) throw new Error(data.error);
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
            grid.innerHTML = '<p style="opacity:0.4; text-align:center; grid-column:1/-1;">Depoda henüz ürün yok. + Yeni rün butonuyla ekleyin.</p>';
            return;
        }
        const hasDepotPriv = ['ADMIN', 'DEPOT'].includes(this.state.activeUser.role);
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
                            catNormalized === 'YEDEK PARA' ? 'cat-yedek' :
                            catNormalized === 'EVRE BİRİMİ' ? 'cat-cevre' : 
                            catNormalized === 'GIDA' ? 'cat-gida' : 'cat-kablo';
            const barWidth = Math.min(100, (item.current_stock / Math.max(item.critical_stock * 2, 1)) * 100);
            const barColor = ratio > 1 ? '#00ff88' : (item.current_stock === 0 ? '#ff4b2b' : '#ffb400');
            const isGidaOrSarf = catNormalized === 'GIDA' || catNormalized === 'SARF MALZEME';
            const label1 = isGidaOrSarf ? 'G. Hafta' : 'Saha';
            const label2 = isGidaOrSarf ? 'Daıtılan' : 'Arızalı';
            const label3 = isGidaOrSarf ? 'Kalan' : 'Kayıp';
            return `
            <div class="card depot-card fade-in" style="cursor:pointer;" onclick="app.openEditDepotItem(${item.id})">
                <div class="flex-between mb-2">
                    <span class="category-badge ${catClass}">${item.category || 'Belirsiz'}</span>
                    <i class="fas fa-edit" style="opacity:0.5; font-size:0.8rem; color:var(--accent);"></i>
                </div>
                <div style="font-size: 1.1rem; font-weight: 700; color: #fff; margin-bottom: 5px; min-height: 2.4em; display: flex; align-items: center;">${item.name}</div>
                <div class="flex-between" style="font-size: 0.85rem;">
                    <span>Depo: <strong style="color:#fff; font-size:1.1rem;">${item.current_stock}</strong> ${item.unit}</span>
                    <span style="opacity:0.5;">Sınır: ${item.critical_stock}</span>
                </div>
                <div class="stock-bar">
                    <div class="stock-bar-fill" style="width: ${barWidth}%; background: ${barColor};"></div>
                </div>
                <div class="flex-row gap-2 mt-2" style="font-size: 0.75rem; opacity: 0.8; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 6px;">
                    <div class="flex-column" style="flex:1; align-items:center;">
                        <span style="opacity:0.6; font-size: 0.6rem;">${label1}</span>
                        <strong style="color:var(--accent);">${item.saha_stock || 0}</strong>
                    </div>
                    <div class="flex-column" style="flex:1; align-items:center; border-left:1px solid rgba(255,255,255,0.1); border-right: ${isGidaOrSarf ? 'none' : '1px solid rgba(255,255,255,0.1)'};">
                        <span style="opacity:0.6; font-size: 0.6rem;">${label2}</span>
                        <strong style="color:#ffb400;">${isGidaOrSarf ? (item.weekly_distributed || 0) : (item.arizali_stock || 0)}</strong>
                    </div>
                    ${isGidaOrSarf ? '' : `
                    <div class="flex-column" style="flex:1; align-items:center;">
                        <span style="opacity:0.6; font-size: 0.6rem;">${label3}</span>
                        <strong style="color:#ff4b2b;">${item.kayip_stock || 0}</strong>
                    </div>`}
                </div>
                <div class="stock-indicator ${stockClass} mt-2">
                    <i class="fas ${stockIcon}"></i> ${stockText}
                </div>
                <div class="depot-actions">
                    <button class="btn-chip" onclick="event.stopPropagation(); app.openDepotTransaction(${item.id}, '${item.name.replace(/'/g, "\\'")}')"><i class="fas fa-exchange-alt"></i> Giri/ıkı</button>
                    ${hasDepotPriv ? `
                    <button class="btn-chip" onclick="event.stopPropagation(); app.deleteDepotItem(${item.id})" style="color:#ff4b2b;" title="Sil"><i class="fas fa-trash"></i></button>
                    ` : ''}
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
        } else if (cat === 'ALERTS') {
            const alerts = items.filter(d => (parseInt(d.current_stock) || 0) <= (parseInt(d.critical_stock) || 0));
            this.renderDepot(alerts);
        } else {
            // Case-insensitive ve daha esnek karılatırma
            const norm = (s) => (s || '').toUpperCase().replace(/İ/g, 'I').replace(/Ğ/g, 'G').replace(/Ü/g, 'U').replace(/Ş/g, 'S').replace(/Ö/g, 'O').replace(/Ç/g, 'C').trim();
            const targetNorm = norm(cat);
            this.renderDepot(items.filter(d => {
                const itemCatNorm = norm(d.category);
                return itemCatNorm === targetNorm || itemCatNorm.includes(targetNorm);
            }));
        }
    },
    openAddDepotModal: function() {
        document.getElementById('depot-add-form').reset();
        document.getElementById('depot-unit').value = 'Adet';
        document.getElementById('depot-saha').value = 0;
        document.getElementById('depot-arizali').value = 0;
        document.getElementById('depot-kayip').value = 0;
        document.getElementById('depot-asset-fields').style.display = 'none';
        document.getElementById('depot-add-modal').style.display = 'flex';
    },
    handleDepotCategoryChange: function(val) {
        val = val || document.getElementById('depot-category').value;
        const fields = document.getElementById('depot-asset-fields');
        if (!fields) return;
        // Varlık alanlarını göster/gizle
        const show = ['Sarf Malzeme', 'Gıda', 'evre Birimi', 'Yedek Parça'].includes(val);
        fields.style.display = show ? 'block' : 'none';
        // Label'ları güncelle
        const labels = fields.querySelectorAll('label');
        if (labels.length >= 4) {
            const isConsumable = val === 'Gıda' || val === 'Sarf Malzeme';
            labels[1].innerText = isConsumable ? 'GEEN HAFTA' : 'SAHADA';
            labels[2].innerText = isConsumable ? 'DAITILAN' : 'ARIZALI';
            labels[3].innerText = isConsumable ? 'DİER / KALAN' : 'KAYIP';
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
        const titleEl = document.getElementById('depot-add-modal-title') || document.getElementById('depot-modal-title');
        if(titleEl) titleEl.innerText = 'rün Düzenle';
        document.getElementById('depot-item-id').value = item.id;
        document.getElementById('depot-name').value = item.name || '';
        document.getElementById('depot-current').value = item.current_stock || 0;
        document.getElementById('depot-critical').value = item.critical_stock || 0;
        document.getElementById('depot-unit').value = item.unit || 'Adet';
        document.getElementById('depot-desc').value = item.description || '';
        document.getElementById('depot-saha').value = item.saha_stock || 0;
        document.getElementById('depot-arizali').value = item.arizali_stock || 0;
        document.getElementById('depot-kayip').value = item.kayip_stock || 0;
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
        document.getElementById('depot-add-modal').style.display = 'flex';
    },
    syncDepotsFromExcel: async function() {
        if(!confirm('DİKKAT: Veritabanındaki güncel depo bilgileri Excel üzerinden batan oluturulacaktır. Onaylıyor musunuz?')) return;
        const btn = document.getElementById('btn-depot-sync');
        if(btn) { btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Aktüalize Ediliyor...'; btn.disabled = true; }
        try {
            const resp = await fetch(this.state.API_BASE + '/depot/sync_from_excel', { method: 'POST' });
            const result = await resp.json();
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
            const resp = await fetch(this.state.API_BASE + '/printers/sync_from_excel', { method: 'POST' });
            const result = await resp.json();
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
            const resp = await fetch(this.state.API_BASE + '/depot/weekly_report');
            const data = await resp.json();
            if(data.error) throw new Error(data.error);
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
            alert('Rapor oluturulamadı! Hata detayı: ' + e.message);
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
            const resp = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: cat,
                    name: name,
                    current_stock: parseInt(document.getElementById('depot-current').value) || 0,
                    critical_stock: parseInt(document.getElementById('depot-critical').value) || 5,
                    unit: document.getElementById('depot-unit').value || 'Adet',
                    description: document.getElementById('depot-desc').value || '',
                    saha_stock: parseInt(document.getElementById('depot-saha').value) || 0,
                    arizali_stock: parseInt(document.getElementById('depot-arizali').value) || 0,
                    kayip_stock: parseInt(document.getElementById('depot-kayip').value) || 0
                })
            });
            const result = await resp.json();
            if (result.error) throw new Error(result.error);
            document.getElementById('depot-add-modal').style.display = 'none';
            this.showToast(id ? 'rün baarıyla güncellendi!' : 'rün depoya eklendi!');
            await this.loadDepot();
            if (this.state.depot_activeFilter) {
                this.filterDepot(this.state.depot_activeFilter);
            }
            this.loadDashboardStats();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    openDepotTransaction: function(id, name) {
        document.getElementById('depot-trans-title').innerText = `Stok İlemi: ${name}`;
        document.getElementById('trans-item-id').value = id;
        document.getElementById('trans-quantity').value = 1;
        document.getElementById('trans-note').value = '';
        this.setTransType('in');
        document.getElementById('depot-transaction-modal').style.display = 'flex';
    },
    setTransType: function(type) {
        document.getElementById('trans-type').value = type;
        document.getElementById('trans-type-in').classList.toggle('active', type === 'in');
        document.getElementById('trans-type-out').classList.toggle('active', type === 'out');
        // ıkı ise neden kutusunu göster
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
            const resp = await fetch(this.state.API_BASE + '/depot/transaction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    depot_item_id: parseInt(itemId),
                    type: type,
                    quantity: qty,
                    note: note,
                    user_name: this.state.activeUser.name,
                    user_id: this.state.activeUser.key
                })
            });
            const result = await resp.json();
            if (result.error) throw new Error(result.error);
            document.getElementById('depot-transaction-modal').style.display = 'none';
            this.showToast(`Stok ${type === 'in' ? 'girii' : 'çıkıı'} yapıldı! Yeni stok: ${result.new_stock}`);
            await this.loadDepot();
            if (this.state.depot_activeFilter) {
                this.filterDepot(this.state.depot_activeFilter);
            }
            this.loadDashboardStats();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    openDepotAssign: function(id, name) {
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
            const resp = await fetch(this.state.API_BASE + '/depot/transaction', {
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
                    note: `Cihaz ${deviceType.toUpperCase()}-${deviceId} için atandı`
                })
            });
            const result = await resp.json();
            if (result.error) throw new Error(result.error);
            document.getElementById('depot-assign-modal').style.display = 'none';
            this.showToast(`Malzeme cihaza atandı ve teknik not oluturuldu!`);
            await this.loadDepot();
            if (this.state.depot_activeFilter) {
                this.filterDepot(this.state.depot_activeFilter);
            }
            this.loadDashboardStats();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    deleteDepotItem: async function(id) {
        if (!confirm('Bu ürünü silmek istediinize emin misiniz?')) return;
        try {
            const resp = await fetch(this.state.API_BASE + '/depot/delete/' + id, { method: 'DELETE' });
            const result = await resp.json();
            if (result.error) throw new Error(result.error);
            this.showToast('rün silindi.');
            this.loadDepot();
            this.loadDashboardStats();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    // 
    //  DEVICE DETAIL & EDIT MODAL
    // 
    openDeviceDetail: async function(id, type) {
        try {
            // Herkes detayları görebilsin (VIEWER dahil)
        this.state.editingId = id;
        this.state.editingType = type;
        // Find item data
        let item = null;
        if (type === 'pc') {
            item = this.state.inventory.find(i => i.id == id);
        } else if (type === 'pr') {
            item = this.state.printers.find(p => p.id == id);
        }
        if (!item) {
            alert('Cihaz bulunamadı (ID: ' + id + ')');
            return;
        }
        // Set title
        const title = document.getElementById('device-detail-title');
        if (type === 'pc') {
            const pcLabel = item.pc_no ? `PC-${item.pc_no.toString().padStart(3, '0')}` : `ID: ${id}`;
            title.innerText = `${pcLabel}  ${item.mahal_adi || 'Detay'}`;
        } else {
            title.innerText = `Yazıcı: ${item.pr_no || item.model || 'Detay'}`;
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
            const resp = await fetch(this.state.API_BASE + '/keyos/check/' + serial);
            const data = await resp.json();
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
            const resp = await fetch(this.state.API_BASE + `/logs/get_record_history/${type === 'pc' ? 'inventory' : 'printers'}/${id}`);
            const logs = await resp.json();
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
            const isSimpleDevice = ['SIRAMATIK', 'KIOSK', 'TABLET'].includes((item.device_type || '').toUpperCase());
            const hideSimpleStyle = isSimpleDevice ? 'display: none;' : '';
            container.innerHTML = `
                <div class="edit-form-grid" style="gap: 12px; padding: 0;">
                    <!-- Row 1: Mahal, Adi, Hostname -->
                    <div class="form-row form-row-3">
                        <div class="form-group">
                            <label>MAHAL KODU</label>
                            <input type="text" class="search-bar" id="edit-mahal_kodu" value="${item.mahal_kodu || ''}" list="mahal-datalist" onchange="app.handleMahalSelection(this.value, 'code')">
                        </div>
                        <div class="form-group">
                            <label>MAHAL ADI</label>
                            <input type="text" class="search-bar" id="edit-mahal_adi" value="${item.mahal_adi || ''}" list="mahal-name-datalist" onchange="app.handleMahalSelection(this.value, 'name')">
                        </div>
                        <div class="form-group">
                            <label>HOSTNAME</label>
                            <input type="text" class="search-bar" id="edit-hostname" value="${item.hostname || ''}" readonly style="background:rgba(255,255,255,0.02); color:var(--accent); font-weight:700;">
                        </div>
                    </div>
                    <!-- Row 2: Kule/Kat, Telefon -->
                    <div class="form-row form-row-3">
                        <div class="form-group">
                            <label>KULE/KAT</label>
                            <div class="flex-row gap-2">
                                <input type="text" class="search-bar" id="edit-kule" value="${item.kule || ''}" style="flex:1; opacity:0.6;" readonly>
                                <input type="text" class="search-bar" id="edit-kat" value="${item.kat || ''}" style="flex:1; opacity:0.6;" readonly>
                            </div>
                        </div>
                        <div class="form-group" style="grid-column: span 2; ${hideSimpleStyle}">
                            <label>TELEFON</label>
                            <input type="text" class="search-bar" id="edit-telefon" value="${item.telefon || ''}" readonly style="opacity:0.6;">
                        </div>
                    </div>
                    <!-- Row 3: IP, PC Seri, Yazıcılar -->
                    <div class="form-row form-row-3">
                         <div class="form-group">
                            <label>IP ADRESİ</label>
                            <input type="text" class="search-bar" id="edit-ip" value="${item.ip || ''}">
                        </div>
                        <div class="form-group">
                            <label>PC SERİ NO</label>
                            <input type="text" class="search-bar" id="edit-pc_seri" value="${item.pc_seri || ''}">
                        </div>
                        <div class="form-group" style="${hideSimpleStyle}">
                            <label>BALI YAZICILAR</label>
                            <input type="text" class="search-bar" id="edit-bagli_yazicilar" value="${item.bagli_yazicilar || ''}" readonly style="opacity:0.6;">
                        </div>
                    </div>
                    <!-- Row 4: BY, BO, TR -->
                    <div class="form-row form-row-3" style="${hideSimpleStyle}">
                        <div class="form-group">
                            <label>BARKOD YAZICI SERİ</label>
                            <input type="text" class="search-bar" id="edit-by_seri" value="${item.by_seri || ''}" list="by-seri-datalist" oninput="app.validateDuplicateSerials(this)">
                        </div>
                        <div class="form-group">
                            <label>BARKOD OKUYUCU SERİ</label>
                            <input type="text" class="search-bar" id="edit-bo_seri" value="${item.bo_seri || ''}" list="bo-seri-datalist" oninput="app.validateDuplicateSerials(this)">
                        </div>
                        <div class="form-group">
                            <label>TARAYICI SERİ NO</label>
                            <input type="text" class="search-bar" id="edit-tarayici_seri" value="${item.tarayici_seri || ''}" list="tr-seri-datalist" oninput="app.validateDuplicateSerials(this)">
                        </div>
                    </div>
                    <!-- Row 5: Monitor -->
                    <div class="form-row form-row-2" style="${hideSimpleStyle}">
                        <div class="form-group">
                            <label>MONİTR SERİ / MODEL</label>
                            <div class="flex-row gap-2">
                                <input type="text" class="search-bar" id="edit-monitor_seri" value="${item.monitor_seri || ''}" placeholder="Seri" style="flex:1;">
                                <input type="text" class="search-bar" id="edit-monitor_model" value="${item.monitor_model || ''}" placeholder="Model" style="flex:1;">
                            </div>
                        </div>
                        <div class="form-group">
                            <label>2. MONİTR SERİ / MODEL</label>
                            <div class="flex-row gap-2">
                                <input type="text" class="search-bar" id="edit-monitor2_seri" value="${item.monitor2_seri || ''}" placeholder="Seri" style="flex:1;">
                                <input type="text" class="search-bar" id="edit-monitor2_model" value="${item.monitor2_model || ''}" placeholder="Model" style="flex:1;">
                            </div>
                        </div>
                    </div>
                    <!-- Row: Tablet Specific (Only for TABLET) -->
                    ${item.device_type === 'TABLET' ? `
                    <div class="form-row form-row-2">
                        <div class="form-group">
                            <label>ZİMMETLENEN Kİİ</label>
                            <input type="text" class="search-bar" id="edit-assigned_to" value="${item.assigned_to || ''}">
                        </div>
                        <div class="form-group">
                            <label>CEP TELEFON</label>
                            <input type="text" class="search-bar" id="edit-phone" value="${item.phone || ''}">
                        </div>
                    </div>
                    <div class="form-row form-row-2">
                        <div class="form-group">
                            <label>UNVAN</label>
                            <input type="text" class="search-bar" id="edit-title" value="${item.title || ''}">
                        </div>
                        <div class="form-group">
                            <label>BİRİM</label>
                            <input type="text" class="search-bar" id="edit-unit" value="${item.unit || ''}">
                        </div>
                    </div>
                    ` : ''}
                    <!-- Row 6: Açıklama -->
                    <div class="form-group">
                        <label>AIKLAMA</label>
                        <textarea class="search-bar" id="edit-aciklama" style="min-height:80px; height:80px; resize:none; width:100%; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.02); color:#fff; border-radius:4px; padding:8px;">${item.aciklama || ''}</textarea>
                    </div>
                    <div id="duplicate-warning" style="display:none; color:#ff4b2b; font-size:0.7rem; font-weight:700; background:rgba(255,75,43,0.1); padding:5px 10px; border-radius:4px; text-align:center; margin-top:5px;">
                        <i class="fas fa-exclamation-triangle"></i> DİKKAT: <span id="duplicate-warning-text"></span>
                    </div>
                    <!-- Bottom Status Bar -->
                    <div class="flex-column gap-2" style="border-top:1px solid rgba(255,255,255,0.05); padding-top:10px;">
                        <div class="flex-row gap-2" style="align-items:center; flex-wrap:wrap;">
                            <label class="check-container" style="font-size:0.7rem;">Sahada
                                <input type="checkbox" id="edit-sahada" ${this.isTrue(item.sahada) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-sahada')">
                                <span class="checkmark"></span>
                            </label>
                            <label class="check-container" style="font-size:0.7rem;">Depoda
                                <input type="checkbox" id="edit-depo" ${this.isTrue(item.depo) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-depo')">
                                <span class="checkmark"></span>
                            </label>
                            <label class="check-container" style="font-size:0.7rem;">Arızalı
                                <input type="checkbox" id="edit-arizali" ${this.isTrue(item.arizali) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-arizali')">
                                <span class="checkmark"></span>
                            </label>
                            <label class="check-container" style="font-size:0.7rem;">Kayıp
                                <input type="checkbox" id="edit-mahalsiz" ${this.isTrue(item.mahalsiz) ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-mahalsiz')">
                                <span class="checkmark"></span>
                            </label>
                            <label class="check-container" style="font-size:0.7rem; color:var(--accent); font-weight:700;">KURULUM BEKLİYOR
                                <input type="checkbox" id="edit-kurulum_bekliyor" ${item.kurulum_bekliyor === 1 ? 'checked' : ''} onclick="app.handleExclusiveCheck('status', 'edit-kurulum_bekliyor')">
                                <span class="checkmark"></span>
                            </label>
                        </div>
                        <div class="flex-row gap-2" style="justify-content: flex-start;">
                             <label class="check-container" style="font-size:0.75rem;">Windows
                                <input type="checkbox" id="edit-windows" ${this.isTrue(item.windows) ? 'checked' : ''} onclick="app.handleExclusiveCheck('os', 'edit-windows')">
                                <span class="checkmark"></span>
                            </label>
                            <label class="check-container" style="font-size:0.75rem;">Keyos
                                <input type="checkbox" id="edit-keyos" ${this.isTrue(item.keyos) ? 'checked' : ''} onclick="app.handleExclusiveCheck('os', 'edit-keyos')">
                                <span class="checkmark"></span>
                            </label>
                        </div>
                    </div>
                </div>
                ${this.loadEditFormFooter('pc')}`;
        } else {
            container.innerHTML = `
                <div class="edit-form-grid">
                    <div class="form-row form-row-2">
                        <div class="form-group">
                            <label>PR NUMARASI</label>
                            <input type="text" class="search-bar" id="edit-pr_no" value="${item.pr_no || ''}" ${!isAdmin ? 'readonly' : ''}>
                        </div>
                        <div class="form-group">
                            <label>MODEL</label>
                            <input type="text" class="search-bar" id="edit-model" value="${item.model || ''}" ${!isAdmin ? 'readonly' : ''}>
                        </div>
                    </div>
                    <!-- 2. Satır: MAHAL VE IP -->
                    <div class="form-row form-row-2">
                        <div class="form-group">
                            <label>MAHAL ADI / KODU</label>
                            <input type="text" class="search-bar" id="edit-mahal" value="${item.mahal || ''}" ${!isAdmin ? 'readonly' : ''}>
                        </div>
                        <div class="form-group">
                            <label>IP ADRESİ</label>
                            <input type="text" class="search-bar" id="edit-ip" value="${item.ip || ''}" ${!isAdmin ? 'readonly' : ''}>
                        </div>
                    </div>
                    <!-- 3. Satır: SERİ VE MAC -->
                    <div class="form-row form-row-2">
                        <div class="form-group">
                            <label>SERİ NO</label>
                            <input type="text" class="search-bar" id="edit-seri" value="${item.seri || ''}" ${!isAdmin ? 'readonly' : ''}>
                        </div>
                        <div class="form-group">
                            <label>MAC ADRESİ</label>
                            <input type="text" class="search-bar" id="edit-mac" value="${item.mac || ''}">
                        </div>
                    </div>
                    ${item.ip ? `
                    <div style="background:rgba(0,210,255,0.05); padding:10px; border-radius:8px; border:1px solid rgba(0,210,255,0.1); margin: 10px 0;">
                        <div class="flex-between">
                            <span style="font-size:0.75rem; color:var(--accent); font-weight:700;"><i class="fas fa-satellite-dish"></i> CANLI YAZICI DURUMU</span>
                            <button class="btn-chip" style="font-size:0.65rem;" onclick="app.checkPrinterStatus('${item.ip}')">YENİLE</button>
                        </div>
                        <div id="printer-live-status-area" style="font-size:0.85rem; color:#fff; margin-top:8px; opacity:0.7;">
                            Sorgulamak için Yenile'ye basın...
                        </div>
                    </div>` : ''}
                    <div class="form-group mt-2">
                        <label>Durum</label>
                        <div class="flex-row gap-2">
                            <label class="check-container" style="flex:1">Kurulu
                                <input type="radio" name="printer-status" id="edit-status-kurulu" ${(!item.status || item.status === 'Kurulu') ? 'checked' : ''} value="Kurulu">
                                <span class="checkmark" style="border-radius:50%;"></span>
                            </label>
                            <label class="check-container" style="flex:1">Arızalı
                                <input type="radio" name="printer-status" id="edit-status-arizali" ${item.status === 'Arızalı' ? 'checked' : ''} value="Arızalı">
                                <span class="checkmark" style="border-radius:50%;"></span>
                            </label>
                            <label class="check-container" style="flex:1">Depoda
                                <input type="radio" name="printer-status" id="edit-status-depo" ${item.status === 'Depoda' ? 'checked' : ''} value="Depoda">
                                <span class="checkmark" style="border-radius:50%;"></span>
                            </label>
                            <label class="check-container" style="flex:1">Serviste
                                <input type="radio" name="printer-status" id="edit-status-serviste" ${item.status === 'Serviste' ? 'checked' : ''} value="Serviste">
                                <span class="checkmark" style="border-radius:50%;"></span>
                            </label>
                        </div>
                    </div>
                </div>
                ${this.loadEditFormFooter('pr')}`;
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
            const el = document.getElementById('edit-' + id) || document.getElementById('add-' + id);
            if (el) el.value = val;
        };
        setVal('mahal_kodu', code);
        setVal('mahal_adi', info.name);
        setVal('kule', info.kule);
        setVal('kat', info.kat);
        setVal('telefon', info.phone);
    },
    handleExclusiveCheck: function(group, currentId) {
        let targets = [];
        if (group === 'status') {
            targets = ['edit-sahada', 'edit-depo', 'edit-arizali', 'edit-mahalsiz'];
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
                ['kule', 'kat', 'mahal_kodu', 'mahal_adi', 'telefon', 'ip', 'aciklama', 'pc_seri', 'monitor_seri', 'monitor_model', 'monitor2_seri', 'monitor2_model', 'bagli_yazicilar', 'by_seri', 'bo_seri', 'tarayici_seri', 'assigned_to', 'phone', 'title', 'unit'].forEach(k => {
                    const el = document.getElementById('edit-' + k);
                    if(el) payload[k] = el.value;
                });
                ['sahada', 'depo', 'arizali', 'mahalsiz', 'windows', 'keyos', 'kurulum_bekliyor'].forEach(k => {
                    const el = document.getElementById('edit-' + k);
                    if(el) payload[k] = el.checked ? 1 : 0;
                });
                const resp = await fetch(this.state.API_BASE + '/inventory/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await resp.json();
                if (result.error) throw new Error(result.error);
            } else if (type === 'pr') {
                // Mevcut yazıcı durumunu kontrol et
                const currentPrinter = (this.state.printers || []).find(p => p.id == id);
                const currentStatus = currentPrinter ? currentPrinter.status : '';
                ['pr_no', 'model', 'ip', 'seri', 'mac', 'mahal'].forEach(k => {
                    const el = document.getElementById('edit-' + k);
                    if(el) payload[k] = el.value;
                });
                const selectedStatusEl = document.querySelector('input[name="printer-status"]:checked');
                const selectedStatus = selectedStatusEl ? selectedStatusEl.value : '';
                if (selectedStatus) payload.status = selectedStatus;

                // YENİ GÜVENLİK: Servis tablosunda açık kaydı (Dönü tarihi olmayan) var mı?
                const openServiceRecord = this.state_service.raw.find(s => 
                    s.pr_no === payload.pr_no && (!s.return_date || s.return_date.trim() === "" || s.return_date === "-")
                );

                if (openServiceRecord && selectedStatus === 'Kurulu') {
                    alert("Yazıcı servis işlemleri tamamlanmamıştır, depocunuz ile iletişime geçin.");
                    return;
                }

                // Eski koruma mantıı (Yedek olarak)
                if ((currentStatus === 'Arızalı' || currentStatus === 'Serviste') && selectedStatus === 'Kurulu' && !openServiceRecord) {
                    alert("UYARI: Bu yazıcının açık bir servis kaydı bulunmaktadır.\n\nYazıcıyı 'Kurulu' olarak iaretleyebilmek için depocunun servis kaydını kapatması (Depoya çekmesi) gerekmektedir.");
                    return;
                }
                const resp = await fetch(this.state.API_BASE + '/printers/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await resp.json();
                if (result.error) throw new Error(result.error);
                await this.loadInventory(); // Reload all to refresh printer state
                this.renderPrinters(this.state.printers);
            }
            this.closeDeviceDetail();
            this.showToast('Cihaz bilgileri güncellendi!');
            this.loadInventory();
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
            const resp = await fetch(this.state.API_BASE + '/printers/status/' + ip);
            const data = await resp.json();
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
            const resp = await fetch(this.state.API_BASE + '/service/sync_from_excel', { method: 'POST' });
            const result = await resp.json();
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
        const item = this.state.inventory.find(i => i.id == this.state.editingId);
        const isPC = type === 'pc' && !['SIRAMATIK', 'KIOSK', 'TABLET'].includes((item.device_type || '').toUpperCase());
        if (isPC) {
            return `
            <div class="flex-row gap-2 mt-4" style="display: grid; grid-template-columns: 1fr 1fr 1fr 1.5fr;">
                <button class="btn btn-secondary" onclick="app.closeDeviceDetail()">İptal</button>
                <button class="btn btn-accent" id="btn-save-device" onclick="app.saveEdit()">Güncelle</button>
                <button class="btn btn-secondary" onclick="app.fetchKeyOSData()" style="border-color: #ff4b2b; color: #ff4b2b; background: rgba(255,75,43,0.05); font-size: 0.75rem; white-space: nowrap; padding: 0 5px;">
                    <i class="fas fa-rotate"></i> KeyOS Sorgula
                </button>
                <button class="btn btn-secondary" onclick="app.openKeyOSEditModal()" style="background: rgba(0,210,255,0.1); border-color: var(--accent); white-space: nowrap; font-size: 0.75rem; padding: 0 5px;">
                    <i class="fas fa-shield-halved"></i> KeyOS zerinden Düzenle
                </button>
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
            const resp = await fetch(this.state.API_BASE + `/notes/get/${deviceType}/${deviceId}`);
            const notes = await resp.json();
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
                <input type="text" id="edit-note-title-${noteId}" class="input-modern mb-2" value="${oldTitle}" placeholder="Balık" style="width:100%;">
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
            const resp = await fetch(this.state.API_BASE + `/notes/update/${noteId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title, content,
                    user_id: this.state.activeUser.key,
                    role: this.state.activeUser.role
                })
            });
            const result = await resp.json();
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
            const resp = await fetch(this.state.API_BASE + '/notes/add', {
                method: 'POST',
                body: formData
            });
            const result = await resp.json();
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
            const resp = await fetch(
                this.state.API_BASE + `/notes/delete/${noteId}?user_id=${this.state.activeUser.key}&role=${this.state.activeUser.role}`,
                { method: 'DELETE' }
            );
            const result = await resp.json();
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
            const resp = await fetch(this.state.API_BASE + `/notes/kb/${this.state_kb.tab}`);
            const data = await resp.json();
            this.state_kb.raw = data;
            this.renderGeneralNotes(data);
        } catch (e) {
            grid.innerHTML = '<p>Balantı hatası.</p>';
        }
    },
    syncKBFromExcel: async function() {
        if (!confirm("database/bilgi_bankasi.xlsx dosyasındaki veriler Bilgi Bankası'na aktarılacak. Mevcut aynı balıklı kayıtlar güncellenecektir. Emin misiniz?")) return;
        try {
            this.showToast('Bilgi Bankası senkronize ediliyor...', 'info');
            const resp = await fetch(this.state.API_BASE + '/notes/kb/sync_from_excel', { method: 'POST' });
            const result = await resp.json();
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
            const resp = await fetch(this.state.API_BASE + '/downloads/list');
            const data = await resp.json();
            if (data.success) {
                this.renderDownloads(data.files);
            } else {
                throw new Error(data.error);
            }
        } catch (e) {
            if (grid) grid.innerHTML = `<div style="color:red; text-align:center; padding:30px;">Dosyalar yüklenemedi: ${e.message}</div>`;
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
                ${files.map(file => {
                    const isBat = file.toLowerCase().endsWith('.bat');
                    const icon = isBat ? 'fa-terminal' : 'fa-file-arrow-down';
                    const color = isBat ? '#0078d7' : 'var(--accent)';
                    return `
                    <div class="card" style="padding: 15px; display: flex; align-items: center; gap: 15px; cursor: pointer; transition: transform 0.2s;" onclick="window.location.href='${this.state.API_BASE}/downloads/get/${encodeURIComponent(file)}'">
                        <div style="width: 45px; height: 45px; background: rgba(255,255,255,0.05); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: ${color};">
                            <i class="fas ${icon} fa-xl"></i>
                        </div>
                        <div style="flex: 1; overflow: hidden;">
                            <div style="font-weight: 600; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${file}">${file}</div>
                            <div style="font-size: 0.7rem; opacity: 0.5; margin-top: 2px;">Tıklayarak İndir</div>
                        </div>
                        <i class="fas fa-download" style="opacity: 0.3;"></i>
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
            const date = n.created_at ? new Date(n.created_at).toLocaleDateString('tr-TR') : '-';
            const isKodlar = this.state_kb.tab === 'kodlar';
            const isAdmin = this.state.activeUser && this.state.activeUser.role === 'ADMIN';
            let contentHtml = '';
            if (isKodlar || true) {
                let userControlHtml = '';
                if (n.requires_user) {
                    userControlHtml = `
                    <div class="kb-user-control mb-2">
                        <div class="flex-row gap-2">
                            <input type="text" id="kb-user-input-${n.id}" class="search-bar" style="height:35px; font-size:0.8rem;" placeholder="Kullanıcı Adı Girin (r: mehmet)">
                            <button class="btn btn-accent btn-sm" onclick="app.applyKBUserPlaceholder(${n.id})">Uygula</button>
                        </div>
                    </div>`;
                }
                contentHtml = `
                    ${userControlHtml}
                    <div class="kb-code-container">
                        <div class="kb-code-block">
                            <pre id="kb-pre-${n.id}">${n.content.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
                        </div>
                        <div class="kb-action-sidebar" style="display: flex; flex-direction: column; gap: 10px; align-items: flex-end;">
                            <div class="flex-row gap-3" style="margin-bottom: 5px;">
                                <i class="fas fa-copy kb-mini-icon" onclick="app.copyToClipboard(document.getElementById('kb-pre-${n.id}').innerText)" title="Kopyala"></i>
                                ${isAdmin ? `
                                <i class="fas fa-edit kb-mini-icon" onclick="app.editKBEntry(${n.id})" title="Düzenle" style="color: #ffcc00;"></i>
                                ` : ''}
                            </div>
                            ${isKodlar ? `
                            <button class="btn btn-accent btn-sm" onclick="app.openRunCommandModal(${n.id})" style="width: 100%; white-space: nowrap;">
                                <i class="fas fa-terminal"></i> ALITIR
                            </button>` : ''}
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
        const n = this.state_kb.raw.find(item => item.id == id);
        if(!n) return;
        document.getElementById('kb-modal').style.display = 'flex';
        document.getElementById('kb-modal-title').innerHTML = '<i class="fas fa-edit"></i> Bilgiyi Düzenle';
        document.getElementById('kb-edit-id').value = id;
        document.getElementById('kb-type').value = n.type || 'kodlar';
        document.getElementById('kb-title').value = n.title || '';
        document.getElementById('kb-content').value = n.content || '';
        document.getElementById('kb-requires-user').checked = !!n.requires_user;
        document.getElementById('kb-btn-delete').style.display = 'block';
        document.getElementById('kb-title').focus();
    },
    saveKBItem: async function() {
        const editId = document.getElementById('kb-edit-id').value;
        const title = document.getElementById('kb-title').value;
        const content = document.getElementById('kb-content').value;
        const type = document.getElementById('kb-type').value;
        const imageFile = document.getElementById('kb-image').files[0];
        if (!title || !content) return alert('Lütfen balık ve içerik giriniz.');
        try {
            this.showToast('Bilgi kaydediliyor...', 'info');
            const formData = new FormData();
            formData.append('device_type', type);
            formData.append('type', type); // Her iki isim de gerekebilir
            formData.append('title', title);
            formData.append('content', content);
            formData.append('requires_user', document.getElementById('kb-requires-user').checked ? 1 : 0);
            formData.append('user_id', this.state.activeUser.key);
            formData.append('user_name', this.state.activeUser.name);
            formData.append('role', this.state.activeUser.role);
            if (imageFile) formData.append('image', imageFile);
            let url = this.state.API_BASE + '/notes/kb/add';
            if (editId) {
                url = `${this.state.API_BASE}/notes/kb/update/${editId}`;
            }
            const resp = await fetch(url, {
                method: 'POST',
                body: formData
            });
            const result = await resp.json();
            if (result.error) throw new Error(result.error);
            this.showToast(editId ? 'Kayıt güncellendi!' : 'Yeni bilgi eklendi!');
            this.closeKBModal();
            this.loadGeneralNotes();
        } catch (e) { alert('Hata: ' + e.message); }
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
            const pre = document.getElementById(`kb-pre-${id}`);
            preContent = pre ? pre.innerText : "";
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
                const resp = await fetch(this.state.API_BASE + '/bim/client_ip');
                const data = await resp.json();
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
        const command = document.getElementById('run-command-text').value.trim();
        const bimFunction = document.getElementById('run-command-func').value || 'RunCommand';
        const bimUser = document.getElementById('run-command-bim-user').value.trim();
        const bimPass = document.getElementById('run-command-bim-pass').value.trim();
        const btn = document.getElementById('btn-execute-run');
        if (!ip) return alert('Lütfen komutun çalıtırılacaı IP adresini giriniz.');
        if (!bimUser) return alert('Lütfen BİM kullanıcı adınızı giriniz.');
        if (!bimPass) return alert('Lütfen BİM ifrenizi giriniz.');
        if (!command) return alert('alıtırılacak komut bulunamadı.');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> İleniyor...';
        btn.disabled = true;
        try {
            const resp = await fetch(this.state.API_BASE + '/bim/run_command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ip: ip,
                    command: command,
                    username: bimUser,
                    password: bimPass,
                    function: bimFunction
                })
            });
            const result = await resp.json();
            if (!resp.ok || result.error) {
                throw new Error(result.error || 'Beklenmeyen bir hata olutu');
            }
            this.showToast('Komut baarıyla iletildi: ' + (result.result || ''));
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
            const resp = await fetch(`${this.state.API_BASE}/notes/kb/delete/${id}?user_id=${this.state.activeUser.key}&role=${this.state.activeUser.role}`, {
                method: 'DELETE'
            });
            const result = await resp.json();
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
    openKBModal: function() {
        document.getElementById('kb-modal').style.display = 'flex';
        document.getElementById('kb-modal-title').innerHTML = '<i class="fas fa-pen-to-square"></i> Yeni Bilgi / Not Ekle';
        document.getElementById('kb-edit-id').value = '';
        document.getElementById('kb-title').value = '';
        document.getElementById('kb-content').value = '';
        document.getElementById('kb-type').value = this.state_kb.tab || 'kodlar';
        document.getElementById('kb-requires-user').checked = false;
        document.getElementById('kb-btn-delete').style.display = 'none';
        document.getElementById('kb-image').value = '';
        document.getElementById('kb-title').focus();
    },
    closeKBModal: function() {
        document.getElementById('kb-modal').style.display = 'none';
    },
    saveKBItem: async function() {
        const editId = document.getElementById('kb-edit-id').value;
        const title = document.getElementById('kb-title').value;
        const content = document.getElementById('kb-content').value;
        const type = document.getElementById('kb-type').value;
        const imageFile = document.getElementById('kb-image').files[0];
        if (!title || !content) { this.showToast('Lütfen balık ve içerik giriniz.', 'warning'); return; }
        try {
            this.showToast('Bilgi kaydediliyor...', 'info');
            const formData = new FormData();
            formData.append('device_type', type);
            formData.append('type', type);
            formData.append('title', title);
            formData.append('content', content);
            formData.append('requires_user', document.getElementById('kb-requires-user').checked ? 1 : 0);
            formData.append('user_id', this.state.activeUser.key);
            formData.append('user_name', this.state.activeUser.name);
            formData.append('role', this.state.activeUser.role);
            if (imageFile) formData.append('image', imageFile);
            let url = this.state.API_BASE + '/notes/kb/add';
            if (editId) {
                url = `${this.state.API_BASE}/notes/kb/update/${editId}`;
            }
            const resp = await fetch(url, {
                method: 'POST',
                body: formData
            });
            const result = await resp.json();
            if (result.error) throw new Error(result.error);
            this.closeKBModal();
            this.showToast(editId ? 'Kayıt güncellendi!' : 'Yeni bilgi eklendi!');
            this.loadGeneralNotes();
        } catch (e) { 
            console.error('KB Save Error:', e);
            this.showToast('Hata: ' + e.message, 'error'); 
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
            const resp = await fetch(this.state.API_BASE + '/service/get_all');
            const data = await resp.json();
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
            let statusClass = "arizali";
            let statusText = (r.status || 'BELİRSİZ').toUpperCase();
            if (statusText === 'SERVİSTE' || statusText === 'SERVİS') {
                statusClass = "depoda"; // Turuncu (status-depoda)
                statusText = "SERVİS";
            } else if (statusText === 'TESLİM EDİLDİ' || statusText === 'DEPODA') {
                statusClass = "sahada";
            }

            return `
            <tr onclick="app.openServiceEditModal(${r.id})">
                <td style="white-space:nowrap;"><span style="color:var(--accent); text-decoration:underline; font-weight:700; cursor:pointer;">${r.pr_no || '-'}</span></td>
                <td>${r.seri || '-'}</td>
                <td style="font-family:monospace; font-size:0.75rem; opacity:0.8;">${r.mac || '-'}</td>
                <td style="font-size:0.8rem; font-weight:600;">${r.mahal || '-'}</td>
                <td>${this.formatDate(r.acq_date)}</td>
                <td>${this.formatDate(r.sent_date)}</td>
                <td>${this.formatDate(r.return_date)}</td>
                <td style="max-width:350px; word-wrap:break-word; font-style:italic; opacity:0.9; font-size:0.8rem;">${r.fault_desc || '-'}</td>
                <td class="col-medium">${ikameHtml}</td>
                <td><span class="status-badge status-${statusClass}" style="min-width:70px; text-align:center;">${statusText}</span></td>
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
            // Eer printer_id varsa bilgileri doldur
            if (printer_id && this.state.printers) {
                const p = this.state.printers.find(x => x.id == printer_id);
                if (p) {
                    if(document.getElementById('service-pr-no')) document.getElementById('service-pr-no').value = p.pr_no || '';
                    if(document.getElementById('service-seri')) document.getElementById('service-seri').value = p.seri || '';
                    if(document.getElementById('service-mac')) document.getElementById('service-mac').value = p.mac || '';
                    if(document.getElementById('service-model')) document.getElementById('service-model').value = p.model || '';
                    if(document.getElementById('service-mahal')) document.getElementById('service-mahal').value = p.mahal || '';
                }
            }
            this.updatePrinterDatalist();
            const modal = document.getElementById('service-modal');
            if(modal) modal.style.display = 'flex';
        } catch (err) {
            console.error("Servis modal hatası:", err);
            alert("Servis kaydı formu açılırken bir hata olutu: " + err.message);
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
            // Ana PR No seçildiyse dier alanları doldur
            const idEl = document.getElementById('service-printer-id');
            const modelEl = document.getElementById('service-model');
            const seriEl = document.getElementById('service-seri');
            const macEl = document.getElementById('service-mac');
            const mahalEl = document.getElementById('service-mahal');
            const acqDateEl = document.getElementById('service-acq-date');
            // PR No'yu düzeltilmi haliyle yaz
            inputEl.value = p.pr_no || val;
            if(idEl) idEl.value = p.id || '';
            if(modelEl) modelEl.value = p.model || '';
            if(seriEl) seriEl.value = p.seri || '';
            if(macEl) macEl.value = p.mac || '';
            if(mahalEl) mahalEl.value = p.mahal || '';
            if(acqDateEl && p.acq_date) acqDateEl.value = p.acq_date.split(' ')[0];
        }
        document.getElementById('service-acq-place').value = s.acq_place || '';
        document.getElementById('service-acq-date').value = s.acq_date || ''; // Popüle et
        document.getElementById('service-sent-date').value = s.sent_date || '';
        document.getElementById('service-return-date').value = s.return_date || '';
        document.getElementById('service-status').value = s.status || 'Serviste';
        document.getElementById('service-fault-desc').value = s.fault_desc || ' ';
        // Durum otomatik güncelleme dinleyicileri
        document.getElementById('service-return-date').onchange = (e) => {
            if(e.target.value) document.getElementById('service-status').value = 'Depoda';
        };
        document.getElementById('service-sent-date').onchange = (e) => {
            if(e.target.value && !document.getElementById('service-return-date').value) 
                document.getElementById('service-status').value = 'Serviste';
        };
        // service-final-status element kontrolü (index.html'de yoksa hata vermemesi için)
        const finalStatusEl = document.getElementById('service-final-status');
        if (finalStatusEl) finalStatusEl.value = s.final_status || '';
        document.getElementById('service-has-substitute').checked = !!s.has_substitute;
        document.getElementById('service-substitute-pr-no').value = s.substitute_pr_no || '';
        document.getElementById('service-substitute-container').style.display = s.has_substitute ? 'block' : 'none';
        document.getElementById('service-modal').style.display = 'flex';
        // Admin ise silme butonunu göster
        const isAdmin = this.state.activeUser && this.state.activeUser.role === 'ADMIN';
        const deleteBtn = document.getElementById('btn-service-delete');
        if (deleteBtn) deleteBtn.style.display = isAdmin ? 'block' : 'none';
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
            acq_date: document.getElementById('service-acq-date').value,
            sent_date: document.getElementById('service-sent-date').value,
            return_date: returnDateVal,
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
    },
    deleteServiceRecord: async function(id) {
        if (!confirm('Bu servis kaydını silmek istediinize emin misiniz?')) return;
        try {
            await fetch(`${this.state.API_BASE}/service/delete/${id}`, { method: 'DELETE' });
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
            const response = await fetch(this.state.API_BASE + '/documents/generate_tutanak', {
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
    openAddModal: function() {
        if(!['ADMIN', 'EDITOR'].includes(this.state.activeUser.role)) {
            return alert('Yeni kayıt eklemek için yetkiniz yok!');
        }
        switch(this.state.view) {
            case 'depot':
                if (['ADMIN', 'DEPOT'].includes(this.state.activeUser.role)) this.openAddDepotItem();
                else alert('Depo yetkiniz yok.');
                break;
            case 'inventory':
                // Reset form
                ['add-pc-no', 'add-ip', 'add-kule', 'add-mahal-kodu', 'add-mahal-adi', 'add-seri'].forEach(id => {
                    const el = document.getElementById(id);
                    if(el) el.value = '';
                });
                document.getElementById('device-add-modal').style.display = 'flex';
                break;
            case 'areas':
                this.openAreaModal(null);
                break;
            default:
                alert('Bu ekranda yeni kayıt yapılamaz.');
        }
    },
    saveNewDevice: async function() {
        const payload = {
            pc_no: document.getElementById('add-pc-no').value,
            ip: document.getElementById('add-ip').value,
            kule: document.getElementById('add-kule').value,
            mahal_kodu: document.getElementById('add-mahal-kodu').value,
            mahal_adi: document.getElementById('add-mahal-adi').value,
            pc_seri: document.getElementById('add-seri').value,
            windows: document.getElementById('add-windows').checked ? 1 : 0,
            keyos: document.getElementById('add-keyos').checked ? 1 : 0,
            sahada: document.getElementById('add-sahada').checked ? 1 : 0
        };
        if (!payload.pc_no && !payload.pc_seri) {
            return alert("En azından PC Numarası veya Seri No girmelisiniz.");
        }
        try {
            const resp = await fetch(this.state.API_BASE + '/inventory/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await resp.json();
            if (result.error) throw new Error(result.error);
            document.getElementById('device-add-modal').style.display = 'none';
            this.showToast('Yeni cihaz baarıyla eklendi!');
            this.loadInventory();
        } catch (e) { alert('Hata: ' + e.message); }
    },
    openAreaModal: function(id) {
        let area = { id: '', name: '', path: '', user: '', password: '' };
        if (id) {
            area = this.state.areas.find(a => a.id == id) || area;
            document.getElementById('area-title').innerHTML = `<i class="fas fa-edit"></i> Alanı Düzenle`;
        } else {
            document.getElementById('area-title').innerHTML = `<i class="fas fa-plus"></i> Yeni Ortak Alan`;
        }
        document.getElementById('area-id').value = area.id;
        document.getElementById('area-name').value = area.name;
        document.getElementById('area-path').value = area.path;
        document.getElementById('area-user').value = area.user;
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
            const resp = await fetch(this.state.API_BASE + '/areas/delete/' + id, { method: 'DELETE' });
            const result = await resp.json();
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
            user: document.getElementById('area-user').value,
            password: document.getElementById('area-pass').value
        };
        if (!payload.name) return alert("A Adı zorunludur.");
        const endpoint = payload.id ? `/areas/update/${payload.id}` : '/areas/add';
        const method = payload.id ? 'PUT' : 'POST';
        try {
            const resp = await fetch(this.state.API_BASE + endpoint, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await resp.json();
            if (result.error) throw new Error(result.error);
            document.getElementById('area-modal').style.display = 'none';
            this.showToast('Ortak alan kaydedildi!');
            this.loadAreas();
        } catch (e) { alert('Hata: ' + e.message); }
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
            const resp = await fetch(this.state.API_BASE + '/users/get_all');
            const users = await resp.json();
            tbody.innerHTML = users.map(u => {
                const created = u.created_at ? new Date(u.created_at).toLocaleDateString('tr-TR') : '-';
                const lastLog = u.last_login ? new Date(u.last_login).toLocaleString('tr-TR') : '-';
                return `
                <tr>
                    <td style="font-weight:600;">${u.username}</td>
                    <td>${u.display_name}</td>
                    <td><span class="role-badge" style="background: rgba(255,255,255,0.2);">${u.role}</span></td>
                    <td style="font-size:0.75rem; opacity:0.6;">${created}</td>
                    <td style="font-size:0.75rem; color:var(--accent);">${lastLog}</td>
                    <td>
                        <div class="flex-row gap-2">
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
        document.getElementById('user-password').placeholder = 'ifre';
        document.getElementById('user-role').value = 'EDITOR';
        this.handleUserRoleChange('EDITOR');
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
        try { allowed = permissions ? JSON.parse(permissions) : []; } catch(e) {}
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
                resp = await fetch(this.state.API_BASE + '/users/update/' + editId, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } else {
                // Yeni ekle
                if (!username || !password) return alert('Kullanıcı adı ve ifre zorunludur.');
                resp = await fetch(this.state.API_BASE + '/users/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password, display_name: displayName, role, permissions })
                });
            }
            const result = await resp.json();
            if (result.error) throw new Error(result.error);
            document.getElementById('user-modal').style.display = 'none';
            this.showToast(editId ? 'Kullanıcı güncellendi!' : 'Kullanıcı eklendi!');
            this.loadUsers();
        } catch(e) { alert('Hata: ' + e.message); }
    },
    deleteUser: async function(id) {
        if (!confirm('Bu kullanıcıyı silmek istediinize emin misiniz?')) return;
        try {
            const resp = await fetch(this.state.API_BASE + '/users/delete/' + id, { method: 'DELETE' });
            const result = await resp.json();
            if (result.error) throw new Error(result.error);
            this.showToast('Kullanıcı silindi.');
            this.loadUsers();
        } catch(e) { alert('Hata: ' + e.message); }
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
            const resp = await fetch(this.state.API_BASE + `/logs/get_all?user=${user}&table=${table}`);
            const data = await resp.json();
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
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; opacity:0.5; padding:30px;"><i class="fas fa-check-circle" style="color:#00ff88;"></i> İlem geçmii temiz.</td></tr>';
                return;
            }
            tbody.innerHTML = data.map(l => {
                const date = l.created_at ? l.created_at.replace('T', ' ').split('.')[0] : '-';
                const cleanOld = (l.old_value || '-').replace('Sahada Kurulu', 'KURULU');
                const cleanNew = (l.new_value || '-').replace('Sahada Kurulu', 'KURULU');
                return `
                <tr>
                    <td style="font-size:0.75rem; white-space:nowrap;">${date}</td>
                    <td><span class="badge" style="background:rgba(0,186,255,0.1); color:var(--accent);">${l.display_name || l.changed_by}</span></td>
                    <td style="font-size:0.75rem;">${l.client_ip || '-'}</td>
                    <td style="font-size:0.7rem; opacity:0.6;">${l.client_mac || '-'}</td>
                    <td style="font-weight:600;">${l.record_label || l.record_id}</td>
                    <td style="color:var(--text-secondary);">${l.field_name}</td>
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
            const resp = await fetch(this.state.API_BASE + '/logs/clear_all', { method: 'DELETE' });
            const result = await resp.json();
            if (result.error) throw new Error(result.error);
            this.showToast(result.message || 'Geçmi temizlendi.');
            // Listeyi sıfırla
            const tbody = document.getElementById('logs-tbody');
            if (tbody) tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; opacity:0.5; padding:30px;"><i class="fas fa-check-circle" style="color:#00ff88;"></i> İlem geçmii temiz.</td></tr>';
            // Kullanıcı filtresini de sıfırla
            const userEl = document.getElementById('log-filter-user');
            if (userEl) { while(userEl.options.length > 1) userEl.remove(1); }
        } catch (e) { alert('Hata: ' + e.message); }
    },
    clearDepotTransactions: async function() {
        if (!confirm('DİKKAT: Tüm stok hareketleri (depo geçmii) kalıcı olarak silinecektir. Onaylıyor musunuz?')) return;
        try {
            const resp = await fetch(this.state.API_BASE + '/depot/clear_transactions', { method: 'DELETE' });
            const result = await resp.json();
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
            btn.style.background = 'var(--accent)';
            btn.style.color = '#000';
            // Sıralama butonlarını ekle
            controls.innerHTML = `
                <div class="flex-between" style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid var(--accent); margin-bottom: 20px;">
                    <span style="font-size: 0.85rem; font-weight: 600;"><i class="fas fa-list-ol"></i> SAYIM SIRALAMASI:</span>
                    <div class="flex-row gap-2">
                        <button class="btn-chip" onclick="app.sortInventory('mahal_kodu')">MAHAL KODUNA GRE</button>
                        <button class="btn-chip" onclick="app.sortInventory('kat')">KATA GRE</button>
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
        }
        this.renderInventory(this.state.inventory);
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
        this.showToast(`Sıralandı: ${by === 'kat' ? 'Kat' : 'Mahal Kodu'}`);
    },
    markCounted: async function(id) {
        if (!this.state.countMode) return;
        try {
            const resp = await fetch(this.state.API_BASE + '/inventory/count', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: id,
                    counted_by: this.state.activeUser.display_name || this.state.activeUser.name
                })
            });
            const result = await resp.json();
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
    resetCount: async function() {
        if (!confirm('TM sayım verileri sıfırlanacak! Yeni bir sayım dönemine balamak istediinize emin misiniz?')) return;
        try {
            const resp = await fetch(this.state.API_BASE + '/inventory/count/reset', { method: 'POST' });
            const result = await resp.json();
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
            const dateStr = new Date(item.created_at).toLocaleString('tr-TR');
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
            const resp = await fetch(this.state.API_BASE + `/logs/get_record_history/${type === 'pc' ? 'inventory' : 'printers'}/${id}`);
            const logs = await resp.json();
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
        const date = new Date(item.created_at).toLocaleString('tr-TR');
        const avatar = item.display_name ? item.display_name[0].toUpperCase() : 'U';
        popup.innerHTML = `
            <div class="hp-header">
                <div class="hp-title">Düzenleme Geçmii (${idx + 1}/${items.length})</div>
                <div class="hp-nav">
                    <button class="hp-nav-btn" ${idx === 0 ? 'disabled' : ''} onclick="app.navigateHistory(-1, event)" title="Daha Yeni"><i class="fas fa-chevron-left"></i></button>
                    <button class="hp-nav-btn" ${idx === items.length - 1 ? 'disabled' : ''} onclick="app.navigateHistory(1, event)" title="Daha Eski"><i class="fas fa-chevron-right"></i></button>
                </div>
            </div>
            <div class="hp-user-info">
                <div class="hp-avatar">${avatar}</div>
                <div class="hp-meta">
                    <span class="hp-username">${item.display_name || item.changed_by}</span>
                    <span class="hp-date">${date}</span>
                </div>
            </div>
            <div class="hp-content">
                <span class="hp-field">${item.field_name.toUpperCase()}</span>
                <div class="hp-values">
                    ${(!item.old_value || item.old_value === 'None') ? 
                        `<span class="hp-new">Eklendi: "${item.new_value}"</span>` : 
                        ((!item.new_value || item.new_value === 'None') ? 
                            `<span class="hp-old">Silindi: "${item.old_value}"</span>` :
                            `<span class="hp-old">${item.old_value}</span> <i class="fas fa-arrow-right" style="opacity:0.3; margin:0 4px;"></i> <span class="hp-new">${item.new_value}</span>`
                        )
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
            const resp = await fetch(this.state.API_BASE + '/inventory/mahal_list');
            const data = await resp.json();
            this.state.mahalMap = {};
            let optionsHtml = '';
            data.forEach(m => {
                this.state.mahalMap[m.mahal] = {
                    name: m.mahal_adi,
                    phone: m.telefon,
                    kule: (m.mahal && m.mahal.includes('.')) ? m.mahal.split('.')[0] : '',
                    kat: (m.mahal && m.mahal.includes('.')) ? m.mahal.split('.')[1] : ''
                };
                optionsHtml += `<option value="${m.mahal}">${m.mahal_adi}</option>`;
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
:: 1. Klasör olutur
if not exist "C:\\OrtakAlan" mkdir "C:\\OrtakAlan"
:: 2. Kalıcı BAT dosyasını olutur (C:\\OrtakAlan)
(
echo @echo off
echo set "DriveLetter=Z:"
echo set "RemotePath=${area.path}"
echo set "Username=${area.user}"
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
echo Kurulum Tamamlandi. Masaustunde hem BAT dosyaniz hem de Surucu kisayolunuz hazir.
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
            const resp = await fetch(this.state.API_BASE + '/inventory/count/undo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id })
            });
            const result = await resp.json();
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
            const list = ['edit-sahada', 'edit-depo', 'edit-arizali', 'edit-mahalsiz', 'edit-kurulum_bekliyor'];
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
            if (warnText) warnText.innerText = `Bu seri numarası (${val}) zaten ${pcLabel} (${duplicate.mahal_adi || ''}) cihazında kayıtlı! Lütfen düzeltin.`;
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
                                <td style="padding:10px;">${r.fault_desc || '-'}</td>
                                <td style="padding:10px;"><span class="status-badge ${r.status === 'Serviste' ? 'status-ariza' : 'status-sahada'}">${r.status}</span></td>
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
            const resp = await fetch(this.state.API_BASE + '/keyos/check_all_mismatches');
            const data = await resp.json();
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
        document.getElementById('keyos-edit-mahal').value = item.mahal_kodu || '';
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
        if (!item || !item.pc_seri) return alert('Seri numarası bulunamadı.');
        if (!user || !pass) return alert('KeyOS yetkili kullanıcı adı ve ifre gereklidir.');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Güncelleniyor...';
        try {
            const resp = await fetch(this.state.API_BASE + '/keyos/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    serial: item.pc_seri,
                    hostname: hostname,
                    placeId: placeId,
                    keyos_user: user,
                    keyos_pass: pass
                })
            });
            const result = await resp.json();
            if (result.success) {
                this.showToast('KeyOS baarıyla güncellendi.');
                document.getElementById('keyos-edit-modal').style.display = 'none';
                this.checkKeyOSMismatches(); // Refresh alerts
            } else {
                throw new Error(result.error || 'Bilinmeyen bir hata olutu.');
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
            this.showToast('KeyOS MGT ile senkronizasyon balatıldı...', 'info');
            const resp = await fetch(this.state.API_BASE + '/keyos/manual_sync', { method: 'POST' });
            const result = await resp.json();
            if (result.error) throw new Error(result.error);
            this.showToast(`Senkronizasyon Baarılı! ${result.count || 0} uyumazlık tespit edildi.`);
            this.checkKeyOSMismatches();
        } catch (e) {
            alert('Senkronizasyon Hatası: ' + e.message);
        } finally {
            if (icon) setTimeout(() => icon.classList.remove('fa-spin'), 1000);
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
            const resp = await fetch(this.state.API_BASE + '/documents/generate_tutanak', {
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
            this.showToast('Barkod baarıyla oluturuldu.');
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
            this.showToast('Barkod oluturuluyor...', 'info');
            const resp = await fetch(this.state.API_BASE + '/documents/generate_tutanak', {
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
            const err = await resp.json().catch(() => ({error: 'Sunucu hatası'}));
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
    document.getElementById('profile-magicinfo-user').value = user.magicinfo_user || '';
    document.getElementById('profile-magicinfo-pass').value = '';
    document.getElementById('profile-session-timeout').value = user.session_timeout !== undefined ? user.session_timeout : 5;
    document.getElementById('profile-settings-modal').style.display = 'flex';
};
app.saveProfileSettings = async function() {
    const payload = {
        id: app.state.activeUser.id,
        keyos_user: document.getElementById('profile-keyos-user').value,
        keyos_pass: document.getElementById('profile-keyos-pass').value,
        bim_user: document.getElementById('profile-bim-user').value,
        bim_pass: document.getElementById('profile-bim-pass').value,
        magicinfo_user: document.getElementById('profile-magicinfo-user').value,
        magicinfo_pass: document.getElementById('profile-magicinfo-pass').value,
        session_timeout: parseInt(document.getElementById('profile-session-timeout').value)
    };
    try {
        app.showToast('Ayarlar kaydediliyor...', 'info');
        const resp = await fetch(app.state.API_BASE + '/users/update_profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await resp.json();
        if (result.error) throw new Error(result.error);
        app.showToast('Profil ayarları baarıyla güncellendi.');
        document.getElementById('profile-settings-modal').style.display = 'none';
        app.state.activeUser.keyos_user = payload.keyos_user;
        app.state.activeUser.bim_user = payload.bim_user;
        app.state.activeUser.magicinfo_user = payload.magicinfo_user;
        if(payload.keyos_pass) app.state.activeUser.keyos_pass = payload.keyos_pass;
        if(payload.bim_pass) app.state.activeUser.bim_pass = payload.bim_pass;
        if(payload.magicinfo_pass) app.state.activeUser.magicinfo_pass = payload.magicinfo_pass;
        app.state.activeUser.session_timeout = payload.session_timeout;
        localStorage.setItem('it_user_data', JSON.stringify(app.state.activeUser));
    } catch (e) { alert('Hata: ' + e.message); }
};
app.init();
window.app = app;
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./sw.js')
            .then(reg => console.log('PWA Service Worker kayıtlı!', reg))
            .catch(err => console.log('PWA kaydı baarısız: ', err));
    });
}
