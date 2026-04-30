import pyodbc
import json
import os
import re
from werkzeug.security import generate_password_hash, check_password_hash

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'sql_ayarlari.json'))

def get_sql_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def _get_raw_connection():
    """Ham pyodbc bağlantısı döndürür."""
    # 1. Öncelik: .env dosyasındaki değerler
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_NAME')
    uid = os.getenv('DB_USER')
    pwd = os.getenv('DB_PASS')

    # 2. Öncelik: Eğer .env yoksa JSON dosyasından oku (Geriye dönük uyumluluk)
    if not all([server, database]):
        try:
            config = get_sql_config()
            server = server or config.get('server')
            database = database or config.get('database')
            uid = uid or config.get('username')
            pwd = pwd or config.get('password')
        except: pass
    
    # Mevcut ODBC Sürücüsünü bul
    import pyodbc as _pyodbc
    available_drivers = _pyodbc.drivers()
    driver = 'SQL Server'
    for d in ['ODBC Driver 17 for SQL Server', 'ODBC Driver 18 for SQL Server', 'SQL Server']:
        if d in available_drivers:
            driver = d
            break
    
    # SQL Auth bağlantı dizesi
    conn_str = (
        f'DRIVER={{{driver}}};'
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={uid};"
        f"PWD={pwd};"
        f"TrustServerCertificate=yes;"
    )
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception:
        # SQL Auth başarısız olursa Windows Auth dene
        conn_str_win = (
            f'DRIVER={{{driver}}};'
            f"SERVER={server};"
            f"DATABASE={database};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str_win)
        return conn



class DictRow:
    """SQLite Row benzeri erişim sağlar: row['column'] ve row[0] ikisi de çalışır."""
    def __init__(self, columns, values):
        self._columns = columns
        self._values = list(values)
        self._dict = dict(zip(columns, self._values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._dict[key]

    def __contains__(self, key):
        return key in self._dict

    def __iter__(self):
        return iter(self._columns)

    def __len__(self):
        return len(self._values)

    def get(self, key, default=None):
        return self._dict.get(key, default)

    def keys(self):
        return self._columns

    def values(self):
        return self._values

    def items(self):
        return self._dict.items()

    def __repr__(self):
        return repr(self._dict)


class CursorWrapper:
    """pyodbc cursor'ını SQLite cursor'ı gibi davrandırır."""
    def __init__(self, cursor):
        self._cursor = cursor
        self._columns = None

    @property
    def lastrowid(self):
        """INSERT sonrası son eklenen ID'yi döndürür (SQL Server SCOPE_IDENTITY)."""
        self._cursor.execute("SELECT SCOPE_IDENTITY()")
        result = self._cursor.fetchone()
        return int(result[0]) if result and result[0] is not None else None

    @property
    def description(self):
        return self._cursor.description

    def execute(self, query, args=()):
        query = _convert_query(query)
        self._cursor.execute(query, args)
        if self._cursor.description:
            self._columns = [col[0] for col in self._cursor.description]
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if self._columns:
            return DictRow(self._columns, row)
        return row

    def fetchall(self):
        rows = self._cursor.fetchall()
        if self._columns:
            return [DictRow(self._columns, row) for row in rows]
        return rows


class ConnectionWrapper:
    """pyodbc connection'ı SQLite connection'ı gibi davrandırır.
    conn.execute() doğrudan çalışır, sonuçlar dict-benzeri Row döner."""
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        return CursorWrapper(self._conn.cursor())

    def execute(self, query, args=()):
        """Doğrudan conn.execute() desteği (SQLite uyumluluğu)."""
        cur = self._conn.cursor()
        query = _convert_query(query)
        cur.execute(query, args)
        
        # SELECT sorgusu ise DictRow döndür
        if cur.description:
            columns = [col[0] for col in cur.description]
            
            class ResultProxy:
                def __init__(self, cursor, columns):
                    self._cursor = cursor
                    self._columns = columns
                def fetchone(self):
                    row = self._cursor.fetchone()
                    if row is None:
                        return None
                    return DictRow(self._columns, row)
                def fetchall(self):
                    rows = self._cursor.fetchall()
                    return [DictRow(self._columns, row) for row in rows]
            
            return ResultProxy(cur, columns)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def _convert_query(query):
    """SQLite sorgularını SQL Server'a uyumlu hale çevirir."""
    # 1. Subquery'lerdeki LIMIT N -> TOP N dönüşümü
    # Örn: (SELECT ... LIMIT 1) -> (SELECT TOP 1 ...)
    def replace_sub_limit(match):
        sub = match.group(0)
        # LIMIT'i bul ve kaldır
        limit_match = re.search(r'\bLIMIT\s+(\d+)\s*(?=\)|$)', sub, re.IGNORECASE)
        if limit_match:
            n = limit_match.group(1)
            # LIMIT kısmını temizle
            sub = sub[:limit_match.start()] + sub[limit_match.end():]
            # SELECT'ten sonra TOP ekle
            sub = re.sub(r'\bSELECT\b', f'SELECT TOP {n}', sub, count=1, flags=re.IGNORECASE)
        return sub

    # Regex: ( ile başlayan ve SELECT içeren, sonlarında LIMIT olan parantez içi bloklar
    query = re.sub(r'\(\s*SELECT.*?\bLIMIT\s+\d+\s*\)', replace_sub_limit, query, flags=re.IGNORECASE | re.DOTALL)

    # 2. Ana sorgudaki LIMIT N -> TOP N dönüşümü (Sondaki LIMIT)
    limit_match = re.search(r'\bLIMIT\s+(\d+)\s*$', query, re.IGNORECASE)
    if limit_match:
        limit_n = limit_match.group(1)
        query = query[:limit_match.start()].rstrip()
        query = re.sub(r'^(\s*SELECT)\b', rf'\1 TOP {limit_n}', query, count=1, flags=re.IGNORECASE)
    
    return query


def get_db_connection():
    """SQLite uyumlu wrapper connection döndürür."""
    raw_conn = _get_raw_connection()
    return ConnectionWrapper(raw_conn)


def query_db(query, args=(), one=False):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, args)
    
    # Ekleme, silme veya güncelleme işlemi ise
    if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
        conn.commit()
        conn.close()
        return None
        
    rv = cur.fetchall()
    
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv


def hash_password(password):
    return generate_password_hash(password)

def verify_password(password, hashed):
    return check_password_hash(hashed, password)


def init_db():
    raw_conn = _get_raw_connection()
    cur = raw_conn.cursor()
    
    # Yardımcı fonksiyon: Tablo varsa oluşturma
    def create_table_if_not_exists(table_name, create_sql):
        check_sql = f"IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{table_name}' and xtype='U') BEGIN {create_sql} END"
        cur.execute(check_sql)

    # Tablo zaten varsa eksik kolonları ekle (Migration)
    def add_column_if_not_exists(table_name, col_name, col_type):
        check_col = f"IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('{table_name}') AND name = '{col_name}') BEGIN ALTER TABLE {table_name} ADD {col_name} {col_type} END"
        cur.execute(check_col)

    create_table_if_not_exists('inventory', """
        CREATE TABLE inventory (
            id INT IDENTITY(1,1) PRIMARY KEY,
            pc_no NVARCHAR(MAX),
            kule NVARCHAR(MAX),
            kat NVARCHAR(MAX),
            mahal_kodu NVARCHAR(MAX),
            mahal_adi NVARCHAR(MAX),
            keyos_mahal NVARCHAR(MAX),
            sahada NVARCHAR(MAX),
            depo NVARCHAR(MAX),
            arizali NVARCHAR(MAX),
            mahalsiz NVARCHAR(MAX),
            telefon NVARCHAR(MAX),
            ip NVARCHAR(MAX),
            bagli_yazicilar NVARCHAR(MAX),
            pc_seri NVARCHAR(MAX),
            monitor_seri NVARCHAR(MAX),
            monitor2_seri NVARCHAR(MAX),
            windows NVARCHAR(MAX),
            keyos NVARCHAR(MAX),
            rdp NVARCHAR(MAX),
            pr6900 NVARCHAR(MAX),
            pr5200 NVARCHAR(MAX),
            pr8690 NVARCHAR(MAX),
            by_seri NVARCHAR(MAX),
            bo_seri NVARCHAR(MAX),
            tarayici_seri NVARCHAR(MAX),
            aciklama NVARCHAR(MAX),
            last_counted_at DATETIME,
            counted_by NVARCHAR(MAX),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(MAX),
            hostname NVARCHAR(MAX),
            device_type NVARCHAR(50) DEFAULT 'PC',
            assigned_to NVARCHAR(MAX),
            card_name NVARCHAR(MAX),
            phone NVARCHAR(MAX),
            title NVARCHAR(MAX),
            unit NVARCHAR(MAX),
            kurulum_bekliyor INT DEFAULT 0
        )
    """)

    # Migration for inventory
    add_column_if_not_exists('inventory', 'device_type', "NVARCHAR(50) DEFAULT 'PC'")
    add_column_if_not_exists('inventory', 'assigned_to', "NVARCHAR(MAX)")
    add_column_if_not_exists('inventory', 'hostname', "NVARCHAR(MAX)")
    add_column_if_not_exists('inventory', 'last_counted_at', 'DATETIME')
    add_column_if_not_exists('inventory', 'counted_by', 'NVARCHAR(MAX)')
    add_column_if_not_exists('inventory', 'card_name', 'NVARCHAR(MAX)')
    add_column_if_not_exists('inventory', 'phone', 'NVARCHAR(MAX)')
    add_column_if_not_exists('inventory', 'title', 'NVARCHAR(MAX)')
    add_column_if_not_exists('inventory', 'unit', 'NVARCHAR(MAX)')
    add_column_if_not_exists('inventory', 'kurulum_bekliyor', 'INT DEFAULT 0')
    add_column_if_not_exists('inventory', 'last_edit_date', 'DATETIME')
    add_column_if_not_exists('inventory', 'last_edit_user', 'NVARCHAR(MAX)')
    add_column_if_not_exists('inventory', 'monitor_model', 'NVARCHAR(MAX)')
    add_column_if_not_exists('inventory', 'monitor2_model', 'NVARCHAR(MAX)')

    create_table_if_not_exists('users', """
        CREATE TABLE users (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(255) UNIQUE,
            password_hash NVARCHAR(MAX),
            display_name NVARCHAR(MAX),
            role NVARCHAR(50),
            permissions NVARCHAR(MAX),
            bim_user NVARCHAR(MAX),
            bim_pass NVARCHAR(MAX),
            keyos_user NVARCHAR(MAX),
            keyos_pass NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE()
        )
    """)
    
    # User credential migration
    add_column_if_not_exists('users', 'bim_user', "NVARCHAR(MAX)")
    add_column_if_not_exists('users', 'bim_pass', "NVARCHAR(MAX)")
    add_column_if_not_exists('users', 'keyos_user', "NVARCHAR(MAX)")
    add_column_if_not_exists('users', 'keyos_pass', "NVARCHAR(MAX)")
    add_column_if_not_exists('users', 'magicinfo_user', "NVARCHAR(MAX)")
    add_column_if_not_exists('users', 'magicinfo_pass', "NVARCHAR(MAX)")
    add_column_if_not_exists('users', 'last_login', "DATETIME")
    add_column_if_not_exists('users', 'session_timeout', "INT DEFAULT 30")

    create_table_if_not_exists('magicinfo_devices', """
        CREATE TABLE magicinfo_devices (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(MAX),
            mac NVARCHAR(MAX),
            ip NVARCHAR(MAX),
            location NVARCHAR(MAX),
            server NVARCHAR(MAX)
        )
    """)

    create_table_if_not_exists('printers', """
        CREATE TABLE printers (
            id INT IDENTITY(1,1) PRIMARY KEY,
            pr_no NVARCHAR(MAX),
            model NVARCHAR(MAX),
            seri NVARCHAR(MAX),
            mac NVARCHAR(MAX),
            ip NVARCHAR(MAX),
            toner NVARCHAR(MAX),
            status NVARCHAR(MAX) DEFAULT 'Kurulu',
            live_status NVARCHAR(MAX),
            mahal NVARCHAR(MAX)
        )
    """)

    create_table_if_not_exists('shared_areas', """
        CREATE TABLE shared_areas (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(MAX),
            [user] NVARCHAR(MAX),
            password NVARCHAR(MAX),
            path NVARCHAR(MAX)
        )
    """)

    create_table_if_not_exists('technical_notes', """
        CREATE TABLE technical_notes (
            id INT IDENTITY(1,1) PRIMARY KEY,
            device_id INT NOT NULL,
            device_type NVARCHAR(MAX) NOT NULL DEFAULT 'pc',
            title NVARCHAR(MAX),
            content NVARCHAR(MAX),
            user_id NVARCHAR(MAX),
            user_name NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE()
        )
    """)

    create_table_if_not_exists('knowledge_base', """
        CREATE TABLE knowledge_base (
            id INT IDENTITY(1,1) PRIMARY KEY,
            type NVARCHAR(50), -- 'kodlar' or 'kapanis'
            title NVARCHAR(MAX),
            content NVARCHAR(MAX),
            image_path NVARCHAR(MAX),
            user_id NVARCHAR(MAX),
            user_name NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE()
        )
    """)

    create_table_if_not_exists('depot_items', """
        CREATE TABLE depot_items (
            id INT IDENTITY(1,1) PRIMARY KEY,
            category NVARCHAR(MAX),
            name NVARCHAR(MAX),
            current_stock INT DEFAULT 0,
            critical_stock INT DEFAULT 5,
            unit NVARCHAR(50) DEFAULT 'Adet',
            description NVARCHAR(MAX),
            saha_stock INT DEFAULT 0,
            arizali_stock INT DEFAULT 0,
            kayip_stock INT DEFAULT 0,
            weekly_distributed INT DEFAULT 0,
            last_sync_date DATETIME DEFAULT GETDATE()
        )
    """)

    create_table_if_not_exists('depot_transactions', """
        CREATE TABLE depot_transactions (
            id INT IDENTITY(1,1) PRIMARY KEY,
            depot_item_id INT,
            transaction_type NVARCHAR(20), -- 'in' or 'out'
            quantity INT,
            device_id INT,
            device_type NVARCHAR(50),
            user_name NVARCHAR(MAX),
            note NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE()
        )
    """)

    create_table_if_not_exists('printer_service_history', """
        CREATE TABLE printer_service_history (
            id INT IDENTITY(1,1) PRIMARY KEY,
            printer_id INT,
            mahal NVARCHAR(MAX),
            seri_no NVARCHAR(MAX),
            ariza_notu NVARCHAR(MAX),
            durum NVARCHAR(50), -- 'Serviste', 'Tamamlandı'
            gidis_tarihi DATETIME DEFAULT GETDATE(),
            donus_tarihi DATETIME,
            alinan_parca NVARCHAR(MAX)
        )
    """)

    # Varsayılan Admin Kullanıcısı
    exists = cur.execute("SELECT id FROM users WHERE username='vefa'").fetchone()
    if not exists:
        admin_pass = hash_password('123')
        cur.execute("INSERT INTO users (username, password_hash, display_name, role) VALUES (?,?,?,?)",
                  ('vefa', admin_pass, 'M. Vefa', 'ADMIN'))

    create_table_if_not_exists('note_images', """
        CREATE TABLE note_images (
            id INT IDENTITY(1,1) PRIMARY KEY,
            note_id INT NOT NULL,
            filename NVARCHAR(MAX) NOT NULL,
            created_at DATETIME DEFAULT GETDATE(),
            FOREIGN KEY (note_id) REFERENCES technical_notes(id)
        )
    """)

    create_table_if_not_exists('printer_service', """
        CREATE TABLE printer_service (
            id INT IDENTITY(1,1) PRIMARY KEY,
            printer_id INT NULL,
            pr_no NVARCHAR(MAX),
            seri NVARCHAR(MAX),
            mac NVARCHAR(MAX),
            mahal NVARCHAR(MAX),
            model NVARCHAR(MAX),
            acq_date NVARCHAR(MAX),
            acq_place NVARCHAR(MAX),
            sent_date NVARCHAR(MAX),
            return_date NVARCHAR(MAX),
            fault_desc NVARCHAR(MAX),
            has_substitute INT DEFAULT 0,
            substitute_pr_no NVARCHAR(MAX),
            status NVARCHAR(MAX) DEFAULT 'Serviste',
            final_status NVARCHAR(MAX),
            user_name NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE()
        )
    """)

    create_table_if_not_exists('audit_logs', """
        CREATE TABLE audit_logs (
            id INT IDENTITY(1,1) PRIMARY KEY,
            table_name NVARCHAR(100) NOT NULL,
            record_id INT NOT NULL,
            record_label NVARCHAR(MAX),
            field_name NVARCHAR(100) NOT NULL,
            old_value NVARCHAR(MAX),
            new_value NVARCHAR(MAX),
            changed_by NVARCHAR(MAX),
            display_name NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE()
        )
    """)

    # Inventory tablosuna sayım sütunları ekle
    try:
        cur.execute("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('inventory') AND name = 'last_counted_at') ALTER TABLE inventory ADD last_counted_at DATETIME NULL")
        cur.execute("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('inventory') AND name = 'counted_by') ALTER TABLE inventory ADD counted_by NVARCHAR(MAX) NULL")
    except: pass

    # Audit log geliştirmeleri
    try:
        cur.execute("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('audit_logs') AND name = 'client_ip') ALTER TABLE audit_logs ADD client_ip NVARCHAR(50)")
        cur.execute("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('audit_logs') AND name = 'client_mac') ALTER TABLE audit_logs ADD client_mac NVARCHAR(50)")
        cur.execute("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('printer_service') AND name = 'acq_place') ALTER TABLE printer_service ADD acq_place NVARCHAR(MAX)")
        # Depot items extra fields for asset management
        cur.execute("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('depot_items') AND name = 'saha_stock') ALTER TABLE depot_items ADD saha_stock INT DEFAULT 0")
        cur.execute("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('depot_items') AND name = 'arizali_stock') ALTER TABLE depot_items ADD arizali_stock INT DEFAULT 0")
        cur.execute("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('depot_items') AND name = 'kayip_stock') ALTER TABLE depot_items ADD kayip_stock INT DEFAULT 0")
        
        # Knowledge Base migration
        cur.execute("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('knowledge_base') AND name = 'user_id') ALTER TABLE knowledge_base ADD user_id NVARCHAR(MAX)")
        cur.execute("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('knowledge_base') AND name = 'user_name') ALTER TABLE knowledge_base ADD user_name NVARCHAR(MAX)")
        cur.execute("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('knowledge_base') AND name = 'requires_user') ALTER TABLE knowledge_base ADD requires_user INT DEFAULT 0")
        
        # User permissions migration
        cur.execute("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('users') AND name = 'permissions') ALTER TABLE users ADD permissions NVARCHAR(MAX)")
        
        # Printer live status migration
        cur.execute("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('printers') AND name = 'live_status') ALTER TABLE printers ADD live_status NVARCHAR(MAX)")
        
        # Printer service migration
        cur.execute("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('printer_service') AND name = 'acq_place') ALTER TABLE printer_service ADD acq_place NVARCHAR(MAX)")
    except: pass


    # Varsayılan kullanıcıları kontrol et ve ekle
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO users (username, password_hash, display_name, role) VALUES (?,?,?,?)",
            ('vefa', hash_password('123'), 'M. Vefa', 'ADMIN'))
        cur.execute("INSERT INTO users (username, password_hash, display_name, role) VALUES (?,?,?,?)",
            ('admin', hash_password('123'), 'Sistem Admin', 'ADMIN'))
        cur.execute("INSERT INTO users (username, password_hash, display_name, role) VALUES (?,?,?,?)",
            ('destek', hash_password('123'), 'Saha Destek', 'EDITOR'))
    
    raw_conn.commit()
    raw_conn.close()
    print("DEBUG: Veritabanı tabloları oluşturuldu / kontrol edildi.")
