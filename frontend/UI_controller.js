/**
 * KEYDATA KOCAELI - IT ENVANTER SISTEMI
 * UI Controller v10.0 - Full Fidelity Restoration
 */
(function() {
    'use strict';
    const app = {
        apiBase: '/api',
        userData: null,
        currentView: 'dashboard',
        inventory: [],

        init: function() {
            this.setupEventListeners();
            this.checkLogin();
            this.loadInitialData();
            
            // Enter tusu ile giris destegi
            document.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && document.body.classList.contains('login-required')) {
                    this.handleLoginButtonClick();
                }
            });
            
            window.app = this;
            console.log("Sistem Başlatıldı...");
        },

        checkLogin: function() {
            const savedData = localStorage.getItem('it_user_data');
            if (savedData) {
                this.userData = JSON.parse(savedData);
                document.body.classList.remove('login-required');
                const overlay = document.getElementById('login-overlay');
                if (overlay) overlay.style.display = 'none';
                document.getElementById('active-user-name').innerText = this.userData.name || 'Kullanıcı';
            } else {
                document.body.classList.add('login-required');
                document.getElementById('login-overlay').style.display = 'flex';
            }
        },

        handleLoginButtonClick: function() {
            const u = document.getElementById('login-user').value;
            const p = document.getElementById('login-pass').value;
            if (u === 'vefa' && p === '123') {
                localStorage.setItem('it_user_data', JSON.stringify({ name: 'M. VEFA', role: 'ADMIN', username: 'vefa' }));
                location.reload();
            } else alert('Hatalı giriş!');
        },

        setupEventListeners: function() {
            document.querySelectorAll('.nav-link').forEach(link => {
                link.onclick = (e) => {
                    e.preventDefault();
                    this.navigateTo(link.getAttribute('data-view'));
                };
            });
        },

        navigateTo: function(viewId) {
            this.currentView = viewId;
            document.querySelectorAll('.view').forEach(v => v.style.display = 'none');
            const target = document.getElementById(`view-${viewId}`);
            if (target) target.style.display = 'block';

            document.querySelectorAll('.nav-link').forEach(l => {
                l.classList.toggle('active', l.getAttribute('data-view') === viewId);
            });

            if (viewId === 'inventory') this.loadInventory();
        },

        loadInitialData: function() {
            if (document.body.classList.contains('login-required')) return;
            this.navigateTo('dashboard');
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
                    <div class="card-header-row">
                        <div>
                            <div class="pc-title">${item.pc_no}</div>
                            <span class="pc-id-label">${item.id || 'A08T68197x01'}</span>
                        </div>
                        <div style="display:flex; flex-direction:column; align-items:flex-end">
                            <i class="fas fa-clock-rotate-left clock-icon"></i>
                            <div class="badge-row">
                                <span class="badge badge-keyos">KEYOS</span>
                                <span class="badge badge-status">KURULU</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="pc-mahal">${item.mahal_adi || 'HEMŞİRE BANKOSU'}</div>
                    <div style="font-size:0.6rem; color:var(--text-secondary); margin-bottom:5px">Kod: ${item.mahal_kodu || 'A.08.T6.819.7'}</div>

                    <div class="pc-data-grid">
                        <div class="pc-data-item">IP: <b>${item.ip || '10.241.16.171'} <i class="fas fa-power-off ip-power"></i></b></div>
                        <div class="pc-data-item">SERİ NO: <b>${item.seri_no || '2N6JRM3'}</b></div>
                        <div class="pc-data-item" style="grid-column: span 2">YAZICILAR: <b>${item.printers || 'PR-092'}</b></div>
                    </div>

                    <div class="pc-footer-data">
                        BY: ${item.by || 'D4.J2210401594'}<br>
                        BO: ${item.bo || '22188010556602'}
                    </div>
                </div>
            `).join('');
        },

        toggleDropdown: function(id) {
            const menu = document.querySelector(`#${id} .dropdown-menu`);
            if (menu) menu.classList.toggle('show');
        },

        closeModal: function(id) {
            const modal = document.getElementById(id);
            if (modal) modal.style.display = 'none';
        },

        handleKeyOSChange: function() {
            const isKeyOS = document.getElementById('check-keyos').checked;
            const rdpWrapper = document.getElementById('rdp-wrapper');
            const rdpCheck = document.getElementById('check-rdp');
            
            if (isKeyOS) {
                rdpWrapper.style.opacity = '1';
                rdpWrapper.style.pointerEvents = 'auto';
                rdpCheck.disabled = false;
            } else {
                rdpWrapper.style.opacity = '0.3';
                rdpWrapper.style.pointerEvents = 'none';
                rdpCheck.checked = false;
                rdpCheck.disabled = true;
            }
        }
    };

    window.addEventListener('DOMContentLoaded', () => app.init());
})();
