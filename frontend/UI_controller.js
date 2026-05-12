/**
 * KEYDATA KOCAEL - IT ENVANTER SSTEM
 * UI Controller v8.0 - Solid Version
 */
(function() {
    'use strict';
    const app = {
        apiBase: (window.location.origin || (window.location.protocol + '//' + window.location.host)) + '/api',
        userData: null,
        currentView: 'dashboard',
        inventory: [],
        printers: [],
        depot: [],
        charts: {},
        filters: {
            inventory: { category: 'PC', block: 'ALL' },
            printers: 'ALL',
            depot: 'ALL'
        },

        init: function() {
            console.log('App Initializing...');
            this.checkLogin();
            this.setupEventListeners();
            this.loadInitialData();
            
            // Register global object
            window.app = this;
        },

        checkLogin: function() {
            const savedData = localStorage.getItem('it_user_data');
            if (savedData) {
                this.userData = JSON.parse(savedData);
                document.body.classList.remove('login-required');
                document.getElementById('login-overlay').style.display = 'none';
                document.getElementById('active-user-name').innerText = this.userData.name || this.userData.username || 'Kullanıcı';
                
                if (this.userData.role === 'ADMIN') {
                    document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'block');
                    document.getElementById('btn-device-add').style.display = 'block';
                    document.getElementById('menu-users').style.display = 'block';
                    document.getElementById('menu-keyos-sync').style.display = 'block';
                }
            } else {
                document.body.classList.add('login-required');
                document.getElementById('login-overlay').style.display = 'flex';
            }
        },

        handleLoginButtonClick: function() {
            const u = document.getElementById('login-user').value;
            const p = document.getElementById('login-pass').value;
            if (!u || !p) {
                alert('Ltfen kullanc ad ve ifre girin.');
                return;
            }

            fetch(`${this.apiBase}/users/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: u, password: p })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const userData = {
                        token: data.token,
                        name: data.user.display_name,
                        username: data.user.username,
                        role: data.user.role,
                        id: data.user.id
                    };
                    localStorage.setItem('it_user_data', JSON.stringify(userData));
                    location.reload();
                } else {
                    alert('Hata: ' + (data.error || 'Giri baarsz.'));
                }
            })
            .catch(err => {
                console.error('Login error:', err);
                // Fallback for demo/dev
                if ((u === 'vefa' || u === 'admin') && p === '123') {
                    localStorage.setItem('it_user_data', JSON.stringify({ name: u, role: 'ADMIN', username: u }));
                    location.reload();
                } else {
                    alert('Sunucuya balanamad.');
                }
            });
        },

        handleLogout: function() {
            localStorage.removeItem('it_user_data');
            location.reload();
        },

        setupEventListeners: function() {
            document.querySelectorAll('.nav-link').forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.navigateTo(link.getAttribute('data-view'));
                });
            });

            // Shortcuts dropdown click outside handler
            window.addEventListener('click', (e) => {
                if (!e.target.closest('.custom-dropdown')) {
                    document.querySelectorAll('.dropdown-menu').forEach(m => m.classList.remove('show'));
                }
            });
        },

        navigateTo: function(viewId) {
            console.log('Navigating to:', viewId);
            this.currentView = viewId;
            
            document.querySelectorAll('.view').forEach(v => v.style.display = 'none');
            const targetView = document.getElementById(`view-${viewId}`);
            if (targetView) targetView.style.display = 'block';

            document.querySelectorAll('.nav-link').forEach(l => {
                l.classList.toggle('active', l.getAttribute('data-view') === viewId);
            });

            if (viewId === 'dashboard') this.updateDashboard();
            if (viewId === 'inventory') this.loadInventory();
            if (viewId === 'printers') this.loadPrinters();
            if (viewId === 'depot') this.loadDepot();
            if (viewId === 'areas') this.loadAreas();
            if (viewId === 'service') this.loadServiceRecords();
        },

        toggleDropdown: function(id) {
            const menu = document.querySelector(`#${id} .dropdown-menu`);
            const isShown = menu.classList.contains('show');
            document.querySelectorAll('.dropdown-menu').forEach(m => m.classList.remove('show'));
            if (!isShown) menu.classList.add('show');
        },

        loadInitialData: function() {
            if (this.userData) {
                this.updateDashboard();
                this.loadMahalList();
            }
        },

        loadMahalList: function() {
            fetch(`${this.apiBase}/inventory/mahal_list`)
                .then(res => res.json())
                .then(data => {
                    const dl = document.getElementById('mahal-datalist');
                    if (dl) {
                        dl.innerHTML = data.map(m => `<option value="${m}">`).join('');
                    }
                })
                .catch(err => console.error('Mahal listesi yklenemedi:', err));
        },

        updateDashboard: function() {
            fetch(`${this.apiBase}/inventory/stats`)
                .then(res => res.json())
                .then(stats => {
                    document.getElementById('stat-os-windows').innerText = stats.windows || 0;
                    document.getElementById('stat-os-keyos').innerText = stats.keyos || 0;
                    document.getElementById('stat-pc-sahada').innerText = stats.sahada || 0;
                    
                    this.initCharts(stats);
                })
                .catch(err => console.error('Stats yklenemedi:', err));
        },

        initCharts: function(stats) {
            const pieCtx = document.getElementById('dashboard-pie-chart');
            if (pieCtx) {
                if (this.charts.pie) this.charts.pie.destroy();
                this.charts.pie = new Chart(pieCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Windows', 'KeyOS'],
                        datasets: [{
                            data: [stats.windows || 0, stats.keyos || 0],
                            backgroundColor: ['#0078d4', '#ff4b2b'],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        cutout: '70%',
                        plugins: { legend: { display: false } }
                    }
                });
            }

            const keyosCtx = document.getElementById('dashboard-keyos-chart');
            if (keyosCtx) {
                if (this.charts.keyos) this.charts.keyos.destroy();
                this.charts.keyos = new Chart(keyosCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Ak', '5-10 Gn', '11-29 Gn', '30+ Gn'],
                        datasets: [{
                            data: [10, 5, 2, 1], // Dummy for now
                            backgroundColor: ['#00ff88', '#00d2ff', '#ffb400', '#ff4b2b'],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        cutout: '70%',
                        plugins: { legend: { display: false } }
                    }
                });
            }
        },

        loadInventory: function() {
            fetch(`${this.apiBase}/inventory/get_all`)
                .then(res => res.json())
                .then(data => {
                    this.inventory = data;
                    this.renderInventory();
                })
                .catch(err => {
                    console.error('Envanter yklenemedi:', err);
                    document.getElementById('inventory-grid').innerHTML = '<p class="text-secondary">Veri yklenemedi.</p>';
                });
        },

        renderInventory: function() {
            const grid = document.getElementById('inventory-grid');
            if (!grid) return;

            let filtered = this.inventory;
            if (this.filters.inventory.category !== 'ALL') {
                filtered = filtered.filter(item => item.type === this.filters.inventory.category);
            }
            if (this.filters.inventory.block !== 'ALL') {
                filtered = filtered.filter(item => item.kule === this.filters.inventory.block);
            }

            grid.innerHTML = filtered.map(item => `
                <div class="card" onclick="app.openDeviceDetail(${item.id})">
                    <div class="card-header">
                        <span class="card-id">${item.pc_no}</span>
                        <div class="status-badge ${item.sahada ? 'status-sahada' : 'status-depoda'}">
                            ${item.sahada ? 'SAHADA' : 'DEPODA'}
                        </div>
                    </div>
                    <div class="card-title-lg">${item.mahal_kodu || 'BELRSZ'}</div>
                    <div class="card-info">
                        <div class="info-item"><span>IP ADRES</span>${item.ip || '-'}</div>
                        <div class="info-item"><span>SER NO</span>${item.seri_no || '-'}</div>
                    </div>
                </div>
            `).join('');
        },

        setInvCategory: function(cat) {
            this.filters.inventory.category = cat;
            document.querySelectorAll('#device-type-filters .btn-chip').forEach(b => {
                b.classList.toggle('active', b.getAttribute('data-category') === cat);
            });
            this.renderInventory();
        },

        setInvBlock: function(block) {
            this.filters.inventory.block = block;
            document.querySelectorAll('#inventory-filters .btn-chip').forEach(b => {
                b.classList.toggle('active', b.getAttribute('data-block') === block);
            });
            this.renderInventory();
        },

        searchInventory: function() {
            const q = document.getElementById('main-search').value.toLowerCase();
            const grid = document.getElementById('inventory-grid');
            if (!grid) return;

            const filtered = this.inventory.filter(item => 
                (item.pc_no && item.pc_no.toLowerCase().includes(q)) ||
                (item.mahal_kodu && item.mahal_kodu.toLowerCase().includes(q)) ||
                (item.ip && item.ip.toLowerCase().includes(q)) ||
                (item.seri_no && item.seri_no.toLowerCase().includes(q))
            );

            grid.innerHTML = filtered.map(item => `
                <div class="card" onclick="app.openDeviceDetail(${item.id})">
                    <div class="card-header">
                        <span class="card-id">${item.pc_no}</span>
                        <div class="status-badge ${item.sahada ? 'status-sahada' : 'status-depoda'}">
                            ${item.sahada ? 'SAHADA' : 'DEPODA'}
                        </div>
                    </div>
                    <div class="card-title-lg">${item.mahal_kodu || 'BELRSZ'}</div>
                    <div class="card-info">
                        <div class="info-item"><span>IP ADRES</span>${item.ip || '-'}</div>
                        <div class="info-item"><span>SER NO</span>${item.seri_no || '-'}</div>
                    </div>
                </div>
            `).join('');
        },

        clearSearch: function(id) {
            document.getElementById(id).value = '';
            if (id === 'main-search') this.renderInventory();
        },

        syncAllDatabases: function() {
            if (!confirm('Tm veritabanlar Excel dosyalarndan senkronize edilecek. Emin misiniz?')) return;
            
            fetch(`${this.apiBase}/sync/all`, { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        alert('Senkronizasyon Baarl:\n' + data.details.join('\n'));
                        location.reload();
                    } else {
                        alert('Hata: ' + data.error);
                    }
                })
                .catch(err => alert('Senkronizasyon hatas: ' + err));
        }
    };

    // Auto-init
    window.addEventListener('DOMContentLoaded', () => app.init());

})();
