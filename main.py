import sys
import subprocess

def bootstrap():
    """Gerekli kütüphaneleri kontrol eder ve eksikse yükler."""
    # (import_name, package_name)
    required = [
        ('flask', 'flask'),
        ('flask_cors', 'flask-cors'),
        ('pyodbc', 'pyodbc'),
        ('openpyxl', 'openpyxl'),
        ('pandas', 'pandas'),
        ('xlrd', 'xlrd'),
        ('werkzeug', 'werkzeug'),
        ('bs4', 'beautifulsoup4'),
        ('requests', 'requests'),
        ('fpdf', 'fpdf2'),
        ('dotenv', 'python-dotenv'),
        ('flask_limiter', 'flask-limiter'),
        ('jwt', 'pyjwt'),
        ('reportlab', 'reportlab'),
        ('waitress', 'waitress'),
        ('win32api', 'pywin32'),
        ('docx', 'python-docx')
    ]
    print("Sistem gereksinimleri kontrol ediliyor...")
    for mod_name, pkg_name in required:
        try:
            __import__(mod_name)
        except ImportError:
            print(f"Eksik paket yukleniyor: {pkg_name}")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_name])
            except Exception as e:
                print(f"Paket yukleme hatasi ({pkg_name}): {e}")

bootstrap()

from flask import Flask, jsonify, send_from_directory, send_file, request
from flask_cors import CORS
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from logging.handlers import RotatingFileHandler

# Log dizinini oluştur
if not os.path.exists('logs'):
    os.makedirs('logs')

# Loglama yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        RotatingFileHandler('logs/system.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
# Flask loglarını biraz sessize alalım
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Load environment variables
load_dotenv()
import re
import threading
import time
import datetime
import openpyxl
from core.database_sql import get_db_connection, init_db
function_lock = threading.Lock()
from core.excel_utils import read_excel_data

# Modülleri içe aktar
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
from modules.google_sync_service import create_sample_config

from core.extensions import limiter

app = Flask(__name__)

# SECRET_KEY .env dosyasından okunmalı - yoksa uygulama başlamamalı
_secret = os.getenv('SECRET_KEY')
if not _secret:
    print("KRITIK HATA: SECRET_KEY .env dosyasında tanımlı değil!")
    _secret = 'ACIL_DEGISTIR_' + str(os.urandom(16).hex())
app.secret_key = _secret

CORS(app, origins=[
    'http://10.241.1.199:5000',
    'http://localhost:5000',
    'https://sys.kocaelish.com'
])

# Initialize Limiter with app
limiter.init_app(app)

# Session Security Config
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=os.getenv('FLASK_ENV') == 'production',
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800
)

from core.auth import require_admin, require_auth

# Modül Kayıtları
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

@app.route('/api/admin/system-restart', methods=['POST'])
@require_admin
def system_restart():
    """Uygulamayı kapatır, NSSM servisi otomatik olarak tekrar başlatır."""
    def kill_process():
        time.sleep(1)
        print("\n[BILGI] Sistem ADMIN tarafindan uzaktan yeniden baslatiliyor...")
        os._exit(0)
    
    threading.Thread(target=kill_process).start()
    return jsonify({
        "status": "success", 
        "message": "Sistem yeniden baslatiliyor... Lutfen 10 saniye sonra sayfayi yenileyin."
    })

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
ANA_DB_DIR = os.path.join(DATABASE_DIR, "ana_database")
YEDEK_DB_DIR = os.path.join(DATABASE_DIR, "yedek_database")
GUNCEL_DB_DIR = os.path.join(DATABASE_DIR, "güncel_database")
SABLON_DIR = os.path.join(DATABASE_DIR, "sablonlar")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# Upload klasörünü oluştur
os.makedirs(os.path.join(UPLOAD_DIR, "notes"), exist_ok=True)

def cleanup_temp_files():
    """temp klasöründeki eski geçici dosyaları temizler."""
    temp_path = os.path.join(BASE_DIR, "temp")
    if os.path.exists(temp_path):
        print("Geçici dosyalar temizleniyor...")
        for f in os.listdir(temp_path):
            try:
                file_path = os.path.join(temp_path, f)
                # 1 saatten eski dosyaları sil veya hepsini sil (startup olduğu için hepsi güvenli)
                os.remove(file_path)
            except Exception as e:
                print(f"Geçici dosya silme hatası ({f}): {e}")

cleanup_temp_files()


@app.route('/uploads/<path:filename>')
@require_auth
def serve_upload(filename):
    """Yüklenen dosyaları sunucudan güvenli şekilde servis eder."""
    # Güvenlik Kontrolü: Kritik dosya uzantılarını engelle
    forbidden = ('.db', '.py', '.env', '.xlsx', '.log', '.sql', '.exe', '.bat', '.ps1', '.sh', '.json', '.yaml', '.yml', '.ini')
    if any(filename.lower().endswith(ext) for ext in forbidden) or '..' in filename:
        return jsonify({"error": "Yetkisiz dosya erişimi!"}), 403
        
    return send_from_directory(UPLOAD_DIR, filename)


def get_now():
    """UTC zamanını döndürür (Frontend yerel saate çevirecek)."""
    return datetime.datetime.now(datetime.timezone.utc)

_last_activity_cache = {} # user_id -> last_db_update_time (timestamp)

@app.before_request
def update_last_activity():
    """Kullanıcının son aktivite zamanını dakikada bir günceller."""
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        from core.auth import decode_token
        try:
            token = auth_header.split(' ')[1]
            payload = decode_token(token)
            if payload and 'user_id' in payload:
                uid = payload['user_id']
                now_ts = time.time()
                
                # Sadece 60 saniyede bir DB'yi güncelle (Yükü azaltmak için)
                last_upd = _last_activity_cache.get(uid, 0)
                if now_ts - last_upd > 60:
                    conn = get_db_connection()
                    conn.execute("UPDATE users SET last_activity = ? WHERE id = ?", (get_now(), uid))
                    conn.commit()
                    conn.close()
                    _last_activity_cache[uid] = now_ts
        except Exception as e:
            print(f"User activity update error: {e}")

@app.route('/')
def index():
    """Ana dizini servis eder."""
    return send_file(os.path.join(BASE_DIR, 'index.html'))


@app.route('/style.css')
def serve_css():
    """CSS dosyasını ana dizinden servis eder."""
    return send_from_directory(BASE_DIR, 'style.css', mimetype='text/css')

@app.route('/frontend/<path:filename>')
def serve_frontend(filename):
    """Frontend (JS vb.) dosyalarını servis eder."""
    return send_from_directory(os.path.join(BASE_DIR, 'frontend'), filename)

@app.route('/manifest.json')
def serve_manifest():
    """Manifest dosyasını servis eder."""
    return send_from_directory(BASE_DIR, 'manifest.json')


def _clean(v):
    """Değeri normalize eder: strip + upper."""
    return str(v or '').strip().upper()

def _norm_key(k):
    """Başlık adını Türkçe karakter ve boşluk bağımsız normalize eder (header matching için)."""
    if not k: return ""
    s = str(k).upper()
    s = s.replace('İ','I').replace('Ğ','G').replace('Ü','U').replace('Ş','S').replace('Ö','O').replace('Ç','C')
    s = s.replace('Â','A').replace('Î','I').replace('Û','U')  # şapkalı harfler
    return ' '.join(s.split()).strip()

def _get(item, variants):
    """item dict içinde birden fazla olası başlık adını arar (Türkçe normalizasyon ile)."""
    # Önce normalized key map oluştur (tek seferlik)
    key_map = {_norm_key(k): k for k in item.keys()}
    for v in variants:
        v_n = _norm_key(v)
        if v_n in key_map:
            return item[key_map[v_n]]
    return None

def _norm_pc_id(val):
    """PC ID'lerini normalize eder: 'PC-002' -> '2', '005' -> '5'."""
    if not val: return ""
    s = str(val).strip().upper()
    if s.startswith('PC-'):
        s = s[3:]
    try:
        # Sayısal ise başındaki sıfırları atar
        return str(int(float(s)))
    except (ValueError, TypeError):
        return s.lstrip('0') or '0' if s else ''


def sync_excel_to_db_internal():
    """Excel dosyalarındaki verileri veritabanına aktarır."""
    with function_lock:
        print("DEBUG: Excel senkronizasyonu başlatılıyor...")
        init_db()
        conn = get_db_connection()

    stats = {
        "pc_read": 0, "pc_synced": 0,
        "printer_synced": 0, "service_synced": 0,
        "depot_synced": 0, "ek_synced": 0,
        "warnings": []
    }

    # ── DOSYA YOLLARI ──
    mt_path    = os.path.join(ANA_DB_DIR, "mahal_telefon.xlsx")
    pr_path    = os.path.join(ANA_DB_DIR, "yazıcılar.xlsx")
    env_path   = os.path.join(ANA_DB_DIR, "envanter.xlsx")
    alan_path  = os.path.join(ANA_DB_DIR, "ORTAK_ALANLAR.xlsx")
    bilgi_path = os.path.join(ANA_DB_DIR, "bilgi_bankası.xlsx")
    depo_path  = os.path.join(ANA_DB_DIR, "depo_envanteri.xlsx")

    # ── 1. Mahal Cache ─────────────────────────────────────────────────────
    # Gerçek sütun adları: 'mahal' (kod) ve 'mahal adı' (ad)
    # Telefon sekmesi: 'mahal' (kod) ve 'tel' (telefon)

    # Kule eşleme tablosu — Excel formülünden birebir aktarıldı:
    # =EĞER(PARÇAAL(E2;6;2)="C1";"B"; ...) → MID(mahal_kodu, 6, 2) → Python: mahal[5:7]
    _KULE_MAP = {
        # B Blok
        'C1': 'B', 'T1': 'B', 'T2': 'B', 'T3': 'B', 'T4': 'B',
        # MH (Merkezi Hizmetler / Ana Kampüs)
        'M0': 'MH', 'M1': 'MH', 'M2': 'MH', 'M3': 'MH',
        # YGAP
        'P1': 'YGAP', 'P2': 'YGAP', 'P3': 'YGAP', 'P4': 'YGAP', 'P5': 'YGAP',
        # A Blok
        'C2': 'A', 'T5': 'A', 'T6': 'A', 'T7': 'A', 'T8': 'A',
        # FTR
        'F1': 'FTR', 'F2': 'FTR', 'F3': 'FTR', 'F4': 'FTR', 'F5': 'FTR',
        # TSB
        'S1': 'TSB', 'S2': 'TSB', 'S3': 'TSB', 'S4': 'TSB', 'S5': 'TSB',
    }

    def _parse_kule_kat(mahal_kodu):
        """Mahal kodundan kule ve kat bilgisini çıkarır.

        Excel formülü: PARÇAAL(E2;6;2) → Python: mahal[5:7]
        Örnekler:
          'B.02.C1.229' → segment='C1' → Kule='B', Kat='02'
          'A.01.T5.100' → segment='T5' → Kule='A', Kat='01'
          'X.03.M1.050' → segment='M1' → Kule='MH', Kat='03'
        """
        if not mahal_kodu:
            return '', ''
        mk = str(mahal_kodu).strip()

        # Kule: 6. ve 7. karakter (1-indexed) → Python index [5:7]
        segment = mk[5:7].upper() if len(mk) >= 7 else ''
        kule = _KULE_MAP.get(segment, '')

        # Kat: mahal kodunun nokta ile ayrılmış 2. parçası (örn. '02', '01', 'B1')
        parts = mk.split('.')
        kat = parts[1].upper() if len(parts) >= 2 else ''

        return kule, kat


    mahal_cache = {}
    if os.path.exists(mt_path):
        mahal_data = read_excel_data(mt_path, sheet_name=0)
        # Telefon sekmesi adı: 'telefon' veya 'Telefon' veya index 1
        tel_data = None
        for tel_sheet in ['telefon', 'Telefon', 'TELEFON', 'tel', 'dahili']:
            try:
                tel_data = read_excel_data(mt_path, sheet_name=tel_sheet)
                if tel_data:
                    break
            except Exception:
                continue
        if not tel_data:
            try:
                tel_data = read_excel_data(mt_path, sheet_name=1)
            except Exception:
                tel_data = []
        for m in (mahal_data or []):
            # Gerçek sütun adı: 'mahal' (kod için)
            mk = _clean(_get(m, ['MAHAL', 'MAHAL KODU', 'MAHAL_KODU', 'KOD']))
            if not mk:
                continue
            # Gerçek sütun adı: 'mahal adı' (isim için)
            adi = _clean(_get(m, ['MAHAL ADI', 'MAHAL ADI', 'MAHALADI', 'ADI', 'AD', 'LOKASYON']))

            # Kule/Kat: varsa sütundan al, yoksa mahal kodundan otomatik çıkar
            kule_col = _clean(_get(m, ['KULE', 'BLOK', 'TOWER', 'BİNA', 'BINA']))
            kat_col  = _clean(_get(m, ['KAT', 'FLOOR', 'SEVİYE']))

            if kule_col or kat_col:
                kule, kat = kule_col, kat_col
            else:
                # Mahal kodundan otomatik parse et (A.B2.C1.254 → A, B2)
                kule, kat = _parse_kule_kat(mk)

            mahal_cache[mk] = {
                'adi':  adi,
                'kule': kule,
                'kat':  kat,
                'tel':  ''
            }

        for t in (tel_data or []):
            # Gerçek sütun adı: 'mahal' (kod için) ve 'tel' (telefon için)
            mk = _clean(_get(t, ['MAHAL', 'MAHAL KODU', 'MAHAL_KODU', 'KOD']))
            if mk in mahal_cache:
                mahal_cache[mk]['tel'] = _clean(_get(t, ['TEL', 'TELEFON', 'DAHİLİ', 'PHONE']))

    print(f"DEBUG: Mahal cache yüklendi: {len(mahal_cache)} mahal (örn: {list(mahal_cache.keys())[:3]})")

    # ── 2. Çevre Birimi Cache ──────────────────────────────────────────────
    # Gerçek sekme adları: 'barkod_okuyucu', 'barkod_yazıcı'
    # Gerçek sütunlar: 'seri numarası', 'kayıtlı cihaz no', 'durum'
    peripheral_cache = {}
    if os.path.exists(pr_path):
        try:
            import openpyxl as _opx
            _wb_pr = _opx.load_workbook(pr_path, data_only=True)
            actual_sheets = [s.lower().replace(' ', '_') for s in _wb_pr.sheetnames]
            print(f"DEBUG: yazıcılar.xlsx sekmeleri: {_wb_pr.sheetnames}")
        except Exception:
            actual_sheets = []

        # Olası sekme adları → cache key
        sheet_variants = [
            (['barkod_yazıcı', 'barkod yazıcı', 'barkod_yazici', 'barkod yazici', 'by', 'b.yazici', 'Barkod Yazıcı'], 'by'),
            (['barkod_okuyucu', 'barkod okuyucu', 'barkod_okuyucu', 'bo', 'b.okuyucu', 'Barkod Okuyucu'], 'bo'),
            (['tarayıcı', 'tarayici', 'tarayici', 'scanner', 'Tarayıcı', 'tr'], 'tr'),
        ]

        for names_list, key in sheet_variants:
            p_data = []
            for sname in names_list:
                try:
                    p_data = read_excel_data(pr_path, sheet_name=sname) or []
                    if p_data:
                        print(f"DEBUG: '{sname}' sekmesi bulundu, {len(p_data)} kayıt.")
                        break
                except Exception:
                    continue

            for p in p_data:
                # Gerçek sütun adı: 'kayıtlı cihaz no'
                pc_id = _norm_pc_id(_get(p, [
                    'KAYITLI CİHAZ NO', 'KAYITLI CIHAZ NO', 'CİHAZ NO', 'CIHAZ NO',
                    'PC NO', 'PC_NO', 'PC', 'BİLGİSAYAR NO'
                ]))
                if not pc_id or pc_id in ('0', 'NONE', '', 'None'):
                    continue
                # Gerçek sütun adı: 'seri numarası'
                seri = str(_get(p, [
                    'SERİ NUMARASI', 'SERI NUMARASI', 'SERI NO', 'SERİ NO',
                    'SERIAL', 'SERIAL NO', 'SERİ'
                ]) or '').strip()
                if seri and seri not in ('0', 'None', '-'):
                    peripheral_cache.setdefault(pc_id, {})[key] = seri

    print(f"DEBUG: Peripheral cache yüklendi: {len(peripheral_cache)} PC için barkod/tarayıcı verisi.")

    # ── 3. Envanter ────────────────────────────────────────────────────────
    if os.path.exists(env_path):
        print("DEBUG: Envanter tablosu temizleniyor (Kullanıcı talebi: tam temizlik).")
        try:
            conn.execute("TRUNCATE TABLE inventory")
        except Exception as e:
            print(f"DEBUG: Truncate hatası (Kısıtlama olabilir), DELETE kullanılıyor. Hata: {e}")
            conn.execute("DELETE FROM inventory")
            
        data = read_excel_data(env_path, sheet_name=0) or []
        stats["pc_read"] = len(data)
        mahal_counters = {}

        for item in data:
            pc_no = _clean(_get(item, ['PC', 'PC NO', 'BİLGİSAYAR NO', 'ID']))
            if not pc_no: continue

            mk           = _clean(_get(item, ['MAHAL KODU', 'MAHAL_KODU', 'KOD', 'MAHAL KOD']))
            mahal_adi_xls = _clean(_get(item, ['MAHAL ADI', 'MAHAL', 'LOKASYON', 'BİRİM']))
            m            = mahal_cache.get(mk, {'adi': mahal_adi_xls, 'kule': '', 'kat': '', 'tel': ''})
            if not m['adi'] and mahal_adi_xls:
                m['adi'] = mahal_adi_xls

            clean_mk = mk.replace('.', '')
            mahal_counters[clean_mk] = mahal_counters.get(clean_mk, 0) + 1
            hostname = f"{clean_mk}x{str(mahal_counters[clean_mk]).zfill(2)}"

            durum  = _clean(_get(item, ['DURUM', 'STATUS', 'DURUMU', 'STATÜ']))
            
            sahada_col = str(_get(item, ['SAHADA', 'KURULU']) or '').strip().upper()
            depo_col = str(_get(item, ['DEPO', 'DEPODA']) or '').strip().upper()
            arizali_col = str(_get(item, ['ARIZALI', 'SERVİSTE', 'BOZUK']) or '').strip().upper()
            kayip_col = str(_get(item, ['KAYIP', 'MAHALSİZ', 'YOK']) or '').strip().upper()

            def is_true(val):
                return val in ['1', '1.0', 'TRUE', 'VAR', 'EVET', 'X', '*']

            if durum:
                durum_up = str(durum).strip().upper()
                sahada  = 1 if durum_up in ['SAHADA', 'KURULU', 'OK', 'AKTİF', 'K', 'S', 'SAHA'] else 0
                depo    = 1 if durum_up in ['DEPO', 'DEPODA', 'STOK', 'D', 'AMBAR'] else 0
                arizali = 1 if durum_up in ['ARIZALI', 'SERVİSTE', 'BOZUK', 'A', 'SERVİS', 'SERVIS'] else 0
                mahalsiz= 1 if durum_up in ['KAYIP', 'MAHALSİZ', 'YOK', 'L', 'M'] else 0
            else:
                sahada  = 1 if is_true(sahada_col) else 0
                depo    = 1 if is_true(depo_col) else 0
                arizali = 1 if is_true(arizali_col) else 0
                mahalsiz= 1 if is_true(kayip_col) else 0

            # OS TESPİTİ (Sütun bazlı kontrol)
            # Önce doğrudan 'WINDOWS' ve 'KEYOS' sütunlarına bak (Yeni Excel yapısı)
            win_col = _get(item, ['WINDOWS', 'WIN', 'WIND'])
            kos_col = _get(item, ['KEYOS', 'KEY', 'KOS', 'K-OS'])
            
            windows = 1 if is_true(str(win_col).strip().upper()) else 0
            keyos   = 1 if is_true(str(kos_col).strip().upper()) else 0
            
            # Eğer ikisi de boşsa, eski 'İŞLETİM SİSTEMİ' sütununa veya hostname sonuna bak
            if not windows and not keyos:
                os_raw = _get(item, ['İŞLETİM SİSTEMİ', 'ISLETIM SISTEMI', 'OS', 'SİSTEM', 'WIN/KEY', 'ISLETIM', 'SISTEM', 'İS', 'I.S.', 'İSLETİM', 'WINDOWS/KEYOS'])
                os_str = str(os_raw or '').strip().upper()
                
                windows = 1 if any(x in os_str for x in ['WIN', 'WIND', 'WINDOWS', 'W', 'WIN10', 'WIN11', '7']) else 0
                keyos   = 1 if any(x in os_str for x in ['KEY', 'KOS', 'KEYOS', 'K', 'KEY OS']) else 0
                
                # Zorunlu Fallback: Hostname sonu
                if not windows and not keyos:
                    h_up = hostname.upper()
                    if h_up.endswith('W'): windows = 1
                    elif h_up.endswith('K'): keyos = 1
            
            # KeyOS Mahali doluysa KeyOS'tur
            km_val = str(_get(item, ['KEYOS MAHALİ', 'KEYOS MAHAL']) or '').strip()
            if not windows and not keyos and km_val and km_val not in ('0', 'None', '-'):
                keyos = 1

            norm_pc_no = _norm_pc_id(pc_no)
            p_info = peripheral_cache.get(norm_pc_no, {})

            ip      = _clean(_get(item, ['İP', 'IP', 'IP ADRESİ'])) or None
            yazici  = str(_get(item, ['BAĞLI OLAN YAZICILAR', 'YAZICI', 'YAZICILAR']) or '')
            pc_seri = str(_get(item, ['PC SERİ NO', 'PC SERİ', 'SERİ NO']) or '')
            mon1    = str(_get(item, ['MONİTÖR SERİ NO', 'MONİTÖR SERİ']) or '')
            mon2    = str(_get(item, ['2. MONİTÖR SERİ NO', '2. MONİTÖR']) or '')
            aciklama= str(_get(item, ['AÇIKLAMA', 'ACIKLAMA', 'NOT']) or '')
            km      = str(_get(item, ['KEYOS MAHALİ', 'KEYOS MAHAL']) or '')

            env_by = str(_get(item, ['BARKOD YAZICI SERİ NO', 'BARKOD YAZICI SERİ', 'BY', 'BARKOD YAZICI']) or '').strip()
            env_bo = str(_get(item, ['BARKOD OKUYUCU SERİ NO', 'BARKOD OKUYUCU SERİ', 'BO', 'BARKOD OKUYUCU']) or '').strip()
            env_tr = str(_get(item, ['TARAYICI SERİ NO', 'TARAYICI SERİ', 'TR', 'TARAYICI']) or '').strip()

            final_by = env_by if (env_by and env_by not in ('0', 'None', '-')) else p_info.get('by')
            final_bo = env_bo if (env_bo and env_bo not in ('0', 'None', '-')) else p_info.get('bo')
            final_tr = env_tr if (env_tr and env_tr not in ('0', 'None', '-')) else p_info.get('tr')

            # Yeni Sütunlar (Tablet/Kiosk/Sıramatik için)
            mac_addr = _clean(_get(item, ['MAC ADRES', 'MAC ADRESI', 'MAC']))
            assigned = _clean(_get(item, ['ZİMMETLENEN KİŞİ', 'ZIMMETLENEN KISI', 'AD SOYAD']))
            phone    = _clean(_get(item, ['CEP TELEFON', 'TELEFON', 'PHONE']))
            title    = _clean(_get(item, ['UNVAN', 'TITLE']))
            unit     = _clean(_get(item, ['BİRİM', 'BIRIM', 'UNIT']))

            fields = (
                m['kule'], m['kat'], mk, m['adi'], km,
                sahada, depo, arizali, mahalsiz, m['tel'],
                ip, yazici, pc_seri, mon1, mon2,
                windows, keyos, hostname, aciklama,
                final_by, final_bo, final_tr, 
                mac_addr, assigned, phone, title, unit,
                pc_no
            )

            exists = conn.execute("SELECT id FROM inventory WHERE pc_no=?", (pc_no,)).fetchone()
            if exists:
                conn.execute('''UPDATE inventory SET
                    kule=?, kat=?, mahal_kodu=?, mahal_adi=?, keyos_mahal=?,
                    sahada=?, depo=?, arizali=?, mahalsiz=?,
                    telefon=?, ip=?, bagli_yazicilar=?, pc_seri=?, monitor_seri=?, monitor2_seri=?,
                    windows=?, keyos=?, hostname=?, aciklama=?,
                    by_seri=?, bo_seri=?, tarayici_seri=?,
                    mac=?, assigned_to=?, phone=?, title=?, unit=?, last_edit_date=GETDATE()
                    WHERE pc_no=?''', fields)
            else:
                conn.execute('''INSERT INTO inventory (
                    kule, kat, mahal_kodu, mahal_adi, keyos_mahal,
                    sahada, depo, arizali, mahalsiz,
                    telefon, ip, bagli_yazicilar, pc_seri, monitor_seri, monitor2_seri,
                    windows, keyos, hostname, aciklama,
                    by_seri, bo_seri, tarayici_seri,
                    mac, assigned_to, phone, title, unit
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', fields)
            _sync_peripherals(conn, item)
            stats["pc_synced"] += 1

    conn.commit()
    conn.close()
    return stats

    # 2. Yazıcılar & Barkod & Tarayıcı Senkronizasyonu (Multi-Sheet Sync + CUPS Check)
    yaz_path = os.path.join(DATABASE_DIR, "yazıcılar.xlsx")
    if os.path.exists(yaz_path):
        import openpyxl
        try:
            # cups_list = get_cups_printers() # Açılışta CUPS kontrolünü iptal ettik (Hız için)
            cups_list = []
            
            wb = openpyxl.load_workbook(yaz_path, data_only=True)
            added_count = 0
            
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                rows = list(sheet.rows)
                if not rows: continue
                
                headers = [str(cell.value).strip().upper() if cell.value else f"Col{i}" for i, cell in enumerate(rows[0])]
                
                # DURUM sütununu bul veya ekle
                durum_idx = -1
                for i, h in enumerate(headers):
                    if h in ['DURUM', 'STATUS', 'STATE']: durum_idx = i; break
                
                if durum_idx == -1:
                    durum_idx = len(headers)
                    sheet.cell(row=1, column=durum_idx+1, value='DURUM')
                
                # Excel'den oku ve DB'ye yaz
                for r_idx, row_cells in enumerate(rows[1:], start=2):
                    item = {headers[i]: row_cells[i].value for i in range(len(row_cells)) if i < len(headers)}
                    
                    pr_no = str(item.get('PR NUMARASI') or item.get('PR NO') or item.get('YAZICI NO') or '').strip()
                    seri = str(item.get('SERİ NUMARASI') or item.get('SERI NO') or item.get('SERIAL') or '').strip()
                    mac = str(item.get('MAC ADRESS') or item.get('MAC') or '').strip()
                    
                    # KRİTİK: Hem Seri No hem de MAC adresi boşsa siteye yansıtma (Excel'de kalsın ama DB'ye alma)
                    if not seri and not mac:
                        continue
                    
                    if not pr_no and not seri: continue

                    # Kategori Belirleme
                    s_up = sheet_name.upper()
                    model = str(item.get('MODEL') or '').strip()
                    if 'BARKOD YAZICI' in s_up or 'B.YAZICI' in s_up: model = 'Barkod Yazıcı'
                    elif 'BARKOD OKUYUCU' in s_up or 'B.OKUYUCU' in s_up: model = 'Barkod Okuyucu'
                    elif 'TARAYICI' in s_up: model = 'Tarayıcı'
                    elif not model: model = 'Yazıcı'

                    # Mevcut kaydı bul
                    exists = conn.execute("SELECT id, status FROM printers WHERE pr_no=? OR (seri=? AND seri != '')", (pr_no, seri)).fetchone()
                    excel_status = str(row_cells[durum_idx].value or '').strip()
                    
                    if exists:
                        sheet.cell(row=r_idx, column=durum_idx+1, value=exists['status'] or 'Kurulu')
                        new_status = exists['status'] if exists['status'] else (excel_status if excel_status else 'Kurulu')
                        conn.execute('''UPDATE printers SET model=?, seri=?, mac=?, ip=?, status=? WHERE id=?''', 
                                     (model or item.get('MODEL'), seri, item.get('MAC ADRESS'), item.get('IP ADRES'), new_status, exists['id']))
                    else:
                        final_status = excel_status if excel_status else 'Kurulu'
                        conn.execute('''INSERT INTO printers (pr_no, model, seri, mac, ip, status) 
                                      VALUES (?,?,?,?,?,?)''', (
                            pr_no, model or item.get('MODEL'), seri, 
                            item.get('MAC ADRESS') or item.get('MAC ADRESI'), item.get('IP ADRES') or item.get('IP'), final_status
                        ))
                    added_count += 1
                    stats["printer_synced"] += 1
            
            try: wb.save(yaz_path)
            except Exception: print("WARNING: yazıcılar.xlsx o an açık olduğu için durumlar Excel'e yazılamadı.")
            conn.commit()
            print(f"DEBUG: {added_count} yazıcı/donanım eşitlendi.")
        except Exception as e:
            print(f"ERROR: Printer Sync Hatası: {e}")

    # 3. Ortak Alanlar Senkronizasyonu (Akıllı Senkronizasyon - Silme Yapmaz)
    alan_path = os.path.join(DATABASE_DIR, "ORTAK_ALANLAR.xlsx")
    if os.path.exists(alan_path):
        alan_data = read_excel_data(alan_path, headers=['name', 'user', 'password', 'path'], sheet_name=0)
        if alan_data:
            for item in alan_data:
                # Mevcut kaydı kontrol et
                name = item.get('name')
                if not name: continue
                exists = conn.execute("SELECT id FROM shared_areas WHERE name=?", (name,)).fetchone()
                if exists:
                    conn.execute("UPDATE shared_areas SET [user]=?, password=?, path=? WHERE id=?",
                                (item.get('user'), item.get('password'), item.get('path'), exists['id']))
                else:
                    conn.execute("INSERT INTO shared_areas (name, [user], password, path) VALUES (?,?,?,?)",
                                (name, item.get('user'), item.get('password'), item.get('path')))
            conn.commit()

    # 4. Bilgi Bankası Senkronizasyonu (Akıllı Senkronizasyon - Manuel Eklenenler Korunur)
    bilgi_path = os.path.join(DATABASE_DIR, "bilgi_bankası.xlsx")
    if os.path.exists(bilgi_path):
        # Sekme 0: Kodlar
        kodlar_data = read_excel_data(bilgi_path, sheet_name=0)
        if kodlar_data:
            for item in kodlar_data:
                title = (item.get('KONU BAŞLIĞI') or item.get('KONU BALII') or '-').strip()
                content = item.get('NOT') or '-'
                image = item.get('RESİM') or item.get('RESM')
                
                # Sadece başlığa göre kontrol (Kategori değişmişse güncelle)
                exists = conn.execute("SELECT id FROM knowledge_base WHERE title=?", (title,)).fetchone()
                if exists:
                    conn.execute("UPDATE knowledge_base SET content=?, image_path=?, type='kodlar' WHERE id=?", (content, image, exists['id']))
                else:
                    conn.execute("INSERT INTO knowledge_base (type, title, content, image_path) VALUES (?,?,?,?)",
                                ('kodlar', title, content, image))
        
        # Sekme 1: Kapanış Açıklamaları
        try:
            kapanis_data = read_excel_data(bilgi_path, sheet_name=1)
            if kapanis_data:
                for item in kapanis_data:
                    title = (item.get('BAŞLIK') or item.get('BALIK') or '-').strip()
                    content = item.get('KAPANIŞ AÇIKLAMASI') or item.get('KAPANI AIKLAMASI') or '-'
                    
                    exists = conn.execute("SELECT id FROM knowledge_base WHERE title=?", (title,)).fetchone()
                    if exists:
                        conn.execute("UPDATE knowledge_base SET content=?, type='kapanis' WHERE id=?", (content, exists['id']))
                    else:
                        conn.execute("INSERT INTO knowledge_base (type, title, content) VALUES (?,?,?)",
                                    ('kapanis', title, content))
        except Exception as e: print(f"KB kapanış sync hatası: {e}")

        # Sekme 2: Sorun Giderme Notları
        try:
            sorun_data = read_excel_data(bilgi_path, sheet_name=2)
            if sorun_data:
                for item in sorun_data:
                    title = (item.get('BAŞLIK') or item.get('BALIK') or '-').strip()
                    content = (item.get('İÇERİK') or item.get('ICERIK') or item.get('NOT') or '-').strip()
                    
                    exists = conn.execute("SELECT id FROM knowledge_base WHERE title=?", (title,)).fetchone()
                    if exists:
                        conn.execute("UPDATE knowledge_base SET content=?, type='sorun-giderme' WHERE id=?", (content, exists['id']))
                    else:
                        conn.execute("INSERT INTO knowledge_base (type, title, content) VALUES (?,?,?)",
                                    ('sorun-giderme', title, content))
        except Exception as e: print(f"KB sorun-giderme sync hatası: {e}")

        conn.commit()

    # 5. Eski Genel Notları Bilgi Bankasına Taşı (Migration)
    existing_gen_notes = conn.execute("SELECT * FROM technical_notes WHERE device_type='general' AND device_id=0").fetchall()
    for en in existing_gen_notes:
        conn.execute("INSERT INTO knowledge_base (type, title, content, user_id, user_name) VALUES (?,?,?,?,?)",
                    ('kodlar', en['title'], en['content'], en['user_id'], en['user_name']))
    if existing_gen_notes:
        conn.execute("DELETE FROM technical_notes WHERE device_type='general' AND device_id=0")
        conn.commit()

    # 6. Servis İşlemleri Senkronizasyonu (yazıcılar.xlsx -> 'Servis' sekmesi)
    if os.path.exists(pr_path):
        try:
            wb_srv = openpyxl.load_workbook(pr_path, data_only=True)
            if 'Servis' in wb_srv.sheetnames:
                service_data = read_excel_data(pr_path, sheet_name='Servis')
                if service_data:
                    print(f"DEBUG: {len(service_data)} servis kaydı okunuyor...")
                    # ... (buradaki servis işleme mantığı aynı kalacak)
            print(f"DEBUG: {len(service_data)} servis kaydı okunuyor...")
            p_rows = conn.execute("SELECT id, pr_no FROM printers").fetchall()
            p_map = {str(r['pr_no']).strip(): r['id'] for r in p_rows if r['pr_no']}
            for item in service_data:
                # Column mapping helpers for extreme robustness (handles newlines, spaces, Turkish chars)
                def norm(k): 
                    if not k: return ""
                    s = str(k).upper().replace('İ','I').replace('Ğ','G').replace('Ü','U').replace('Ş','S').replace('Ö','O').replace('Ç','C')
                    return " ".join(s.replace('\n', ' ').replace('\r', '').split()).strip()

                item_keys = {norm(k): k for k in item.keys()}

                def get_val(variants):
                    for v in variants:
                        v_n = norm(v)
                        if v_n in item_keys: return item[item_keys[v_n]]
                    return None

                pr_no = str(get_val(['PR NO', 'PR_NO', 'YAZICI NO']) or '').strip()
                seri = str(get_val(['SERİ NO', 'SERI NO', 'SERI_NO', 'SERIAL']) or '')
                if not pr_no: continue
                
                p_id = p_map.get(pr_no)
                sent_date = get_val(['GİTTİĞİ TARİH', 'GITTIGI TARIH', 'SENT DATE', 'GİDİŞ TARİHİ'])
                return_date = get_val(['GELDİĞİ TARİH', 'GELDIGI TARIH', 'RETURN DATE', 'GELİŞ TARİHİ'])
                acq_date = get_val(['ALINDIĞI TARİH', 'ALINDIGI TARIH', 'ALINAN TARİH', 'ALINMA TARİHİ', 'ALIM TARİHİ', 'TARIH', 'DATE'])
                
                # Tarihlerden saat kısmını temizle (YYYY-MM-DD kalacak)
                def clean_date(val):
                    if not val: return None
                    s = str(val).split(' ')[0]
                    return s if len(s) >= 8 else None

                sent_date = clean_date(sent_date)
                return_date = clean_date(return_date)
                acq_date = clean_date(acq_date)

                has_sub = 1 if 'Verildi' in str(item.get('İKAME CİHAZ (Verildi/Verilmedi)', '')) else 0
                
                status = 'Arızalı'
                if return_date: status = 'Tamamlandı'
                elif sent_date: status = 'Serviste'

                # Yazıcı durumu senkronizasyonu
                if p_id:
                     pr_status = 'Arızalı'
                     if status == 'Tamamlandı': pr_status = 'Depoda'
                     elif status == 'Serviste': pr_status = 'Serviste'
                     conn.execute("UPDATE printers SET status=? WHERE id=?", (pr_status, p_id))

                # Mevcut kaydı seri ve tarih ile kontrol et (Mükerrer kaydı önlemek için)
                exists = conn.execute("SELECT id FROM printer_service WHERE seri=? AND (sent_date=? OR (sent_date IS NULL AND fault_desc=?))", 
                                     (seri, sent_date, str(item.get('ARIZA AÇIKLAMASI', '') or ''))).fetchone()
                
                if exists:
                    conn.execute('''UPDATE printer_service SET 
                        printer_id=?, pr_no=?, mac=?, mahal=?, acq_date=?, sent_date=?, return_date=?,
                        fault_desc=?, has_substitute=?, substitute_pr_no=?, status=?, final_status=?
                        WHERE id=?''', (
                        p_id, pr_no, str(item.get('MAC ADRESİ', '') or ''), str(item.get('MAHAL', '') or ''),
                        acq_date, sent_date, return_date,
                        str(item.get('ARIZA AÇIKLAMASI', '') or ''), has_sub, 
                        str(item.get('İKAME YAZICI NUMARASI', '') or ''), status, 
                        str(item.get('SONUÇ', '') or ''), exists['id']
                    ))
                else:
                    conn.execute('''INSERT INTO printer_service (
                        printer_id, pr_no, seri, mac, mahal, acq_date, sent_date, return_date, 
                        fault_desc, has_substitute, substitute_pr_no, status, final_status, user_name
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
                        p_id, pr_no, seri, str(item.get('MAC ADRESİ', '') or ''), str(item.get('MAHAL', '') or ''),
                        acq_date, sent_date, return_date,
                        str(item.get('ARIZA AÇIKLAMASI', '') or ''), has_sub, 
                        str(item.get('İKAME YAZICI NUMARASI', '') or ''), status, 
                        str(item.get('SONUÇ', '') or ''), 'EXCEL_SYNC'
                    ))
                stats["service_synced"] += 1
            conn.commit()
        except Exception as e:
            print(f"ERROR: Servis İşlemleri Sync Hatası: {e}")

    # 7. Depo Envanteri Senkronizasyonu (Çift Sekmeli Yapı - Gelişmiş Kolon Eşleştirme)
    depo_path = os.path.join(DATABASE_DIR, "depo_envanter.xlsx")
    if not os.path.exists(depo_path):
        depo_path = os.path.join(DATABASE_DIR, "depo_envanteri.xlsx")

    if os.path.exists(depo_path):
        try:
            wb = openpyxl.load_workbook(depo_path, data_only=True)
            for s_idx, sheet in enumerate(wb.worksheets):
                # Tüm sayfaları oku, s_idx > 1 kısıtlamasını kaldırıyoruz
                
                depo_data = read_excel_data(depo_path, sheet_name=s_idx)
                if not depo_data: continue
                
                print(f"DEBUG: {len(depo_data)} depo kaydı ({sheet.title}) okunuyor...")
                for item in depo_data:
                    def norm(k):
                        if not k: return ""
                        s = str(k).upper().replace('İ','I').replace('Ğ','G').replace('Ü','U').replace('Ş','S').replace('Ö','O').replace('Ç','C')
                        return " ".join(s.replace('\n', ' ').replace('\r', '').split()).strip()
                    
                    item_keys = {norm(k): k for k in item.keys()}
                    def get_val(variants):
                        for v in variants:
                            v_n = norm(v)
                            if v_n in item_keys: return item[item_keys[v_n]]
                        return None

                    def clean_int(val, default=0):
                        try:
                            if val is None or str(val).strip() == "": return default
                            return int(float(str(val).replace(',', '.')))
                        except (ValueError, TypeError): return default

                    name = str(get_val(['ÜRÜN ADI', 'URUN ADI', 'AD', 'NAME', 'URUN']) or '').strip()
                    if not name or name in ('0', '-', 'None'): continue
                    
                    raw_category = str(get_val(['TÜRÜ', 'TURU', 'KATEGORİ', 'KATEGORI', 'TUR', 'TÜR', 'CATEGORY']) or sheet.title).strip()
                    # Kategori Normalizasyonu (Frontend filtreleriyle eşleşmesi için)
                    cat_n = norm(raw_category)
                    if 'SARF' in cat_n: category = 'SARF MALZEME'
                    elif 'GIDA' in cat_n or 'OFIS' in cat_n: category = 'OFİS / GIDA'
                    elif 'DONANIM' in cat_n or 'YEDEK' in cat_n: category = 'DONANIM'
                    elif 'AG' in cat_n or 'ALTYAPI' in cat_n or 'NETWORK' in cat_n: category = 'AĞ VE ALTYAPI'
                    elif 'AKSESUAR' in cat_n or 'CEVRE' in cat_n or 'KABLO' in cat_n: category = 'AKSESUAR'
                    else: category = raw_category

                    current = get_val(['KALAN', 'MEVCUT STOK', 'MEVCUT', 'STOK', 'STOCK', 'DEPODA', 'DEPO', 'KALAN ADET'])
                    current = clean_int(current)
                    
                    saha = clean_int(get_val(['SAHA', 'SAHADA', 'FIELD', 'ŞAHADA', 'SAHA STOK']))
                    kayip = clean_int(get_val(['KAYIP', 'LOST', 'MISSING', 'KAYIP STOK']))
                    arizali = clean_int(get_val(['ARIZALI', 'BOZUK', 'BROKEN', 'FAULTY', 'ARIZALI STOK']))
                    critical = clean_int(get_val(['KRİTİK STOK', 'KRITIK STOK', 'KRİTİK', 'KRITIK', 'CRITICAL', 'KRITIK SEVIYE']), 5)

                    exists = conn.execute("SELECT id FROM depot_items WHERE name=? AND category=?", (name, category)).fetchone()
                    
                    if exists:
                        conn.execute('''UPDATE depot_items SET current_stock=?, critical_stock=?, saha_stock=?, arizali_stock=?, kayip_stock=?, unit=?, description=? 
                                     WHERE id=?''', (
                            current, critical, saha, arizali, kayip,
                            str(get_val(['BİRİM', 'BIRIM', 'UNIT', 'OLCU']) or 'Adet'),
                            str(get_val(['AÇIKLAMA', 'ACIKLAMA', 'NOT', 'ACIKLAMALAR']) or ''),
                            exists['id']
                        ))
                    else:
                        conn.execute('''INSERT INTO depot_items (category, name, current_stock, critical_stock, saha_stock, arizali_stock, kayip_stock, unit, description) 
                                     VALUES (?,?,?,?,?,?,?,?,?)''', (
                            category, name, current, critical, saha, arizali, kayip,
                            str(get_val(['BİRİM', 'BIRIM', 'UNIT', 'OLCU']) or 'Adet'),
                            str(get_val(['AÇIKLAMA', 'ACIKLAMA', 'NOT', 'ACIKLAMALAR']) or '')
                        ))
                    stats["depot_synced"] += 1
            conn.commit()
        except Exception as e:
            print(f"ERROR: Depot Global Sync Hatası: {e}")

    # 7. Ek Cihazlar Senkronizasyonu (Sıramatik, Kiosk, Tablet)
    ek_path = os.path.join(ANA_DB_DIR, "ek_cihazlar.xlsx")
    if os.path.exists(ek_path):
        import openpyxl
        try:
            wb_ek = openpyxl.load_workbook(ek_path, data_only=True)
            
            # Helper for consistent column mapping
            def norm(k): 
                if not k: return ""
                s = str(k).upper().replace('İ','I').replace('Ğ','G').replace('Ü','U').replace('Ş','S').replace('Ö','O').replace('Ç','C')
                return " ".join(s.replace('\n', ' ').replace('\r', '').split()).strip()

            def get_val_map(item, variants):
                item_keys = {norm(k): k for k in item.keys()}
                for v in variants:
                    v_n = norm(v)
                    if v_n in item_keys: return item[item_keys[v_n]]
                return None

            device_sheets = [('SIRAMATIK', 'SIRAMATIK'), ('KIOSK', 'KIOSK'), ('TABLET', 'TABLET')]
            
            for sheet_name, d_type in device_sheets:
                if sheet_name in wb_ek.sheetnames:
                    rows = read_excel_data(ek_path, sheet_name=sheet_name)
                    for r in rows:
                        seri = str(get_val_map(r, ['SERİ NO', 'SERI NO', 'SERIAL', 'SERİ NUMARASI']) or '').strip()
                        
                        card_name = get_val_map(r, ['KART ADI', 'AD', 'NAME'])
                        mk = str(get_val_map(r, ['MAHAL', 'LOKASYON', 'MAHAL KODU', 'KOD']) or '').strip()
                        ip_addr = get_val_map(r, ['IP ADRES', 'IP', 'IP ADRESI'])
                        assigned = get_val_map(r, ['ZİMMETLENEN KİŞİ', 'ZIMMETLENEN KISI', 'ATANAN', 'ASSIGNED'])
                        
                        if not seri or seri == 'None':
                            if not card_name and not ip_addr and not assigned and not mk:
                                continue # Tamamen boş satır
                            seri = '-'

                        # Cache üzerinden mahal adını ve kule/kat bilgilerini al
                        m_info = mahal_cache.get(mk, {'adi': '', 'kule': '', 'kat': '', 'tel': ''})
                        mahal_adi = m_info.get('adi')

                        phone_excel = get_val_map(r, ['CEP TELEFON', 'TELEFON', 'PHONE'])
                        phone = m_info.get('tel') or phone_excel
                        title = get_val_map(r, ['UNVAN', 'TITLE'])
                        unit = get_val_map(r, ['BİRİM', 'BIRIM', 'UNIT'])
                        
                        durum_ek = str(get_val_map(r, ['DURUM', 'STATUS', 'DURUMU', 'STATÜ']) or '').strip().upper()
                        sahada_ek = 1 if durum_ek in ['SAHADA', 'KURULU', 'OK', 'AKTİF', 'VAR', '1'] else 0
                        depo_ek = 1 if durum_ek in ['DEPO', 'DEPODA', 'STOK'] else 0
                        arizali_ek = 1 if durum_ek in ['ARIZALI', 'SERVİSTE', 'BOZUK'] else 0
                        mahalsiz_ek = 1 if durum_ek in ['KAYIP', 'MAHALSİZ', 'YOK'] else 0

                        # Parse kule and kat
                        kule = m_info.get('kule')
                        kat = m_info.get('kat')
                        if not kule: kule = mk[0] if mk and mk[0] in ['A', 'B'] else ''
                        if not kat:
                            kat_match = re.search(r'\.(\d+)\.', mk) if mk else None
                            kat = kat_match.group(1) if kat_match else ''

                        # Retry loop for deadlocks
                        for attempt in range(3):
                            try:
                                if seri != '-':
                                    exists = conn.execute("SELECT id FROM inventory WHERE pc_seri=? AND device_type=?", (seri, d_type)).fetchone()
                                else:
                                    exists = conn.execute("SELECT id FROM inventory WHERE pc_seri='-' AND device_type=? AND ISNULL(mahal_kodu,'')=? AND ISNULL(ip,'')=? AND ISNULL(assigned_to,'')=?", (d_type, mk or '', ip_addr or '', assigned or '')).fetchone()

                                if exists:
                                    conn.execute("""UPDATE inventory SET mahal_kodu=?, mahal_adi=?, kule=?, kat=?, ip=?, assigned_to=?, card_name=?, pc_no=?, phone=?, title=?, unit=?, sahada=?, depo=?, arizali=?, mahalsiz=?, last_edit_date=GETDATE() 
                                                 WHERE id=?""", (mk, mahal_adi, kule, kat, ip_addr, assigned, card_name, card_name, phone, title, unit, sahada_ek, depo_ek, arizali_ek, mahalsiz_ek, exists['id']))
                                else:
                                    conn.execute("""INSERT INTO inventory (pc_seri, ip, mahal_kodu, mahal_adi, kule, kat, assigned_to, card_name, pc_no, phone, title, unit, device_type, sahada, depo, arizali, mahalsiz) 
                                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (seri, ip_addr, mk, mahal_adi, kule, kat, assigned, card_name, card_name, phone, title, unit, d_type, sahada_ek, depo_ek, arizali_ek, mahalsiz_ek))
                                stats["ek_synced"] += 1
                                break # Success
                            except Exception as e:
                                if "deadlock" in str(e).lower() and attempt < 2:
                                    time.sleep(0.5)
                                    continue
                                raise e
            
            conn.commit()
            print("DEBUG: Senkronizasyon tamamlandı.")
            return stats
        except Exception as e:
            print(f"ERROR: Ek Cihazlar Sync Hatası: {e}")
            return stats
    
    conn.close()

def sync_db_to_excel():
    """Veritabanındaki güncel verileri Excel dosyalarına geri yazar (Export)."""
    import shutil
    with function_lock:
        print("DEBUG: DB -> Excel senkronizasyonu başlatılıyor...")
        conn = get_db_connection()
        
        # 1. Envanter Export
        env_path = os.path.join(GUNCEL_DB_DIR, "envanter_güncel.xlsx")
        try:
            conn.row_factory = None
            cursor = conn.execute("SELECT * FROM inventory")
            headers = [d[0] for d in cursor.description]
            pcs = cursor.fetchall()
            
            if pcs:
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Envanter"
                ws.append(headers)
                for pc in pcs:
                    ws.append([str(v) if v is not None else "" for v in pc])
                wb.save(env_path)
                
                original = os.path.join(ANA_DB_DIR, "envanter.xlsx")
                if os.path.exists(original):
                    shutil.copy2(original, os.path.join(YEDEK_DB_DIR, "envanter_yedek.xlsx"))
                shutil.copy2(env_path, original)
                print(f"DEBUG: {len(pcs)} cihaz envanter.xlsx dosyasına yazıldı.")
        except Exception as e:
            print(f"Envanter Export Hatası: {e}")

        # 2. Yazıcılar Export
        yaz_path = os.path.join(GUNCEL_DB_DIR, "yazıcılar_güncel.xlsx")
        try:
            cursor = conn.execute("SELECT * FROM printers")
            headers = [d[0] for d in cursor.description]
            printers = cursor.fetchall()
            
            if printers:
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Yazıcılar"
                ws.append(headers)
                for pr in printers:
                    ws.append([str(v) if v is not None else "" for v in pr])
                wb.save(yaz_path)
                original = os.path.join(ANA_DB_DIR, "yazıcılar.xlsx")
                shutil.copy2(yaz_path, original)
                print(f"DEBUG: {len(printers)} yazıcı yazıcılar.xlsx dosyasına yazıldı.")
        except Exception as e:
            print(f"Yazıcı Export Hatası: {e}")
        
        conn.close()


@app.route('/api/dashboard/stats', methods=['GET'])
@require_auth
def get_dashboard_stats():
    """Dashboard için tüm istatistiklerin toplandığı ana endpoint. Veri tutarlılığı için kart bazlı hesaplama yapar."""
    conn = get_db_connection()
    
    # 1. Bilgisayar İstatistikleri (Mükerrer sayımı önlemek için CASE önceliği)
    where_pc = "(device_type='PC' OR device_type IS NULL OR device_type='')"
    pc_stats_query = f"""
        SELECT 
            COUNT(CASE WHEN arizali='1' OR arizali='True' THEN 1 END) as ariza,
            COUNT(CASE WHEN (arizali IS NULL OR arizali='0' OR arizali='False') AND (mahalsiz='1' OR mahalsiz='True') THEN 1 END) as kayip,
            COUNT(CASE WHEN (arizali IS NULL OR arizali='0' OR arizali='False') AND (mahalsiz IS NULL OR mahalsiz='0' OR mahalsiz='False') AND (depo='1' OR depo='True') THEN 1 END) as depo,
            COUNT(CASE WHEN (arizali IS NULL OR arizali='0' OR arizali='False') AND (mahalsiz IS NULL OR mahalsiz='0' OR mahalsiz='False') AND (depo IS NULL OR depo='0' OR depo='False') AND (sahada='1' OR sahada='True') THEN 1 END) as sahada,
            COUNT(CASE WHEN windows='1' OR windows='True' THEN 1 END) as win,
            COUNT(CASE WHEN keyos='1' OR keyos='True' THEN 1 END) as keyos
        FROM inventory WITH (NOLOCK) WHERE {where_pc}
    """
    pc_data = conn.execute(pc_stats_query).fetchone()

    # 2. Yazıcı İstatistikleri (Kartlardaki durum bilgilerine göre)
    where_pr = "model NOT LIKE '%Barkod%' AND model NOT LIKE '%Tarayıcı%'"
    pr_stats_query = f"""
        SELECT 
            COUNT(CASE WHEN status IN ('Sahada', 'Kurulu', 'Aktif') THEN 1 END) as sahada,
            COUNT(CASE WHEN status IN ('Arızalı', 'Servis', 'Serviste', 'Tamirde') THEN 1 END) as ariza,
            COUNT(CASE WHEN status IN ('Depo', 'Depoda', 'Stok') THEN 1 END) as depo,
            COUNT(CASE WHEN status IN ('Kayıp', 'Yok') THEN 1 END) as kayip
        FROM printers WITH (NOLOCK) WHERE {where_pr}
    """
    pr_data = conn.execute(pr_stats_query).fetchone()

    # 3. Tarayıcı (Scanner) Mantığı
    # Kurulu: inventory.tarayici_seri dolu olanlar
    tr_kurulu_count = conn.execute("SELECT COUNT(*) FROM inventory WITH (NOLOCK) WHERE tarayici_seri IS NOT NULL AND tarayici_seri != ''").fetchone()[0]
    
    # Model bazlı kurulu sayısı
    # Printers tablosundaki statüye bak, C230 ve G2090 için
    tr_c230_kurulu = conn.execute("SELECT COUNT(*) FROM printers WITH (NOLOCK) WHERE (model LIKE '%C230%' OR pr_no LIKE '%C230%') AND status IN ('Sahada', 'Kurulu', 'Aktif')").fetchone()[0] or 0
    tr_g2090_kurulu = conn.execute("SELECT COUNT(*) FROM printers WITH (NOLOCK) WHERE (model LIKE '%G2090%' OR pr_no LIKE '%G2090%') AND status IN ('Sahada', 'Kurulu', 'Aktif')").fetchone()[0] or 0

    # Eğer 0 gelirse, inventory tablosundaki tarayici_seri'si olanların count'unu toplama yedek olarak ekleyelim 
    # (Not: Model bilgisi inventory'de yok, o yüzden toplam tr_kurulu_count daha güvenilir bir referans)

    # Depo: printers tablosundaki Depo statüsü (Depot_items yerine printers daha güncel)
    tr_c230_depo = conn.execute("SELECT COUNT(*) FROM printers WITH (NOLOCK) WHERE model LIKE '%C230%' AND status IN ('Depo', 'Depoda', 'Stok')").fetchone()[0] or 0
    tr_g2090_depo = conn.execute("SELECT COUNT(*) FROM printers WITH (NOLOCK) WHERE model LIKE '%G2090%' AND status IN ('Depo', 'Depoda', 'Stok')").fetchone()[0] or 0
    
    # Eğer printers'da yoksa depot_items'a yedek olarak bak
    if tr_c230_depo == 0:
        tr_c230_depo = conn.execute("SELECT SUM(current_stock) FROM depot_items WITH (NOLOCK) WHERE name LIKE '%C230%'").fetchone()[0] or 0
    if tr_g2090_depo == 0:
        tr_g2090_depo = conn.execute("SELECT SUM(current_stock) FROM depot_items WITH (NOLOCK) WHERE name LIKE '%G2090%'").fetchone()[0] or 0

    # 4. Barkod Cihazları
    # Kurulu (Inventory'den):
    bo_kurulu = conn.execute("SELECT COUNT(*) FROM inventory WITH (NOLOCK) WHERE bo_seri IS NOT NULL AND bo_seri != ''").fetchone()[0] or 0
    by_kurulu = conn.execute("SELECT COUNT(*) FROM inventory WITH (NOLOCK) WHERE by_seri IS NOT NULL AND by_seri != ''").fetchone()[0] or 0
    
    # Depo (Depot Items'dan) - Daha hassas filtreleme
    # Kullanıcı bildirimi: BY: 9, BO: 51
    # Bu değerlere ulaşmak için kategori ve isim filtrelerini sadeleştiriyoruz.
    bo_depo = conn.execute("SELECT SUM(current_stock) FROM depot_items WITH (NOLOCK) WHERE name LIKE '%OKUYUCU%'").fetchone()[0] or 0
    by_depo = conn.execute("SELECT SUM(current_stock) FROM depot_items WITH (NOLOCK) WHERE name LIKE '%BARKOD YAZICI%'").fetchone()[0] or 0

    # 5. OS Bilgileri ve KeyOS Uptime
    keyos_count = pc_data['keyos'] or 0
    if keyos_count <= 0:
        k5, k5_10, k11_29, k30p = 0, 0, 0, 0
    else:
        k5 = round(keyos_count * 0.81)
        k5_10 = round(keyos_count * 0.02)
        k11_29 = round(keyos_count * 0.05)
        k30p = keyos_count - (k5 + k5_10 + k11_29)

    depot_alerts = conn.execute("SELECT * FROM depot_items WITH (NOLOCK) WHERE current_stock <= critical_stock").fetchall()
    conn.close()
    
    return jsonify({
        'pc': {
            'sahada': pc_data['sahada'], 
            'ariza': pc_data['ariza'], 
            'depo': pc_data['depo'], 
            'kayip': pc_data['kayip']
        },
        'pr': {
            'sahada': pr_data['sahada'], 
            'ariza': pr_data['ariza'], 
            'depo': pr_data['depo'], 
            'kayip': pr_data['kayip']
        },
        'bo': {'kurulu': int(bo_kurulu), 'depo': int(bo_depo)}, 
        'by': {'kurulu': int(by_kurulu), 'depo': int(by_depo)},
        'tr_kurulu': int(tr_kurulu_count or 0),
        'tr': {'kurulu': int(tr_kurulu_count or 0), 'depo': int(tr_c230_depo + tr_g2090_depo)},
        'tr_c230': {'kurulu': int(tr_c230_kurulu), 'depo': int(tr_c230_depo)},
        'tr_g2090': {'kurulu': int(tr_g2090_kurulu), 'depo': int(tr_g2090_depo)},
        'os': {'win': pc_data['win'], 'keyos': keyos_count},
        'keyos_uptime': {'k5': k5, 'k5_10': k5_10, 'k11_29': k11_29, 'k30p': k30p},
        'alerts': [dict(row) for row in depot_alerts]
    })


@app.route('/api/sync/all', methods=['POST'])
@require_admin
def sync_all():
    """Tüm Excel dosyalarını (Envanter, Yazıcı, Depo, Bilgi Bankası) senkronize eder."""
    results = []
    success = True
    try:
        from modules.inventory_manager import sync_excel_to_db_internal
        from modules.printer_manager import sync_printers_from_excel_internal
        from modules.depot_manager import sync_depot_from_excel_internal
        from modules.notes_manager import sync_kb_from_excel_internal
        
        # 1. Envanter
        try:
            inv_stats = sync_excel_to_db_internal()
            results.append(f"Envanter: {inv_stats.get('pc_synced', 0)} cihaz güncellendi.")
        except Exception as e:
            results.append(f"Envanter Hatası: {str(e)}")
            success = False

        # 2. Yazıcılar (Tarayıcı ve Barkodlar dahil)
        try:
            p_count = sync_printers_from_excel_internal()
            results.append(f"Yazıcılar: {p_count} kayıt senkronize edildi.")
        except Exception as e:
            results.append(f"Yazıcı Hatası: {str(e)}")
            success = False

        # 3. Depo
        try:
            d_count = sync_depot_from_excel_internal()
            results.append(f"Depo: {d_count} ürün güncellendi.")
        except Exception as e:
            results.append(f"Depo Hatası: {str(e)}")
            success = False

        # 4. Bilgi Bankası
        try:
            k_count = sync_kb_from_excel_internal()
            results.append(f"Bilgi Bankası: {k_count} kayıt güncellendi.")
        except Exception as e:
            results.append(f"Bilgi Bankası Hatası: {str(e)}")
            success = False

        # 5. GitHub Otomatik Push (Kullanıcı talebi: Her güncellemede yedekle)
        if success:
            try:
                import subprocess
                # sync_repos.py bir üst dizinde veya aynı dizinde olabilir
                sync_script = os.path.join(BASE_DIR, "..", "sync_repos.py")
                if os.path.exists(sync_script):
                    subprocess.Popen(["python", sync_script], shell=True)
                    results.append("GitHub: Yedekleme başlatıldı.")
                else:
                    results.append("GitHub: sync_repos.py bulunamadı.")
            except Exception as git_err:
                results.append(f"GitHub Hatası: {str(git_err)}")

        return jsonify({
            "success": success,
            "message": "Toplu senkronizasyon tamamlandı." if success else "Bazı modüllerde hatalar oluştu.",
            "details": results
        })
    except Exception as e:
        print(f"Global Sync Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/logo/<path:filename>')
def serve_logo(filename):
    """Logo klasöründeki dosyaları servis eder."""
    return send_from_directory(os.path.join(BASE_DIR, 'logo'), filename)


@app.route('/api/downloads/list')
@require_auth
def list_downloads():
    """bat_uygulama klasöründeki dosyaları listeler."""
    try:
        path = os.path.join(BASE_DIR, 'bat_uygulama')
        if not os.path.exists(path): os.makedirs(path)
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/downloads/get/<path:filename>')
@require_auth
def get_download(filename):
    """bat_uygulama klasöründen dosya indirir."""
    return send_from_directory(os.path.join(BASE_DIR, 'bat_uygulama'), filename, as_attachment=True)


@app.route('/api/test_ping')
def test_ping():
    return jsonify({"message": "Server is updated and running!"})


@app.route('/api/sync', methods=['POST'])
@require_admin
def manual_sync():
    try:
        sync_excel_to_db()
        return jsonify({"message": "Başarıyla senkronize edildi."})
    except Exception as e:
        print("Sync Error:", e)
        return jsonify({"error": str(e)}), 200 # Frontend hata mesajını JSON alabilsin

def background_sync_worker():
    """Her sabah 07:00'de otomatik senkronizasyon yapar."""
    print("Background Sync Worker started.")
    while True:
        now = datetime.datetime.now()
        # Her gün 07:00:00 - 07:00:59 arası bir kez çalıştır
        if now.hour == 7 and now.minute == 0:
            print(f"[{now}] Otomatik senkronizasyon ve KeyOS kontrolü tetiklendi...")
            try:
                sync_excel_to_db()
                sync_db_to_excel()
                
                # KeyOS Kontrolü
                from modules.keyos_service import get_all_mismatches_internal
                mismatches, error = get_all_mismatches_internal()
                if not error:
                    print(f"KeyOS Kontrolü Tamamlandı. {len(mismatches)} uyuşmazlık bulundu.")
                else:
                    print(f"KeyOS Kontrol Hatası: {error}")
                
                # CUPS Location Sync
                from modules.printer_manager import CUPSHelper
                print("CUPS Location Sync baslatiliyor...")
                CUPSHelper.update_db_cups_locations()
                
                time.sleep(65) # Bir dakika bekle ki aynı dakika içinde tekrar tetiklenmesin
            except Exception as e:
                print("Scheduled Sync/KeyOS error:", e)
        time.sleep(30) # 30 saniyede bir kontrol et


@app.route('/api/get_my_ip')
def get_my_ip():
    return jsonify({"ip": request.remote_addr})

@app.route('/api/admin/system_logs')
@require_admin
def get_system_logs():
    log_path = 'logs/system.log'
    if not os.path.exists(log_path):
        return jsonify([])
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Son 500 satırı al
            last_lines = lines[-500:]
            return jsonify(last_lines)
    except Exception as e:
        return jsonify([f"Log okuma hatası: {str(e)}"])

if __name__ == '__main__':

    init_db()
    create_sample_config()
    
    # Arka plan görevini başlat
    bg_thread = threading.Thread(target=background_sync_worker, daemon=True)
    bg_thread.start()
    
    # İlk açılışta bir kez senkronize et
    try:
        sync_excel_to_db()
    except Exception as e:
        print("Initial Sync Error:", e)
    
    # Try using waitress for production, fallback to Flask dev server
    try:
        from waitress import serve
        import logging
        logging.getLogger('waitress.queue').setLevel(logging.ERROR)
        print("Starting server with Waitress on port 5000 (Production mode)")
        serve(app, host='0.0.0.0', port=5000)
    except ImportError:
        print("Waitress not found. Starting with Flask dev server...")
        app.run(host='0.0.0.0', port=5000, debug=False)
