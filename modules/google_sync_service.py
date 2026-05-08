"""
Google Sheets Yedekleme Servisi - Altyapı Modülü
=================================================
Bu modül, Google Sheets'e veri yazmak için gerekli altyapıyı içerir.
Kullanım için bir Google Cloud Service Account JSON dosyası gereklidir.

Adımlar:
1. https://console.cloud.google.com/ adresine gidin
2. Yeni proje oluşturun veya mevcut projeyi seçin
3. "Google Sheets API" etkinleştirin
4. Kimlik Bilgileri > Hizmet Hesabı oluşturun
5. JSON anahtar dosyasını indirin
6. Bu dosyayı `database/google_credentials.json` olarak kaydedin
7. Google Sheets'te hedef tabloyu oluşturun ve Hizmet Hesabı e-postasını paylaşın
"""

import os
import json

CREDENTIALS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'google_credentials.json'))
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'google_config.json'))


def is_google_sync_enabled():
    """Google Sheets senkronizasyonunun aktif olup olmadığını kontrol eder."""
    return os.path.exists(CREDENTIALS_PATH) and os.path.exists(CONFIG_PATH)


def get_google_config():
    """Google config dosyasını okur. Örnek: {"spreadsheet_id": "...", "sheet_name": "Envanter"}"""
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def sync_to_google_sheets(data_rows, sheet_name="Envanter"):
    """
    Veriyi Google Sheets'e yazar.
    
    Args:
        data_rows: List[dict] - Yazılacak veriler
        sheet_name: str - Sayfa adı
    
    Returns:
        bool - Başarılı mı
    """
    if not is_google_sync_enabled():
        print("Google Sync: Devre dışı (credentials dosyası bulunamadı)")
        return False
    
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        
        config = get_google_config()
        if not config:
            print("Google Sync: Config dosyası bulunamadı")
            return False
        
        spreadsheet_id = config.get('spreadsheet_id')
        if not spreadsheet_id:
            print("Google Sync: spreadsheet_id bulunamadı")
            return False
        
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        
        # Başlıkları yaz
        if not data_rows:
            return True
        
        headers = list(data_rows[0].keys())
        values = [headers]
        for row in data_rows:
            values.append([str(row.get(h, '')) for h in headers])
        
        # Sayfayı temizle ve yaz
        range_name = f"{sheet_name}!A1"
        
        # Önce temizle
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A:ZZ"
        ).execute()
        
        # Sonra yaz
        body = {'values': values}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"Google Sync: {len(data_rows)} satır '{sheet_name}' sayfasına yazıldı")
        return True
        
    except ImportError:
        print("Google Sync: google-api-python-client paketi yüklü değil. Çalıştırın: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        return False
    except Exception as e:
        print(f"Google Sync Hatası: {e}")
        return False


def create_sample_config():
    """Örnek config dosyası oluşturur."""
    if os.path.exists(CONFIG_PATH):
        return
    
    sample = {
        "spreadsheet_id": "BURAYA_GOOGLE_SHEETS_ID_YAZIN",
        "sheet_envanter": "Envanter",
        "sheet_yazicilar": "Yazıcılar",
        "sheet_depo": "Depo"
    }
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(sample, f, indent=2, ensure_ascii=False)
    print(f"Google Sync: Örnek config oluşturuldu: {CONFIG_PATH}")
