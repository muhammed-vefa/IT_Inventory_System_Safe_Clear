import json
from core.database_sql import query_db

def get_integration_config(site_code):
    """
    Belirtilen site_code (örn. 'KEYOS', 'CUPS') için entegrasyon ayarlarını veritabanından çeker.
    Eğer bulamazsa veya aktif değilse None döner.
    """
    try:
        query = "SELECT * FROM external_integrations WHERE site_code = ? AND is_deleted = 0 AND is_active = 1"
        result = query_db(query, (site_code,), one=True)
        
        if result:
            # settings_json string olarak tutuluyorsa dict'e çevir
            if result.get('settings_json'):
                try:
                    result['settings'] = json.loads(result['settings_json'])
                except:
                    result['settings'] = {}
            else:
                result['settings'] = {}
            return result
        return None
    except Exception as e:
        print(f"[Integrations] Config çekilirken hata ({site_code}): {e}")
        return None

def get_all_integrations():
    """Tüm entegrasyon tanımlarını getirir."""
    query = "SELECT * FROM external_integrations WHERE is_deleted = 0"
    return query_db(query) or []
