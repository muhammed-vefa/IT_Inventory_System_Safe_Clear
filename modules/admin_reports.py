import os
import re
import base64
from datetime import datetime
from flask import Blueprint, jsonify, request
from core.auth import require_admin, require_auth

admin_reports_bp = Blueprint('admin_reports', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# İzin verilen dizinler (Çalışma Anayasası/Kurallar)
ALLOWED_DIRS = [
    'logs',
    'logs/cmd',
    'logs/performance',
    'reports',
    'reports/performance',
    'reports/integrity',
    'reports/git',
    'reports/backup',
    'database'
]

# İzin verilen dosya uzantıları
ALLOWED_EXTENSIONS = ['.log', '.txt', '.md', '.csv', '.json']

# Kara liste dosya adları
DISALLOWED_NAMES = ['.env', 'credentials.json', 'token.json']


def mask_sensitive_data(content):
    """Log ve raporlar içindeki şifre, token vb. gizli bilgileri maskeler."""
    if not content:
        return content
    
    # 1. Genel key=value veya key:value yapıları için
    content = re.sub(
        r'(?i)(password|pass|token|secret|api_key|private_key|bim_pass|keyos_pass|password_hash|cookie|session|jwt)\s*([:=])\s*([^\s,;\'"\r\n]+)',
        r'\1\2****',
        content
    )
    
    # 2. HTTP Authorization Header'ları için (Authorization: Bearer ...)
    content = re.sub(
        r'(?i)(Authorization\s*:\s*Bearer\s+)([^\s,;\'"\r\n]+)',
        r'\1****',
        content
    )
    
    return content


def resolve_file_id(file_id):
    """file_id değerini doğrulanmış mutlak yola dönüştürür. Hata durumunda None döner."""
    if not file_id:
        return None
    try:
        decoded_path = base64.urlsafe_b64decode(file_id.encode('utf-8')).decode('utf-8')
    except Exception:
        return None
    
    # Path traversal engelleme
    safe_path = os.path.normpath(os.path.join(BASE_DIR, decoded_path))
    
    is_allowed = False
    for allowed_dir in ALLOWED_DIRS:
        allowed_abs = os.path.normpath(os.path.join(BASE_DIR, allowed_dir))
        try:
            # os.path.commonpath ile path traversal kontrolü
            if os.path.commonpath([allowed_abs, safe_path]) == allowed_abs:
                is_allowed = True
                break
        except ValueError:
            continue
            
    if not is_allowed:
        return None
        
    filename = os.path.basename(safe_path)
    if filename.lower() in DISALLOWED_NAMES:
        return None
        
    _, ext = os.path.splitext(filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        return None
        
    if not os.path.exists(safe_path) or not os.path.isfile(safe_path):
        if filename.lower() == 'server_console.log':
            try:
                os.makedirs(os.path.dirname(safe_path), exist_ok=True)
                with open(safe_path, 'w', encoding='utf-8') as f:
                    f.write("[+] Sunucu Baslatildi - Canli Konsol Log Akisi\n")
            except Exception:
                return None
        else:
            return None
        
    return safe_path


def scan_dir(category_id, rel_dir):
    """Güvenli bir şekilde belirtilen klasördeki dosyaları tarar ve metadata üretir."""
    abs_dir = os.path.normpath(os.path.join(BASE_DIR, rel_dir))
    
    # Klasör mevcut değilse otomatik olarak oluştur (Production Resilience)
    if not os.path.exists(abs_dir):
        try:
            os.makedirs(abs_dir, exist_ok=True)
        except Exception as e:
            print(f"[Admin Reports] Klasör oluşturma hatası ({abs_dir}): {e}")
            return []
            
    files_list = []
    try:
        for entry in os.scandir(abs_dir):
            if entry.is_file():
                filename = entry.name
                _, ext = os.path.splitext(filename)
                
                # Uzantı ve kara liste kontrolü
                if ext.lower() not in ALLOWED_EXTENSIONS:
                    continue
                if filename.lower() in DISALLOWED_NAMES:
                    continue
                    
                # file_id: Proje kök dizinine göre göreceli yolun base64 hali
                rel_path = os.path.relpath(entry.path, BASE_DIR).replace('\\', '/')
                file_id = base64.urlsafe_b64encode(rel_path.encode('utf-8')).decode('utf-8')
                
                stat = entry.stat()
                files_list.append({
                    "file_id": file_id,
                    "category": category_id,
                    "file_name": filename,
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    "type": ext.replace('.', '').lower(),
                    "safe_to_view": True
                })
    except Exception as e:
        print(f"[Admin Reports] Klasör tarama hatası ({abs_dir}): {e}")
        
    return files_list


def tail_file(file_path, num_lines=300):
    """Büyük log dosyalarının son N satırını bellek dostu şekilde okur."""
    chunk_size = 8192
    lines = []
    try:
        with open(file_path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            position = file_size
            
            buffer = bytearray()
            while position > 0 and len(lines) <= num_lines:
                read_size = min(chunk_size, position)
                position -= read_size
                f.seek(position)
                chunk = f.read(read_size)
                buffer[:0] = chunk  # Başına ekle
                
                lines = buffer.split(b'\n')
                
            if len(lines) > num_lines:
                lines = lines[-num_lines:]
                
            return '\n'.join([line.decode('utf-8', errors='ignore').rstrip('\r') for line in lines])
    except Exception as e:
        print(f"[Admin Reports] Tail hatası ({file_path}), standard okumaya dönülüyor: {e}")
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            return ''.join(all_lines[-num_lines:])


@admin_reports_bp.route('', methods=['GET'])
@require_admin
def index():
    """Rapor izleme modülü durumunu ve izin verilen dizinleri döner."""
    return jsonify({
        "success": True,
        "message": "IT Rapor/Log Izleme Merkezi Aktif",
        "allowed_directories": ALLOWED_DIRS
    })


@admin_reports_bp.route('/categories', methods=['GET'])
@require_admin
def list_categories():
    """Rapor kategorilerini listeler."""
    categories = [
        {"id": "cmd", "name": "CMD İşlem Logları"},
        {"id": "performance", "name": "Performans Raporları & Logları"},
        {"id": "git", "name": "GitHub İşlem Raporları"},
        {"id": "backup", "name": "Yedekleme Raporları"},
        {"id": "integrity", "name": "Bütünlük Raporları"},
        {"id": "scheduler", "name": "Zamanlanmış Görev Raporları"}
    ]
    return jsonify({"success": True, "categories": categories})


@admin_reports_bp.route('/list', methods=['GET'])
@require_admin
def list_reports():
    """Kategoriye veya tüm listeye göre rapor dosyalarını listeler."""
    category = request.args.get('category', '').strip().lower()
    
    files = []
    if category == 'cmd':
        files.extend(scan_dir('cmd', 'logs/cmd'))
    elif category == 'performance':
        files.extend(scan_dir('performance', 'reports/performance'))
        files.extend(scan_dir('performance', 'logs/performance'))
    elif category == 'git':
        files.extend(scan_dir('git', 'reports/git'))
    elif category == 'backup':
        files.extend(scan_dir('backup', 'reports/backup'))
    elif category == 'integrity':
        files.extend(scan_dir('integrity', 'reports/integrity'))
    elif category == 'scheduler':
        files.extend(scan_dir('scheduler', 'database'))
    else:
        # Belirtilmemişse tüm alt ve ana dizinleri tara
        files.extend(scan_dir('cmd', 'logs/cmd'))
        files.extend(scan_dir('performance', 'reports/performance'))
        files.extend(scan_dir('performance', 'logs/performance'))
        files.extend(scan_dir('git', 'reports/git'))
        files.extend(scan_dir('backup', 'reports/backup'))
        files.extend(scan_dir('integrity', 'reports/integrity'))
        files.extend(scan_dir('scheduler', 'database'))
        
        # Ana dizinlerdeki dosyaları da tara
        files.extend(scan_dir('cmd', 'logs'))
        files.extend(scan_dir('integrity', 'reports'))
        
    # Tarihe göre yeniden eskiye sırala
    files.sort(key=lambda x: x['modified_at'], reverse=True)
    return jsonify({"success": True, "items": files})


@admin_reports_bp.route('/view', methods=['GET'])
@require_admin
def view_report():
    """Seçilen raporu güvenli şekilde tam içerik olarak okur (Maks 5MB)."""
    file_id = request.args.get('file_id')
    file_path = resolve_file_id(file_id)
    if not file_path:
        return jsonify({"success": False, "error": "Geçersiz dosya veya erişim engellendi"}), 400
        
    try:
        file_size = os.path.getsize(file_path)
        if file_size > 5 * 1024 * 1024:
            return jsonify({
                "success": False, 
                "error": "Dosya boyutu 5MB sınırını aşıyor. Lütfen 'tail' (son satırlar) modunu kullanın.",
                "size": file_size
            }), 400
            
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        masked_content = mask_sensitive_data(content)
        return jsonify({
            "success": True,
            "file_name": os.path.basename(file_path),
            "content": masked_content,
            "size": file_size
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_reports_bp.route('/tail', methods=['GET'])
@require_admin
def tail_report():
    """Seçilen log dosyasının son N satırını güvenli ve optimize şekilde okur."""
    file_id = request.args.get('file_id')
    lines_arg = request.args.get('lines', '300')
    
    try:
        num_lines = min(max(int(lines_arg), 10), 1000)
    except ValueError:
        num_lines = 300
        
    file_path = resolve_file_id(file_id)
    if not file_path:
        return jsonify({"success": False, "error": "Geçersiz dosya veya erişim engellendi"}), 400
        
    try:
        content = tail_file(file_path, num_lines)
        masked_content = mask_sensitive_data(content)
        return jsonify({
            "success": True,
            "file_name": os.path.basename(file_path),
            "content": masked_content,
            "lines": num_lines,
            "size": os.path.getsize(file_path)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
