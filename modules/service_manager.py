from core.utils import normalize_row
from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection
from core.auth import require_auth, require_admin, require_editor

service_manager_bp = Blueprint('service_manager', __name__)

@service_manager_bp.route('/get_all', methods=['GET'])
@require_auth
def get_all():
    conn = get_db_connection()
    if not conn: return jsonify([])
    cursor = conn.cursor()
    query = """
        SELECT s.*, p.cups_location as printer_location 
        FROM printer_service s
        LEFT JOIN printers p ON s.pr_no = p.pr_no
        WHERE s.is_deleted = 0
        ORDER BY CASE WHEN s.acquisition_date IS NULL THEN 0 ELSE 1 END DESC, s.acquisition_date DESC, s.id DESC
    """
    cursor.execute(query)
    columns = [column[0].lower() for column in cursor.description]
    
    results = []
    for row in cursor.fetchall():
        d = dict(zip(columns, row))
        if not d.get('location_code'):
            d['location_code'] = d.get('printer_location')
            
        # Servis tablosunda "SERVİSTE-" önekini gizle (Sadece CUPS ve backend işlemleri için kullanılsın)
        if d.get('location_code') and d['location_code'].startswith('SERVİSTE-'):
            d['location_code'] = d['location_code'].replace('SERVİSTE-', '', 1)
            
        d['mahal'] = d.get('location_code')
        
        # Eğer geçmiş kayıtlarda status NULL ise, tarihlere bakarak toparla
        if not d.get('status'):
            if d.get('return_date'):
                d['status'] = 'Tamamlandı'
            elif d.get('sent_date'):
                d['status'] = 'Serviste'
            else:
                d['status'] = 'Arızalı'
                
        results.append(normalize_row(d))
        
    conn.close()
    return jsonify(results)

from datetime import datetime
import traceback

def parse_date_safely(val):
    if not val:
        return None
    val_str = str(val).strip()
    if val_str.lower() in ('', 'none', 'null', '-', 'undefined'):
        return None
    
    formats = [
        "%d.%m.%Y",          # 18.05.2026
        "%Y-%m-%d",          # 2026-05-18
        "%Y-%m-%d %H:%M:%S", # 2026-05-18 16:30:00
        "%d/%m/%Y",          # 18/05/2026
        "%Y/%m/%d"           # 2026/05/18
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt)
        except ValueError:
            continue
    return None


@service_manager_bp.route('/add', methods=['POST'])
@require_auth
def add_service():
    try:
        data = request.json
        print("ADD SERVICE PAYLOAD:", data)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # UI'dan gelen tarihleri kontrol et, bos ise None yap ve guvenli parse et
        acq_date = parse_date_safely(data.get('acquisition_date') or data.get('acq_date'))
        sent_date = parse_date_safely(data.get('sent_date'))
        return_date = parse_date_safely(data.get('return_date'))
        fault_desc = data.get('fault_description') or data.get('fault_desc') or None
        
        if fault_desc and str(fault_desc).strip() in ('', 'None', 'null', 'undefined'):
            fault_desc = None

        if return_date:
            data['status'] = 'Tamamlandı'
            p_status = (0, 0, 1, 0) # is_faulty, in_service, warehouse, on_field
        elif sent_date:
            data['status'] = 'Serviste'
            p_status = (0, 1, 0, 0)
        else:
            data['status'] = 'Arızalı'
            p_status = (1, 0, 0, 0)

        print("ADD PARSED DATES - acq_date:", acq_date, "sent_date:", sent_date, "return_date:", return_date)

        pr_no = data.get('pr_no')
        cursor.execute("SELECT location_code FROM printers WHERE pr_no=?", (pr_no,))
        pr_row = cursor.fetchone()
        current_location = pr_row[0] if pr_row and pr_row[0] else (data.get('mahal') or data.get('location_code'))

        cursor.execute("""
            INSERT INTO printer_service (
                pr_no, sla_no, serial_no, mac, model, fault_description, 
                status, acquisition_date, sent_date, return_date, 
                has_substitute, substitute_pr_no, user_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pr_no, data.get('sla_no'), data.get('seri') or data.get('serial_no'), 
            data.get('mac'), data.get('model'), 
            fault_desc, data.get('status'), 
            acq_date, sent_date, return_date,
            1 if data.get('has_substitute') else 0,
            data.get('substitute_pr_no'),
            data.get('user_name', 'system')
        ))
        
        if data.get('has_substitute') or return_date:
            cursor.execute("UPDATE printers SET is_faulty=?, in_service=?, warehouse=?, on_field=?, location_code='Depo' WHERE pr_no=?", (*p_status, data.get('pr_no')))
        else:
            loc = current_location or 'BİLİNMİYOR'
            if not loc.startswith('SERVİSTE-'):
                new_location = f"SERVİSTE-{loc}"
            else:
                new_location = loc
            cursor.execute("UPDATE printers SET is_faulty=?, in_service=?, warehouse=?, on_field=?, location_code=? WHERE pr_no=?", (*p_status, new_location, data.get('pr_no')))
        
        conn.commit()
        conn.close()

        # CUPS Pause & Reject if status is 'Arızalı' or 'Serviste'
        if data['status'] in ('Arızalı', 'Serviste') and pr_no:
            try:
                import requests
                cups_admin_url = 'http://10.241.1.21:49631/admin/'
                # Pause Printer
                requests.post(cups_admin_url, data={
                    'OP': 'pause-printer',
                    'printer_name': pr_no,
                    'confirm': 'Yes'
                }, timeout=5, verify=False)
                # Reject Jobs
                requests.post(cups_admin_url, data={
                    'OP': 'reject-jobs',
                    'printer_name': pr_no,
                    'confirm': 'Yes'
                }, timeout=5, verify=False)
            except Exception as cups_err:
                print(f"[CUPS Auto Automation Error] {cups_err}")

        return jsonify({"success": True})
    except Exception as e:
        print("ADD SERVICE ERROR:", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@service_manager_bp.route('/update/<int:record_id>', methods=['PUT'])
@require_auth
def update_service(record_id):
    try:
        user_role = request.current_user.get('role', '')
        if user_role not in ('ADMIN', 'DEPOT'):
            return jsonify({"success": False, "error": "Bu işlem için yetkiniz bulunmamaktadır. Sadece Admin ve Depocu işlem yapabilir."}), 403

        data = request.json
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "error": "Database connection failed"}), 500
        cursor = conn.cursor()

        # Check existing return_date in database
        cursor.execute("SELECT return_date, pr_no FROM printer_service WHERE id = ?", (record_id,))
        existing_row = cursor.fetchone()
        if existing_row:
            existing_return_date, existing_pr_no = existing_row
            if existing_return_date is not None and user_role != 'ADMIN':
                conn.close()
                return jsonify({"success": False, "error": "Geldiği tarih bilgisi girilmiş kapalı kayıtları sadece Admin düzenleyebilir."}), 403
        
        acq_date = parse_date_safely(data.get('acquisition_date') or data.get('acq_date'))
        sent_date = parse_date_safely(data.get('sent_date'))
        return_date = parse_date_safely(data.get('return_date'))
        fault_desc = data.get('fault_description') or data.get('fault_desc') or None
        
        if fault_desc and str(fault_desc).strip() in ('', 'None', 'null', 'undefined'):
            fault_desc = None

        if return_date:
            data['status'] = 'Tamamlandı'
            p_status = (0, 0, 1, 0) # is_faulty, in_service, warehouse, on_field
        elif sent_date:
            data['status'] = 'Serviste'
            p_status = (0, 1, 0, 0)
        else:
            data['status'] = 'Arızalı'
            p_status = (1, 0, 0, 0)

        update_sql = """
            UPDATE printer_service SET 
                pr_no = ?, sla_no = ?, serial_no = ?, mac = ?, 
                model = ?, fault_description = ?, status = ?, 
                acquisition_date = ?, sent_date = ?, return_date = ?,
                has_substitute = ?, substitute_pr_no = ?, user_name = ?
            WHERE id = ?
        """
        
        values = (
            data.get('pr_no'), data.get('sla_no'), data.get('seri') or data.get('serial_no'), 
            data.get('mac'), data.get('model'), 
            fault_desc, data.get('status'), 
            acq_date, sent_date, return_date,
            1 if data.get('has_substitute') else 0,
            data.get('substitute_pr_no'),
            data.get('user_name', 'system'),
            record_id
        )

        cursor.execute(update_sql, values)
        
        if data.get('has_substitute') or return_date:
            cursor.execute("UPDATE printers SET is_faulty=?, in_service=?, warehouse=?, on_field=?, location_code='Depo' WHERE pr_no=?", (*p_status, data.get('pr_no')))
        else:
            cursor.execute("UPDATE printers SET is_faulty=?, in_service=?, warehouse=?, on_field=? WHERE pr_no=?", (*p_status, data.get('pr_no')))
        
        conn.commit()
        conn.close()

        # CUPS Pause & Reject if status is 'Arızalı' or 'Serviste'
        pr_no = data.get('pr_no')
        if data['status'] in ('Arızalı', 'Serviste') and pr_no:
            try:
                import requests
                cups_admin_url = 'http://10.241.1.21:49631/admin/'
                # Pause Printer
                requests.post(cups_admin_url, data={
                    'OP': 'pause-printer',
                    'printer_name': pr_no,
                    'confirm': 'Yes'
                }, timeout=5, verify=False)
                # Reject Jobs
                requests.post(cups_admin_url, data={
                    'OP': 'reject-jobs',
                    'printer_name': pr_no,
                    'confirm': 'Yes'
                }, timeout=5, verify=False)
            except Exception as cups_err:
                print(f"[CUPS Auto Automation Error] {cups_err}")

        return jsonify({"success": True})
    except Exception as e:
        print("UPDATE SERVICE ERROR:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@service_manager_bp.route('/delete/<int:record_id>', methods=['DELETE'])
@require_admin
def delete_service(record_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE printer_service SET is_deleted = 1 WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@service_manager_bp.route('/export_pdf', methods=['GET'])
def export_pdf():
    import os
    import io
    from fpdf import FPDF
    from flask import send_file
    import datetime
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 'Arızalı' (Servise Teslim Bekliyor) veya 'Serviste' olanlari getir
        query = """
            SELECT s.pr_no, s.serial_no, s.mac, s.model, s.fault_description, s.status
            FROM printer_service s
            WHERE s.status IN ('Arızalı', 'Serviste') AND s.is_deleted = 0
            ORDER BY s.acquisition_date DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        class PDF(FPDF):
            def header(self):
                # Font ayari
                if os.path.exists("C:\\Windows\\Fonts\\arial.ttf"):
                    self.add_font('Arial', '', 'C:\\Windows\\Fonts\\arial.ttf')
                    self.add_font('Arial', 'B', 'C:\\Windows\\Fonts\\arialbd.ttf')
                    
                # Ust border cizgisi (Mavi)
                self.set_line_width(0.5)
                self.set_draw_color(30, 64, 175)
                self.line(10, 10, 287, 10)
                
                # Sol Alan (KEYDATA LOGO YAZISI)
                self.set_y(15)
                self.set_font('Arial' if os.path.exists("C:\\Windows\\Fonts\\arialbd.ttf") else 'helvetica', 'B', 22)
                self.set_text_color(55, 71, 79)
                self.cell(40, 10, 'KEY', border=0, align='R')
                self.set_text_color(211, 47, 47)
                self.cell(20, 10, 'DATA', border=0, align='L')
                
                # Orta Alan (BASLIK)
                self.set_text_color(0, 0, 0)
                self.set_x(100)
                self.set_font('Arial' if os.path.exists("C:\\Windows\\Fonts\\arialbd.ttf") else 'helvetica', 'B', 18)
                self.cell(100, 10, 'YAZICI SERVIS TESLIM FORMU', border=0, align='C')
                
                # Sag Alan (Tarih)
                self.set_font('Arial' if os.path.exists("C:\\Windows\\Fonts\\arialbd.ttf") else 'helvetica', 'B', 14)
                self.set_x(247)
                self.cell(40, 10, f'{datetime.datetime.now().strftime("%d.%m.%Y")}', border=0, align='R')
                
                self.ln(12)
                
                # Alt border cizgisi (Mavi)
                self.set_draw_color(30, 64, 175)
                self.line(10, self.get_y(), 287, self.get_y())
                self.ln(5)

            def footer(self):
                self.set_y(-15)
                self.set_font('Arial' if os.path.exists("C:\\Windows\\Fonts\\arial.ttf") else 'helvetica', '', 8)
                self.set_text_color(100, 100, 100)
                self.cell(0, 10, f'Sayfa {self.page_no()}', 0, 0, 'C')

        pdf = PDF(orientation='L', format='A4')
        pdf.add_page()
        
        has_arial = os.path.exists("C:\\Windows\\Fonts\\arial.ttf")
        font_name = 'Arial' if has_arial else 'helvetica'
        
        # SUTUN GENISLIKLERI (Toplam 277mm - A4 Yatay Kullanilabilir Alan)
        col_widths = [10, 25, 35, 35, 40, 95, 37]
        headers = ['NO', 'PR NO', 'SERI NO', 'MAC ADRESI', 'YAZICI MODELI', 'ARIZA ACIKLAMASI', 'TESLIMAT DURUMU']
        
        pdf.set_font(font_name, 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.set_text_color(0, 0, 0)
        pdf.set_draw_color(150, 150, 150)
        pdf.set_line_width(0.2)
        
        # Tablo Basliklari
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 12, header, border=1, align='C', fill=True)
        pdf.ln()

        pdf.set_font(font_name, '', 9)
        
        # Tablo Icerigi
        for idx, row in enumerate(rows):
            no_str = str(idx + 1)
            pr_no = str(row[0] or '')
            seri = str(row[1] or '')
            mac = str(row[2] or '')
            model = str(row[3] or '')[:30]
            desc = str(row[4] or '')[:65]
            status_raw = str(row[5] or '')
            
            # Durum metni ve rengi
            if status_raw == 'Arızalı' or status_raw == 'Arizali':
                status_text = 'SERVISE TESLIM BEKLIYOR'
                status_color = (41, 128, 185) # Mavi ton
            elif status_raw == 'Serviste':
                status_text = 'SERVISTE'
                status_color = (21, 101, 192) # Koyu Mavi
            else:
                status_text = status_raw.upper()
                status_color = (100, 100, 100)

            # Sayfa sonu kontrolu (Sayfa tasarsa yeni sayfa ve basliklari ekle)
            if pdf.get_y() > 180:
                pdf.add_page()
                pdf.set_font(font_name, 'B', 10)
                pdf.set_fill_color(240, 240, 240)
                pdf.set_text_color(0, 0, 0)
                for i, header in enumerate(headers):
                    pdf.cell(col_widths[i], 12, header, border=1, align='C', fill=True)
                pdf.ln()
                pdf.set_font(font_name, '', 9)
            
            # Satir Yuksekligi
            line_h = 8
            
            pdf.set_text_color(0, 0, 0)
            
            # 0. NO (Beyaz)
            pdf.set_fill_color(255, 255, 255)
            pdf.cell(col_widths[0], line_h, no_str, border=1, align='C', fill=True)
            
            # 1. PR NO (Acik Yesil Arkaplan)
            pdf.set_fill_color(200, 230, 201) 
            pdf.cell(col_widths[1], line_h, pr_no, border=1, align='C', fill=True)
            
            # Beyaza don
            pdf.set_fill_color(255, 255, 255)
            
            # 2. SERI NO
            pdf.cell(col_widths[2], line_h, seri, border=1, align='C', fill=True)
            
            # 3. MAC ADRESI
            pdf.cell(col_widths[3], line_h, mac, border=1, align='C', fill=True)
            
            # 4. YAZICI MODELI
            pdf.cell(col_widths[4], line_h, model, border=1, align='C', fill=True)
            
            # 5. ARIZA ACIKLAMASI
            pdf.cell(col_widths[5], line_h, desc, border=1, align='L', fill=True)
            
            # 6. TESLIMAT DURUMU (Mavi yazi rengi)
            pdf.set_text_color(*status_color)
            pdf.set_font(font_name, 'B', 8)
            pdf.cell(col_widths[6], line_h, status_text, border=1, align='C', fill=True)
            
            # Satir sonu, ayarlari sifirla
            pdf.set_text_color(0, 0, 0)
            pdf.set_font(font_name, '', 9)
            pdf.ln()
            
        pdf.ln(20)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font(font_name, 'B', 12)
        
        # Imza alanlari (Yatay oldugu icin daha genis)
        pdf.set_x(50)
        pdf.cell(95, 10, 'Teslim Eden', border=0, align='C')
        pdf.set_x(150)
        pdf.cell(95, 10, 'Teslim Alan', border=0, align='C')
        pdf.ln(15)
        pdf.set_x(50)
        pdf.cell(95, 10, 'Ad Soyad / Imza', border=0, align='C')
        pdf.set_x(150)
        pdf.cell(95, 10, 'Ad Soyad / Imza', border=0, align='C')

        pdf_bytes = pdf.output()
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=False,
            download_name=f'Servis_Teslim_Formu_{datetime.datetime.now().strftime("%Y%m%d")}.pdf'
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
