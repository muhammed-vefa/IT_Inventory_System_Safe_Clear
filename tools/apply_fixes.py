import re

with open('frontend/UI_controller.js', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. SİL Button
c = re.sub(r'\$\{isAdmin \? `\n                    <div class=\"area-action-btn\" onclick=\"app\.runAreaAction\(\$\{area\.id\}, \'delete\'\)\" title=\"SİL\" style=\"color: #ff4b2b;\">\n                        <div class=\"icon-circle\" style=\"background: rgba\(255, 75, 43, 0\.1\); border: 1px solid rgba\(255, 75, 43, 0\.2\);\"><i class=\"fas fa-trash\"></i></div>\n                        <span>SİL</span>\n                    </div>` : \'\'\}',
r'''                    <div class="area-action-btn" onclick="app.runAreaAction(${area.id}, 'delete')" title="SİL" style="color: #ff4b2b;">
                        <div class="icon-circle" style="background: rgba(255, 75, 43, 0.1); border: 1px solid rgba(255, 75, 43, 0.2);"><i class="fas fa-trash"></i></div>
                        <span>SİL</span>
                    </div>''', c)

# 2. Depot Report
c = c.replace(
'''        if(navKeyosSync) navKeyosSync.style.display = isAdmin ? 'block' : 'none';
        if(navKeyosReport) navKeyosReport.style.display = isAdmin ? 'block' : 'none';
        const navAdminReports = document.getElementById('menu-admin-reports');''',
'''        if(navKeyosSync) navKeyosSync.style.display = isAdmin ? 'block' : 'none';
        if(navKeyosReport) navKeyosReport.style.display = isAdmin ? 'block' : 'none';
        const navDepotReport = document.getElementById('menu-depot-report');
        if(navDepotReport) navDepotReport.style.display = (isAdmin || role === 'DEPOT') ? 'block' : 'none';
        const navAdminReports = document.getElementById('menu-admin-reports');'''
)

# 3. kb-btn-add
c = c.replace("'btn-device-add', 'kb-btn-add', 'menu-admin-reports']", "'btn-device-add', 'menu-admin-reports']")

# 4. openDepotTransaction - Category
c = c.replace(
'''    openDepotTransaction: function(id, name, mode = 'in') {
        const item = this.state.depot.find(d => d.id == id);
        this.state.editingDepotOrigin = item ? (item.table_origin || 'depot') : 'depot';
        
        document.getElementById('depot-trans-title').innerText''',
'''    openDepotTransaction: function(id, name, mode = 'in') {
        const item = this.state.depot.find(d => d.id == id);
        this.state.editingDepotOrigin = item ? (item.table_origin || 'depot') : 'depot';
        this.state.editingDepotCategory = item ? (item.category || '') : '';
        
        document.getElementById('depot-trans-title').innerText'''
)

# 5. setTransType
c = c.replace(
'''        const reasonCont = document.getElementById('trans-reason-container');
        if (reasonCont) reasonCont.style.display = (type === 'out') ? 'block' : 'none';
    },''',
'''        const reasonCont = document.getElementById('trans-reason-container');
        const cat = (this.state.editingDepotCategory || '').toUpperCase().trim();
        const isConsumable = ['SARF MALZEME', 'OFİS / GİDA', 'OFİS / GIDA'].includes(cat);
        if (reasonCont) {
            if (isConsumable) {
                reasonCont.style.display = 'none';
            } else {
                reasonCont.style.display = (type === 'out') ? 'block' : 'none';
            }
        }
    },'''
)

# 6. executeDepotTransaction
c = c.replace(
'''                    user_id: this.state.activeUser.key,
                    table_type: this.state.editingDepotOrigin || 'depot'
                })''',
'''                    user_id: this.state.activeUser.key,
                    table_type: this.state.editingDepotOrigin || 'depot',
                    category: this.state.editingDepotCategory || ''
                })'''
)

# 7. renderDepot - catClass and statsHtml
c = c.replace(
'''            const catNormalized = (item.category || "").toUpperCase().trim();
            const catClass = catNormalized === 'SARF MALZEME' ? 'cat-sarf' :''',
'''            const catNormalized = (item.category || "").toUpperCase().trim();
            const isConsumable = ['SARF MALZEME', 'OFİS / GİDA', 'OFİS / GIDA'].includes(catNormalized);
            const catClass = catNormalized === 'SARF MALZEME' ? 'cat-sarf' :'''
)

c = c.replace(
'''            return `
            <div class="card depot-card fade-in" style="border-left: 4px solid ${barColor};">
                <div class="flex-between mb-2">''',
'''            const statsHtml = isConsumable ? '' : `
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
                </div>`;
            return `
            <div class="card depot-card fade-in" style="cursor:pointer; border-left: 4px solid ${barColor};" onclick="app.openEditDepotItem(${item.id})">
                <div class="flex-between mb-2">'''
)

c = c.replace(
'''                <div class="stock-bar" style="height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; margin-bottom: 12px;">
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

                <div class="flex-row gap-2" style="border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px;">''',
'''                <div class="stock-bar" style="height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; margin-bottom: 12px;">
                    <div class="stock-bar-fill" style="width: ${barWidth}%; background: ${barColor}; height: 100%;"></div>
                </div>

                ${statsHtml}

                <div class="flex-row gap-2" style="border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px;">'''
)

# 8. handleDepotCategoryChange
c = c.replace(
'''    handleDepotCategoryChange: function(val) {
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
            labels[2].innerText = isConsumable ? 'DAĞITILAN' : 'ARIZALI';
            labels[3].innerText = isConsumable ? 'KALAN' : 'KAYIP';
            // 3. inputu gizle (Gıda/Sarf için gereksiz dendi)
            const input3 = document.getElementById('depot-kayip');
            if (input3 && input3.parentElement) {
                input3.parentElement.style.display = isConsumable ? 'none' : 'block';
            }
        }
    },''',
'''    handleDepotCategoryChange: function(val) {
        val = val || document.getElementById('depot-category').value;
        const fields = document.getElementById('depot-asset-fields');
        if (!fields) return;
        const isConsumable = ['SARF MALZEME', 'OFİS / GİDA', 'OFİS / GIDA'].includes(val.toUpperCase().trim());
        fields.style.display = isConsumable ? 'none' : 'block';
    },'''
)

with open('frontend/UI_controller.js', 'w', encoding='utf-8') as f:
    f.write(c)

print('All python replacements completed successfully.')
