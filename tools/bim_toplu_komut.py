import requests
import urllib.parse
import getpass
import time
import sys

# KSH Keydata Eray Sönmez and others...
ips_text = """
10.241.16.106
10.241.16.168
10.241.16.236
10.241.16.240

10.241.17.56
10.241.17.188
10.241.17.16
10.241.17.97
10.241.17.11
10.241.17.15
10.241.17.67
10.241.17.60

10.241.18.75
10.241.18.132
10.241.18.79
10.241.18.78
10.241.18.76
10.241.18.77

10.241.19.95
10.241.19.65
10.241.19.94
10.241.19.196
10.241.19.197
10.241.19.202

10.241.22.64
10.241.22.13
10.241.23.42
10.241.34.41

10.241.16.106
10.241.16.168
10.241.16.171
10.241.16.236
10.241.16.240
10.241.16.251

10.241.17.11
10.241.17.15
10.241.17.16
10.241.17.19/2
10.241.17.23
10.241.17.41
10.241.17.97
10.241.17.51
10.241.17.56
10.241.17.67
10.241.17.60
10.241.17.82
10.241.17.118
10.241.17.127
10.241.17.188
10.241.17.255

10.241.18.75
10.241.18.132
10.241.18.79
10.241.18.78
10.241.18.76
10.241.18.77
10.241.18.105
10.241.18.234
10.241.18.250

10.241.19.95
10.241.19.65
10.241.19.94
10.241.19.161
10.241.19.196
10.241.19.197
10.241.19.202

10.241.21.85
10.241.22.64
10.241.22.13
10.241.23.42
10.241.34.41
10.241.18.132
10.241.19.2
10.241.19.1
10.241.22.84
10.241.19.4
10.241.20.175
10.241.17.28
10.241.19.96
10.241.17.39
10.241.20.126
10.241.21.100
10.241.20.21
10.241.22.243
10.241.35.88
10.241.18.18
"""

# Extract unique IPs
raw_lines = ips_text.strip().split('\n')
ip_list = []
for line in raw_lines:
    line = line.strip()
    if not line or not line[0].isdigit():
        continue
    # Fix 10.241.17.19/2
    if '/' in line:
        line = line.split('/')[0].strip()
    if line not in ip_list:
        ip_list.append(line)

command = "sed -i 's/^#//' /KEYDATA/Script/WebKontrol.sh"
print(f"Toplam {len(ip_list)} benzersiz IP bulundu.")
print(f"Calistirilacak komut: {command}")
print("-" * 50)

try:
    # Try fetching from user's DB config if they have requests locally
    username = input("BIM Kullanici Adi: ").strip()
    password = getpass.getpass("BIM Sifresi: ").strip()
except EOFError:
    print("Etkilesimli terminal bulunamadi. Hata.")
    sys.exit(1)

if not username or not password:
    print("Kullanici adi ve sifre zorunludur.")
    sys.exit(1)

bim_base_url = "http://bim.kocaelish.com"
base_url = f"{bim_base_url}/Handler.ashx"

browser_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Referer": f"{bim_base_url}/",
    "Origin": bim_base_url,
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

print("\nBIM sistemine giris yapiliyor...")
login_data = {
    "Functions": "Login",
    "UserName": username,
    "Password": password
}

session = requests.Session()
encoded_login_data = urllib.parse.urlencode(login_data)
try:
    login_resp = session.post(base_url, data=encoded_login_data, headers=browser_headers, timeout=10, verify=False)
except Exception as e:
    print(f"BIM baglanti hatasi: {e}")
    sys.exit(1)

if login_resp.status_code != 200 or login_resp.text.strip() == "Error" or not login_resp.text.strip():
    print(f"HATA: BIM sitesi giris bilgilerinizi reddetti. (Sunucu Yaniti: {login_resp.text.strip()})")
    sys.exit(1)

ipa_session = login_resp.text.strip()
print(f"Giris basarili! Session ID: {ipa_session[:10]}...\n")

success_count = 0
failed_count = 0

for i, ip in enumerate(ip_list):
    print(f"[{i+1}/{len(ip_list)}] {ip} adresine komut gonderiliyor...")
    
    headers = browser_headers.copy()
    headers["X-Forwarded-For"] = ip
    headers["Client-IP"] = ip
    headers["IPASession"] = ipa_session
    
    post_data = {
        "Functions": "RunCommand",
        "IPAddress": ip,
        "UserName": username,
        "Commands": command
    }
    
    encoded_post_data = urllib.parse.urlencode(post_data)
    
    try:
        cmd_resp = session.post(base_url, data=encoded_post_data, headers=headers, timeout=10, verify=False)
        if cmd_resp.status_code == 200:
            result = cmd_resp.text.strip()
            if result.lower() == "error" or "exception" in result.lower():
                print(f"  -> BASSARISIZ: {result}")
                failed_count += 1
            else:
                print(f"  -> BASARILI: Komut iletildi. (Cevap: {result})")
                success_count += 1
        else:
            print(f"  -> BASSARISIZ: HTTP {cmd_resp.status_code}")
            failed_count += 1
    except requests.exceptions.Timeout:
        print("  -> ZAMAN ASIMI: Komut iletildi ama 10 sn icinde yanit alinmadi. Arka planda tamamlanabilir.")
        success_count += 1
    except Exception as e:
        print(f"  -> HATA: {e}")
        failed_count += 1
        
    time.sleep(0.2) # Sunucuyu yormamak icin kisa bekleme

print("\n" + "="*50)
print(f"ISLEM TAMAMLANDI!")
print(f"Basarili: {success_count} | Basarisiz: {failed_count}")
print("="*50)
input("Cikmak icin Enter'a basin...")
