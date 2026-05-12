import os
import shutil
import time
import datetime
import subprocess

SOURCE_DIR = r"C:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory_System"
BACKUP_DIR = r"C:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory_System_Safe_Clear"
HISTORY_DIR = r"C:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\it_backups"

if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

def run_backup():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"[{timestamp}] Backup balatlyor...")
    
    # 1. Safe_Clear alanına kopyala
    try:
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
        shutil.copytree(SOURCE_DIR, BACKUP_DIR, ignore=shutil.ignore_patterns('.git', '__pycache__', 'logs', 'database'))
        print("Safe_Clear alan gncellendi.")
    except Exception as e:
        print(f"Kopyalama hatas: {e}")

    # 2. Tarihli ZIP olutur
    zip_name = os.path.join(HISTORY_DIR, f"IT_Inventory_Backup_{timestamp}")
    shutil.make_archive(zip_name, 'zip', SOURCE_DIR)
    print(f"ZIP yedek oluturuldu: {zip_name}.zip")

    # 3. Git Push (Safe_Clear)
    try:
        os.chdir(BACKUP_DIR)
        subprocess.run(["git", "init"], check=False)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto-Backup {timestamp}"], check=False)
        # subprocess.run(["git", "push", "origin", "main"], check=False) # Gerekirse aktif edilebilir
        print("Git ilemleri tamamland.")
    except Exception as e:
        print(f"Git hatas: {e}")

if __name__ == "__main__":
    while True:
        run_backup()
        print("Bir sonraki yedekleme 15 dakika sonra...")
        time.sleep(15 * 60)
