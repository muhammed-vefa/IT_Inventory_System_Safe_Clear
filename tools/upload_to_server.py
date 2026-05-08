import paramiko
import os
import time
from dotenv import load_dotenv

# .env dosyasından credential'ları yükle
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

HOST = os.getenv("SFTP_HOST", "10.241.1.199")
PORT = int(os.getenv("SFTP_PORT", "2205"))
USER = os.getenv("SFTP_USER")
PASS = os.getenv("SFTP_PASS")
REMOTE_BASE = os.getenv("SFTP_REMOTE_BASE", "C:/WebApps/IT_Inventory_System")

FILES_TO_UPLOAD = [
    "modules/printer_manager.py",
    "frontend/UI_controller.js",
    "modules/keyos_service.py",
    "main.py",
    "index.html"
]

def upload():
    if not USER or not PASS:
        print("HATA: SFTP_USER ve SFTP_PASS .env dosyasında tanımlı olmalı!")
        return False

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {HOST}:{PORT} with SSHClient...")
        # Increase timeout and banner_timeout for slow connections
        client.connect(HOST, port=PORT, username=USER, password=PASS, 
                       timeout=20, banner_timeout=20, allow_agent=False, look_for_keys=False)
        
        sftp = client.open_sftp()
        print("SFTP Session opened.")
        
        for file_rel_path in FILES_TO_UPLOAD:
            local_path = os.path.join(os.getcwd(), file_rel_path.replace('/', os.sep))
            remote_path = f"{REMOTE_BASE}/{file_rel_path}"
            
            # Simple remote directory check
            remote_dir = os.path.dirname(remote_path)
            try:
                sftp.stat(remote_dir)
            except IOError:
                print(f"Creating remote directory: {remote_dir}")
                # This only works for 1 level, but modules/frontend exist
                try:
                    sftp.mkdir(remote_dir)
                except:
                    pass
            
            if os.path.exists(local_path):
                print(f"Uploading {file_rel_path}...")
                sftp.put(local_path, remote_path)
            else:
                print(f"Warning: Local file not found: {local_path}")
            
        sftp.close()
        client.close()
        print("Upload completed successfully!")
        return True
    except Exception as e:
        print(f"Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    upload()
