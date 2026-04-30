import requests
from bs4 import BeautifulSoup
import re
import datetime
import os

def get_brother_printer_status(ip):
    """
    Yazıcının web arayüzünden durum, toner ve bakım (Drum vb.) bilgilerini çeker.
    Brother MFC-L6900DW ve benzeri modeller için optimize edilmiştir.
    """
    status_info = {
        "ip": ip,
        "device_status": "Bilinmiyor",
        "toner_level": "Bilinmiyor",
        "maintenance_msg": "",
        "success": False,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
    }
    
    if not ip or ip in ["-", "None", ""]:
        return status_info

    # Brother modelleri için taranacak URL'ler
    urls = [
        f"http://{ip}/general/status.html",
        f"http://{ip}/common/status.html",
        f"http://{ip}/status/status.html",
        f"http://{ip}/"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for url in urls:
        try:
            response = requests.get(url, timeout=3, verify=False, headers=headers)
            if response.ok:
                html_content = response.text
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 1. Bakım Mesajları (Drum, Fuser vb.)
                maintenance_keywords = [
                    "Drum Değiştir", "Replace Drum", "Drum Near End", "Drum Ömrü Az",
                    "Replace Toner", "Toner Düşük", "Toner Low", "Kapak Açık", "Cover Open",
                    "Kağıt Yok", "No Paper", "Sıkışma", "Jam"
                ]
                for kw in maintenance_keywords:
                    if kw in html_content:
                        status_info["maintenance_msg"] = kw
                        break
                
                # 2. Durum Tespiti (Brother Status ID'leri)
                # MFC-L6900DW ve benzeri modern Brother'lar için gelitirilmi tarama
                status_el = soup.find(id=re.compile(r"(status|moni_data|state|disp_area)", re.I))
                
                if not status_el:
                    # Alternatif: 'Status' veya 'Durum' yazan hücrenin yanındaki hücreyi bul
                    label = soup.find(text=re.compile(r"(Status|Durum|Cihaz Durumu)", re.I))
                    if label:
                        status_el = label.find_next(['td', 'span', 'div', 'p'])

                if not status_el:
                    # Bazı modellerde 'moni_data' bir JS dizisi içindedir
                    status_match = re.search(r"moni_data\s*=\s*\[\"(.*?)\"", html_content)
                    if status_match:
                        status_info["device_status"] = status_match.group(1)
                        status_info["success"] = True
                
                if status_el:
                    status_info["device_status"] = status_el.get_text(strip=True)
                    status_info["success"] = True

                # 3. Toner Seviyesi (Gelişmiş Pattern'ler)
                # Brother MFC-L6900DW genelde 'tonerremain' görseli veya moni_data[1] kullanır.
                
                # Pattern A: moni_data[1] (Yüzde deeri)
                if status_info["toner_level"] == "Bilinmiyor":
                    js_match = re.search(r"moni_data\s*=\s*\[(.*?)\]", html_content)
                    if js_match:
                        parts = [p.strip().replace('"', '') for p in js_match.group(1).split(',')]
                        if len(parts) > 1 and parts[1].isdigit():
                            status_info["toner_level"] = f"%{parts[1]}"

                # Pattern B: TonerRemain class'ı (Bar genişliği)
                if status_info["toner_level"] == "Bilinmiyor":
                    toner_img = soup.find('img', class_=re.compile(r"tonerremain", re.I)) or \
                                soup.find('img', src=re.compile(r"toner.*remain", re.I))
                    if toner_img:
                        w = toner_img.get('width')
                        if w and w.isdigit():
                            val = int(w)
                            if val <= 100: status_info["toner_level"] = f"%{val}"
                            elif val <= 160: status_info["toner_level"] = f"%{int((val/160)*100)}"
                            elif val <= 56: status_info["toner_level"] = f"%{int((val/56)*100)}"

                # Pattern C: Text bazlı "Toner" araması
                if status_info["toner_level"] == "Bilinmiyor":
                    toner_text = soup.find(text=re.compile(r"Toner.*?(\d+%)", re.I))
                    if toner_text:
                        match = re.search(r"(\d+%)", toner_text)
                        if match: status_info["toner_level"] = match.group(1)

                if status_info["success"] or status_info["device_status"] != "Bilinmiyor":
                    # Bakım mesajı varsa duruma ekle
                    if status_info["maintenance_msg"]:
                        status_info["device_status"] = f"{status_info['device_status']} ({status_info['maintenance_msg']})"
                    return status_info
                    
        except Exception:
            continue
            
    return {
        "ip": ip, 
        "success": False, 
        "device_status": status_info["device_status"], 
        "toner_level": status_info["toner_level"],
        "timestamp": status_info["timestamp"]
    }
