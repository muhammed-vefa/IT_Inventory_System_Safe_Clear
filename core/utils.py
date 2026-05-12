import re

def _clean(v):
    """Değeri normalize eder: strip + upper."""
    if v is None: return ""
    return str(v).strip().upper()

def _norm_key(k):
    """Başlık adını Türkçe karakter ve boşluk bağımsız normalize eder (header matching için)."""
    if not k: return ""
    # Önce Unicode olarak büyük harfe çevir
    s = str(k).upper()
    
    # UTF-8 bozulmalarını temizle
    replacements = {
        'Ä°': 'I', 'Ğ': 'G', 'Ü': 'U', 'Ş': 'S', 'Ö': 'O', 'Ç': 'C',
        'ı': 'I', 'ğ': 'G', 'ü': 'U', 'ş': 'S', 'ö': 'O', 'ç': 'C',
        'Ä': 'I', 'Å': 'S', 'Ã': 'A' # Genel bozulmalar
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
        
    # Standart Türkçe karakterleri Latinize et (Eşleşme garantisi için)
    tr_map = {
        'İ': 'I', 'I': 'I', 'ı': 'I', 'İ': 'I',
        'Ğ': 'G', 'Ü': 'U', 'Ş': 'S', 'Ö': 'O', 'Ç': 'C',
        '': 'A', 'Î': 'I', 'Û': 'U'
    }
    for tr, lat in tr_map.items():
        s = s.replace(tr, lat)
        
    # Sadece harf ve rakam bırak, boşlukları normalize et
    s = re.sub(r'[^A-Z0-9]', ' ', s)
    return ' '.join(s.split()).strip()

def _get(item, variants):
    """item dict içinde birden fazla olası başlık adını arar (Normalizasyon ile)."""
    if not item: return None
    # Önce normalized key map oluştur (item anahtarları için)
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
        return str(int(float(s)))
    except:
        return s.lstrip('0') or '0' if s else ''
