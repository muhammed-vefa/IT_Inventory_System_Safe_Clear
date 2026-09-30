from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection
from core.auth import require_auth, require_admin
from modules.inventory_core import check_column_exists
import traceback

building_map_bp = Blueprint('building_map_bp', __name__)

@building_map_bp.route('/layout/<building_name>', methods=['GET'])
@require_auth
def get_layout(building_name):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check and Init DB
        cursor.execute("IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='building_layouts' and xtype='U') SELECT 0 ELSE SELECT 1")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                CREATE TABLE building_layouts (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    building_name NVARCHAR(50),
                    floor_level INT,
                    wing NVARCHAR(50),
                    department_name NVARCHAR(200),
                    last_updated_by NVARCHAR(100),
                    last_updated_at DATETIME DEFAULT GETDATE()
                )
            ''')
            conn.commit()
            
        # Default seeding if empty (Oto-onarım ve ilk kurulum)
        # A KULE: 11 floors * 4 wings = 44
        cursor.execute("SELECT COUNT(*) FROM building_layouts WHERE building_name = 'A KULE'")
        a_count = cursor.fetchone()[0]
        if a_count < 44:
            cursor.execute("DELETE FROM building_layouts WHERE building_name = 'A KULE'")
            data = []
            for f in range(2, 9):
                data.extend([(f, 'T5', None), (f, 'T6', None), (f, 'T7', None), (f, 'T8', None)])
            data_dict = {
                8: {'T6': 'ENFEKSİYON', 'T8': 'PSİKİYATRİ'},
                7: {'T5': 'GASTRO / ENDOKRİN', 'T6': 'İÇ HASTALIKLARI 1', 'T7': 'İÇ HASTALIKLARI 2', 'T8': 'NEFROLOJİ'},
                6: {'T5': 'GENEL CERRAHİ 1', 'T6': 'GENEL CERRAHİ 2', 'T7': 'GENEL CERRAHİ 3', 'T8': 'NÖROLOJİ'},
                5: {'T5': 'ORTOPEDİ 1', 'T6': 'ORTOPEDİ 2', 'T7': 'ORTOPEDİ 3 / ÜROLOJİ', 'T8': 'BEYİN CERRAHİ'},
                4: {'T5': 'KARDİYOLOJİ', 'T6': 'GÖZ - PLASTİK', 'T7': 'ÜROLOJİ', 'T8': 'KBB'},
                3: {'T5': 'REA 3', 'T6': 'GÖĞÜS HASTALIKLARI', 'T7': 'REA 4', 'T8': 'KVC'},
                2: {'T6': 'MESCİT'}
            }
            for i, row in enumerate(data):
                f, w, _ = row
                if f in data_dict and w in data_dict[f]:
                    data[i] = (f, w, data_dict[f][w])
            for f, w, d in data:
                cursor.execute('INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by) VALUES (?, ?, ?, ?, ?)', ('A KULE', f, w, d, 'System'))
            conn.commit()

        # B KULE: 8 floors * 4 wings = 32
        cursor.execute("SELECT COUNT(*) FROM building_layouts WHERE building_name = 'B KULE'")
        b_count = cursor.fetchone()[0]
        if b_count < 32:
            cursor.execute("DELETE FROM building_layouts WHERE building_name = 'B KULE'")
            data_b = []
            for f in range(-1, 7): 
                data_b.extend([(f, 'T1', f'{f}. KAT T1'), (f, 'T2', f'{f}. KAT T2'), (f, 'T3', f'{f}. KAT T3'), (f, 'T4', f'{f}. KAT T4')])
            for f, w, d in data_b:
                cursor.execute('INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by) VALUES (?, ?, ?, ?, ?)', ('B KULE', f, w, d, 'System'))
            conn.commit()
            
        # MH: 5 floors (-2 to 2) * 4 wings = 20
        cursor.execute("SELECT COUNT(*) FROM building_layouts WHERE building_name = 'MH'")
        mh_count = cursor.fetchone()[0]
        if mh_count < 20:
            cursor.execute("DELETE FROM building_layouts WHERE building_name = 'MH'")
            data_mh = []
            for f in range(-2, 3): 
                data_mh.extend([(f, 'M0', f'{f}. KAT M0'), (f, 'M1', f'{f}. KAT M1'), (f, 'M2', f'{f}. KAT M2'), (f, 'M3', f'{f}. KAT M3')])
            for f, w, d in data_mh:
                cursor.execute('INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by) VALUES (?, ?, ?, ?, ?)', ('MH', f, w, d, 'System'))
            conn.commit()
            
        # FTR: 4 floors (-1 to 2) * 2 wings = 8
        cursor.execute("SELECT COUNT(*) FROM building_layouts WHERE building_name = 'FTR' AND wing = 'F1'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("DELETE FROM building_layouts WHERE building_name = 'FTR'")
            data_ftr = []
            for f in range(-1, 3): 
                data_ftr.extend([(f, 'F1', f'{f}. KAT F1'), (f, 'F2', f'{f}. KAT F2')])
            for f, w, d in data_ftr:
                cursor.execute('INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by) VALUES (?, ?, ?, ?, ?)', ('FTR', f, w, d, 'System'))
            conn.commit()
            
        # TSB: 3 floors (-2 to 0) * 3 wings = 9
        cursor.execute("SELECT COUNT(*) FROM building_layouts WHERE building_name = 'TSB' AND wing = 'S1'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("DELETE FROM building_layouts WHERE building_name = 'TSB'")
            data_tsb = []
            for f in range(-2, 1): 
                data_tsb.extend([(f, 'S1', f'{f}. KAT S1'), (f, 'S2', f'{f}. KAT S2'), (f, 'S3', f'{f}. KAT S3')])
            for f, w, d in data_tsb:
                cursor.execute('INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by) VALUES (?, ?, ?, ?, ?)', ('TSB', f, w, d, 'System'))
            conn.commit()
            
        # YGAP: 4 floors (-1 to 2) * 2 wings = 8
        cursor.execute("SELECT COUNT(*) FROM building_layouts WHERE building_name = 'YGAP' AND wing = 'P1'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("DELETE FROM building_layouts WHERE building_name = 'YGAP'")
            data_ygap = []
            for f in range(-1, 3): 
                data_ygap.extend([(f, 'P1', f'{f}. KAT P1'), (f, 'P2', f'{f}. KAT P2')])
            for f, w, d in data_ygap:
                cursor.execute('INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by) VALUES (?, ?, ?, ?, ?)', ('YGAP', f, w, d, 'System'))
            conn.commit()
            
        # Safe column checks
        pcs_has_deleted = check_column_exists("pcs", "is_deleted")
        pcs_has_faulty = check_column_exists("pcs", "is_faulty")
        pr_has_deleted = check_column_exists("printers", "is_deleted")
        pr_has_faulty = check_column_exists("printers", "is_faulty")
        
        pcs_del_clause = "(p.is_deleted=0 OR p.is_deleted IS NULL) AND" if pcs_has_deleted else ""
        pcs_faulty_clause = "p.is_faulty = 1 AND" if pcs_has_faulty else "0=1 AND"

        pr_del_clause = "(pr.is_deleted=0 OR pr.is_deleted IS NULL) AND" if pr_has_deleted else ""
        pr_faulty_clause = "pr.is_faulty = 1 AND" if pr_has_faulty else "0=1 AND"

        # Sadece var olan veriyi çek ve arızalı cihaz sayısını pcs ve printers tablolarından getir
        # "mahal bilgisinde kanat yazıyor" dendiği için b.department_name yerine b.wing kullanıyoruz, ancak kat bilgisini de ekliyoruz!
        # Yeni format desteği: a.07.t6.343 -> 07.t6 veya -1.t6, 0. kat için G0
        query = f"""
            SELECT b.floor_level, b.wing, b.department_name,
                   (
                       (SELECT COUNT(*) FROM pcs p WHERE {pcs_del_clause} {pcs_faulty_clause} p.location_code LIKE '%' + b.wing + '%' AND (p.location_code LIKE '%' + RIGHT('0' + CAST(b.floor_level AS VARCHAR), 2) + '.' + b.wing + '%' OR p.location_code LIKE '%' + CAST(b.floor_level AS VARCHAR) + '. KAT%' OR (b.floor_level = 0 AND (p.location_code LIKE '%ZEMİN%' OR p.location_code LIKE '%G0.' + b.wing + '%'))))
                       +
                       (SELECT COUNT(*) FROM printers pr WHERE {pr_del_clause} {pr_faulty_clause} pr.location_code LIKE '%' + b.wing + '%' AND (pr.location_code LIKE '%' + RIGHT('0' + CAST(b.floor_level AS VARCHAR), 2) + '.' + b.wing + '%' OR pr.location_code LIKE '%' + CAST(b.floor_level AS VARCHAR) + '. KAT%' OR (b.floor_level = 0 AND (pr.location_code LIKE '%ZEMİN%' OR pr.location_code LIKE '%G0.' + b.wing + '%'))))
                   ) as faulty_count
            FROM building_layouts b
            WHERE b.building_name = ?
            ORDER BY b.floor_level DESC
        """
            
        cursor.execute(query, (building_name,))
        rows = cursor.fetchall()
        
        # Katlara ve kanatlara gore grupla
        floors = {}
        all_wings = set()
        for r in rows:
            floor = r[0]
            wing = r[1]
            dept = r[2]
            faulty_count = r[3]
            
            all_wings.add(wing)
            if floor not in floors:
                floors[floor] = {}
            floors[floor][wing] = {"dept": dept, "faulty": faulty_count > 0}

        all_wings = sorted(list(all_wings))

        # Formatli liste olustur
        layout = []
        for f in sorted(floors.keys(), reverse=True):
            row_data = {"floor": f}
            for w in all_wings:
                # To maintain compatibility with JS, return object for each wing instead of string
                row_data[w.lower()] = floors[f].get(w)
            layout.append(row_data)

        conn.close()
        return jsonify({"success": True, "layout": layout, "wings": all_wings})
    except Exception as e:
        print("GET LAYOUT ERROR:", traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@building_map_bp.route('/update', methods=['POST'])
@require_admin
def update_layout():
    try:
        data = request.json
        building = data.get('building')
        floor = data.get('floor')
        wing = data.get('wing')
        dept = data.get('dept')
        user = request.user.get('username', 'System')
        
        if not building or floor is None or not wing:
            return jsonify({"error": "Eksik bilgi"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Update or Insert
        cursor.execute("""
            SELECT id FROM building_layouts 
            WHERE building_name=? AND floor_level=? AND wing=?
        """, (building, floor, wing))
        row = cursor.fetchone()
        
        if row:
            cursor.execute("""
                UPDATE building_layouts 
                SET department_name=?, last_updated_by=?, last_updated_at=GETDATE()
                WHERE id=?
            """, (dept if dept else None, user, row[0]))
        else:
            cursor.execute("""
                INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by)
                VALUES (?, ?, ?, ?, ?)
            """, (building, floor, wing, dept if dept else None, user))
            
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Güncellendi"})
    except Exception as e:
        print("UPDATE DEPT ERROR:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@building_map_bp.route('/devices', methods=['GET'])
@require_auth
def get_devices():
    try:
        dept = request.args.get('department')
        wing = request.args.get('wing')
        floor = request.args.get('floor')
        
        # Mahal bilgisinde zaten T4, T5 gibi kanatlar yazıyor. Kanata göre arayalım:
        search_wing = wing if wing and wing != 'undefined' else ''
        if not search_wing:
            # Fallback
            search_wing = dept.split(' ')[-1] if (dept and ' ' in dept) else dept
            
        search_term = f"%{search_wing}%"
        
        # Kat SQL şartı (a.07.t6.343 gibi formatlar için)
        if floor is not None and floor != 'undefined':
            try:
                floor_int = int(floor)
                # 7 -> 07, ama -1 -> -1
                floor_pad = f"0{floor_int}" if 0 <= floor_int < 10 else str(floor_int)
                floor_clause = f"AND (location_code LIKE '%{floor_pad}.{search_wing}%' OR location_code LIKE '%{floor}. KAT%' OR ({floor} = 0 AND (location_code LIKE '%ZEMİN%' OR location_code LIKE '%G0.{search_wing}%')))"
            except ValueError:
                floor_clause = f"AND (location_code LIKE '%{floor}. KAT%' OR location_code LIKE '%ZEMİN%')"
        else:
            floor_clause = ""
        
        pcs_has_deleted = check_column_exists("pcs", "is_deleted")
        pcs_has_faulty = check_column_exists("pcs", "is_faulty")
        pr_has_deleted = check_column_exists("printers", "is_deleted")
        pr_has_faulty = check_column_exists("printers", "is_faulty")
        
        pcs_del_clause = "(is_deleted=0 OR is_deleted IS NULL) AND" if pcs_has_deleted else ""
        pr_del_clause = "(is_deleted=0 OR is_deleted IS NULL) AND" if pr_has_deleted else ""

        # PCs tablosundan sorgula
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT * 
            FROM pcs 
            WHERE {pcs_del_clause} location_code LIKE ? {floor_clause}
        """, (search_term,))
        pc_cols = [column[0].lower() for column in cursor.description]
        pc_rows = cursor.fetchall()
        
        pcs = []
        for r in pc_rows:
            row_dict = dict(zip(pc_cols, r))
            pcs.append({
                "id": row_dict.get('id'),
                "type": "pc",
                "name": row_dict.get('pc_no') or row_dict.get('hostname') or 'Bilinmiyor',
                "ip": row_dict.get('ip') or 'Yok',
                "is_faulty": 1 if (pcs_has_faulty and row_dict.get('is_faulty')) else 0
            })
            
        # Yazicilari bul
        cursor.execute(f"""
            SELECT *
            FROM printers 
            WHERE {pr_del_clause} location_code LIKE ? {floor_clause}
        """, (search_term,))
        pr_cols = [column[0].lower() for column in cursor.description]
        pr_rows = cursor.fetchall()
        
        printers = []
        for r in pr_rows:
            row_dict = dict(zip(pr_cols, r))
            printers.append({
                "id": row_dict.get('id'),
                "type": "printer",
                "name": row_dict.get('pr_no') or row_dict.get('model') or 'Bilinmiyor',
                "ip": row_dict.get('ip') or 'Yok',
                "is_faulty": 1 if (pr_has_faulty and row_dict.get('is_faulty')) else 0
            })
            
        conn.close()
        return jsonify({"success": True, "pcs": pcs, "printers": printers})
    except Exception as e:
        print("GET DEVICES ERROR:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@building_map_bp.route('/init', methods=['GET'])
def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='building_layouts' and xtype='U')
            CREATE TABLE building_layouts (
                id INT IDENTITY(1,1) PRIMARY KEY,
                building_name NVARCHAR(50),
                floor_level INT,
                wing NVARCHAR(50),
                department_name NVARCHAR(200),
                last_updated_by NVARCHAR(100),
                last_updated_at DATETIME DEFAULT GETDATE()
            )
        ''')
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM building_layouts WHERE building_name = 'A KULE'")
        if cursor.fetchone()[0] == 0:
            data_a = [
                (8, 'T5', None), (8, 'T6', 'ENFEKSİYON'), (8, 'T7', None), (8, 'T8', 'PSİKİYATRİ'),
                (7, 'T5', 'GASTRO / ENDOKRİN'), (7, 'T6', 'İÇ HASTALIKLARI 1'), (7, 'T7', 'İÇ HASTALIKLARI 2'), (7, 'T8', 'NEFROLOJİ'),
                (6, 'T5', 'GENEL CERRAHİ 1'), (6, 'T6', 'GENEL CERRAHİ 2'), (6, 'T7', 'GENEL CERRAHİ 3'), (6, 'T8', 'NÖROLOJİ'),
                (5, 'T5', 'ORTOPEDİ 1'), (5, 'T6', 'ORTOPEDİ 2'), (5, 'T7', 'ORTOPEDİ 3 / ÜROLOJİ'), (5, 'T8', 'BEYİN CERRAHİ'),
                (4, 'T5', 'KARDİYOLOJİ'), (4, 'T6', 'GÖZ - PLASTİK'), (4, 'T7', 'ÜROLOJİ'), (4, 'T8', 'KBB'),
                (3, 'T5', 'REA 3'), (3, 'T6', 'GÖĞÜS HASTALIKLARI'), (3, 'T7', 'REA 4'), (3, 'T8', 'KVC'),
                (2, 'T5', None), (2, 'T6', 'MESCİT'), (2, 'T7', None), (2, 'T8', None),
                (1, 'T5', 'KORONER 1'), (1, 'T6', None), (1, 'T7', 'REA 1'), (1, 'T8', 'REA 2'),
                (0, 'T5', 'SAĞLIK KURULU'), (0, 'T6', None), (0, 'T7', 'YANIK'), (0, 'T8', 'KORONER 2'),
                (-1, 'T5', 'A4-A3 POL'), (-1, 'T6', None), (-1, 'T7', 'HEMODİYALİZ'), (-1, 'T8', 'A5 POL'),
                (-2, 'T5', 'A1-A2 POL'), (-2, 'T6', None), (-2, 'T7', None), (-2, 'T8', 'TUTUKLU / OTOPSİ')
            ]
            for f, w, d in data:
                cursor.execute('INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by) VALUES (?, ?, ?, ?, ?)', ('A KULE', f, w, d, 'System'))
            conn.commit()
            return jsonify({"message": "Table created and seeded."})
        return jsonify({"message": "Table exists and already seeded."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
