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

@printer_pages_bp.route('/available_dates', methods=['GET', 'OPTIONS'])
@require_auth
def get_available_dates():
    from core.database_sql import query_db
    try:
        # SQL Server'da sadece tarih kismini alip distinct yapmak cok daha performanslidir
        logs = query_db("SELECT DISTINCT CAST(timestamp AS DATE) as log_date FROM printer_page_logs ORDER BY log_date DESC")
        if not logs:
            return jsonify({"success": True, "data": []})
            
        unique_dates = []
        for log in logs:
            ts = log.get('log_date')
            if ts:
                if hasattr(ts, 'strftime'):
                    unique_dates.append(ts.strftime("%Y-%m-%d"))
                elif isinstance(ts, str):
                    unique_dates.append(ts[:10])
                    
        return jsonify({"success": True, "data": unique_dates})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@require_auth
def get_available_dates():
    from core.database_sql import query_db
    try:
        # Get unique dates from the logs (SQLite/SQL Server compatible cast or substring depending on DB)
        # Using a simple substring for datetime strings to get 'YYYY-MM-DD'
        logs = query_db("SELECT timestamp FROM printer_page_logs")
        if not logs:
            return jsonify({"success": True, "data": []})
            
        unique_dates = set()
        for log in logs:
            ts = log.get('timestamp')
            if ts:
                if hasattr(ts, 'strftime'):
                    unique_dates.add(ts.strftime("%Y-%m-%d"))
                elif isinstance(ts, str):
                    unique_dates.add(ts[:10])
                    
        sorted_dates = sorted(list(unique_dates), reverse=True)
        return jsonify({"success": True, "data": sorted_dates})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
