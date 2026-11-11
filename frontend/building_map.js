// building_map.js
// Bina haritasi icin JS fonksiyonlari

const BuildingMap = {
    buildings: ['A KULE', 'B KULE', 'MH', 'FTR', 'TSB', 'YGAP'],
    currentBuilding: 'A KULE',
    activeCell: null,
    
    init: function() {
        this.renderTabs();
        this.loadLayout(this.currentBuilding);
    },
    
    renderTabs: function() {
        const container = document.getElementById('bm-buildings-tabs');
        if(!container) return;
        
        container.innerHTML = '';
        this.buildings.forEach(b => {
            const btn = document.createElement('button');
            btn.className = 'btn-chip' + (b === this.currentBuilding ? ' active' : '');
            btn.textContent = b;
            btn.onclick = () => {
                document.querySelectorAll('#bm-buildings-tabs .btn-chip').forEach(el => el.classList.remove('active'));
                btn.classList.add('active');
                this.currentBuilding = b;
                this.loadLayout(b);
            };
            container.appendChild(btn);
        });
    },
    
    loadLayout: async function(buildingName) {
        const grid = document.getElementById('bm-grid');
        grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 50px;"><i class="fas fa-spinner fa-spin fa-2x"></i></div>';
        
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`/api/building_map/layout/${encodeURIComponent(buildingName)}`, {
                headers: token ? { 'Authorization': 'Bearer ' + token } : {}
            });
            const data = await res.json();
            
            if(data.success) {
                this.renderGrid(data.layout);
            } else {
                grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: red;">Hata: ${data.error}</div>`;
            }
        } catch(e) {
            grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: red;">Bağlantı Hatası</div>`;
        }
    },
    
    renderGrid: function(layout) {
        const grid = document.getElementById('bm-grid');
        grid.innerHTML = '';
        
        try {
            if(!layout || layout.length === 0) {
                grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 50px; color: var(--muted);">Bu bina için henüz plan oluşturulmamış.</div>`;
                return;
            }

            // Find all unique wings in the layout
            let wings = new Set();
            layout.forEach(row => {
                Object.keys(row).forEach(k => {
                    if(k !== 'floor' && k !== 'id') wings.add(k); // ignore id if it exists
                });
            });
            
            // Kanatlar alfabetik, Çekirdek (C1, C2) en sağda/sonda
            wings = Array.from(wings).sort((a, b) => {
                const aUp = a.toUpperCase();
                const bUp = b.toUpperCase();
                const isACore = aUp === 'C1' || aUp === 'C2' || aUp.includes('ÇEKİRDEK');
                const isBCore = bUp === 'C1' || bUp === 'C2' || bUp.includes('ÇEKİRDEK');
                if (isACore && !isBCore) return 1;
                if (!isACore && isBCore) return -1;
                return aUp.localeCompare(bUp);
            });
            
            if(wings.length === 0) {
                grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 50px; color: var(--muted);">Kat planı bulunamadı.</div>`;
                return;
            }

            // Adjust grid template columns based on number of wings
            grid.style.gridTemplateColumns = `90px repeat(${wings.length}, minmax(150px, 1fr))`;

            // Headers
            grid.innerHTML += `<div></div>`;
            wings.forEach(w => {
                const wUpper = w.toUpperCase();
                let wName = wUpper;
                if (wUpper === 'C1' || wUpper === 'C2') {
                    wName = 'ÇEKİRDEK';
                } else if (!wUpper.includes('KANAT')) {
                    wName = wUpper + ' KANADI';
                }
                grid.innerHTML += `<div class="bm-grid-header">${wName}</div>`;
            });
                
            layout.forEach(row => {
                // Floor label
                const fLabel = document.createElement('div');
                fLabel.className = 'bm-floor-label';
                fLabel.innerText = row.floor + '. KAT';
                grid.appendChild(fLabel);

                wings.forEach(wing => {
                    const cell = document.createElement('div');
                    const cellData = row[wing];
                    const dept = cellData ? cellData.dept : null;
                    const isFaulty = cellData ? cellData.faulty : false;
                    
                    if (!dept) {
                        cell.className = 'bm-cell empty';
                        cell.innerHTML = '---';
                    } else {
                        cell.className = 'bm-cell';
                        const statusClass = isFaulty ? 'danger' : 'safe';
                        cell.innerHTML = `
                            <div class="bm-status-dot ${statusClass}" style="position: absolute; top: 10px; right: 10px;"></div>
                            <i class="fas fa-hospital-user" style="color: rgba(255,255,255,0.7); font-size: 1.2rem;"></i>
                            <span>${dept}</span>
                        `;
                        
                        cell.onclick = () => {
                            if (this.activeCell) this.activeCell.classList.remove('active');
                            cell.classList.add('active');
                            this.activeCell = cell;
                            this.openSidebar(dept, row.floor, wing.toUpperCase());
                        };
                        
                        // Edit button logic
                        const editBtn = document.createElement('div');
                        editBtn.className = 'bm-edit-btn';
                        editBtn.innerHTML = '<i class="fas fa-pencil-alt"></i>';
                        editBtn.onclick = (e) => {
                            e.stopPropagation();
                            this.promptEdit(row.floor, wing, dept);
                        };
                        cell.appendChild(editBtn);
                    }
                    
                    grid.appendChild(cell);
                });
            });
        } catch(e) {
            grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: red; padding: 20px;">JS Hatası: ${e.message}</div>`;
        }
    },
    
    promptEdit: function(floor, wing, currentDept) {
        const wUpper = (wing || '').toUpperCase();
        const wingLabel = (wUpper === 'C1' || wUpper === 'C2') ? 'Çekirdek' : `${wUpper} Kanadı`;
        const newDept = prompt(`${floor}. Kat ${wingLabel} için yeni birim adı girin (Boş bırakmak için iptal edin veya silin):`, currentDept);
        if(newDept !== null) {
            this.saveEdit(floor, wing, newDept);
        }
    },
    
    saveEdit: async function(floor, wing, newDept) {
        try {
            const token = localStorage.getItem('token');
            const res = await fetch('/api/building_map/update', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': token ? ('Bearer ' + token) : ''
                },
                body: JSON.stringify({
                    building: this.currentBuilding,
                    floor: floor,
                    wing: wing,
                    dept: newDept
                })
            });
            const data = await res.json();
            if(data.success) {
                app.showNotification('Başarılı', 'Birim adı güncellendi.', 'success');
                this.loadLayout(this.currentBuilding); // Reload
            } else {
                app.showNotification('Hata', data.error, 'error');
            }
        } catch(e) {
            app.showNotification('Hata', 'Bağlantı hatası.', 'error');
        }
    },
    
    openSidebar: async function(dept, floor, wing) {
        const wUpper = (wing || '').toUpperCase();
        const wingDisplay = (wUpper === 'C1' || wUpper === 'C2') ? 'Çekirdek' : `${wUpper} Kanadı`;
        document.getElementById('bm-sb-title').innerText = dept || ((wUpper === 'C1' || wUpper === 'C2') ? 'ÇEKİRDEK' : 'BOŞ DEPARTMAN');
        document.getElementById('bm-sb-loc').innerHTML = `<i class="fas fa-map-marker-alt"></i> ${this.currentBuilding} / ${floor}. Kat / ${wingDisplay}`;
        
        const listContainer = document.getElementById('bm-sb-list');
        listContainer.innerHTML = '<div style="text-align:center; padding: 20px;"><i class="fas fa-spinner fa-spin fa-2x" style="color:var(--accent);"></i></div>';
        
        document.getElementById('bm-sb-pc').innerText = '...';
        document.getElementById('bm-sb-pr').innerText = '...';
        document.getElementById('bm-sb-err').innerText = '...';
        
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`/api/building_map/devices?building=${encodeURIComponent(this.currentBuilding)}&department=${encodeURIComponent(dept || '')}&wing=${encodeURIComponent(wing)}&floor=${encodeURIComponent(floor)}`, {
                headers: token ? { 'Authorization': 'Bearer ' + token } : {}
            });
            const data = await res.json();
            
            if(data.success) {
                const pcs = data.pcs || [];
                const printers = data.printers || [];
                
                const errPcs = pcs.filter(p => p.is_faulty);
                const errPrs = printers.filter(p => p.is_faulty);
                const totalErr = errPcs.length + errPrs.length;
                
                document.getElementById('bm-sb-pc').innerText = pcs.length;
                document.getElementById('bm-sb-pr').innerText = printers.length;
                document.getElementById('bm-sb-err').innerText = totalErr;
                
                let html = '';
                const allDevices = [...pcs, ...printers];
                
                if(allDevices.length === 0) {
                    html = '<div style="text-align:center; padding: 20px; color: var(--muted);">Bu birimde cihaz bulunamadı.</div>';
                } else {
                    allDevices.forEach(d => {
                        const isErr = d.is_faulty;
                        const isPc = d.type === 'pc';
                        const icon = isPc ? 'fa-desktop' : 'fa-print';
                        const extra = isPc ? (d.ip || 'IP Yok') : (d.model || d.ip || 'Yazıcı');
                        const errHtml = isErr ? `<div style="color: #ff003c; font-size: 0.7rem; margin-top: 5px; font-weight: 700;"><i class="fas fa-exclamation-circle"></i> Arıza Kaydı Var</div>` : '';
                        
                        let displayName = (d.name || 'İsimsiz').toString().trim();
                        if (/^\d+$/.test(displayName)) {
                            displayName = (isPc ? 'PC-' : 'PR-') + displayName.padStart(3, '0');
                        }
                        
                        const locCode = (d.location_code || '').trim();
                        const locBadge = locCode ? `<span style="font-size: 0.75rem; color: #38bdf8; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.25); padding: 2px 7px; border-radius: 4px; font-weight: 600; font-family: monospace; letter-spacing: 0.3px;" title="Mahal Kodu"><i class="fas fa-map-marker-alt" style="margin-right: 4px; font-size: 0.7rem;"></i>${locCode}</span>` : '';
                        
                        html += `
                        <div class="bm-device-card ${isErr ? 'broken' : ''}" onclick="app.editDevice(${d.id}, '${d.type}')" style="cursor: pointer; color: #ffffff;">
                            <div style="flex: 1; margin-right: 15px;">
                                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                                    <span style="font-weight: 700; font-size: 0.95rem; color: #ffffff;">${displayName}</span>
                                    ${locBadge}
                                </div>
                                <div style="font-size: 0.75rem; color: rgba(255,255,255,0.7); font-family: monospace; background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px; display: inline-block;">
                                    <i class="fas ${icon}"></i> ${extra}
                                </div>
                                ${errHtml}
                            </div>
                            <i class="fas ${icon}" style="font-size: 1.5rem; color: rgba(255,255,255,0.2);"></i>
                        </div>`;
                    });
                }
                
                document.getElementById('bm-sb-list').innerHTML = html;
                
            }
        } catch(e) {
            document.getElementById('bm-sb-list').innerHTML = '<div style="color:red; text-align:center;">Veriler alınamadı.</div>';
        }
    }
};

// Listen to view changes
const originalNavigateTo = app.navigateTo;
app.navigateTo = function(viewId) {
    originalNavigateTo.call(app, viewId);
    if(viewId === 'building-map') {
        BuildingMap.init();
    }
};

// Check if we are already on building-map when this script loads
if (app.state && app.state.view === 'building-map') {
    BuildingMap.init();
}
