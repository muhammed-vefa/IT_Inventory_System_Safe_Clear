from flask import Blueprint, jsonify
from core.database_sql import query_db
from core.auth import require_auth
import pandas as pd
import os

mahal_manager_bp = Blueprint('mahal_manager', __name__)

EXCEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'mahal_telefon.xlsx'))

@mahal_manager_bp.route('/get_all', methods=['GET'])
@require_auth
def get_mahal_data():
    """Mahal ve telefon verilerini birleştirerek döndürür."""
    if not os.path.exists(EXCEL_PATH):
        return jsonify({"error": "mahal_telefon.xlsx bulunamadı"}), 404
    
    try:
        # Mahal sayfasını oku (İŞLETME MAHALİ, MAHAL ADI)
        df_mahal = pd.read_excel(EXCEL_PATH, sheet_name='mahal')
        # Telefon sayfasını oku (mahal tel, tel)
        df_tel = pd.read_excel(EXCEL_PATH, sheet_name='telefon')
        
        # Sütun isimlerini normalize et (dosyadaki garip karakterler için)
        # Mahal sayfası
        mahal_cols = df_mahal.columns.tolist()
        code_col = mahal_cols[0] # İŞLETME MAHALİ
        name_col = mahal_cols[1] # MAHAL ADI
        
        # Telefon sayfası
        tel_cols = df_tel.columns.tolist()
        tel_code_col = tel_cols[0] # mahal tel
        phone_val_col = tel_cols[1] # tel
        
        # Listeleri hazırla
        mahal_list = []
        tel_map = {}
        
        # Telefonları map'e al (kolay erişim için)
        for _, row in df_tel.iterrows():
            code = str(row[tel_code_col]).strip()
            phone = str(row[phone_val_col]).strip()
            if code and code != 'nan':
                tel_map[code] = phone if phone != 'nan' else ''
        
        # Mahalleri hazırla
        seen_codes = set()
        for _, row in df_mahal.iterrows():
            code = str(row[code_col]).strip()
            name = str(row[name_col]).strip()
            
            if not code or code == 'nan' or code in seen_codes:
                continue
            
            seen_codes.add(code)
            
            # Kule ve Kat bilgisini koddan ayıklama (Örn: A.05... -> Kule=A, Kat=05)
            # Eğer kodda nokta varsa parçala
            parts = code.split('.')
            kule = parts[0] if len(parts) > 0 else ''
            kat = parts[1] if len(parts) > 1 else ''
            
            mahal_list.append({
                "code": code,
                "name": name if name != 'nan' else '',
                "kule": kule,
                "kat": kat,
                "phone": tel_map.get(code, '')
            })
            
        return jsonify(mahal_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
