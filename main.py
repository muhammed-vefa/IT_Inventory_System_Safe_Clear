import sys
import subprocess
def bootstrap():
 """Gerekli ktphaneleri kontrol eder ve eksikse ykler."""
 required = [
 ('flask', 'flask'), ('flask_cors', 'flask-cors'), ('pyodbc', 'pyodbc'),
 ('openpyxl', 'openpyxl'), ('pandas', 'pandas'), ('xlrd', 'xlrd'),
 ('werkzeug', 'werkzeug'), ('bs4', 'beautifulsoup4'), ('requests', 'requests'),
 ('fpdf', 'fpdf2'), ('dotenv', 'python-dotenv'), ('flask_limiter', 'flask-limiter'),
 ('jwt', 'pyjwt'), ('reportlab', 'reportlab'), ('waitress', 'waitress'),
 ('win32api', 'pywin32'), ('docx', 'python-docx')
 ]
 for mod_name, pkg_name in required:
 try:
 __import__(mod_name)
 except ImportError:
 subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_name])
bootstrap()
from flask import Flask, jsonify, send_from_directory, send_file, request
from flask_cors import CORS
from dotenv import load_dotenv
import os, logging, threading, time, datetime, openpyxl, json
from logging.handlers import RotatingFileHandler
if not os.path.exists('logs'): os.makedirs('logs')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
 handlers=[RotatingFileHandler('logs/system.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'),
logging.StreamHandler()])
load_dotenv()
from core.database_sql import get_db_connection, init_db
from core.excel_utils import read_excel_data
from core.utils import _clean, _get, _norm_key, _norm_pc_id
from core.extensions import limiter
# Modller
from modules.inventory_manager import inventory_manager_bp, _sync_peripherals
from modules.printer_manager import printer_manager_bp
from modules.document_service import document_service_bp
from modules.areas_manager import areas_manager_bp
from modules.notes_manager import notes_manager_bp
from modules.depot_manager import depot_manager_bp
from modules.user_manager import user_manager_bp
from modules.logs_manager import logs_manager_bp
from modules.mahal_manager import mahal_manager_bp
from modules.service_manager import service_manager_bp
from modules.bim_service import bim_service_bp
from modules.keyos_service import keyos_service_bp
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or 'SUPER_SECRET_KEY_123'
app.config['JSON_AS_ASCII'] = False
CORS(app)
limiter.init_app(app)
app.register_blueprint(inventory_manager_bp, url_prefix='/api/inventory')
app.register_blueprint(printer_manager_bp, url_prefix='/api/printers')
app.register_blueprint(document_service_bp, url_prefix='/api/documents')
app.register_blueprint(areas_manager_bp, url_prefix='/api/areas')
app.register_blueprint(notes_manager_bp, url_prefix='/api/notes')
app.register_blueprint(depot_manager_bp, url_prefix='/api/depot')
app.register_blueprint(user_manager_bp, url_prefix='/api/users')
app.register_blueprint(logs_manager_bp, url_prefix='/api/logs')
app.register_blueprint(mahal_manager_bp, url_prefix='/api/mahal')
app.register_blueprint(service_manager_bp, url_prefix='/api/service')
app.register_blueprint(bim_service_bp, url_prefix='/api/bim')
app.register_blueprint(keyos_service_bp, url_prefix='/api/keyos')
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
@app.route('/')
def index(): return send_file(os.path.join(BASE_DIR, 'index.html'))
@app.route('/style.css')
def serve_css(): return send_from_directory(BASE_DIR, 'style.css', mimetype='text/css')
@app.route('/frontend/<path:filename>')
def serve_frontend(filename): return send_from_directory(os.path.join(BASE_DIR, 'frontend'), filename)
def sync_excel_to_db_internal():
 from core.database_sql import get_db_connection, init_db
 from core.excel_utils import read_excel_data
 from core.utils import _clean, _norm_key, _get, _norm_pc_id
 import openpyxl

 stats = {"pc_synced": 0, "areas_synced": 0}
 def get_p(f): return os.path.join(BASE_DIR, 'database', 'ana_database', f)

 mt_path, env_path, alan_path, pr_path = get_p("mahal_telefon.xlsx"), get_p("envanter.xlsx"),
get_p("ORTAK_ALANLAR.xlsx"), get_p("yazclar.xlsx")

 init_db()
 conn = get_db_connection()

 # --- YEN PROFESYONEL SYNC MANTII ---
 try:
 from core.sync_manager import SyncManager
 sync_mgr = SyncManager(BASE_DIR)

 # 1. Mahaller & Telefonlar
 sync_mgr.sync_mahal_and_phones()

 # 2. Envanter (PC, Tablet, Siramatik)
 inv_stats = sync_mgr.sync_inventory()
 stats["pc_synced"] = sum(v for k,v in inv_stats.items() if k != 'skipped')

 # 3. Servis Kaytlar (Tarih Standartlatrma)
 sync_mgr.sync_service_records()

 except Exception as e:
 print(f"HATA: Yeni senkronizasyon srasnda bir sorun olutu: {e}")

 if os.path.exists(alan_path):
 try:
 conn.execute("DELETE FROM shared_areas")
 data = read_excel_data(alan_path, sheet_name=0)
 for r in data:
 name = _get(r, ['NAME', 'AD', 'ALAN ADI'])
 if name:
 conn.execute("INSERT INTO shared_areas (name, [user], password, path) VALUES (?,?,?,?)",
(name, _get(r, ['USER']), _get(r, ['PASSWORD', 'SIFRE']), _get(r, ['PATH', 'YOL'])))
 stats["areas_synced"] += 1
 conn.commit()
 except: pass
 conn.close()
 return stats
@app.route('/api/sync/all', methods=['POST'])
def sync_all():
 from modules.printer_manager import sync_printers_from_excel_internal
 from modules.depot_manager import sync_depot_from_excel_internal
 from modules.notes_manager import sync_kb_from_excel_internal
 results = []
 try:
 inv = sync_excel_to_db_internal()
 results.append(f"Envanter: {inv['pc_synced']} cihaz gncellendi.")
 results.append(f"Ortak Alanlar: {inv['areas_synced']} kayt gncellendi.")
 results.append(f"Yazclar: {sync_printers_from_excel_internal()} kayt senkronize edildi.")
 results.append(f"Depo: {sync_depot_from_excel_internal()} rn gncellendi.")
 results.append(f"Bilgi Bankas: {sync_kb_from_excel_internal()} kayt gncellendi.")
 return app.response_class(response=json.dumps({"success":True, "details":results}, ensure_ascii=False),
mimetype='application/json')
 except Exception as e:
 return jsonify({"success":False, "error":str(e)}), 500
if __name__ == '__main__':
 init_db()
 try:
 from waitress import serve
 serve(app, host='0.0.0.0', port=5000)
 except:
 app.run(host='0.0.0.0', port=5000)
