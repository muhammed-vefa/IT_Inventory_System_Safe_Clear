import asyncio
from playwright.async_api import async_playwright

BLUR_JS = """
    const tables = document.querySelectorAll('table');
    tables.forEach(t => {
        const headers = Array.from(t.querySelectorAll('th'));
        headers.forEach((th, index) => {
            if(th.textContent.includes('Seri No') || th.textContent.includes('IP Adresi') || th.textContent.includes('MAC') || th.textContent.includes('Lokal Hostname') || th.textContent.includes('KeyOS Hostname')) {
                t.querySelectorAll('tbody tr').forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if(cells[index]) {
                        cells[index].style.filter = 'blur(6px)';
                        cells[index].style.opacity = '0.5';
                    }
                });
            }
        });
    });
"""


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        print("Sayfaya gidiliyor...")
        await page.goto("http://sys.ornek-kurum.com/")
        
        # Wait for login form
        await page.wait_for_selector("#login-user")
        
        print("Giriş yapılıyor...")
        # Fill login
        await page.fill("#login-user", "vefa")
        await page.fill("#login-pass", "-*-94Vefa")
        await page.click("#btn-login-submit")
        
        print("Dashboard yükleniyor...")
        # Wait for dashboard to load (wait for the view-dashboard to be visible)
        await page.wait_for_selector("#view-dashboard", state="visible")
        # Give it enough time to load API data and animations
        await page.wait_for_timeout(10000)
        await page.screenshot(path=r"C:\Users\MUHAMMED-VEFA-IS\OneDrive\Desktop\LinkedIn_Resimleri\dashboard_ss.png")
        print("Dashboard resmi kaydedildi.")
        
        # Click Envanter
        print("Envanter sayfasına geçiliyor...")
        await page.click(".nav-link[data-view='inventory']")
        await page.wait_for_selector("#view-inventory", state="visible")
        await page.wait_for_timeout(4000)
        # Blur sensitive info
        await page.evaluate(BLUR_JS)
        await page.screenshot(path=r"C:\Users\MUHAMMED-VEFA-IS\OneDrive\Desktop\LinkedIn_Resimleri\inventory_ss.png")
        print("Envanter resmi kaydedildi.")
        
        # Click Bilgi Bankası
        print("Bilgi Bankası sayfasına geçiliyor...")
        await page.click(".nav-link[data-view='general-notes']")
        await page.wait_for_selector("#view-general-notes", state="visible")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=r"C:\Users\MUHAMMED-VEFA-IS\OneDrive\Desktop\LinkedIn_Resimleri\kb_ss.png")
        print("Bilgi Bankası resmi kaydedildi.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
