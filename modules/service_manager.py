from flask import Blueprint, jsonify, request, send_file
from core.database_sql import query_db, get_db_connection
from core.auth import require_auth, require_editor, require_admin
import os
import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
from modules.printer_manager import CUPSHelper

service_manager_bp = Blueprint('service_manager', __name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

@service_manager_bp.route('/get_all', methods=['GET'])
@require_auth
def get_service_records():
    try:
        # Tarihe göre (en yeni en üstte) sıralama.
        # sent_date veya acq_date üzerinden en yeni kaydı üste alır.
        items = query_db("""
            SELECT * FROM printer_service 
            ORDER BY 
                CASE 
                    WHEN sent_date IS NOT NULL AND sent_date != '' THEN sent_date 
                    ELSE COALESCE(acq_date, '1900-01-01') 
                END DESC, 
                id DESC
        """)
        return jsonify([dict(row) for row in items])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@service_manager_bp.route('/add', methods=['POST'])
@require_editor
def add_service_record():
    data = request.json
    try:
        conn = get_db_connection()
        
        # Durum Mantığı:
        # 1. Eğer return_date (geldiği tarih) varsa -> 'Depoda'
        # 2. Eğer sent_date (gittiği tarih) varsa -> 'Serviste'
        # 3. Hiçbiri yoksa (sadece kayıt açıldıysa) -> 'Arızalı'
        
        main_status = 'Arızalı'
        if data.get('return_date') and str(data.get('return_date')).strip():
            main_status = 'Depoda'
        elif data.get('sent_date') and str(data.get('sent_date')).strip():
            main_status = 'Serviste'

        printer_id = data.get('printer_id')
        pr_no = data.get('pr_no')
        
        # Yazıcıyı bul (printer_id yoksa pr_no üzerinden - case insensitive)
        if not printer_id and pr_no:
            printer = conn.execute("SELECT id FROM printers WHERE UPPER(LTRIM(RTRIM(pr_no)))=UPPER(?)", (str(pr_no).strip(),)).fetchone()
            if printer: printer_id = printer['id']

        if printer_id:
            # Lifecycle: Arızalı (Kayıt) -> Serviste (Gitti) -> Depoda (Geldi)
            conn.execute("UPDATE printers SET status=? WHERE id=?", (main_status, printer_id))
            conn.commit() # Ensure immediate commit
            print(f"DEBUG: Printer {printer_id} status updated to {main_status}")
        elif pr_no:
            conn.execute("UPDATE printers SET status=? WHERE UPPER(pr_no)=UPPER(?)", (main_status, str(pr_no).strip()))
            conn.commit()
            print(f"DEBUG: Printer {pr_no} status updated to {main_status} via pr_no")

        # CUPS Koruması: Servise giden yazıcıyı CUPS'ta durdur
        if pr_no:
            pr_no_upper = str(pr_no).strip().upper()
            if pr_no_upper.startswith('PR-') and main_status in ['Arızalı', 'Serviste']:
                try:
                    print(f"DEBUG: Triggering CUPS Auto-Pause for {pr_no_upper}")
                    CUPSHelper.set_status(pr_no_upper, 'pause-printer')
                    CUPSHelper.set_status(pr_no_upper, 'reject-jobs')
                    
                    # İKAME VERİLDİ İSE: Mahal Bilgisini DEPO yap (Veritabanı + CUPS)
                    if data.get('has_substitute'):
                        print(f"DEBUG: Substitute detected, moving {pr_no_upper} to DEPO in DB and CUPS")
                        conn.execute("UPDATE printers SET mahal='DEPO' WHERE pr_no=?", (pr_no_upper,))
                        conn.commit()
                        CUPSHelper.update_location(pr_no_upper, 'DEPO')
                        
                    print(f"DEBUG: CUPS auto-paused and location updated for {pr_no_upper}")
                except Exception as e:
                    print(f"DEBUG: CUPS auto-orchestration error for {pr_no_upper}: {e}")
            else:
                print(f"DEBUG: CUPS Skip (Not a PR or wrong status): {pr_no_upper} / {main_status}")

        # İkame yazıcı varsa durumunu 'Kurulu' yap
        if data.get('substitute_pr_no'):
            conn.execute("UPDATE printers SET status='Kurulu' WHERE pr_no=?", (data.get('substitute_pr_no'),))

        conn.execute('''INSERT INTO printer_service (
            printer_id, pr_no, seri, mac, mahal, model, acq_date, acq_place, sent_date, return_date,
            fault_desc, has_substitute, substitute_pr_no, status, user_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
            data.get('printer_id'), data.get('pr_no'), data.get('seri'), 
            data.get('mac'), data.get('mahal'), data.get('model'), 
            data.get('acq_date'), data.get('acq_place'), 
            data.get('sent_date'), data.get('return_date'), data.get('fault_desc'),
            1 if data.get('has_substitute') else 0, data.get('substitute_pr_no'),
            main_status, data.get('user_name')
        ))
        
        conn.commit()
        conn.close()
        return jsonify({"message": "Servis kaydı oluşturuldu"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@service_manager_bp.route('/update/<int:id>', methods=['PUT'])
def update_service_record(id):
    data = request.json
    try:
        conn = get_db_connection()
        
        # Durum Mantığı:
        # 1. return_date (Geldi) girilirse -> 'Tamamlandı' (Kayıt) ve Yazıcı -> 'Depoda'
        # 2. sent_date (Gitti) girilirse ve return yoksa -> 'Serviste'
        # 3. Sadece kayıt varsa -> 'Arızalı'
        
        main_status = 'Arızalı'
        printer_status = 'Arızalı'
        
        if data.get('return_date') and str(data.get('return_date')).strip():
            main_status = 'Tamamlandı'
            printer_status = 'Depoda'
        elif data.get('sent_date') and str(data.get('sent_date')).strip():
            main_status = 'Serviste'
            printer_status = 'Serviste'

        # Yazıcıyı bul ve durumunu güncelle
        record = conn.execute("SELECT printer_id, pr_no FROM printer_service WHERE id=?", (id,)).fetchone()
        p_id = record['printer_id'] if record else None
        
        if not p_id and record and record['pr_no']:
             p_row = conn.execute("SELECT id FROM printers WHERE pr_no=?", (record['pr_no'],)).fetchone()
             if p_row: p_id = p_row['id']

        if p_id:
            conn.execute("UPDATE printers SET status=? WHERE id=?", (printer_status, p_id))
            
            # CUPS Koruması: Servise giden yazıcıyı CUPS'ta durdur (Güncelleme anında)
            if record and record['pr_no']:
                pr_no_upper = str(record['pr_no']).strip().upper()
                if pr_no_upper.startswith('PR-') and printer_status in ['Arızalı', 'Serviste']:
                    try:
                        print(f"DEBUG: Triggering CUPS Auto-Pause on Update for {pr_no_upper}")
                        CUPSHelper.set_status(pr_no_upper, 'pause-printer')
                        CUPSHelper.set_status(pr_no_upper, 'reject-jobs')
                        
                        # İKAME VERİLDİ İSE: Mahal Bilgisini DEPO yap (Veritabanı + CUPS)
                        if data.get('has_substitute'):
                            print(f"DEBUG: Substitute detected on update, moving {pr_no_upper} to DEPO in DB and CUPS")
                            conn.execute("UPDATE printers SET mahal='DEPO' WHERE pr_no=?", (pr_no_upper,))
                            conn.commit()
                            CUPSHelper.update_location(pr_no_upper, 'DEPO')
                            
                        print(f"DEBUG: CUPS auto-paused and location updated for {pr_no_upper} on update")
                    except Exception as e:
                        print(f"DEBUG: CUPS auto-orchestration error for {pr_no_upper}: {e}")
                
                # CUPS Serbest Bırakma: Depoya gelen yazıcıyı CUPS'ta aktif et
                if pr_no_upper.startswith('PR-') and printer_status == 'Depoda':
                    try:
                        print(f"DEBUG: Triggering CUPS Auto-Resume on Update for {pr_no_upper}")
                        CUPSHelper.set_status(pr_no_upper, 'resume-printer')
                        CUPSHelper.set_status(pr_no_upper, 'accept-jobs')
                        print(f"DEBUG: CUPS auto-resumed {pr_no_upper} on update")
                    except Exception as e:
                        print(f"DEBUG: CUPS auto-resume error for {pr_no_upper}: {e}")

        conn.execute('''UPDATE printer_service SET 
            sent_date=?, return_date=?, status=?, final_status=?, has_substitute=?, substitute_pr_no=?, 
            fault_desc=?, acq_date=?, acq_place=?
            WHERE id=?''', (
            data.get('sent_date'), data.get('return_date'), 
            main_status, data.get('final_status'),
            1 if data.get('has_substitute') else 0, data.get('substitute_pr_no'),
            data.get('fault_desc'), data.get('acq_date'), data.get('acq_place'), id
        ))
        
        conn.commit()
        conn.close()
        return jsonify({"message": "Servis kaydı güncellendi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@service_manager_bp.route('/sync_from_excel', methods=['POST'])
def sync_service_from_excel():
    """database/servise_giden_yazıcılar.xlsx dosyasını okur ve içeri aktarır. (10 Kolon Düzeni)"""
    excel_path = os.path.join(BASE_DIR, "database", "servise_giden_yazıcılar.xlsx")
    if not os.path.exists(excel_path):
        return jsonify({"error": f"Dosya bulunamadı: {excel_path}"}), 404
        
    try:
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        ws = wb.active
        
        conn = get_db_connection()
        added_count = 0
        
        def clean_date_excel(val):
            if not val or val == 'None': return None
            if isinstance(val, datetime.datetime): return val.strftime('%Y-%m-%d')
            s = str(val).split(' ')[0].strip()
            return s if len(s) >= 8 else None

        # Sütunlar: A: pr_no, B: seri, C: mac, D: mahal, E: acq_date, F: sent_date, G: return_date, H: fault_desc, I: has_substitute, J: substitute_pr_no
        for row in ws.iter_rows(min_row=2, values_only=True):
            pr_seri = str(row[1] or '').strip()
            if not pr_seri: continue
            
            pr_no = str(row[0] or '').strip()
            seri = pr_seri
            mac = str(row[2] or '').strip()
            mahal = str(row[3] or '').strip()
            acq_date = clean_date_excel(row[4])
            sent_date = clean_date_excel(row[5])
            return_date = clean_date_excel(row[6])
            
            fault_desc = str(row[7] or '').strip()
            sub_text = str(row[8] or '').lower()
            has_sub = 1 if ('evet' in sub_text or 'verildi' in sub_text) else 0
            sub_pr = str(row[9] or '').strip()
            
            # Yazıcıyı bul (ID almak için)
            printer = conn.execute("SELECT id FROM printers WHERE seri=?", (seri,)).fetchone()
            p_id = printer['id'] if printer else None
            
            # Durum belirle
            m_status = 'Arızalı'
            if return_date: m_status = 'Tamamlandı'
            elif sent_date: m_status = 'Serviste'
            
            # Kayıt var mı kontrol et (Seri ve Arıza Açıklaması üzerinden mükerrerlik önlemi)
            exists = conn.execute("SELECT id FROM printer_service WHERE seri=? AND fault_desc=?", (seri, fault_desc)).fetchone()
            
            if exists:
                conn.execute('''UPDATE printer_service SET 
                    printer_id=?, pr_no=?, mac=?, mahal=?, acq_date=?, sent_date=?, return_date=?,
                    fault_desc=?, has_substitute=?, substitute_pr_no=?, status=?
                    WHERE id=?''', (
                    p_id, pr_no, mac, mahal, acq_date, sent_date, return_date,
                    fault_desc, has_sub, sub_pr, m_status, exists['id']
                ))
            else:
                conn.execute('''INSERT INTO printer_service (
                    printer_id, pr_no, seri, mac, mahal, acq_date, sent_date, return_date, 
                    fault_desc, has_substitute, substitute_pr_no, status, user_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                    p_id, pr_no, seri, mac, mahal, acq_date, sent_date, return_date,
                    fault_desc, has_sub, sub_pr, m_status, 'Excel_Sync'
                ))
            
            # Yazıcı durumunu güncelle
            if p_id:
                p_st = 'Depoda' if return_date else ('Serviste' if sent_date else 'Arızalı')
                conn.execute("UPDATE printers SET status=? WHERE id=?", (p_st, p_id))
            
            added_count += 1
        
        conn.commit()
        conn.close()
        return jsonify({"message": f"{added_count} yeni kayıt Excel'den içeri aktarıldı."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@service_manager_bp.route('/delete/<int:id>', methods=['DELETE'])
@require_admin
def delete_service_record(id):
    try:
        query_db("DELETE FROM printer_service WHERE id=?", (id,))
        return jsonify({"message": "Kayıt silindi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@service_manager_bp.route('/export_form', methods=['GET'])
def export_delivery_form():
    """Serviste olan yazıcılar için Resim 2 formatında Excel teslim formu üretir."""
    try:
        # 1. Serviste olanlar (Daha önce teslim edilenler)
        serviste_items = query_db("SELECT * FROM printer_service WHERE status='Serviste'")
        
        # 2. Arızalı olanlar (Teslim edilmeyi bekleyenler)
        arizali_items = query_db("SELECT * FROM printer_service WHERE status='Arızalı'")
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "YAZICI SERVİS TESLİM FORMU"
        
        # Stil tanımlamaları
        header_font = Font(bold=True, size=12)
        border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        center_align = Alignment(horizontal='center', vertical='center')
        
        # Başlık ve Tarih
        ws.merge_cells('A1:F1')
        ws['A1'] = "YAZICI SERVİS TESLİM FORMU"
        ws['A1'].font = Font(bold=True, size=14)
        ws['A1'].alignment = center_align
        
        today = datetime.datetime.now().strftime("%d.%m.%Y")
        ws['G1'] = today
        ws['G1'].font = Font(bold=True, size=12)
        ws['G1'].alignment = Alignment(horizontal='right', vertical='center')
        
        # Sütun Genişliklerini Başta Ayarla (Daha stabil)
        ws.column_dimensions['A'].width = 6
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 28
        ws.column_dimensions['D'].width = 28
        ws.column_dimensions['E'].width = 35
        ws.column_dimensions['F'].width = 60 # Arıza Açıklaması Genişletildi
        ws.column_dimensions['G'].width = 40 # Durum Genişletildi
        
        # Tablo Başlıkları
        headers = ['NO', 'PR NO', 'SERİ NO', 'MAC ADRESİ', 'YAZICI MODEL', 'ARIZA AÇIKLAMASI', 'TESLİMAT DURUMU']
        
        start_row = 3
        for i, h in enumerate(headers):
            cell = ws.cell(row=start_row, column=i+1)
            cell.value = h
            cell.font = header_font
            cell.border = border
            cell.alignment = center_align
            cell.fill = openpyxl.styles.PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

        current_row = start_row + 1
        
        # 1. BÖLÜM: SERVİSTE OLANLAR
        for idx, item in enumerate(serviste_items):
            ws.cell(row=current_row, column=1).value = idx + 1
            ws.cell(row=current_row, column=2).value = item['pr_no']
            ws.cell(row=current_row, column=3).value = item['seri']
            ws.cell(row=current_row, column=4).value = item['mac']
            ws.cell(row=current_row, column=5).value = item['model']
            ws.cell(row=current_row, column=6).value = item['fault_desc']
            ws.cell(row=current_row, column=7).value = "SERVİSTE"
            
            for col in range(1, 8):
                ws.cell(row=current_row, column=col).border = border
                # Sadece açıklama (6. kolon) wrap olacak, dierleri tek satır (Genişlik yetmezse Excel'de kayabilir ama kodda zorlamıyoruz)
                ws.cell(row=current_row, column=col).alignment = Alignment(wrap_text=(col == 6), vertical='center')
            current_row += 1

        # BOŞLUK BIRAK
        current_row += 1

        # 2. BÖLÜM: SERVİSE TESLİM BEKLEYENLER (ARIZALI)
        for idx, item in enumerate(arizali_items):
            ws.cell(row=current_row, column=1).value = len(serviste_items) + idx + 1
            ws.cell(row=current_row, column=2).value = item['pr_no']
            ws.cell(row=current_row, column=3).value = item['seri']
            ws.cell(row=current_row, column=4).value = item['mac']
            ws.cell(row=current_row, column=5).value = item['model']
            ws.cell(row=current_row, column=6).value = item['fault_desc']
            ws.cell(row=current_row, column=7).value = "SERVİSE TESLİM BEKLİYOR"
            
            for col in range(1, 8):
                ws.cell(row=current_row, column=col).border = border
                ws.cell(row=current_row, column=col).alignment = Alignment(wrap_text=(col == 6), vertical='center')
            current_row += 1

        # Genişlik ayarları zaten yukarıda yapıldı (Dims kaldırıldı)

        filename = f"Servis_Teslim_Formu_{today.replace('.','_')}.xlsx"
        save_path = os.path.join(BASE_DIR, filename)
        wb.save(save_path)
        
        return send_file(save_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@service_manager_bp.route('/export_pdf', methods=['GET'])
@require_auth
def export_service_pdf():
    """Serviste olan ve arızalı yazıcılar için PDF formatında teslim formu üretir."""
    try:
        from modules.document_service import generate_pdf_direct
        
        # 1. Verileri çek
        serviste = query_db("SELECT * FROM printer_service WHERE status='Serviste'")
        arizali = query_db("SELECT * FROM printer_service WHERE status='Arızalı'")
        
        records = []
        for item in serviste:
            records.append({
                "pr_no": item['pr_no'],
                "seri": item['seri'],
                "mac": item['mac'],
                "model": item['model'] or '-',
                "status": "SERVİSTE"
            })
        for item in arizali:
            records.append({
                "pr_no": item['pr_no'],
                "seri": item['seri'],
                "mac": item['mac'],
                "model": item['model'] or '-',
                "status": "ARIZALI"
            })

        if not records:
            return jsonify({"error": "Teslim edilecek veya serviste olan yazıcı bulunamadı."}), 404

        # 2. PDF oluştur
        pdf_data = {
            "records": records,
            "note": "Yukarıda bilgileri yer alan cihazlar servis işlemi için teslim edilmiştir / servistedir.",
            "veren": "BİLGİ İŞLEM",
            "alan": "...................."
        }
        
        pdf_path = generate_pdf_direct("SERVICE", pdf_data)
        
        # 3. Gönder
        now_str = datetime.datetime.now().strftime("%d_%m_%Y")
        return send_file(pdf_path, as_attachment=True, download_name=f"Servis_Teslim_Formu_{now_str}.pdf")

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
