/**
 * KEYDATA KOCAELI - IT ENVANTER SISTEMI
 * UI Controller v8.1 - Robust Version
 */
(function() {
    'use strict';
    const app = {
        apiBase: (window.location.origin || (window.location.protocol + '//' + window.location.host)) + '/api',
        userData: null,
        currentView: 'dashboard',
        inventory: [],
        charts: {},

        init: function() {
            console.log('App Initializing...');
            this.setupEventListeners();
            this.checkLogin();
            this.loadInitialData();
            window.app = this;
        },

        checkLogin: function() {
            const savedData = localStorage.getItem('it_user_data');
            if (savedData) {
                try {
                    this.userData = JSON.parse(savedData);
                    document.body.classList.remove('login-required');
                    const overlay = document.getElementById('login-overlay');
                    if (overlay) overlay.style.display = 'none';
                    
                    const nameEl = document.getElementById('active-user-name');
                    if (nameEl) nameEl.innerText = this.userData.name || this.userData.username || 'Kullanıcı';
                    
                    if (this.userData.role === 'ADMIN') {
                        document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'block');
                    }
                } catch(e) { console.error('Login check error:', e); }
            } else {
                document.body.classList.add('login-required');
                const overlay = document.getElementById('login-overlay');
                if (overlay) overlay.style.display = 'flex';
            }
        },

        handleLoginButtonClick: function() {
            const u = document.getElementById('login-user').value;
            const p = document.getElementById('login-pass').value;
            if (!u || !p) return alert('Lütfen bilgileri girin.');

            fetch(`${this.apiBase}/users/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: u, password: p })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    localStorage.setItem('it_user_data', JSON.stringify({
                        name: data.user.display_name,
                        username: data.user.username,
                        role: data.user.role,
                        token: data.token
                    }));
                    location.reload();
                } else alert('Hata: ' + data.error);
            }).catch(() => {
                // Dev fallback
                if (u === 'vefa' && p === '123') {
                    localStorage.setItem('it_user_data', JSON.stringify({ name: 'M. VEFA', role: 'ADMIN', username: 'vefa' }));
                    location.reload();
                }
            });
        },

        setupEventListeners: function() {
            document.querySelectorAll('.nav-link').forEach(link => {
                link.onclick = (e) => {
                    e.preventDefault();
                    const view = link.getAttribute('data-view');
                    this.navigateTo(view);
                };
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
        },

        toggleDropdown: function(id) {
            const menu = document.querySelector(`#${id} .dropdown-menu`);
            if (menu) {
                const isShown = menu.classList.contains('show');
                document.querySelectorAll('.dropdown-menu').forEach(m => m.classList.remove('show'));
                if (!isShown) menu.classList.add('show');
            }
        },

        loadInitialData: function() {
            if (document.body.classList.contains('login-required')) return;
            this.updateDashboard();
        },

        updateDashboard: function() {
            fetch(`${this.apiBase}/inventory/stats`)
                .then(res => res.json())
                .then(stats => {
                    const map = {
                        'stat-os-windows': stats.windows,
                        'stat-os-keyos': stats.keyos,
                        'stat-pc-sahada': stats.sahada
                    };
                    for (let id in map) {
                        const el = document.getElementById(id);
                        if (el) el.innerText = map[id] || 0;
                    }
                    this.initCharts(stats);
                }).catch(e => console.error('Dashboard error:', e));
        },

        initCharts: function(stats) {
            const pieCtx = document.getElementById('dashboard-pie-chart');
            if (pieCtx && typeof Chart !== 'undefined') {
                if (this.charts.pie) this.charts.pie.destroy();
                this.charts.pie = new Chart(pieCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Win', 'KeyOS'],
                        datasets: [{
                            data: [stats.windows || 0, stats.keyos || 0],
                            backgroundColor: ['#0078d4', '#ff4b2b'],
                            borderWidth: 0
                        }]
                    },
                    options: { cutout: '70%', plugins: { legend: { display: false } } }
                });
            }
        },

        loadInventory: function() {
            fetch(`${this.apiBase}/inventory/get_all`)
                .then(res => res.json())
                .then(data => {
                    this.inventory = data;
                    this.renderInventory();
                });
        },

        renderInventory: function() {
            const grid = document.getElementById('inventory-grid');
            if (!grid) return;
            grid.innerHTML = this.inventory.map(item => `
                <div class="card">
                    <div class="card-header"><span class="card-id">${item.pc_no}</span></div>
                    <div class="card-title-lg">${item.mahal_kodu || 'BELIRSIZ'}</div>
                </div>
            `).join('');
        },

        handleLogout: function() {
            localStorage.removeItem('it_user_data');
            location.reload();
        }
    };

    window.addEventListener('DOMContentLoaded', () => app.init());
})();
