from flask import Blueprint, request, jsonify
from core.auth import require_admin, require_auth
from modules.printer_pages_service import fetch_all_printer_pages_sync, get_page_report

printer_pages_bp = Blueprint('printer_pages', __name__)

@printer_pages_bp.route('/force_page_sync', methods=['POST', 'OPTIONS'])
@require_admin
def force_page_sync():
    try:
        success_count = fetch_all_printer_pages_sync()
        return jsonify({"success": True, "message": f"{success_count} yazıcının sayaç bilgisi başarıyla çekildi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@printer_pages_bp.route('/page_report', methods=['POST', 'OPTIONS'])
@require_admin
def page_report():
    try:
        data = request.json or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({"success": False, "error": "Başlangıç ve Bitiş tarihi gereklidir."}), 400
            
        report_data = get_page_report(start_date, end_date)
        return jsonify({"success": True, "data": report_data})
    except Exception as e:
        import traceback
        print("\n" + "="*50)
        print("RAPORLAMA HATASI (PAGE REPORT):")
        traceback.print_exc()
        print("="*50 + "\n")
        return jsonify({"success": False, "error": str(e)}), 500
