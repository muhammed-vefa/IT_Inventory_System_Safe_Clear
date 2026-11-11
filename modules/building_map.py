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
        # A KULE: 7 floors (2-8) * 5 wings (T5, T6, T7, T8, C2)
        cursor.execute("SELECT COUNT(*) FROM building_layouts WHERE building_name = 'A KULE'")
        a_count = cursor.fetchone()[0]
        if a_count < 28:
            cursor.execute("DELETE FROM building_layouts WHERE building_name = 'A KULE'")
            data = []
            for f in range(2, 9):
                data.extend([(f, 'T5', None), (f, 'T6', None), (f, 'T7', None), (f, 'T8', None), (f, 'C2', 'ÇEKİRDEK')])
            data_dict = {
                8: {'T6': 'ENFEKSİYON', 'T8': 'PSİKİYATRİ', 'C2': 'ÇEKİRDEK'},
                7: {'T5': 'GASTRO / ENDOKRİN', 'T6': 'İÇ HASTALIKLARI 1', 'T7': 'İÇ HASTALIKLARI 2', 'T8': 'NEFROLOJİ', 'C2': 'ÇEKİRDEK'},
                6: {'T5': 'GENEL CERRAHİ 1', 'T6': 'GENEL CERRAHİ 2', 'T7': 'GENEL CERRAHİ 3', 'T8': 'NÖROLOJİ', 'C2': 'ÇEKİRDEK'},
                5: {'T5': 'ORTOPEDİ 1', 'T6': 'ORTOPEDİ 2', 'T7': 'ORTOPEDİ 3 / ÜROLOJİ', 'T8': 'BEYİN CERRAHİ', 'C2': 'ÇEKİRDEK'},
                4: {'T5': 'KARDİYOLOJİ', 'T6': 'GÖZ - PLASTİK', 'T7': 'ÜROLOJİ', 'T8': 'KBB', 'C2': 'ÇEKİRDEK'},
                3: {'T5': 'REA 3', 'T6': 'GÖĞÜS HASTALIKLARI', 'T7': 'REA 4', 'T8': 'KVC', 'C2': 'ÇEKİRDEK'},
                2: {'T6': 'MESCİT', 'C2': 'ÇEKİRDEK'}
            }
            for i, row in enumerate(data):
                f, w, _ = row
                if f in data_dict and w in data_dict[f]:
                    data[i] = (f, w, data_dict[f][w])
            for f, w, d in data:
                cursor.execute('INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by) VALUES (?, ?, ?, ?, ?)', ('A KULE', f, w, d, 'System'))
            conn.commit()

        # A KULE Çekirdek (C2) Eksik Katları Otomatik Tamamlama
        cursor.execute("SELECT DISTINCT floor_level FROM building_layouts WHERE building_name = 'A KULE'")
        a_floors = [r[0] for r in cursor.fetchall()]
        if not a_floors:
            a_floors = list(range(2, 9))
        for f in a_floors:
            cursor.execute("SELECT COUNT(*) FROM building_layouts WHERE building_name = 'A KULE' AND floor_level = ? AND wing = 'C2'", (f,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by) VALUES ('A KULE', ?, 'C2', 'ÇEKİRDEK', 'System')", (f,))
        conn.commit()

        # B KULE: 8 floors * 5 wings (T1, T2, T3, T4, C1)
        cursor.execute("SELECT COUNT(*) FROM building_layouts WHERE building_name = 'B KULE'")
        b_count = cursor.fetchone()[0]
        if b_count < 32:
            cursor.execute("DELETE FROM building_layouts WHERE building_name = 'B KULE'")
            data_b = []
            for f in range(-1, 7): 
                data_b.extend([(f, 'T1', f'{f}. KAT T1'), (f, 'T2', f'{f}. KAT T2'), (f, 'T3', f'{f}. KAT T3'), (f, 'T4', f'{f}. KAT T4'), (f, 'C1', 'ÇEKİRDEK')])
            for f, w, d in data_b:
                cursor.execute('INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by) VALUES (?, ?, ?, ?, ?)', ('B KULE', f, w, d, 'System'))
            conn.commit()

        # B KULE Çekirdek (C1) Eksik Katları Otomatik Tamamlama
        cursor.execute("SELECT DISTINCT floor_level FROM building_layouts WHERE building_name = 'B KULE'")
        b_floors = [r[0] for r in cursor.fetchall()]
        if not b_floors:
            b_floors = list(range(-1, 7))
        for f in b_floors:
            cursor.execute("SELECT COUNT(*) FROM building_layouts WHERE building_name = 'B KULE' AND floor_level = ? AND wing = 'C1'", (f,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by) VALUES ('B KULE', ?, 'C1', 'ÇEKİRDEK', 'System')", (f,))
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
            
        # FTR: 6 floors (-2 to 3) * 5 wings (F1, F2, F3, F4, F5)
        ftr_target_floors = list(range(-2, 4)) # -2, -1, 0, 1, 2, 3
        ftr_target_wings = ['F1', 'F2', 'F3', 'F4', 'F5']
        for f in ftr_target_floors:
            for w in ftr_target_wings:
                cursor.execute("SELECT COUNT(*) FROM building_layouts WHERE building_name = 'FTR' AND floor_level = ? AND wing = ?", (f, w))
                if cursor.fetchone()[0] == 0:
                    cursor.execute("INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by) VALUES ('FTR', ?, ?, ?, 'System')", (f, w, f'{f}. KAT {w}'))
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
            
        # YGAP: 5 floors (-1 to 3) * 5 wings (P1, P2, P3, P4, P5)
        ygap_target_floors = list(range(-1, 4)) # -1, 0, 1, 2, 3
        ygap_target_wings = ['P1', 'P2', 'P3', 'P4', 'P5']
        for f in ygap_target_floors:
            for w in ygap_target_wings:
                cursor.execute("SELECT COUNT(*) FROM building_layouts WHERE building_name = 'YGAP' AND floor_level = ? AND wing = ?", (f, w))
                if cursor.fetchone()[0] == 0:
                    cursor.execute("INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by) VALUES ('YGAP', ?, ?, ?, 'System')", (f, w, f'{f}. KAT {w}'))
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
        # Bina filtresi (A KULE ve B KULE için C2/C1 ve kanat ayrımı)
        b_clean = (building_name or '').strip().upper()
        if 'A KULE' in b_clean:
            b_filter_pc = "AND (p.location_code LIKE 'A.%' OR p.location_code LIKE '%A KULE%' OR p.location_code LIKE '%A BLOK%')"
            b_filter_pr = "AND (pr.location_code LIKE 'A.%' OR pr.location_code LIKE '%A KULE%' OR pr.location_code LIKE '%A BLOK%')"
        elif 'B KULE' in b_clean:
            b_filter_pc = "AND (p.location_code LIKE 'B.%' OR p.location_code LIKE '%B KULE%' OR p.location_code LIKE '%B BLOK%')"
            b_filter_pr = "AND (pr.location_code LIKE 'B.%' OR pr.location_code LIKE '%B KULE%' OR pr.location_code LIKE '%B BLOK%')"
        elif 'FTR' in b_clean:
            b_filter_pc = "AND (p.location_code LIKE '%FTR%' OR p.location_code LIKE '%.F%' OR p.location_code LIKE 'F.%')"
            b_filter_pr = "AND (pr.location_code LIKE '%FTR%' OR pr.location_code LIKE '%.F%' OR pr.location_code LIKE 'F.%')"
        elif 'YGAP' in b_clean:
            b_filter_pc = "AND (p.location_code LIKE '%YGAP%' OR p.location_code LIKE '%.P%' OR p.location_code LIKE 'P.%' OR p.location_code LIKE 'Y.%')"
            b_filter_pr = "AND (pr.location_code LIKE '%YGAP%' OR pr.location_code LIKE '%.P%' OR pr.location_code LIKE 'P.%' OR pr.location_code LIKE 'Y.%')"
        else:
            b_filter_pc = ""
            b_filter_pr = ""

        # Yeni format desteği: A.05.C2.591, A.07.T6.343, A.B1.C2, A.G0.C2
        floor_match_pc = """(
            (b.floor_level > 0 AND (p.location_code LIKE '%' + RIGHT('0' + CAST(b.floor_level AS VARCHAR), 2) + '.' + b.wing + '%' OR p.location_code LIKE '%' + CAST(b.floor_level AS VARCHAR) + '. KAT%'))
            OR (b.floor_level = 0 AND (p.location_code LIKE '%G0.' + b.wing + '%' OR p.location_code LIKE '%ZEMİN%'))
            OR (b.floor_level < 0 AND (p.location_code LIKE '%B' + CAST(ABS(b.floor_level) AS VARCHAR) + '.' + b.wing + '%' OR p.location_code LIKE '%-' + CAST(ABS(b.floor_level) AS VARCHAR) + '. KAT%'))
        )"""

        floor_match_pr = """(
            (b.floor_level > 0 AND (pr.location_code LIKE '%' + RIGHT('0' + CAST(b.floor_level AS VARCHAR), 2) + '.' + b.wing + '%' OR pr.location_code LIKE '%' + CAST(b.floor_level AS VARCHAR) + '. KAT%'))
            OR (b.floor_level = 0 AND (pr.location_code LIKE '%G0.' + b.wing + '%' OR pr.location_code LIKE '%ZEMİN%'))
            OR (b.floor_level < 0 AND (pr.location_code LIKE '%B' + CAST(ABS(b.floor_level) AS VARCHAR) + '.' + b.wing + '%' OR pr.location_code LIKE '%-' + CAST(ABS(b.floor_level) AS VARCHAR) + '. KAT%'))
        )"""

        query = f"""
            SELECT b.floor_level, b.wing, b.department_name,
                   (
                       (SELECT COUNT(*) FROM pcs p WHERE {pcs_del_clause} {pcs_faulty_clause} p.location_code LIKE '%' + b.wing + '%' {b_filter_pc} AND {floor_match_pc})
                       +
                       (SELECT COUNT(*) FROM printers pr WHERE {pr_del_clause} {pr_faulty_clause} pr.location_code LIKE '%' + b.wing + '%' {b_filter_pr} AND {floor_match_pr})
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

        # Kanat sıralaması: Kanatlar önce, Çekirdek (C1, C2) en sağda/sonda
        def wing_sort_key(w):
            w_up = str(w).upper()
            if w_up in ('C1', 'C2', 'ÇEKİRDEK'):
                return (1, w_up)
            return (0, w_up)

        all_wings = sorted(list(all_wings), key=wing_sort_key)

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
        data = request.json or {}
        building = data.get('building') or data.get('building_name')
        floor = data.get('floor') if data.get('floor') is not None else data.get('floor_level')
        wing = data.get('wing')
        dept = data.get('dept') if data.get('dept') is not None else data.get('department_name')
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
        building = request.args.get('building', '')
        dept = request.args.get('department')
        wing = request.args.get('wing')
        floor = request.args.get('floor')
        
        # Mahal bilgisinde kanat / çekirdek kodu yazıyor (T6, C2, C1 vb.)
        search_wing = wing if wing and wing != 'undefined' else ''
        if not search_wing:
            # Fallback
            search_wing = dept.split(' ')[-1] if (dept and ' ' in dept) else dept
            
        search_term = f"%{search_wing}%"
        
        # Bina filtresi
        building_clause = ""
        if building:
            b_clean = building.strip().upper()
            if 'A KULE' in b_clean or b_clean == 'A':
                building_clause = "AND (location_code LIKE 'A.%' OR location_code LIKE '%A KULE%' OR location_code LIKE '%A BLOK%')"
            elif 'B KULE' in b_clean or b_clean == 'B':
                building_clause = "AND (location_code LIKE 'B.%' OR location_code LIKE '%B KULE%' OR location_code LIKE '%B BLOK%')"
            elif 'MH' in b_clean:
                building_clause = "AND (location_code LIKE 'M.%' OR location_code LIKE '%MH%')"
            elif 'FTR' in b_clean:
                building_clause = "AND (location_code LIKE '%FTR%' OR location_code LIKE '%.F%' OR location_code LIKE 'F.%')"
            elif 'TSB' in b_clean:
                building_clause = "AND (location_code LIKE 'T.%' OR location_code LIKE 'S.%' OR location_code LIKE '%TSB%')"
            elif 'YGAP' in b_clean:
                building_clause = "AND (location_code LIKE '%YGAP%' OR location_code LIKE '%.P%' OR location_code LIKE 'P.%' OR location_code LIKE 'Y.%')"
        
        # Kat SQL şartı (A.05.C2.591, A.07.T6.343, A.B1.C2, A.G0.C2 gibi formatlar için)
        if floor is not None and floor != 'undefined':
            try:
                floor_int = int(floor)
                if floor_int > 0:
                    floor_pad = f"0{floor_int}" if floor_int < 10 else str(floor_int)
                    floor_clause = f"AND (location_code LIKE '%.{floor_pad}.{search_wing}%' OR location_code LIKE '%{floor_pad}.{search_wing}%' OR location_code LIKE '%{floor_int}. KAT%')"
                elif floor_int == 0:
                    floor_clause = f"AND (location_code LIKE '%.G0.{search_wing}%' OR location_code LIKE '%G0.{search_wing}%' OR location_code LIKE '%ZEMİN%')"
                else:
                    b_num = abs(floor_int)
                    floor_clause = f"AND (location_code LIKE '%.B{b_num}.{search_wing}%' OR location_code LIKE '%B{b_num}.{search_wing}%' OR location_code LIKE '%-{b_num}. KAT%')"
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
            WHERE {pcs_del_clause} location_code LIKE ? {building_clause} {floor_clause}
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
                "location_code": str(row_dict.get('location_code') or row_dict.get('keyos_location') or '').strip(),
                "is_faulty": 1 if (pcs_has_faulty and row_dict.get('is_faulty')) else 0
            })
            
        # Yazicilari bul
        cursor.execute(f"""
            SELECT *
            FROM printers 
            WHERE {pr_del_clause} location_code LIKE ? {building_clause} {floor_clause}
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
                "location_code": str(row_dict.get('location_code') or row_dict.get('cups_location') or '').strip(),
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
                (8, 'T5', None), (8, 'T6', 'ENFEKSİYON'), (8, 'T7', None), (8, 'T8', 'PSİKİYATRİ'), (8, 'C2', 'ÇEKİRDEK'),
                (7, 'T5', 'GASTRO / ENDOKRİN'), (7, 'T6', 'İÇ HASTALIKLARI 1'), (7, 'T7', 'İÇ HASTALIKLARI 2'), (7, 'T8', 'NEFROLOJİ'), (7, 'C2', 'ÇEKİRDEK'),
                (6, 'T5', 'GENEL CERRAHİ 1'), (6, 'T6', 'GENEL CERRAHİ 2'), (6, 'T7', 'GENEL CERRAHİ 3'), (6, 'T8', 'NÖROLOJİ'), (6, 'C2', 'ÇEKİRDEK'),
                (5, 'T5', 'ORTOPEDİ 1'), (5, 'T6', 'ORTOPEDİ 2'), (5, 'T7', 'ORTOPEDİ 3 / ÜROLOJİ'), (5, 'T8', 'BEYİN CERRAHİ'), (5, 'C2', 'ÇEKİRDEK'),
                (4, 'T5', 'KARDİYOLOJİ'), (4, 'T6', 'GÖZ - PLASTİK'), (4, 'T7', 'ÜROLOJİ'), (4, 'T8', 'KBB'), (4, 'C2', 'ÇEKİRDEK'),
                (3, 'T5', 'REA 3'), (3, 'T6', 'GÖĞÜS HASTALIKLARI'), (3, 'T7', 'REA 4'), (3, 'T8', 'KVC'), (3, 'C2', 'ÇEKİRDEK'),
                (2, 'T5', None), (2, 'T6', 'MESCİT'), (2, 'T7', None), (2, 'T8', None), (2, 'C2', 'ÇEKİRDEK'),
                (1, 'T5', 'KORONER 1'), (1, 'T6', None), (1, 'T7', 'REA 1'), (1, 'T8', 'REA 2'), (1, 'C2', 'ÇEKİRDEK'),
                (0, 'T5', 'SAĞLIK KURULU'), (0, 'T6', None), (0, 'T7', 'YANIK'), (0, 'T8', 'KORONER 2'), (0, 'C2', 'ÇEKİRDEK'),
                (-1, 'T5', 'A4-A3 POL'), (-1, 'T6', None), (-1, 'T7', 'HEMODİYALİZ'), (-1, 'T8', 'A5 POL'), (-1, 'C2', 'ÇEKİRDEK'),
                (-2, 'T5', 'A1-A2 POL'), (-2, 'T6', None), (-2, 'T7', None), (-2, 'T8', 'TUTUKLU / OTOPSİ'), (-2, 'C2', 'ÇEKİRDEK')
            ]
            for f, w, d in data_a:
                cursor.execute('INSERT INTO building_layouts (building_name, floor_level, wing, department_name, last_updated_by) VALUES (?, ?, ?, ?, ?)', ('A KULE', f, w, d, 'System'))
            conn.commit()
            return jsonify({"message": "Table created and seeded."})
        return jsonify({"message": "Table exists and already seeded."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
