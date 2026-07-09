import os
import subprocess
import time

def run_command(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=timeout)
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out."
    except Exception as e:
        return False, str(e)

def remote_install_msi(ip, username, password, installer_folder_path):
    """
    Kopya ve yukleme islemini gerceklestirir.
    Args:
        ip: Hedef IP adresi
        username: Hedef PC Local Admin kullanici adi (örn: Administrator)
        password: Sifre
        installer_folder_path: Sunucudaki directsetup klasorunun yolu
    Returns:
        (success_bool, message_str)
    """
    if not os.path.exists(installer_folder_path):
        return False, f"Ajan klasoru bulunamadi: {installer_folder_path}"

    target_dir = rf"\\{ip}\C$\Windows\Temp\directsetup"
    
    # 1. Klasöre erisim icin IPC$ oturumu ac
    connect_cmd = f'net use \\\\{ip}\\ipc$ /user:"{username}" "{password}"'
    succ, out = run_command(connect_cmd)
    
    if not succ and "multiple connections" not in out.lower():
        # Eger hata verdiyse ve hata sebebi "zaten bagli" degilse, devam edemeyiz.
        return False, f"IPC$ baglantisi saglanamadi. Ag veya yetki sorunu olabilir. Detay: {out}"
        
    try:
        # 2. Klasoru xcopy ile kopyala
        # /E: Alt klasorleri de kopyala, /Y: Uzerine yaz, /I: Hedefin bir klasor oldugunu varsay
        copy_cmd = f'xcopy /E /Y /I "{installer_folder_path}" "{target_dir}"'
        succ, out = run_command(copy_cmd, timeout=120)
        
        if not succ:
            return False, f"Klasor kopyalanamadi. C$ paylasimi kapali olabilir. Detay: {out}"
            
        # 3. WMI uzerinden kurulum komutunu tetikle
        # Kurulum klasorune gecis yapip, mst ve crt parametreleriyle msiexec calistir
        remote_cd = r"C:\Windows\Temp\directsetup"
        msi_cmd = f'msiexec /i DesktopCentralAgent.msi TRANSFORMS="DesktopCentralAgent.mst" ENABLESILENT=yes REBOOT=ReallySuppress INSTALLSOURCE=Manual SERVER_ROOT_CRT="{remote_cd}\\DMRootCA-Server.crt" DS_ROOT_CRT="{remote_cd}\\DMRootCA.crt" /qn'
        
        wmi_cmd = f'wmic /node:"{ip}" /user:"{username}" /password:"{password}" process call create "cmd.exe /c cd {remote_cd} && {msi_cmd}"'
        succ, out = run_command(wmi_cmd, timeout=30)
        
        if not succ or "ReturnValue" not in out:
            return False, f"Kurulum komutu tetiklenemedi. WMI kapali olabilir. Detay: {out}"
            
        return True, "Kurulum komutu basariyla tetiklendi. Arka planda tamamlanacaktir."
        
    finally:
        # Baglantiyi kopart
        disconnect_cmd = f'net use \\\\{ip}\\ipc$ /delete /y'
        run_command(disconnect_cmd)

if __name__ == '__main__':
    import sys
    import getpass
    
    print("=== Desktop Central Toplu Ajan Kurulum Araci ===")
    ips_input = input("Hedef IP Adreslerini girin (virgülle ayirin): ")
    ips = [ip.strip() for ip in ips_input.split(',') if ip.strip()]
    
    if not ips:
        print("Hata: IP adresi girmediniz.")
        sys.exit(1)
        
    username = input("Local Admin Kullanici Adi (örn: Administrator): ")
    password = getpass.getpass("Sifre (Ekranda gorunmez): ")
    
    # Kendi dizinindeki directsetup'i bulmaya calis
    default_installer = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'agent_installer', 'directsetup')
    
    installer_path = input(f"Installer Klasoru [{default_installer}]: ")
    if not installer_path.strip():
        installer_path = default_installer
        
    for ip in ips:
        print(f"\n[{ip}] Kurulum deneniyor...")
        succ, msg = remote_install_msi(ip, username, password, installer_path)
        if succ:
            print(f"[{ip}] BASARILI: {msg}")
        else:
            print(f"[{ip}] HATA: {msg}")
            
    print("\nIslem tamamlandi.")
