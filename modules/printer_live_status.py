import requests
import re
import urllib3
import json
import os
import concurrent.futures

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
CACHE_FILE = os.path.join(BASE_DIR, 'database', 'printer_live_status.json')

def fetch_printer_status(ip):
    """
    Fetches the toner and device status from a printer's IP.
    Currently specifically tailored for Brother MFC-L6900DW series, but can be expanded.
    """
    result = {
        "status": "Bilinmiyor",
        "toner": "Bilinmiyor",
        "is_online": False
    }
    
    if not ip or not isinstance(ip, str) or len(ip.strip()) < 7:
        return result
        
    try:
        # Try fetching the status page
        url = f"http://{ip}/general/status.html"
        resp = requests.get(url, timeout=3, verify=False)
        result["is_online"] = True
        
        if resp.status_code == 200:
            content = resp.content
            # Safe decoding with Turkish fallback
            encoding = None
            content_type = resp.headers.get('content-type', '').lower()
            if 'charset=' in content_type:
                encoding = content_type.split('charset=')[-1].strip()
            
            if not encoding:
                charset_match = re.search(rb'charset=["\']?([a-zA-Z0-9_-]+)', content[:2000], re.IGNORECASE)
                if charset_match:
                    encoding = charset_match.group(1).decode('ascii', errors='ignore').strip()
            
            html = None
            encodings_to_try = []
            if encoding:
                encodings_to_try.append(encoding)
            encodings_to_try.extend(['utf-8', 'windows-1254', 'iso-8859-9'])
            
            for enc in encodings_to_try:
                try:
                    html = content.decode(enc)
                    break
                except Exception:
                    continue
            
            if html is None:
                html = content.decode(resp.apparent_encoding or 'utf-8', errors='replace')

            # Try to parse toner level
            # Look for <img ... class="tonerremain" height="50" />
            toner_match = re.search(r'class="tonerremain"\s+height="(\d+)"', html)
            if toner_match:
                height = int(toner_match.group(1))
                # 50 represents 100%
                percentage = int((height / 50.0) * 100)
                result["toner"] = f"%{min(percentage, 100)}"
                
            # Try to parse device status
            # Look for <span class="moni moniOk">Uyku                  </span>
            status_match = re.search(r'<span class="moni[^>]*>([^<]+)</span>', html)
            if status_match:
                result["status"] = status_match.group(1).strip()
    except Exception as e:
        # Printer is probably offline
        pass
        
    return result

def update_live_status_cache(printers):
    """
    Given a list of printer dicts (from DB), fetches their status and writes to cache.
    """
    cache = {}
    
    def fetch_and_map(p):
        ip = p.get('ip')
        pr_no = p.get('pr_no')
        if ip and pr_no:
            status = fetch_printer_status(ip)
            return pr_no, status
        return None
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(fetch_and_map, printers)
        for res in results:
            if res:
                cache[res[0]] = res[1]
                
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[Printer Cache Error] {e}")

_PRINTER_LIVE_CACHE = None
_PRINTER_LIVE_MTIME = 0

def get_live_status_cache():
    global _PRINTER_LIVE_CACHE, _PRINTER_LIVE_MTIME
    try:
        if not os.path.exists(CACHE_FILE):
            return {}
            
        current_mtime = os.path.getmtime(CACHE_FILE)
        if _PRINTER_LIVE_CACHE is not None and current_mtime == _PRINTER_LIVE_MTIME:
            return _PRINTER_LIVE_CACHE
            
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            _PRINTER_LIVE_CACHE = json.load(f)
            _PRINTER_LIVE_MTIME = current_mtime
            return _PRINTER_LIVE_CACHE
    except Exception:
        pass
    return {}
