import pyodbc, os

def get_db_connection():
    # Yaygin sunucu isimlerini dene
    server_names = [".", "localhost", r".\SQLEXPRESS", os.environ.get("COMPUTERNAME", "localhost")]
    
    for server in server_names:
        conn_str = (
            f"Driver={{SQL Server}};"
            f"Server={server};"
            "Database=IT_Inventory;"
            "Trusted_Connection=yes;"
            "Connection Timeout=5;" # Hizli timeout
        )
        try:
            conn = pyodbc.connect(conn_str, autocommit=True)
            print(f"[+] Veritabanı bağlantısı başarılı: {server}")
            return conn
        except:
            continue
            
    print("[-] Hiçbir SQL Server instance'ına bağlanılamadı!")
    return None

def init_db():
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    tables = [
        """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='inventory' AND xtype='U')
        CREATE TABLE inventory (
            id INT IDENTITY(1,1) PRIMARY KEY,
            pc_no NVARCHAR(50), ip NVARCHAR(50), kule NVARCHAR(50),
            mahal_kodu NVARCHAR(50), mahal_adi NVARCHAR(255), seri_no NVARCHAR(100),
            mac_adresi NVARCHAR(100), windows BIT, keyos BIT, sahada BIT,
            note NVARCHAR(MAX), last_seen DATETIME,
            type NVARCHAR(50) DEFAULT 'PC'
        )""",
        """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='printers' AND xtype='U')
        CREATE TABLE printers (
            id INT IDENTITY(1,1) PRIMARY KEY,
            pr_no NVARCHAR(50), mahal NVARCHAR(255), model NVARCHAR(100),
            seri_no NVARCHAR(100), ip NVARCHAR(50), status NVARCHAR(50),
            note NVARCHAR(MAX), last_updated DATETIME DEFAULT GETDATE(),
            type NVARCHAR(50) DEFAULT 'PR'
        )""",
        """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='shared_areas' AND xtype='U')
        CREATE TABLE shared_areas (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255), [user] NVARCHAR(100), password NVARCHAR(100), path NVARCHAR(MAX)
        )""",
        """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='audit_logs' AND xtype='U')
        CREATE TABLE audit_logs (
            id INT IDENTITY(1,1) PRIMARY KEY,
            timestamp DATETIME DEFAULT GETDATE(), [user] NVARCHAR(100),
            ip_address NVARCHAR(50), mac_address NVARCHAR(50), device_name NVARCHAR(100),
            table_name NVARCHAR(50), old_value NVARCHAR(MAX), new_value NVARCHAR(MAX)
        )""",
        """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
        CREATE TABLE users (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(100) UNIQUE, password NVARCHAR(255),
            display_name NVARCHAR(255), role NVARCHAR(50) DEFAULT 'VIEWER',
            permissions NVARCHAR(MAX)
        )""",
        """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='depot_items' AND xtype='U')
        CREATE TABLE depot_items (
            id INT IDENTITY(1,1) PRIMARY KEY,
            category NVARCHAR(100), name NVARCHAR(255),
            current_stock INT DEFAULT 0, critical_limit INT DEFAULT 0,
            unit NVARCHAR(50), description NVARCHAR(MAX),
            saha_count INT DEFAULT 0, arizali_count INT DEFAULT 0, kayip_count INT DEFAULT 0
        )""",
        """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='service_records' AND xtype='U')
        CREATE TABLE service_records (
            id INT IDENTITY(1,1) PRIMARY KEY,
            pr_no NVARCHAR(50), mahal NVARCHAR(255), fault_description NVARCHAR(MAX),
            acquisition_date DATETIME, sent_date DATETIME, return_date DATETIME,
            status NVARCHAR(50), created_by NVARCHAR(100),
            substitute_pr_no NVARCHAR(50), sla_no NVARCHAR(100)
        )""",
        """IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='technical_notes' AND xtype='U')
        CREATE TABLE technical_notes (
            id INT IDENTITY(1,1) PRIMARY KEY,
            device_type NVARCHAR(50), device_id INT,
            title NVARCHAR(255), content NVARCHAR(MAX),
            image_path NVARCHAR(MAX), timestamp DATETIME DEFAULT GETDATE(),
            created_by NVARCHAR(100)
        )"""
    ]
    for q in tables: cursor.execute(q)
    # Varsayılan admin
    try:
        cursor.execute("SELECT * FROM users WHERE username='vefa'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (username, password, display_name, role) VALUES (?,?,?,?)",
                         ('vefa', '123', 'Mehmet Vefa', 'ADMIN'))
    except: pass
    conn.commit()
    conn.close()
