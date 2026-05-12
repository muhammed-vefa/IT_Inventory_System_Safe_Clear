with open('index.html', 'a', encoding='utf-8') as f:
    f.write('''
    <div id="full-inventory-modal" class="modal-backdrop" style="display: none;">
        <div class="card" style="max-width: 95%; width: 1400px; max-height: 90vh; overflow: hidden; display: flex; flex-direction: column;">
            <div class="flex-between mb-3">
                <h3 style="color: var(--accent); margin:0;"><i class="fas fa-table"></i> Detaylı Envanter Listesi</h3>
                <div class="flex-row gap-2">
                    <button class="btn btn-secondary btn-sm" onclick="app.exportInventoryToExcel()"><i class="fas fa-file-excel"></i> Excel'e Aktar</button>
                    <i class="fas fa-times modal-close" onclick="document.getElementById('full-inventory-modal').style.display='none'"></i>
                </div>
            </div>
            <div style="overflow: auto; flex: 1; border-radius: 8px; background: rgba(0,0,0,0.2);">
                <table id="full-inventory-table" class="kb-table" style="width: 100%; border-collapse: collapse; font-size: 0.8rem;">
                    <thead style="position: sticky; top: 0; background: #1a222d; z-index: 10;">
                        <tr>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1);">ID</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1);">MAHAL</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1);">HOSTNAME</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1);">IP ADRESİ</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1);">MAC ADRESİ</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1);">SERİ NO</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1);">DURUM</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1);">ZİMMET</th>
                        </tr>
                    </thead>
                    <tbody id="full-inventory-tbody"></tbody>
                </table>
            </div>
        </div>
    </div>
''')
