$filePath = "frontend\UI_controller.js"
$content = [System.IO.File]::ReadAllText($filePath, [System.Text.Encoding]::UTF8)

$oldFunc = @'
    downloadServiceDeliveryForm: function() {
        const url = `${this.state.API_BASE}/service/export_form`;
        const a = document.createElement('a');
        a.href = url;
        a.download = `Servis_Teslim_Formu_${new Date().toLocaleDateString('tr-TR').replace(/\./g,'_')}.xlsx`;
        a.click();
        this.showToast('Excel formu hazırlanıyor ve indiriliyor...');
    },
'@

$newFunc = @'
    downloadServiceDeliveryForm: async function() {
        try {
            this.showToast('Servis teslim formu PDF olarak hazirlanıyor...', 'info');
            const resp = await fetch(this.state.API_BASE + '/service/get_all');
            const allRecords = await resp.json();
            if (allRecords.error) throw new Error(allRecords.error);

            const records = allRecords.filter(function(s) {
                return s.status === 'Serviste' || s.status === 'Arızalı' || s.status === 'Arizali' || s.status === 'Tamamlandı';
            });

            const jsPDFLib = window.jspdf;
            if (!jsPDFLib) throw new Error('jsPDF kütüphanesi yüklenemedi!');
            const doc = new jsPDFLib.jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });

            try { doc.addImage('logo/ht_left.png', 'PNG', 10, 5, 28, 14); } catch(e) {}
            try { doc.addImage('logo/ht_right.png', 'PNG', 254, 5, 28, 14); } catch(e) {}

            doc.setFontSize(15);
            doc.setFont('helvetica', 'bold');
            doc.setTextColor(30, 30, 30);
            doc.text('YAZICI SERVIS TESLIM FORMU', 148.5, 13, { align: 'center' });

            const dateStr = new Date().toLocaleDateString('tr-TR');
            doc.setFontSize(10);
            doc.setFont('helvetica', 'normal');
            doc.setTextColor(80, 80, 80);
            doc.text(dateStr, 283, 13, { align: 'right' });
            doc.setDrawColor(180, 180, 180);
            doc.line(10, 17, 287, 17);

            const self = this;
            const tableBody = records.map(function(s, idx) {
                let durumText = s.status || 'Serviste';
                if (s.status === 'Arizali' || s.status === 'Arızalı') durumText = 'SERVISE TESLIM BEKLIYOR';
                else if (s.status === 'Serviste') durumText = 'SERVISTE';
                else if (s.status === 'Tamamlandı') durumText = 'TAMAMLANDI';
                return [
                    idx + 1,
                    self.fixTurkishForPDF(s.pr_no || '-'),
                    self.fixTurkishForPDF(s.seri || '-'),
                    self.fixTurkishForPDF(s.mac || '-'),
                    self.fixTurkishForPDF(s.model || '-'),
                    self.fixTurkishForPDF(s.fault_desc || '-'),
                    self.fixTurkishForPDF(durumText)
                ];
            });

            if (tableBody.length === 0) {
                tableBody.push([{ content: 'Servis kaydi bulunamadi.', colSpan: 7, styles: { halign: 'center', textColor: [150,150,150] } }]);
            }

            doc.autoTable({
                startY: 21,
                head: [['NO', 'PR NO', 'SERI NO', 'MAC ADRESI', 'YAZICI MODEL', 'ARIZA ACIKLAMASI', 'TESLIMAT DURUMU']],
                body: tableBody,
                theme: 'grid',
                headStyles: { fillColor: [35,35,35], textColor: [255,255,255], fontSize: 8, fontStyle: 'bold', halign: 'center', cellPadding: 3 },
                bodyStyles: { fontSize: 8, cellPadding: 2.5 },
                alternateRowStyles: { fillColor: [245,245,245] },
                columnStyles: {
                    0: { cellWidth: 10, halign: 'center' },
                    1: { cellWidth: 22, halign: 'center', fontStyle: 'bold' },
                    2: { cellWidth: 40, halign: 'center', fontSize: 7 },
                    3: { cellWidth: 40, halign: 'center', fontSize: 7 },
                    4: { cellWidth: 35 },
                    5: { cellWidth: 'auto', overflow: 'linebreak' },
                    6: { cellWidth: 42, halign: 'center', fontStyle: 'bold' }
                },
                didParseCell: function(data) {
                    if (data.column.index === 6 && data.section === 'body') {
                        var val = (data.cell.raw || '').toString().toUpperCase();
                        if (val.indexOf('SERVISTE') !== -1) data.cell.styles.textColor = [200,30,30];
                        else if (val.indexOf('BEKLIYOR') !== -1) data.cell.styles.textColor = [220,100,0];
                        else if (val.indexOf('TAMAMLANDI') !== -1) data.cell.styles.textColor = [20,140,60];
                    }
                }
            });

            var finalY = doc.lastAutoTable.finalY + 8;
            doc.setFontSize(8);
            doc.setTextColor(130,130,130);
            doc.text('Toplam ' + records.length + ' kayit | ' + new Date().toLocaleString('tr-TR'), 14, finalY);
            doc.text('IT Departmani - Yazici Servis Takip', 287, finalY, { align: 'right' });
            doc.save('Servis_Teslim_Formu_' + dateStr.replace(/\./g,'_') + '.pdf');
            this.showToast('PDF basariyla indirildi.', 'success');
        } catch(e) {
            console.error('Servis PDF Hatasi:', e);
            alert('PDF olusturulamadi: ' + e.message);
        }
    },
'@

if ($content.Contains("downloadServiceDeliveryForm: function()")) {
    # Find exact boundaries
    $startIdx = $content.IndexOf("    downloadServiceDeliveryForm: function()")
    $endIdx = $content.IndexOf("    },`r`n", $startIdx) + 7
    $before = $content.Substring(0, $startIdx)
    $after = $content.Substring($endIdx)
    $newContent = $before + $newFunc + $after
    [System.IO.File]::WriteAllText($filePath, $newContent, [System.Text.Encoding]::UTF8)
    Write-Output "SUCCESS: Function replaced"
} else {
    Write-Output "ERROR: Function not found"
    Write-Output ($content.Substring($content.IndexOf("downloadServiceDeliveryForm") - 10, 200))
}
