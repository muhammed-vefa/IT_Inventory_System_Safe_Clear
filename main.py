import sys
import subprocess
import os
import logging
import threading
import time
import datetime
import json
import openpyxl
from flask import Flask, jsonify, send_from_directory, send_file, request
from flask_cors import CORS
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

def bootstrap():
    """Gerekli kütüphaneleri kontrol eder ve eksikse yükler."""
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

# --- Imports after bootstrap ---
from core.database_sql import get_db_connection, init_db
from core.excel_utils import read_excel_data
from core.utils import _clean, _get, _norm_key, _norm_pc_id
from core.extensions import limiter

# Modules
from modules.inventory_manager import inventory_manager_bp
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

# Register Blueprints
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
def index():
    return send_file(os.path.join(BASE_DIR, 'index.html'))

@app.route('/style.css')
def serve_css():
    return send_from_directory(BASE_DIR, 'style.css', mimetype='text/css')

@app.route('/frontend/<path:filename>')
def serve_frontend(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'frontend'), filename)

def sync_excel_to_db_internal():
    stats = {"pc_synced": 0, "areas_synced": 0}
    def get_p(f): return os.path.join(BASE_DIR, 'database', 'ana_database', f)
    
    mt_path = get_p("mahal_telefon.xlsx")
    env_path = get_p("envanter.xlsx")
    alan_path = get_p("ORTAK_ALANLAR.xlsx")
    
    init_db()
    conn = get_db_connection()
    if not conn: return stats

    try:
        from core.sync_manager import SyncManager
        sync_mgr = SyncManager(BASE_DIR)
        sync_mgr.sync_mahal_and_phones()
        inv_stats = sync_mgr.sync_inventory()
        stats["pc_synced"] = sum(v for k,v in inv_stats.items() if k != 'skipped')
    except Exception as e:
        print(f"Sync error: {e}")

    conn.close()
    return stats

@app.route('/api/sync/all', methods=['POST'])
def sync_all():
    try:
        inv = sync_excel_to_db_internal()
        return jsonify({"success": True, "details": [f"Envanter güncellendi: {inv['pc_synced']}"]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists('logs'): os.makedirs('logs')
    init_db()
    try:
        from waitress import serve
        print("Waitress sunucusu baslatiliyor (0.0.0.0:5000)...")
        serve(app, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Waitress failed: {e}. Flask debug mode baslatiliyor...")
        app.run(host='0.0.0.0', port=5000)
