import asyncio
from playwright.async_api import async_playwright
import os

SAVE_DIR = r"c:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory\site_gorselleri"
os.makedirs(SAVE_DIR, exist_ok=True)

VIEWS = [
    ("dashboard", "dashboard"),
    ("inventory", "envanter"),
    ("general-notes", "bilgi-bankasi"),
    ("areas", "ortak-alanlar"),
    ("printers", "yazicilar"),
    ("depot", "depo"),
    ("docs", "tutanaklar"),
    ("test", "test-alani"),
    ("installations", "hizli-kurulumlar"),
    ("admin-reports", "sistem-raporlari"),
    ("logs", "islem-gecmisi"),
    ("users", "kullanici-yonetimi")
]

MODALS = [
    ("doc-modal-hasar-tespit", "hasar-tespit-tutanagi"),
    ("doc-modal-zimmet", "zimmet-tutanagi"),
    ("doc-modal-izin-istek", "izin-istek-tutanagi"),
    ("doc-modal-sla-sehven", "sla-sehven-tutanagi"),
    ("doc-modal-barcode-55x45", "barkod-55x45"),
    ("doc-modal-barcode-100x100", "barkod-100x100"),
    ("device-detail-modal", "cihaz-detaylari"),
    ("kb-modal", "bilgi-bankasi-yeni"),
    ("history-modal", "duzenleme-gecmisi"),
    ("device-notes-modal", "cihaz-notlari"),
    ("device-add-modal", "yeni-cihaz-ekle"),
    ("area-modal", "ortak-alan-ekle"),
    ("service-modal", "yeni-servis-kaydi"),
    ("depot-add-modal", "depo-yeni-urun"),
    ("depot-transaction-modal", "depo-stok-islemi"),
    ("depot-assign-modal", "depo-zimmet-atama"),
    ("user-modal", "yeni-kullanici-ekle"),
    ("printer-add-modal", "yeni-yazici-ekle"),
    ("mahal-import-modal", "mahal-excel-yukle"),
    ("script-modal", "tanimlama-kodu"),
    ("run-command-modal", "komut-calistir"),
    ("profile-settings-modal", "profil-ayarlari")
]

def get_next_filename(base_name):
    """Bulunan en büyük numaraya göre bir sonraki dosya adını üretir."""
    filepath = os.path.join(SAVE_DIR, f"{base_name}.png")
    if not os.path.exists(filepath):
        return filepath
    counter = 2
    while True:
        new_filepath = os.path.join(SAVE_DIR, f"{base_name}-{counter}.png")
        if not os.path.exists(new_filepath):
            return new_filepath
        counter += 1

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--start-maximized'])
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        print("Sisteme giriliyor...")
        await page.goto("http://sys.ornek-kurum.com/")
        await page.wait_for_timeout(2000)
        
        # Giriş Ekranı
        filename = get_next_filename("giris-ekrani")
        await page.screenshot(path=filename)
        print(f"{filename} kaydedildi.")
        
        print("Login yapılıyor...")
        await page.fill("#login-user", "vefa")
        await page.fill("#login-pass", "-*-94Vefa")
        await page.click("#btn-login-submit")
        await page.wait_for_selector("#view-dashboard", state="visible")
        await page.wait_for_timeout(3000)
        
        # Admin Menu (Users vb) görünmüyorsa aktif edelim
        await page.evaluate("""
            const adminMenus = document.querySelectorAll('.admin-only, #menu-users, #menu-admin-reports, #menu-history, #menu-test, #menu-installations');
            adminMenus.forEach(el => el.style.display = 'flex');
        """)
        
        for view_id, base_name in VIEWS:
            print(f"Navigasyon: {view_id}")
            # Try to click the nav link or evaluate click if hidden
            await page.evaluate(f"app.navigateTo('{view_id}')")
            try:
                await page.wait_for_selector(f"#view-{view_id}", state="visible", timeout=5000)
                await page.wait_for_timeout(1000) # verilerin yüklenmesi için bekle
                
                filename = get_next_filename(base_name)
                await page.screenshot(path=filename, full_page=True)
                print(f"{filename} kaydedildi.")
            except Exception as e:
                print(f"Sayfa yüklenemedi {view_id}: {e}")
                    
        # Modalları göster ve çek
        print("Modallar çekiliyor...")
        for modal_id, base_name in MODALS:
            print(f"Modal açılıyor: {modal_id}")
            try:
                await page.evaluate(f"document.getElementById('{modal_id}').style.display = 'flex';")
                await page.wait_for_timeout(1000)
                filename = get_next_filename(base_name)
                await page.screenshot(path=filename)
                print(f"{filename} kaydedildi.")
                await page.evaluate(f"document.getElementById('{modal_id}').style.display = 'none';")
                await page.wait_for_timeout(500)
            except Exception as e:
                print(f"Modal {modal_id} açılamadı: {e}")
                
        await browser.close()
        print("Tüm görseller başarıyla çekildi.")

if __name__ == "__main__":
    asyncio.run(main())
