import requests
from bs4 import BeautifulSoup
import re
import urllib3
import json
import os
import socket
import concurrent.futures

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
CACHE_FILE = os.path.join(BASE_DIR, 'database', 'printer_live_status.json')

STATUS_MAP_TR = {
    "ready": "Hazır",
    "hazır": "Hazır",
    "sleep": "Uyku",
    "uyku": "Uyku",
    "uykuda": "Uyku",
    "deep sleep": "Derin Uyku",
    "derin uyku": "Derin Uyku",
    "derin uykuda": "Derin Uyku",
    "printing": "Yazdırılıyor",
    "yazdırılıyor": "Yazdırılıyor",
    "yazdırıyor": "Yazdırılıyor",
    "warming up": "Isınıyor",
    "warm up": "Isınıyor",
    "ısınıyor": "Isınıyor",
    "cooling down": "Soğutuluyor",
    "soğutuluyor": "Soğutuluyor",
    "cover open": "Kapak Açık",
    "kapak açık": "Kapak Açık",
    "door open": "Kapak Açık",
    "no paper": "Kağıt Yok",
    "kağıt yok": "Kağıt Yok",
    "paper empty": "Kağıt Yok",
    "out of paper": "Kağıt Yok",
    "paper jam": "Kağıt Sıkışması",
    "kağıt sıkışması": "Kağıt Sıkışması",
    "jam tray": "Kağıt Sıkışması",
    "jam inside": "Kağıt Sıkışması",
    "jam rear": "Kağıt Sıkışması",
    "toner low": "Toner Az",
    "toner az": "Toner Az",
    "replace toner": "Toner Bitti / Değiştir",
    "toner bitti": "Toner Bitti / Değiştir",
    "replace drum": "Drum Değiştir",
    "drum değiştir": "Drum Değiştir",
    "drum near end": "Drum Ömrü Az",
    "drum end soon": "Drum Ömrü Az",
}

def _is_ip_reachable(ip, timeout=0.35):
    """
    Hızlı port kontrolü (Port 80 HTTP, 443 HTTPS, 9100 RAW, 515 LPR, 631 IPP).
    Yazıcı kapalıysa saniyelerce beklemek yerine 0.35 saniyede tespit eder.
    """
    for port in (80, 443, 9100, 515, 631):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            res = s.connect_ex((ip, port))
            s.close()
            if res == 0:
                return True, port
        except Exception:
            pass
    return False, None

def _decode_html(resp):
    content = resp.content
    encoding = None
    content_type = resp.headers.get('content-type', '').lower()
    if 'charset=' in content_type:
        encoding = content_type.split('charset=')[-1].strip()
    
    if not encoding:
        charset_match = re.search(rb'charset=["\']?([a-zA-Z0-9_-]+)', content[:2000], re.IGNORECASE)
        if charset_match:
            encoding = charset_match.group(1).decode('ascii', errors='ignore').strip()
    
    encodings_to_try = []
    if encoding:
        encodings_to_try.append(encoding)
    encodings_to_try.extend(['utf-8', 'windows-1254', 'iso-8859-9', 'cp1252'])
    
    for enc in encodings_to_try:
        try:
            return content.decode(enc)
        except Exception:
            continue
    return content.decode(resp.apparent_encoding or 'utf-8', errors='replace')

def _parse_html_status_and_toner(html):
    """
    Brother yazıcıların tüm modelleri için (MFC-L6900DW, HL-L5210DN, DCP-L5510DN,
    MFC-L5510DN, HL-L5200DW vb.) web arayüzünden durum ve toner bilgilerini ayrıştırır.
    """
    status = "Bilinmiyor"
    toner = "Bilinmiyor"
    maintenance_msg = ""
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 0. Menü, navigasyon, kenar çubuğu ve başlıkları temizle (Menü öğelerinin durum sanılmasını engeller)
    for nav in soup.find_all(id=re.compile(r'(menu|nav|navigation|headerFrame|footerFrame|LayoutButton)', re.I)):
        nav.decompose()
    for nav in soup.find_all(class_=re.compile(r'(menu|nav|sidebar|links)', re.I)):
        nav.decompose()

    # 1. Bakım / Uyarı Mesajları Taraması
    m_keywords = [
        ("Drum Değiştir", "Drum Değiştir"), ("Replace Drum", "Drum Değiştir"),
        ("Drum Near End", "Drum Ömrü Az"), ("Drum Ömrü Az", "Drum Ömrü Az"),
        ("Replace Toner", "Toner Bitti"), ("Toner Düşük", "Toner Az"),
        ("Toner Low", "Toner Az"), ("Toner Az", "Toner Az"),
        ("Kapak Açık", "Kapak Açık"), ("Cover Open", "Kapak Açık"),
        ("Door Open", "Kapak Açık"), ("Kağıt Yok", "Kağıt Yok"),
        ("No Paper", "Kağıt Yok"), ("Paper Jam", "Kağıt Sıkışması"),
        ("Sıkışma", "Kağıt Sıkışması"), ("Jam Tray", "Kağıt Sıkışması")
    ]
    html_lower = html.lower()
    for kw, norm in m_keywords:
        if kw.lower() in html_lower:
            maintenance_msg = norm
            break

    # 2. CİHAZ DURUMU (STATUS) TESPİTİ
    # Yöntem A: 'moni' class'lı span / div / elementler (Brother standardı)
    moni_span = soup.find('span', class_=re.compile(r'moni', re.I))
    if moni_span:
        t = moni_span.get_text(strip=True)
        if t and "refresh" not in t.lower() and "interval" not in t.lower():
            status = t

    # Yöntem B: ID bazlı arama (moni_data, status, state, disp_area)
    if status == "Bilinmiyor":
        moni_el = soup.find(id=re.compile(r'(moni_data|monidata|status|state|disp_area)', re.I))
        if moni_el:
            t = moni_el.get_text(strip=True)
            if t and "refresh" not in t.lower() and "interval" not in t.lower():
                status = t

    # Yöntem C: JavaScript moni_data dizisi (Örn: moni_data = ["Sleep", 85, ...])
    if status == "Bilinmiyor":
        js_match = re.search(r"moni_data\s*=\s*\[(.*?)\]", html)
        if js_match:
            parts = [p.strip().replace('"', '').replace("'", '') for p in js_match.group(1).split(',')]
            if len(parts) > 0 and parts[0] and "refresh" not in parts[0].lower():
                status = parts[0]

    # Yöntem D: Etiket (Device Status / Durum hücresinin yanındaki değer)
    if status == "Bilinmiyor":
        label = soup.find(string=re.compile(r'(Device\s*Status|Cihaz\s*Durumu)', re.I))
        if label:
            val = label.find_next(['dd', 'td', 'span', 'div', 'p'])
            if val:
                t = val.get_text(strip=True)
                if t and t.lower() not in ['status', 'durum', 'cihaz durumu', 'device status', 'automatic refresh'] and "refresh" not in t.lower():
                    status = t

    # Yöntem E: Genel metin içi durum anahtar kelimeleri
    if status == "Bilinmiyor":
        text_content = soup.get_text()
        kw_list = [
            ("Derin Uykuda", "Derin Uyku"), ("Derin Uyku", "Derin Uyku"), ("Deep Sleep", "Derin Uyku"),
            ("Uykuda", "Uyku"), ("Uyku", "Uyku"), ("Sleep", "Uyku"),
            ("Hazır", "Hazır"), ("Ready", "Hazır"),
            ("Yazdırılıyor", "Yazdırılıyor"), ("Printing", "Yazdırılıyor"),
            ("Isınıyor", "Isınıyor"), ("Warming Up", "Isınıyor"), ("Warm Up", "Isınıyor"),
            ("Soğutuluyor", "Soğutuluyor"), ("Cooling Down", "Soğutuluyor"),
            ("Kapak Açık", "Kapak Açık"), ("Cover Open", "Kapak Açık"), ("Door Open", "Kapak Açık"),
            ("Kağıt Sıkışması", "Kağıt Sıkışması"), ("Paper Jam", "Kağıt Sıkışması"), ("Jam Tray", "Kağıt Sıkışması"),
            ("Kağıt Yok", "Kağıt Yok"), ("No Paper", "Kağıt Yok"), ("Out of Paper", "Kağıt Yok"),
            ("Toner Az", "Toner Az"), ("Toner Low", "Toner Az"),
            ("Toner Bitti", "Toner Bitti / Değiştir"), ("Replace Toner", "Toner Bitti / Değiştir")
        ]
        for kw, norm in kw_list:
            if re.search(r'\b' + re.escape(kw) + r'\b', text_content, re.I):
                status = norm
                break

    # Durum metnini Türkçe karşılığına çevir
    st_clean = status.strip().lower()
    if st_clean in STATUS_MAP_TR:
        status = STATUS_MAP_TR[st_clean]

    if maintenance_msg and maintenance_msg.lower() not in status.lower():
        status = f"{status} ({maintenance_msg})"

    # 3. TONER SEVİYESİ TESPİTİ
    # Yöntem A: JS moni_data dizisi
    js_match = re.search(r"moni_data\s*=\s*\[(.*?)\]", html)
    if js_match:
        parts = [p.strip().replace('"', '').replace("'", '') for p in js_match.group(1).split(',')]
        if len(parts) > 1 and parts[1].isdigit():
            val = int(parts[1])
            if 0 <= val <= 100:
                toner = f"%{val}"

    # Yöntem B: 'tonerremain' sınıfı veya toner görseli (Brother 6900/5200/5210/5510)
    # 6900 modellerinde 50px = %100; 5210 ve 5510 modellerinde 56px = %100
    if toner == "Bilinmiyor":
        toner_imgs = soup.find_all('img', class_=re.compile(r'tonerremain', re.I))
        if not toner_imgs:
            toner_imgs = soup.find_all('img', src=re.compile(r'toner.*remain|black\.gif|toner.*\.gif', re.I))
            
        for img in toner_imgs:
            h = img.get('height')
            w = img.get('width')
            val = None
            if h and str(h).isdigit():
                val = int(h)
            elif w and str(w).isdigit():
                val = int(w)
                
            if val is not None:
                if val <= 50:
                    pct = int((val / 50.0) * 100)
                elif val <= 56:
                    pct = int((val / 56.0) * 100)
                elif val <= 100:
                    pct = val
                elif val <= 160:
                    pct = int((val / 160.0) * 100)
                else:
                    pct = 100
                toner = f"%{min(max(pct, 0), 100)}"
                break

    # Yöntem C: Tablo satırlarında Toner / Siyah / Black araması
    if toner == "Bilinmiyor":
        for tr in soup.find_all('tr'):
            row_txt = tr.get_text()
            if re.search(r'toner|siyah|black', row_txt, re.I):
                pct_match = re.search(r'(\d{1,3})\s*%', row_txt)
                if pct_match:
                    v = int(pct_match.group(1))
                    if 0 <= v <= 100:
                        toner = f"%{v}"
                        break

    # Yöntem D: Regex ile Toner yüzdesi arama
    if toner == "Bilinmiyor":
        m = re.search(r'(?:Toner|Black|Siyah)[^<\n\r]{0,30}?(?:Seviyesi|Level|Remaining|Kalan)?[:\s]+%?\s*(\d{1,3})\s*%?', html, re.I)
        if m:
            val = int(m.group(1))
            if 0 <= val <= 100:
                toner = f"%{val}"

    return status, toner

def _query_snmp_status_and_toner(ip, timeout=0.4):
    """
    Brother yazıcılarda SNMP UDP port 161 üzerinden hızlı durum ve toner sorgulaması.
    """
    try:
        oid_status = (1, 3, 6, 1, 2, 1, 25, 3, 5, 1, 1, 1)
        oid_bytes = bytearray([oid_status[0] * 40 + oid_status[1]])
        for val in oid_status[2:]:
            if val < 128:
                oid_bytes.append(val)
            else:
                sub = []
                while val > 0:
                    sub.append(val & 0x7F)
                    val >>= 7
                sub.reverse()
                for i in range(len(sub) - 1):
                    sub[i] |= 0x80
                oid_bytes.extend(sub)
                
        oid_len = len(oid_bytes)
        varbind = bytearray([0x30, oid_len + 4, 0x06, oid_len]) + oid_bytes + bytearray([0x05, 0x00])
        varbind_list = bytearray([0x30, len(varbind)]) + varbind
        pdu_body = bytearray([0x02, 0x01, 0x01, 0x02, 0x01, 0x00, 0x02, 0x01, 0x00]) + varbind_list
        pdu = bytearray([0xA0, len(pdu_body)]) + pdu_body
        community = b'public'
        snmp_body = bytearray([0x02, 0x01, 0x00, 0x04, len(community)]) + bytearray(community) + pdu
        packet = bytearray([0x30, len(snmp_body)]) + snmp_body
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(packet, (ip, 161))
        data, _ = sock.recvfrom(1024)
        sock.close()
        
        if data and len(data) > 20:
            pdu_idx = data.find(b'\xA2')
            if pdu_idx != -1:
                last_byte = data[-1]
                status_val = int(last_byte)
                status_map = {1: "Diğer", 2: "Bilinmiyor", 3: "Hazır", 4: "Yazdırılıyor", 5: "Isınıyor"}
                if status_val in status_map:
                    return status_map[status_val], "Normal", True
    except Exception:
        pass
    return None, None, False

def fetch_printer_status(ip):
    """
    Brother yazıcılardan (MFC-L6900DW, HL-L5210DN, DCP-L5510DN, MFC-L5510DN, HL-L5200DW vb.)
    toner seviyesi ve canlı durum bilgisini çeker.
    """
    result = {
        "status": "Bilinmiyor",
        "toner": "Bilinmiyor",
        "is_online": False
    }
    
    if not ip or not isinstance(ip, str) or len(ip.strip()) < 7 or ip.strip() in ["-", "None", "0"]:
        return result
        
    ip = ip.strip()
    
    # 1. Hızlı erişilebilirlik kontrolü
    reachable, open_port = _is_ip_reachable(ip, timeout=0.35)
    if not reachable:
        return result
        
    result["is_online"] = True
    proto = "https" if open_port == 443 else "http"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    session = requests.Session()

    # 2. Öncelikli olarak monitor.html uç noktaları (DCP-L5510DN / HL-L5210DN dinamik canlı LCD durumu)
    monitor_urls = [
        f"{proto}://{ip}/home/monitor.html",
        f"{proto}://{ip}/general/monitor.html",
        f"{proto}://{ip}/common/monitor.html",
        f"{proto}://{ip}/monitor.html"
    ]
    for m_url in monitor_urls:
        try:
            m_resp = session.get(m_url, timeout=1.5, verify=False, headers=headers)
            if m_resp.status_code == 200 and m_resp.content:
                html = _decode_html(m_resp)
                st, _ = _parse_html_status_and_toner(html)
                if st != "Bilinmiyor":
                    result["status"] = st
                    break
        except Exception:
            continue

    # 3. Sayfa içi durum ve toner seviyesi uç noktaları
    status_urls = [
        f"{proto}://{ip}/home/status.html",
        f"{proto}://{ip}/general/status.html",
        f"{proto}://{ip}/general/information.html",
        f"{proto}://{ip}/common/status.html",
        f"{proto}://{ip}/status/status.html",
        f"{proto}://{ip}/etc/mnt_info.html",
        f"{proto}://{ip}/main/main.html",
        f"{proto}://{ip}/"
    ]
    
    for url in status_urls:
        try:
            resp = session.get(url, timeout=2.0, verify=False, headers=headers, allow_redirects=True)
            if resp.status_code == 200 and resp.content:
                html = _decode_html(resp)
                st, tn = _parse_html_status_and_toner(html)
                
                if result["status"] == "Bilinmiyor" and st != "Bilinmiyor":
                    result["status"] = st
                if result["toner"] == "Bilinmiyor" and tn != "Bilinmiyor":
                    result["toner"] = tn
                    
                # Hem durum hem toner bulunduysa döngüden çık
                if result["status"] != "Bilinmiyor" and result["toner"] != "Bilinmiyor":
                    return result
        except Exception:
            continue

    # 4. HTTP ile durum veya toner bulunamadıysa SNMP Fallback
    if result["status"] == "Bilinmiyor" or result["toner"] == "Bilinmiyor":
        snmp_st, snmp_tn, snmp_ok = _query_snmp_status_and_toner(ip, timeout=0.4)
        if snmp_ok:
            if result["status"] == "Bilinmiyor" and snmp_st:
                result["status"] = snmp_st
            if result["toner"] == "Bilinmiyor" and snmp_tn:
                result["toner"] = snmp_tn

    # 5. Yazıcı online fakat durum henüz okunamadıysa varsayılan 'Hazır' ver
    if result["is_online"] and result["status"] == "Bilinmiyor":
        result["status"] = "Hazır"
        
    return result

def update_live_status_cache(printers):
    """
    Veritabanındaki yazıcı listesini alarak canlı durumlarını çeker ve JSON önbelleğe yazar.
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
