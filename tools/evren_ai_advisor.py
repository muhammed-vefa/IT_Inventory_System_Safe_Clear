"""
IT INVENTORY - EVREN MILLI YAPAY ZEKA MODELI PROJE DANISMANI
------------------------------------------------------------
T.C. Cumhurbaskanligi Savunma Sanayii Baskanligi (SSB) / SAYZEK 
bunyesindeki yerli ve milli EVREN LLM API'sine baglanarak
IT Inventory projesinin gelistirme, guvenlik ve optimizasyon
analizini yapar.

Baglanti:
Base URL: https://evren-llmapi.ssyz.org.tr/v1 (OpenAI Uyumlu)
Model: evren-savunma-llm-v1 (veya paneldeki guncel model)
"""

import os
import sys
import json
from dotenv import load_dotenv

# .env yukle
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
env_path = os.path.join(BASE_DIR, "tools", ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(env_path)

EVREN_API_KEY = os.getenv("EVREN_API_KEY")
EVREN_BASE_URL = os.getenv("EVREN_BASE_URL", "https://evren-llmapi.ssyz.org.tr/v1")
EVREN_MODEL = os.getenv("EVREN_MODEL", "evren-savunma-llm-v1")

PROJECT_SUMMARY = """
PROJE ADI: KSH IT Envanter ve Yonetim Sistemi (KEYDATA KSH)
MIMARI:
- Backend: Python 3.12/3.13, Flask RESTful API, pyodbc (MS SQL Server PooledDB), JWT Auth, RBAC
- Frontend: Vanilla JavaScript (UI_controller.js), Responsive CSS (Dark Glassmorphism), PWA (Service Worker)
- Veritabani: Microsoft SQL Server (IT_INVENTORY)
- Entegrasyonlar:
  * KeyOS MGT (Linux ince istemciler telemetri/aktiflik sorgusu)
  * CUPS IPP Yazici Yonetimi (Yazici duraklatma, devam ettirme, sayac sorgulama)
  * Desktop Central API
  * MYM Personel & Sicil Senkronizasyonu
  * VPN Kullanici ve Donanim Zimmet Takibi
- Son Eklenen Moduller:
  * Donanim Klavye Test Modulu (F1-F12 tarayici capture phase onleme)
  * O(1) Map Lookups ile KeyOS istemci render optimizasyonu
  * Sade Kullanici Arayuzu (5 ana sekme + Profil menusunde alt moduller)
  * Depo Stok & Donanim Takibi (Kritik esik bildirimleri)
  * Tutanaklar & Dijital Formlar (SLA, Hasar Tespit, Zimmet)
"""

def check_or_prompt_api_key():
    global EVREN_API_KEY
    if not EVREN_API_KEY:
        print("=" * 70)
        print("EVREN YAPAY ZEKA MODELI ENTEGRASYONU")
        print("=" * 70)
        print("EVREN API anahtari (.env icinde EVREN_API_KEY) bulunamadi.")
        print("\nNasil Alinir?")
        print("1. https://evren.ssyz.org.tr adresine e-Devlet ile giris yapin.")
        print("2. 'API Anahtarlari' bolumunden yeni bir anahtar (evren_llm_...) olusturun.")
        print("3. tools/.env dosyasina 'EVREN_API_KEY=evren_llm_xxxx' seklinde ekleyin.")
        print("=" * 70)
        
        user_key = input("\nSimdi kullanmak uzere EVREN API Key girmek ister misiniz? (Enter ile gecin): ").strip()
        if user_key:
            EVREN_API_KEY = user_key
        else:
            return False
    return True

def ask_evren(prompt_text):
    try:
        from openai import OpenAI
    except ImportError:
        print("[HATA] 'openai' kutuphanesi yuklu degil. Lutfen 'pip install openai' calistirin.")
        return None

    if not check_or_prompt_api_key():
        return None

    print(f"\n[EVREN API] Baglanti kuruluyor: {EVREN_BASE_URL} (Model: {EVREN_MODEL})...")
    
    try:
        client = OpenAI(
            base_url=EVREN_BASE_URL,
            api_key=EVREN_API_KEY
        )

        response = client.chat.completions.create(
            model=EVREN_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Sen T.C. Savunma Sanayii Baskanligi EVREN platformunda calisan Kidemli Yazilim Mimari ve Siber Guvenlik Danismanisin. Kurumsal saglik ve IT altyapisi icin gelistirilen projeleri analiz edip somut, uygulanabilir ve modern gelistirme onerileri sunarsin."
                },
                {
                    "role": "user",
                    "content": f"{PROJECT_SUMMARY}\n\nSORU / TALEP:\n{prompt_text}"
                }
            ],
            temperature=0.3
        )

        answer = response.choices[0].message.content
        return answer

    except Exception as e:
        print(f"\n[HATA] EVREN API cagrisi basarisiz oldu: {e}")
        return None

if __name__ == "__main__":
    soru = "Bu IT Envanter ve Yonetim projesinde su anki mimariye gore hangi kritik gelistirmeleri yapmaliyiz? Guvenlik, mimari, kullanici deneyimi ve yapay zeka entegrasyonu acisindan onerilerini maddeler halinde listele."
    
    if len(sys.argv) > 1:
        soru = " ".join(sys.argv[1:])

    print("Proje ozeti hazirlandi. EVREN modeline iletiliyor...")
    cevap = ask_evren(soru)
    
    if cevap:
        print("\n" + "=" * 70)
        print("EVREN YAPAY ZEKA MODELININ ONERILERI:")
        print("=" * 70)
        print(cevap)
        print("=" * 70)
