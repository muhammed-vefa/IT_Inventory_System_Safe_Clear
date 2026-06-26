import pyodbc
from dbutils.pooled_db import PooledDB
import os
import datetime
from dotenv import load_dotenv

# Uygulama dizini ve Veri dizini yapilandirmasi
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# .env yukleme
env_path = os.path.join(BASE_DIR, ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(BASE_DIR, "tools", ".env")
load_dotenv(env_path, override=True)
DB_SERVER = os.getenv("DB_SERVER", ".\\SQLEXPRESS")
DB_NAME = os.getenv("DB_NAME", "IT_INVENTORY")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

_pools = {}

def get_db_connection(target_db=DB_NAME):
    try:
        user = str(DB_USER).strip() if DB_USER else None
        pw = str(DB_PASS).strip() if DB_PASS else None
        server = str(DB_SERVER).strip() if DB_SERVER else r".\SQLEXPRESS"
        
        if target_db not in _pools:
            if user and pw:
                conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={target_db};UID={user};PWD={pw};"
            else:
                conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={target_db};Trusted_Connection=yes;"
            
            _pools[target_db] = PooledDB(
                pyodbc,    # creator
                5,         # mincached
                0,         # maxcached
                0,         # maxshared
                20,        # maxconnections
                True,      # blocking
                None,      # maxusage
                None,      # setsession
                True,      # reset
                None,      # failures
                1,         # ping
                conn_str,  # *args passed to creator
                timeout=10 # **kwargs passed to creator
            )
        
        return _pools[target_db].connection()
    except Exception as e:
        print(f"DB Baglanti Hatasi ({target_db}): {e}")
        return None

def backup_sql_db():
    """SQL Server veritabanini .bak olarak yedekler."""
    try:
        yedek_path = os.path.join(BASE_DIR, "database", "yedek")
        if not os.path.exists(yedek_path):
            os.makedirs(yedek_path)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        backup_file = os.path.join(yedek_path, f"SQL_Backup_{timestamp}.bak")
        
        conn = get_db_connection(target_db=DB_NAME)
        if not conn: return False, f"Veritabani baglantisi kurulamadi ({DB_NAME})."
        
        conn.autocommit = True
        cursor = conn.cursor()
        query = f"BACKUP DATABASE [{DB_NAME}] TO DISK = '{backup_file}' WITH FORMAT, MEDIANAME = 'SQLServerBackups', NAME = 'Full Backup of {DB_NAME}'"
        cursor.execute(query)
        while cursor.nextset():
            pass
        conn.close()
        
        print(f"[*] Veritabani yedegi {backup_file} klasorune basariyla kaydedildi.")
        return True, backup_file
    except Exception as e:
        err_msg = f"Yedekleme Hatasi: {e}"
        print(f"[!] {err_msg}")
        return False, err_msg

def restore_sql_db(backup_file_path):
    """SQL Server veritabanini verilen .bak dosyasindan geri yukler."""
    try:
        if not os.path.exists(backup_file_path):
            return False, f"Yedek dosyasi bulunamadi: {backup_file_path}"
            
        conn_master = get_db_connection(target_db="master")
        if not conn_master: return False, "Master DB baglantisi kurulamadi."
        
        conn_master.autocommit = True
        cursor = conn_master.cursor()
        
        # 1. Diger baglantilari kopar (SINGLE_USER)
        cursor.execute(f"ALTER DATABASE [{DB_NAME}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
        
        # 2. Restore Islemi
        query = f"RESTORE DATABASE [{DB_NAME}] FROM DISK = '{backup_file_path}' WITH REPLACE"
        cursor.execute(query)
        while cursor.nextset():
            pass
            
        # 3. Sistemi yeniden yayina ac
        cursor.execute(f"ALTER DATABASE [{DB_NAME}] SET MULTI_USER")
        conn_master.close()
        
        print(f"[*] Veritabani basariyla restore edildi: {backup_file_path}")
        return True, "Geri yukleme (Restore) islemi basariyla tamamlandi."
    except Exception as e:
        err_msg = f"Restore Hatasi: {e}"
        print(f"[!] {err_msg}")
        try:
            if 'cursor' in locals() and cursor:
                cursor.execute(f"ALTER DATABASE [{DB_NAME}] SET MULTI_USER")
            if 'conn_master' in locals() and conn_master:
                conn_master.close()
        except Exception as cleanup_err:
            print(f"[!] Cleanup Hatasi: {cleanup_err}")
        return False, err_msg


def init_db():
    conn_master = get_db_connection(target_db="master")
    if not conn_master: return
    conn_master.autocommit = True
    cursor_m = conn_master.cursor()
    try:
        cursor_m.execute(f"IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{DB_NAME}') CREATE DATABASE [{DB_NAME}]")
    finally:
        conn_master.close()

    conn = get_db_connection(target_db=DB_NAME)
    if not conn: return
    cursor = conn.cursor()

    # =====================================================
    #  TABLO TANIMLARI — v11: AYRILMIS YAPI
    # =====================================================
    tables = {
        # --- ENVANTER ---
        "pcs": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            pc_no NVARCHAR(100),
            location_code NVARCHAR(100),
            keyos_location NVARCHAR(255),
            on_field BIT DEFAULT 1,
            warehouse BIT DEFAULT 0,
            is_faulty BIT DEFAULT 0,
            without_location BIT DEFAULT 0,
            pending_installation BIT DEFAULT 0,
            ip NVARCHAR(50),
            mac NVARCHAR(100),
            connected_printers NVARCHAR(MAX),
            pc_serial NVARCHAR(100),
            monitor_serial NVARCHAR(100),
            monitor2_serial NVARCHAR(100),
            windows BIT DEFAULT 1,
            keyos BIT DEFAULT 0,
            rdp BIT DEFAULT 0,
            pr6900 NVARCHAR(100),
            pr5200 NVARCHAR(100),
            pr8690 NVARCHAR(100),
            by_serial NVARCHAR(100),
            bo_serial NVARCHAR(100),
            scanner_serial NVARCHAR(100),
            description NVARCHAR(MAX),
            last_counted_at DATETIME,
            counted_by NVARCHAR(255),
            hostname NVARCHAR(100),
            device_type NVARCHAR(50) DEFAULT 'PC',
            hostname_mismatch BIT DEFAULT 0,
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        "queing_machines": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            pc_no NVARCHAR(100),
            location_code NVARCHAR(100),
            on_field BIT DEFAULT 1,
            warehouse BIT DEFAULT 0,
            is_faulty BIT DEFAULT 0,
            without_location BIT DEFAULT 0,
            pending_installation BIT DEFAULT 0,
            ip NVARCHAR(50),
            mac NVARCHAR(100),
            serial_no NVARCHAR(100),
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        "tablets": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            pc_no NVARCHAR(100),
            location_code NVARCHAR(100),
            on_field BIT DEFAULT 1,
            warehouse BIT DEFAULT 0,
            is_faulty BIT DEFAULT 0,
            without_location BIT DEFAULT 0,
            pending_installation BIT DEFAULT 0,
            ip NVARCHAR(50),
            mac NVARCHAR(100),
            serial_no NVARCHAR(100),
            assigned_to NVARCHAR(255),
            phone NVARCHAR(100),
            title NVARCHAR(255),
            unit NVARCHAR(100),
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        "monitors": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255),
            location_code NVARCHAR(100),
            on_field BIT DEFAULT 1,
            warehouse BIT DEFAULT 0,
            is_faulty BIT DEFAULT 0,
            without_location BIT DEFAULT 0,
            in_service BIT DEFAULT 0,
            model NVARCHAR(100),
            serial_no NVARCHAR(100),
            mac NVARCHAR(100),
            assigned_to NVARCHAR(255),
            notes NVARCHAR(MAX),
            status NVARCHAR(50),
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        # --- YAZICILAR ---
        "printers": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            pr_no NVARCHAR(100),
            model NVARCHAR(100),
            serial_no NVARCHAR(100),
            mac NVARCHAR(100),
            ip NVARCHAR(50),
            location_code NVARCHAR(255),
            cups_location NVARCHAR(255),
            cups_queue_name NVARCHAR(255),
            on_field BIT DEFAULT 1,
            warehouse BIT DEFAULT 0,
            is_faulty BIT DEFAULT 0,
            without_location BIT DEFAULT 0,
            in_service BIT DEFAULT 0,
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        "barcode_printers": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255),
            serial_no NVARCHAR(100),
            status NVARCHAR(50),
            pc_no NVARCHAR(100),
            location_code NVARCHAR(255),
            on_field BIT DEFAULT 1,
            warehouse BIT DEFAULT 0,
            is_faulty BIT DEFAULT 0,
            without_location BIT DEFAULT 0,
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        "barcode_readers": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255),
            serial_no NVARCHAR(100),
            status NVARCHAR(50),
            pc_no NVARCHAR(100),
            location_code NVARCHAR(255),
            on_field BIT DEFAULT 1,
            warehouse BIT DEFAULT 0,
            is_faulty BIT DEFAULT 0,
            without_location BIT DEFAULT 0,
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        "scanners": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255),
            model NVARCHAR(100),
            serial_no NVARCHAR(100),
            status NVARCHAR(50),
            pc_no NVARCHAR(100),
            location_code NVARCHAR(255),
            on_field BIT DEFAULT 1,
            warehouse BIT DEFAULT 0,
            is_faulty BIT DEFAULT 0,
            without_location BIT DEFAULT 0,
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        "printer_service": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            pr_no NVARCHAR(100),
            sla_no NVARCHAR(100),
            serial_no NVARCHAR(100),
            mac NVARCHAR(100),
            location_code NVARCHAR(255),
            model NVARCHAR(100),
            acquisition_date DATETIME,
            sent_date DATETIME,
            return_date DATETIME,
            fault_description NVARCHAR(MAX),
            has_substitute BIT DEFAULT 0,
            substitute_pr_no NVARCHAR(100),
            status NVARCHAR(50),
            user_name NVARCHAR(255),
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        "printer_service_history": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            pr_no NVARCHAR(100),
            location_code NVARCHAR(255),
            serial_no NVARCHAR(100),
            fault_description NVARCHAR(MAX),
            status NVARCHAR(50),
            sent_date DATETIME,
            return_date DATETIME,
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        # --- BILGI BANKASI ---
        "technical_notes": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            title NVARCHAR(255),
            content NVARCHAR(MAX),
            requires_user BIT DEFAULT 0,
            user_name NVARCHAR(255),
            image_path NVARCHAR(MAX),
            is_restricted BIT DEFAULT 0,
            allowed_users NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        "closure_notes": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            title NVARCHAR(255),
            content NVARCHAR(MAX),
            requires_user BIT DEFAULT 0,
            user_name NVARCHAR(255),
            image_path NVARCHAR(MAX),
            is_restricted BIT DEFAULT 0,
            allowed_users NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        "troubleshooting_notes": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            title NVARCHAR(255),
            content NVARCHAR(MAX),
            requires_user BIT DEFAULT 0,
            user_name NVARCHAR(255),
            image_path NVARCHAR(MAX),
            is_restricted BIT DEFAULT 0,
            allowed_users NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        # --- ORTAK ALANLAR ---
        "shared_areas": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255),
            path NVARCHAR(MAX),
            username NVARCHAR(100),
            password NVARCHAR(255),
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        # --- DEPO ---
        "depot_items": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            category NVARCHAR(100),
            name NVARCHAR(255),
            critical_stock INT DEFAULT 0,
            current_stock INT DEFAULT 0,
            unit NVARCHAR(50) DEFAULT 'Adet',
            description NVARCHAR(MAX),
            field_stock INT DEFAULT 0,
            faulty_stock INT DEFAULT 0,
            lost_stock INT DEFAULT 0,
            total_stock INT DEFAULT 0,
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        "depot_transactions": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_type NVARCHAR(50) DEFAULT 'depot',
            transaction_type NVARCHAR(50),
            quantity INT NOT NULL,
            previous_stock INT NOT NULL,
            new_stock INT NOT NULL,
            username NVARCHAR(100),
            created_at DATETIME DEFAULT GETDATE(),
            description NVARCHAR(MAX)
        )""",

        "consumable_items": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            category NVARCHAR(100),
            name NVARCHAR(255),
            critical_stock INT DEFAULT 0,
            current_stock INT DEFAULT 0,
            unit NVARCHAR(50) DEFAULT 'Adet',
            description NVARCHAR(MAX),
            field_stock INT DEFAULT 0,
            total_stock INT DEFAULT 0,
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        # --- MAHAL ---
        "mahal_list": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            location_code NVARCHAR(100),
            location_name NVARCHAR(255),
            phone_number NVARCHAR(100),
            tower NVARCHAR(50),
            floor NVARCHAR(50),
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        # --- KULLANICILAR ---
        "users": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(100) UNIQUE,
            password_hash NVARCHAR(MAX),
            display_name NVARCHAR(255),
            role NVARCHAR(50) DEFAULT 'USER',
            permissions NVARCHAR(MAX),
            bim_user NVARCHAR(100),
            bim_pass NVARCHAR(255),
            keyos_user NVARCHAR(100),
            keyos_pass NVARCHAR(255),
            last_login DATETIME,
            session_timeout INT DEFAULT 60,
            session_token NVARCHAR(MAX),
            trusted_ips NVARCHAR(MAX),
            last_activity DATETIME,
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        "user_sessions": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL,
            session_token NVARCHAR(MAX) NOT NULL,
            ip_address NVARCHAR(100),
            user_agent NVARCHAR(MAX),
            is_trusted BIT DEFAULT 0,
            created_at DATETIME DEFAULT GETDATE(),
            last_activity DATETIME DEFAULT GETDATE()
        )""",

        # --- ENTEGRASYONLAR ---
        "external_integrations": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            site_code NVARCHAR(100) UNIQUE,
            base_url NVARCHAR(255),
            auth_username NVARCHAR(255),
            auth_password NVARCHAR(255),
            api_key NVARCHAR(255),
            settings_json NVARCHAR(MAX),
            is_active BIT DEFAULT 1,
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",

        # --- GECMIS ---
        "audit_logs": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            timestamp DATETIME DEFAULT GETDATE(),
            table_name NVARCHAR(100),
            record_id INT,
            record_label NVARCHAR(255),
            field_name NVARCHAR(255),
            old_value NVARCHAR(MAX),
            new_value NVARCHAR(MAX),
            changed_by NVARCHAR(100),
            display_name NVARCHAR(255),
            client_ip NVARCHAR(50),
            client_mac NVARCHAR(100),
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",
        
        "refresh_tokens": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL,
            token NVARCHAR(MAX) NOT NULL,
            expires_at DATETIME NOT NULL,
            revoked BIT DEFAULT 0,
            replaced_by_token NVARCHAR(MAX),
            client_ip NVARCHAR(50),
            user_agent NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",
        
        "user_activity_log": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            timestamp DATETIME DEFAULT GETDATE(),
            user_id INT,
            username NVARCHAR(100),
            action NVARCHAR(255),
            details NVARCHAR(MAX),
            client_ip NVARCHAR(50),
            user_agent NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE(),
            last_edit_date DATETIME,
            last_edit_user NVARCHAR(255),
            is_deleted BIT DEFAULT 0,
            archive_date DATETIME,
            deleted_at DATETIME
        )""",
        "sync_status": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            operation NVARCHAR(100),
            status NVARCHAR(50),
            details NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE()
        )""",
        "sync_logs": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            sync_id INT,
            log_message NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE()
        )""",
        "printer_page_logs": """(
            id INT IDENTITY(1,1) PRIMARY KEY,
            pr_no NVARCHAR(100),
            serial_no NVARCHAR(100),
            location_code NVARCHAR(255),
            ip_address NVARCHAR(50),
            page_count INT,
            timestamp DATETIME DEFAULT GETDATE(),
            created_at DATETIME DEFAULT GETDATE()
        )"""
    }

    # --- TABLOLARI SIFIRDAN OLUŞTURMA VE ŞEMA ZORLAMASI ---
    # SADECE EKSIK OLANLARI OLUSTUR
    for table_name, schema in tables.items():
        try:
            cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.tables WHERE name='{table_name}') CREATE TABLE [{table_name}] {schema}")
        except Exception as e:
            print(f"[CREATE HATA] {table_name}: {e}")

    # GARANTI: refresh_tokens eger hala yoksa zorla olustur (Sysobjects veya sys.tables sorunu varsa diye)
    try:
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name='refresh_tokens')
        BEGIN
            CREATE TABLE refresh_tokens (
                id INT IDENTITY(1,1) PRIMARY KEY,
                user_id INT NOT NULL,
                token NVARCHAR(MAX) NOT NULL,
                expires_at DATETIME NOT NULL,
                revoked BIT DEFAULT 0,
                replaced_by_token NVARCHAR(MAX),
                created_at DATETIME DEFAULT GETDATE(),
                client_ip NVARCHAR(50),
                user_agent NVARCHAR(MAX)
            )
        END
        
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('refresh_tokens') AND name = 'replaced_by_token')
        BEGIN
            ALTER TABLE refresh_tokens ADD replaced_by_token NVARCHAR(MAX)
        END
        
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('users') AND name = 'trusted_ips')
        BEGIN
            ALTER TABLE users ADD trusted_ips NVARCHAR(MAX)
        END
        
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('users') AND name = 'session_token')
        BEGIN
            ALTER TABLE users ADD session_token NVARCHAR(MAX)
        END
        """)
    except Exception as e:
        print(f"[CRITICAL CREATE HATA] refresh_tokens: {e}")

    # --- Admin kullanicisi ---
    try:
        from werkzeug.security import generate_password_hash
        admin_default_pass = os.getenv("ADMIN_DEFAULT_PASS", "change_me_immediately")
        admin_pw_hash = generate_password_hash(admin_default_pass)
        cursor.execute(
            "IF EXISTS (SELECT * FROM users WHERE username='vefa') "
            "UPDATE users SET role='ADMIN' WHERE username='vefa' "
            "ELSE INSERT INTO users (username, password_hash, display_name, role) "
            "VALUES ('vefa', ?, 'Vefa', 'ADMIN')",
            (admin_pw_hash,)
        )
    except Exception as e:
        print(f"[ADMIN SEED] {e}")

    # Sütun bazlı güncellemeler (archive_date ve deleted_at ekle)
    for t in tables.keys():
        try:
            cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('{t}') AND name = 'archive_date') ALTER TABLE {t} ADD archive_date DATETIME")
            cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('{t}') AND name = 'deleted_at') ALTER TABLE {t} ADD deleted_at DATETIME")
        except Exception as e:
            print(f"[DB Schema Update Error] archive_date/deleted_at eklenemedi: {e}")

    # NULL TEMIZLIGI (AŞAMA 5)
    try:
        cursor.execute("""
            UPDATE users 
            SET 
                bim_user = ISNULL(bim_user, ''),
                bim_pass = ISNULL(bim_pass, ''),
                keyos_user = ISNULL(keyos_user, ''),
                keyos_pass = ISNULL(keyos_pass, ''),
                session_timeout = ISNULL(session_timeout, 30)
        """)
    except Exception as e:
        print(f"[NULL CLEANUP] {e}")

    required_columns = [
        ("pcs", "is_deleted", "BIT DEFAULT 0"),
        ("pcs", "on_field", "BIT DEFAULT 1"),
        ("pcs", "is_faulty", "BIT DEFAULT 0"),
        ("pcs", "warehouse", "BIT DEFAULT 0"),
        ("pcs", "without_location", "BIT DEFAULT 0"),
        ("printers", "is_deleted", "BIT DEFAULT 0"),
        ("printers", "cups_queue_name", "NVARCHAR(255)"),
        ("tablets", "is_deleted", "BIT DEFAULT 0"),
        ("tablets", "serial_no", "NVARCHAR(100)"),
        ("queing_machines", "is_deleted", "BIT DEFAULT 0"),
        ("monitors", "is_deleted", "BIT DEFAULT 0"),
        ("barcode_printers", "is_deleted", "BIT DEFAULT 0"),
        ("barcode_printers", "location_code", "NVARCHAR(255)"),
        ("barcode_printers", "on_field", "BIT DEFAULT 1"),
        ("barcode_printers", "warehouse", "BIT DEFAULT 0"),
        ("barcode_printers", "is_faulty", "BIT DEFAULT 0"),
        ("barcode_printers", "without_location", "BIT DEFAULT 0"),
        ("barcode_readers", "is_deleted", "BIT DEFAULT 0"),
        ("barcode_readers", "location_code", "NVARCHAR(255)"),
        ("barcode_readers", "on_field", "BIT DEFAULT 1"),
        ("barcode_readers", "warehouse", "BIT DEFAULT 0"),
        ("barcode_readers", "is_faulty", "BIT DEFAULT 0"),
        ("barcode_readers", "without_location", "BIT DEFAULT 0"),
        ("scanners", "is_deleted", "BIT DEFAULT 0"),
        ("scanners", "location_code", "NVARCHAR(255)"),
        ("scanners", "on_field", "BIT DEFAULT 1"),
        ("scanners", "warehouse", "BIT DEFAULT 0"),
        ("scanners", "is_faulty", "BIT DEFAULT 0"),
        ("scanners", "without_location", "BIT DEFAULT 0"),
        ("depot_items", "is_deleted", "BIT DEFAULT 0"),
        ("depot_items", "total_stock", "INT DEFAULT 0"),
        ("depot_items", "current_stock", "INT DEFAULT 0"),
        ("depot_items", "field_stock", "INT DEFAULT 0"),
        ("depot_items", "faulty_stock", "INT DEFAULT 0"),
        ("depot_items", "lost_stock", "INT DEFAULT 0"),
        ("consumable_items", "is_deleted", "BIT DEFAULT 0"),
        ("consumable_items", "total_stock", "INT DEFAULT 0"),
        ("consumable_items", "current_stock", "INT DEFAULT 0"),
        ("consumable_items", "field_stock", "INT DEFAULT 0"),
        ("technical_notes", "is_restricted", "BIT DEFAULT 0"),
        ("technical_notes", "allowed_users", "NVARCHAR(MAX)"),
        ("closure_notes", "is_restricted", "BIT DEFAULT 0"),
        ("closure_notes", "allowed_users", "NVARCHAR(MAX)"),
        ("troubleshooting_notes", "is_restricted", "BIT DEFAULT 0"),
        ("troubleshooting_notes", "allowed_users", "NVARCHAR(MAX)"),
        # --- EXCEL ALIGNMENT MIGRATIONS ---
        ("mahal_list", "location_name", "NVARCHAR(255)"),
        ("mahal_list", "phone_number", "NVARCHAR(100)"),
        ("printer_service", "acquisition_date", "DATETIME"),
        ("printer_service", "fault_description", "NVARCHAR(MAX)"),
        ("printer_service_history", "fault_description", "NVARCHAR(MAX)"),
        ("shared_areas", "username", "NVARCHAR(100)"),
        ("shared_areas", "password", "NVARCHAR(255)"),
        ("audit_logs", "client_mac", "NVARCHAR(100)"),
        ("users", "permissions", "NVARCHAR(MAX)"),
        ("users", "bim_user", "NVARCHAR(100)"),
        ("users", "bim_pass", "NVARCHAR(255)"),
        ("users", "keyos_user", "NVARCHAR(100)"),
        ("users", "keyos_pass", "NVARCHAR(255)")
    ]

    for table, col, dtype in required_columns:
        try:
            cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('{table}') AND name = '{col}') ALTER TABLE {table} ADD {col} {dtype}")
        except Exception as e:
            print(f"Migration error adding column {col} to {table}: {e}")

    # Force resize existing password columns in users table to support Fernet encryption (NVARCHAR(255))
    for col in ["bim_pass", "keyos_pass"]:
        try:
            cursor.execute(f"IF EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('users') AND name = '{col}') ALTER TABLE users ALTER COLUMN [{col}] NVARCHAR(255)")
        except Exception as e:
            print(f"Migration error altering column {col} in users: {e}")

    # --- ZORUNLU ŞEMA GÜNCELLEME (MIGRATION) ---
    for table in ["pcs", "printers", "tablets", "queing_machines", "barcode_printers", "barcode_readers", "scanners", "depot_items", "consumable_items"]:
        try:
            cursor.execute(f"UPDATE {table} SET is_deleted = 0 WHERE is_deleted IS NULL")
        except Exception as e:
            print(f"[DB Schema Update Error] {table} is_deleted güncellenemedi: {e}")

    # --- COLUMN TYPE CORRECTIONS (DATETIME Normalization) ---
    # Clean up bad string representations — only when column is still varchar/nvarchar
    date_clean_targets = [
        ("printer_service", ["acquisition_date", "sent_date", "return_date"]),
        ("printer_service_history", ["sent_date", "return_date"])
    ]
    for tbl, cols in date_clean_targets:
        for col in cols:
            try:
                cursor.execute(f"""
                    IF EXISTS (SELECT 1 FROM sys.tables WHERE name = '{tbl}')
                       AND EXISTS (
                           SELECT 1 FROM sys.columns c
                           JOIN sys.types t ON c.system_type_id = t.system_type_id
                           WHERE c.object_id = OBJECT_ID('{tbl}') AND c.name = '{col}'
                             AND t.name IN ('varchar','nvarchar','char','nchar')
                       )
                    BEGIN
                        UPDATE [{tbl}] SET [{col}] = NULL
                        WHERE TRY_CONVERT(DATETIME, [{col}]) IS NULL AND [{col}] IS NOT NULL
                    END
                """)
            except Exception as e:
                print(f"Migration error cleaning {tbl} {col}: {e}")

    type_corrections = [
        ("printer_service", "acquisition_date", "DATETIME"),
        ("printer_service", "sent_date", "DATETIME"),
        ("printer_service", "return_date", "DATETIME"),
        ("printer_service_history", "sent_date", "DATETIME"),
        ("printer_service_history", "return_date", "DATETIME"),
        ("user_sessions", "session_token", "NVARCHAR(MAX)"),
        ("user_sessions", "user_agent", "NVARCHAR(MAX)")
    ]
    for table, col, dtype in type_corrections:
        try:
            # Only ALTER if table exists and column is still varchar/nvarchar
            cursor.execute(f"""
                IF EXISTS (SELECT 1 FROM sys.tables WHERE name = '{table}')
                   AND EXISTS (
                       SELECT 1 FROM sys.columns c
                       JOIN sys.types t ON c.system_type_id = t.system_type_id
                       WHERE c.object_id = OBJECT_ID('{table}') AND c.name = '{col}'
                         AND t.name IN ('varchar','nvarchar','char','nchar','text','ntext')
                   )
                BEGIN
                    ALTER TABLE [{table}] ALTER COLUMN [{col}] {dtype}
                END
            """)
        except Exception as e:
            print(f"Migration error altering {col} in {table}: {e}")

    # --- DATA COPY MIGRATIONS (BACKWARD COMPATIBILITY) ---
    data_migrations = [
        ("mahal_list", "mahal_adi", "location_name"),
        ("mahal_list", "telefon", "phone_number"),
        ("printer_service", "acq_date", "acquisition_date"),
        ("printer_service", "fault_desc", "fault_description"),
        ("printer_service_history", "fault_desc", "fault_description"),
        ("shared_areas", "user", "username"),
        ("depot_items", "saha_stock", "field_stock"),
        ("depot_items", "arizali_stock", "faulty_stock"),
        ("depot_items", "kayip_stock", "lost_stock"),
        ("consumable_items", "saha_stock", "field_stock")
    ]
    for table, old_col, new_col in data_migrations:
        try:
            cursor.execute(f"SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('{table}') AND name = '{old_col}'")
            has_old = cursor.fetchone()
            cursor.execute(f"SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('{table}') AND name = '{new_col}'")
            has_new = cursor.fetchone()
            if has_old and has_new:
                # Replace bad string representations with NULL
                if old_col in ('acq_date', 'sent_date', 'return_date'):
                    cursor.execute(f"UPDATE {table} SET {old_col} = NULL WHERE {old_col} = '-' OR {old_col} = 'None' OR {old_col} = ''")
                
                # Copy values
                if new_col in ('acquisition_date', 'sent_date', 'return_date'):
                    # Safe conversion to DATETIME
                    cursor.execute(f"UPDATE {table} SET {new_col} = TRY_CONVERT(DATETIME, {old_col}, 104) WHERE {new_col} IS NULL AND {old_col} IS NOT NULL")
                else:
                    cursor.execute(f"UPDATE {table} SET {new_col} = {old_col} WHERE {new_col} IS NULL AND {old_col} IS NOT NULL")
        except Exception as e:
            print(f"Migration error copying data from {old_col} to {new_col} in {table}: {e}")

    try:
        # external_integrations tablosunda integration_name yanlislikla olusturulduysa site_code olarak degistir.
        cursor.execute("IF EXISTS(SELECT * FROM sys.columns WHERE Name = N'integration_name' AND Object_ID = Object_ID(N'external_integrations')) BEGIN EXEC sp_rename 'external_integrations.integration_name', 'site_code', 'COLUMN' END")
    except Exception as e:
        print(f"Migration error renaming integration_name to site_code: {e}")


    # --- INDEX YAPILANDIRMASI (PERFORMANS IYILESTIRMESI) ---
    # Anayasa Madde 9: Eski kolon adlari (pc_seri, mahal_kodu) yasaktir.
    # Guncel kolon adlari kullanilmaktadir.
    indexes = [
        ("idx_pcs_location_code", "pcs", "location_code"),
        ("idx_pcs_pc_serial", "pcs", "pc_serial"),
        ("idx_pcs_ip", "pcs", "ip"),
        ("idx_pcs_is_deleted", "pcs", "is_deleted"),
        ("idx_mahal_list_location_code", "mahal_list", "location_code"),
        ("idx_printers_location_code", "printers", "location_code"),
        ("idx_printers_serial_number", "printers", "serial_number"),
        ("idx_printers_is_deleted", "printers", "is_deleted"),
        ("idx_printers_ip", "printers", "ip"),
        ("idx_tablets_is_deleted", "tablets", "is_deleted"),
        ("idx_monitors_is_deleted", "monitors", "is_deleted")
    ]
    for idx_name, tbl_name, col_name in indexes:
        try:
            cursor.execute(f"""
                IF EXISTS (
                    SELECT 1 FROM sys.columns
                    WHERE object_id = OBJECT_ID('{tbl_name}') AND name = '{col_name}'
                      AND max_length > 0 AND max_length <= 1700
                )
                AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = '{idx_name}' AND object_id = OBJECT_ID('{tbl_name}'))
                BEGIN
                    CREATE INDEX {idx_name} ON {tbl_name}({col_name})
                END
            """)
        except Exception as e:
            print(f"Migration error creating index {idx_name}: {e}")

    conn.commit()
    conn.close()
    print(f"DB: {DB_NAME} Hazir. (v12.9 — Excel Uyumlu Şema ve Performans Indeksleri)")

def query_db(query, args=(), one=False):
    """Veritabaninda sorgu calistirir ve sonuclari sozluk (dict) listesi olarak doner.
    Context Manager (with) kullanilarak baglanti guvenligi saglanmistir.
    """
    conn = get_db_connection()
    if not conn:
        return None
        
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(query, args)
                if query.strip().upper().startswith("SELECT"):
                    description = cursor.description
                    if not description:
                        return []
                    columns = [column[0].lower() for column in description]
                    from core.utils import normalize_row
                    results = [normalize_row(dict(zip(columns, row))) for row in cursor.fetchall()]
                    return (results[0] if results else None) if one else results
                conn.commit()
                return True
    except Exception as e:
        # Kurumsal guvenlik: Sadece logla, disariya sistem sirdirmadan genel hata don
        print(f"Database Query Error: {e}")
        print(f"Failed Query: {query}")
        print(f"Query Args: {args}")
        return None

# init_db()  <-- MODUL SEVIYESINDE CAGIRILMAMALI. main.py veya manuel tetiklenmeli.
