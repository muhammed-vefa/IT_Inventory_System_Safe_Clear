import os
import json
from flask import Blueprint, jsonify, request, send_file, render_template_string, Response, send_from_directory
from werkzeug.utils import secure_filename
import shutil
import urllib.parse
from core.auth import require_admin, require_editor

import datetime

installations_manager_bp = Blueprint('installations_manager', __name__)
# Sabit yol (IT_Inventory dizini icindeki static/kurulum_dosyalari)
INSTALL_DIR = os.path.join(os.getcwd(), 'static', 'kurulum_dosyalari')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DL_DIR = os.path.join(BASE_DIR, 'static', 'bat_uygulamalar')

def get_download_dir():
    """Gerekli indirmeler için standart yolu döndürür."""
    path = os.path.join(BASE_DIR, 'static', 'bat_uygulamalar')
    os.makedirs(path, exist_ok=True)
    return path

def safe_join(base_dir, user_path):
    """Path traversal engelleyici güvenli yol birleştirici"""
    if not user_path:
        return None
    user_path = str(user_path).replace('\\', '/')
    if '..' in user_path or user_path.startswith('/'):
        return None
    if os.path.isabs(user_path) or os.path.splitdrive(user_path)[0]:
        return None
    base = os.path.abspath(base_dir)
    target = os.path.abspath(os.path.join(base, user_path))
    if os.path.commonpath([base, target]) != base:
        return None
    return target

def get_safe_app_dir(app_id, check_exists=True):
    """app_id için güvenli klasör yolu döndürür."""
    if not app_id:
        return None
    app_id = str(app_id).replace('\\', '/')
    if '..' in app_id or '/' in app_id or os.path.isabs(app_id) or os.path.splitdrive(app_id)[0]:
        return None
    app_dir = os.path.abspath(os.path.join(INSTALL_DIR, app_id))
    if os.path.commonpath([os.path.abspath(INSTALL_DIR), app_dir]) != os.path.abspath(INSTALL_DIR):
        return None
    if check_exists and (not os.path.exists(app_dir) or not os.path.isdir(app_dir)):
        return None
    return app_dir

def file_info(path, filename):
    stat = os.stat(path)
    size = stat.st_size
    if size >= 1024 * 1024:
        size_text = f"{size / (1024 * 1024):.1f} MB"
    elif size >= 1024:
        size_text = f"{size / 1024:.1f} KB"
    else:
        size_text = f"{size} B"
    return {
        'name': filename,
        'size': size_text,
        'date': datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
    }

@installations_manager_bp.route('/apps', methods=['GET'])
def list_apps():
    if not os.path.exists(INSTALL_DIR):
        os.makedirs(INSTALL_DIR, exist_ok=True)
    
    apps = []
    # Bazi bilinen uygulamalar icin ozel silent install argumanlari. 
    known_args = {
        'ANYDESK': '/sAll /rs /qn',
        'CHROME': '/silent /install',
        'MSI': '/quiet /norestart',
        'JAVA': '/s',
        'WINRAR': '/S',
        '7ZIP': '/S',
        '7-ZIP': '/S',
        'VLC': '/L=1033 /S'
    }

    for item in sorted(os.listdir(INSTALL_DIR)):
        item_path = os.path.join(INSTALL_DIR, item)
        if os.path.isdir(item_path):
            args = "/S" # Genel varsayilan
            item_upper = item.upper()
            
            # Sifir imaj kontrolu (sadece sifirimaj.txt dosyasina bakar)
            is_sifir_imaj = os.path.exists(os.path.join(item_path, 'sifirimaj.txt'))
                
            # Ozel script kontrolu
            is_custom = False
            if os.path.exists(os.path.join(item_path, 'isvec.ps1')):
                is_custom = True
            
            for key, val in known_args.items():
                if key in item_upper:
                    args = val
                    break
            
            # Klasor isminden okunakli isim uret (Basta numara varsa temizle: "03_E_Imza" -> "E Imza")
            import re
            clean_name = re.sub(r'^\d+_', '', item)
            display_name = clean_name.replace('_', ' ').title()
            
            icon_url = None
            for f in os.listdir(item_path):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.ico', '.svg')):
                    encoded_f = urllib.parse.quote(f)
                    encoded_item = urllib.parse.quote(item)
                    icon_url = f'/api/isvec/{encoded_item}/file/{encoded_f}'
                    break
                    
            # Aciklama kontrolu
            description = ""
            aciklama_path = os.path.join(item_path, 'aciklama.txt')
            if os.path.exists(aciklama_path):
                try:
                    with open(aciklama_path, 'r', encoding='utf-8') as f:
                        description = f.read().strip()
                except:
                    pass

            apps.append({
                'icon_url': icon_url,
                'id': item,
                'name': display_name,
                'args': args,
                'description': description,
                'is_sifir_imaj': is_sifir_imaj,
                'is_custom': is_custom
            })
    
    return jsonify({'apps': apps})

@installations_manager_bp.route('/<app_id>/manifest', methods=['GET'])
def get_manifest(app_id):
    app_dir = get_safe_app_dir(app_id)
    if not app_dir:
        return jsonify({'error': 'App not found'}), 404
        
    files = []
    for root, dirs, filenames in os.walk(app_dir):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, app_dir)
            files.append(rel_path.replace('\\', '/'))
            
    return jsonify({'files': files})

@installations_manager_bp.route('/<app_id>/file/<path:subpath>', methods=['GET'])
def get_file(app_id, subpath):
    app_dir = get_safe_app_dir(app_id)
    if not app_dir:
        return "App not found", 404
    
    safe_path = safe_join(app_dir, subpath)
    if not safe_path:
        return "Invalid file path", 400
        
    return send_from_directory(app_dir, subpath)

@installations_manager_bp.route('/<app_id>/download', methods=['GET'])
def download_installer(app_id):
    app_dir = get_safe_app_dir(app_id)
    if not app_dir:
        return "App not found", 404
        
    # En guncel dosyayi bulur
    installers = []
    valid_exts = ('.exe', '.msi', '.bat', '.iso', '.zip', '.rar', '.7z', '.ps1', '.vbs', '.reg')
    for f in os.listdir(app_dir):
        if f.lower().endswith(valid_exts):
            file_path = os.path.join(app_dir, f)
            installers.append((file_path, os.path.getmtime(file_path), f))
    
    if installers:
        # Tarihe gore azalan siralama (en yeni en basta)
        installers.sort(key=lambda x: x[1], reverse=True)
        newest_file_path, _, newest_filename = installers[0]
        return send_file(newest_file_path, as_attachment=True, download_name=newest_filename)
            
    return "Installer not found in directory", 404

@installations_manager_bp.route('/bulk', methods=['GET'])
def generate_bulk_script():
    ids = request.args.get('ids', '')
    if not ids:
        return "No IDs provided", 400
        
    id_list = ids.split(',')
    
    # Meta paket aliases (Sanal Paketler)
    expanded_list = []
    for uid in id_list:
        if uid == 'Kullanici_VPN_Kurulumu':
            expanded_list.extend(['web terminal', 'E_Imza_Paketi', 'FORTİNET', 'SERTİFİKALAR', '.lisans', 'Site_Kisayollari'])
        else:
            expanded_list.append(uid)
            
    # Remove duplicates but preserve order (if any)
    final_list = []
    for uid in expanded_list:
        if uid not in final_list:
            final_list.append(uid)
            
    id_list = final_list
    
    ps1_template = """
$ProgressPreference = 'SilentlyContinue'
$ErrorActionPreference = 'SilentlyContinue'
$WarningPreference = 'SilentlyContinue'

if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    try {
        Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    } catch {}
    exit
}

# CMD penceresini gizle (Eger bat uzerinden cagrilmissa)
$code = @"
using System;
using System.Runtime.InteropServices;
public class Window {
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
Add-Type -TypeDefinition $code -ErrorAction SilentlyContinue
[Window]::ShowWindow((Get-Process -Id $pid).MainWindowHandle, 0) | Out-Null

Add-Type -AssemblyName System.Windows.Forms
$form = New-Object System.Windows.Forms.Form
$form.Text = "Isvec Cakisi - Toplu Kurulum"
$form.Size = New-Object System.Drawing.Size(550,450)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "Sizable"
$form.MinimizeBox = $true
$form.MaximizeBox = $true

$label = New-Object System.Windows.Forms.Label
$label.Location = New-Object System.Drawing.Point(20,10)
$label.Size = New-Object System.Drawing.Size(400,20)
$label.Text = "Toplu kurulum hazirlaniyor..."
$form.Controls.Add($label)

$listView = New-Object System.Windows.Forms.ListView
$listView.Location = New-Object System.Drawing.Point(20,40)
$listView.Size = New-Object System.Drawing.Size(500,300)
$listView.View = [System.Windows.Forms.View]::Details
$listView.FullRowSelect = $true
$listView.GridLines = $true
$listView.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Bottom -bor [System.Windows.Forms.AnchorStyles]::Left -bor [System.Windows.Forms.AnchorStyles]::Right
$listView.Columns.Add("Program Adi", 250) | Out-Null
$listView.Columns.Add("Durum", 220) | Out-Null
$form.Controls.Add($listView)

$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Location = New-Object System.Drawing.Point(20,350)
$progressBar.Size = New-Object System.Drawing.Size(500,25)
$progressBar.Style = "Blocks"
$progressBar.Minimum = 0
$progressBar.Maximum = {{TOTAL_COUNT}}
$progressBar.Anchor = [System.Windows.Forms.AnchorStyles]::Bottom -bor [System.Windows.Forms.AnchorStyles]::Left -bor [System.Windows.Forms.AnchorStyles]::Right
$form.Controls.Add($progressBar)

$form.Show() | Out-Null
[System.Windows.Forms.Application]::DoEvents()

$apps = @(
{{APPS_ARRAY}}
)

foreach ($app in $apps) {
    $item = New-Object System.Windows.Forms.ListViewItem($app.Name)
    $item.SubItems.Add("Bekliyor") | Out-Null
    $app | Add-Member -MemberType NoteProperty -Name "ListItem" -Value $item
    $listView.Items.Add($item) | Out-Null
}
[System.Windows.Forms.Application]::DoEvents()

function Set-Status($app, $msg) {
    $app.ListItem.SubItems[1].Text = $msg
    $listView.EnsureVisible($app.ListItem.Index)
    $label.Text = "Islem: $($app.Name) - $msg"
    [System.Windows.Forms.Application]::DoEvents()
}

$sharePathB64 = "XFwxMC4yNDEuMS4xOTlca3VydWx1bV9kb3N5YWxhcmk="
$sharePath = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($sharePathB64))

$hasErrors = $false

foreach ($app in $apps) {
    Set-Status $app "Baglanti saglaniyor..."
    $progressBar.Value += 1
    $env:SEE_MASK_NOZONECHECKS = 1
    
    try {
        $appShareDir = "$sharePath\$($app.Id)"
        if (!(Test-Path $appShareDir)) {
            Set-Status $app "HATA: Ag yolu bulunamadi ($appShareDir)"
            $hasErrors = $true
            continue
        }

        if ($app.IsCustom) {
            Set-Status $app "Agdan ozel script calistiriliyor..."
            [System.Windows.Forms.Application]::DoEvents()
            
            $ps1Path = Join-Path $appShareDir "isvec.ps1"
            if (Test-Path $ps1Path) {
                $prevLoc = Get-Location
                Set-Location $appShareDir
                & $ps1Path
                Set-Location $prevLoc
            }
        }
        else {
            Set-Status $app "Agdan kurulum dosyasi araniyor..."
            $exeFile = Get-ChildItem -Path $appShareDir -Include *.exe,*.msi,*.jar -Recurse | Sort-Object Length -Descending | Select-Object -First 1
            
            if ($exeFile) {
                Set-Status $app "Sessiz kurulum yapiliyor..."
                [System.Windows.Forms.Application]::DoEvents()
                
                $argsArray = $app.Args -split ' ' | Where-Object { $_ -ne '' }
                if ($exeFile.Name.ToLower().EndsWith('.msi')) {
                    $process = Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$($exeFile.FullName)`" $($app.Args)" -Wait -PassThru -NoNewWindow
                    if ($process.ExitCode -ne 0 -and $process.ExitCode -ne 3010) { Set-Status $app "HATA: MSI Kod $($process.ExitCode)"; $hasErrors = $true; continue }
                } elseif ($exeFile.Name.ToLower().EndsWith('.iso') -or $exeFile.Name.ToLower().EndsWith('.zip') -or $exeFile.Name.ToLower().EndsWith('.rar') -or $exeFile.Name.ToLower().EndsWith('.7z')) {
                    Set-Status $app "Masaustune kopyalaniyor..."
                    $desktopPath = [Environment]::GetFolderPath("Desktop")
                    Copy-Item -Path $exeFile.FullName -Destination $desktopPath -Force
                } else {
                    $process = Start-Process -FilePath $exeFile.FullName -ArgumentList $argsArray -Wait -PassThru -NoNewWindow
                    if ($process.ExitCode -ne 0 -and $process.ExitCode -ne 3010 -and $null -ne $process.ExitCode) { Set-Status $app "HATA: EXE Kod $($process.ExitCode)"; $hasErrors = $true; continue }
                }
            } else {
                Set-Status $app "HATA: Kurulum dosyasi bulunamadi."
                $hasErrors = $true
                continue
            }
        }
        
        Set-Status $app "Tamamlandi"
    } catch {
        $hasErrors = $true
        Set-Status $app "HATA! $($_.Exception.Message)"
    }
}
Remove-Item Env:\SEE_MASK_NOZONECHECKS -ErrorAction SilentlyContinue

if ($hasErrors) {
    $label.Text = "BAZI KURULUMLARDA HATA OLUSTU! Pencereyi siz kapatin."
    $label.ForeColor = "Red"
    [System.Windows.Forms.Application]::DoEvents()
    while ($form.Visible) {
        [System.Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds 200
    }
} else {
    $label.Text = "TUM KURULUMLAR TAMAMLANDI! Otomatik kapaniyor..."
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Seconds 3
    $form.Close()
}

# Kendini sil (script bittikten sonra iz birakmamak icin)
if ($PSCommandPath -and (Test-Path $PSCommandPath)) {
    Remove-Item -Path $PSCommandPath -Force -ErrorAction SilentlyContinue
}
"""
    
    host = request.headers.get('X-Forwarded-Host', request.headers.get('Host', 'sys.kocaelish.com'))
    if '127.0.0.1' in host or 'localhost' in host:
        host = 'sys.kocaelish.com'
    scheme = request.headers.get('X-Forwarded-Proto', 'http')
    base_url = f"{scheme}://{host}/api/isvec"
    
    apps_array_str = ""
    
    if not os.path.exists(INSTALL_DIR):
        os.makedirs(INSTALL_DIR, exist_ok=True)
    
    # Argumanlari yeniden hesaplayalim veya list_apps icindeki mantigi kopyalayalim
    known_args = {
        'ANYDESK': '/sAll /rs /qn',
        'CHROME': '/silent /install',
        'MSI': '/quiet /norestart',
        'JAVA': '/s',
        'WINRAR': '/S',
        '7ZIP': '/S',
        '7-ZIP': '/S',
        'VLC': '/L=1033 /S'
    }
    
    count = 0
    for app_id in id_list:
        app_dir = get_safe_app_dir(app_id)
        if app_dir:
            count += 1
            item_upper = app_id.upper()
            args = "/S"
            for key, val in known_args.items():
                if key in item_upper:
                    args = val
                    break
            
            installer_name = "setup.exe"
            valid_exts = ('.exe', '.msi', '.bat', '.iso', '.zip', '.rar', '.7z', '.ps1', '.vbs', '.reg')
            for f in os.listdir(app_dir):
                if f.lower().endswith(valid_exts):
                    installer_name = f
                    if f.lower().endswith('.msi') and args == "/S":
                        args = "/quiet /norestart"
                    break

            is_custom = "$false"
            if os.path.exists(os.path.join(app_dir, 'isvec.ps1')):
                is_custom = "$true"
            
            display_name = app_id.replace('_', ' ').title()
            encoded_app_id = urllib.parse.quote(app_id)
            apps_array_str += f"    @{{ Id='{app_id}'; Name='{display_name}'; BaseUrl='{base_url}/{encoded_app_id}'; Args='{args}'; IsCustom={is_custom}; InstallerName='{installer_name}' }},\n"

    ps1_content = ps1_template.replace('{{TOTAL_COUNT}}', str(count)).replace('{{APPS_ARRAY}}', apps_array_str.rstrip(',\n'))
    
    bom = b'\xef\xbb\xbf'
    return Response(bom + ps1_content.encode('utf-8'), mimetype='text/plain; charset=utf-8')

@installations_manager_bp.route('/<app_id>/', methods=['GET'])
def generate_script(app_id):
    # Bu endpoint tekli kurulumlar icindir. Sadece bulk scriptin kucultulmus halidir.
    return generate_bulk_script_for_single(app_id)

def generate_bulk_script_for_single(app_id):
    ps1_template = """
$ProgressPreference = 'SilentlyContinue'
$ErrorActionPreference = 'SilentlyContinue'
$WarningPreference = 'SilentlyContinue'

if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    try {
        Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    } catch {}
    exit
}

$code = @"
using System;
using System.Runtime.InteropServices;
public class Window {
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
Add-Type -TypeDefinition $code -ErrorAction SilentlyContinue
[Window]::ShowWindow((Get-Process -Id $pid).MainWindowHandle, 0) | Out-Null

Add-Type -AssemblyName System.Windows.Forms
$form = New-Object System.Windows.Forms.Form
$form.Text = "Isvec Cakisi - {{APP_NAME}}"
$form.Size = New-Object System.Drawing.Size(400,120)
$form.StartPosition = "CenterScreen"
$form.TopMost = $false
$form.FormBorderStyle = "FixedSingle"
$form.MinimizeBox = $true
$form.MaximizeBox = $false

$label = New-Object System.Windows.Forms.Label
$label.Location = New-Object System.Drawing.Point(20,20)
$label.Size = New-Object System.Drawing.Size(340,30)
$label.Text = "Kurulum baslatiliyor..."
$form.Controls.Add($label)

$form.Show() | Out-Null
$form.Refresh()

function Add-Log($msg) {
    $label.Text = $msg
    $form.Refresh()
}

try {
    $tempDir = Join-Path $env:TEMP "isvec_{{APP_ID}}"
$sharePathB64 = "XFwxMC4yNDEuMS4xOTlca3VydWx1bV9kb3N5YWxhcmk="
$sharePath = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($sharePathB64))

try {
    $env:SEE_MASK_NOZONECHECKS = 1
    
    $appShareDir = "$sharePath\{{APP_ID}}"
    if (!(Test-Path $appShareDir)) {
        Add-Log "HATA: Ag yolu bulunamadi ($appShareDir)"
        Start-Sleep -Seconds 3
        exit
    }

    if ({{IS_CUSTOM}}) {
        Add-Log "Agdan ozel script calistiriliyor..."
        $ps1Path = Join-Path $appShareDir "isvec.ps1"
        if (Test-Path $ps1Path) {
            $prevLoc = Get-Location
            Set-Location $appShareDir
            & $ps1Path
            Set-Location $prevLoc
        }
    }
    else {
        Add-Log "Agdan kurulum dosyasi araniyor..."
        $exeFile = Get-ChildItem -Path $appShareDir -Include *.exe,*.msi,*.jar -Recurse | Sort-Object Length -Descending | Select-Object -First 1
        
        if ($exeFile) {
            Add-Log "Ag uzerinden sessiz kurulum yapiliyor..."
            $argsArray = "{{ARGS}}" -split ' ' | Where-Object { $_ -ne '' }
            if ($exeFile.Name.ToLower().EndsWith('.msi')) {
                $process = Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$($exeFile.FullName)`" $argsArray" -Wait -PassThru -NoNewWindow
            } elseif ($exeFile.Name.ToLower().EndsWith('.iso') -or $exeFile.Name.ToLower().EndsWith('.zip') -or $exeFile.Name.ToLower().EndsWith('.rar') -or $exeFile.Name.ToLower().EndsWith('.7z')) {
                Add-Log "Masaustune kopyalaniyor..."
                $desktopPath = [Environment]::GetFolderPath("Desktop")
                Copy-Item -Path $exeFile.FullName -Destination $desktopPath -Force
            } else {
                $process = Start-Process -FilePath $exeFile.FullName -ArgumentList $argsArray -Wait -PassThru -NoNewWindow
            }
        } else {
            Add-Log "HATA: Kurulum dosyasi bulunamadi."
        }
    }
    Add-Log "Islem bitti!"
} catch {
    $errMsg = $_.Exception.Message
    Add-Log "HATA: Kurulum sirasinda sorun olustu! Detay: $errMsg"
}
Start-Sleep -Seconds 2
$form.Close()

# Kendini sil (script bittikten sonra iz birakmamak icin)
if ($PSCommandPath -and (Test-Path $PSCommandPath)) {
    Remove-Item -Path $PSCommandPath -Force -ErrorAction SilentlyContinue
}
"""
    host = request.headers.get('X-Forwarded-Host', request.headers.get('Host', 'sys.kocaelish.com'))
    if '127.0.0.1' in host or 'localhost' in host:
        host = 'sys.kocaelish.com'
    scheme = request.headers.get('X-Forwarded-Proto', 'http')
    encoded_app_id = urllib.parse.quote(app_id)
    base_url = f"{scheme}://{host}/api/isvec/" + encoded_app_id
    
    app_dir = get_safe_app_dir(app_id)
    if not app_dir:
        return "App not found", 404
        
    known_args = {
        'ANYDESK': '/sAll /rs /qn',
        'CHROME': '/silent /install',
        'MSI': '/quiet /norestart',
        'JAVA': '/s',
        'WINRAR': '/S',
        '7ZIP': '/S',
        '7-ZIP': '/S',
        'VLC': '/L=1033 /S'
    }
    
    item_upper = app_id.upper()
    args = "/S"
    for key, val in known_args.items():
        if key in item_upper:
            args = val
            break
            
    is_custom = "$false"
    installer_name = "setup.exe"
    if os.path.exists(app_dir):
        for f in os.listdir(app_dir):
            if f.lower().endswith(('.exe', '.msi', '.bat')):
                installer_name = f
                if f.lower().endswith('.msi') and args == "/S":
                    args = "/quiet /norestart"
                break

    if os.path.exists(os.path.join(app_dir, 'isvec.ps1')):
        is_custom = "$true"
        
    display_name = app_id.replace('_', ' ').title()
    
    ps1_content = ps1_template.replace('{{APP_ID}}', app_id)\
                              .replace('{{APP_NAME}}', display_name)\
                              .replace('{{INSTALLER_NAME}}', installer_name)\
                              .replace('{{BASE_URL}}', base_url)\
                              .replace('{{ARGS}}', args)\
                              .replace('{{IS_CUSTOM}}', is_custom)
                              
    bom = b'\xef\xbb\xbf'
    return Response(bom + ps1_content.encode('utf-8'), mimetype='text/plain; charset=utf-8')



@installations_manager_bp.route('/downloads/list', methods=['GET'])
def list_download_files():
    """Hızlı Kurulumlar > Gerekli İndirmeler listesini döndürür."""
    try:
        dl_dir = get_download_dir()
        os.makedirs(dl_dir, exist_ok=True)
        files = []
        for filename in os.listdir(dl_dir):
            full_path = os.path.join(dl_dir, filename)
            if os.path.isfile(full_path):
                files.append(file_info(full_path, filename))
        files.sort(key=lambda x: x.get('name', '').lower())
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'files': []}), 500

@installations_manager_bp.route('/downloads/get/<path:filename>', methods=['GET'])
def get_download_file(filename):
    """Gerekli indirmeler dosyasını indirir."""
    dl_dir = get_download_dir()
    file_path = safe_join(dl_dir, filename)
    if not file_path or not os.path.exists(file_path) or not os.path.isfile(file_path):
        return jsonify({'success': False, 'error': 'Dosya bulunamadı'}), 404
    return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))

@installations_manager_bp.route('/downloads/upload', methods=['POST'])
@require_editor
def upload_download_file():
    """Gerekli indirmeler alanına dosya yükler."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Dosya seçilmedi'}), 400
        file = request.files['file']
        if not file or not file.filename:
            return jsonify({'success': False, 'error': 'Geçersiz dosya'}), 400
        dl_dir = get_download_dir()
        os.makedirs(dl_dir, exist_ok=True)
        filename = secure_filename(file.filename)
        file.save(os.path.join(dl_dir, filename))
        return jsonify({'success': True, 'message': 'Dosya yüklendi'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@installations_manager_bp.route('/downloads/delete/<path:filename>', methods=['DELETE'])
@require_editor
def delete_download_file(filename):
    """Gerekli indirmeler alanından dosya siler."""
    try:
        dl_dir = get_download_dir()
        file_path = safe_join(dl_dir, filename)
        if not file_path or not os.path.exists(file_path) or not os.path.isfile(file_path):
            return jsonify({'success': False, 'error': 'Dosya bulunamadı'}), 404
        os.remove(file_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@installations_manager_bp.route('/upload', methods=['POST'])
@require_editor
def upload_new_app():
    if 'file' not in request.files:
        return jsonify({'error': 'Dosya secilmedi'}), 400
        
    file = request.files['file']
    app_name = request.form.get('app_name', '').strip()
    is_sifir_imaj = request.form.get('is_sifir_imaj') == 'true'
    
    if not file or not file.filename:
        return jsonify({'error': 'Gecersiz dosya'}), 400
    if not app_name:
        return jsonify({'error': 'Uygulama adi bos olamaz'}), 400
        
    folder_name = app_name.upper().replace(' ', '_')
        
    app_dir = get_safe_app_dir(folder_name, check_exists=False)
    if not app_dir:
        return jsonify({'error': 'Gecersiz uygulama adi'}), 400
    
    os.makedirs(app_dir, exist_ok=True)
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(app_dir, filename)
    file.save(file_path)
    
    # Sifir imaj isaretleme (sifirimaj.txt ile)
    if is_sifir_imaj:
        with open(os.path.join(app_dir, 'sifirimaj.txt'), 'w') as f:
            f.write('1')
    
    return jsonify({'success': True, 'message': f'{folder_name} basariyla eklendi!'})

@installations_manager_bp.route('/update/<app_id>', methods=['POST'])
@require_editor
def update_app(app_id):
    if 'file' not in request.files:
        return jsonify({'error': 'Dosya secilmedi'}), 400
        
    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'Gecersiz dosya'}), 400
        
    app_dir = get_safe_app_dir(app_id)
    if not app_dir:
        return jsonify({'error': 'Klasor bulunamadi'}), 404
        
    filename = secure_filename(file.filename)
    file_path = os.path.join(app_dir, filename)
    file.save(file_path)
    
    # Versiyon rotasyonu: Sadece .exe ve .msi dosyalarini kontrol et
    installers = []
    for f in os.listdir(app_dir):
        if f.lower().endswith('.exe') or f.lower().endswith('.msi'):
            p = os.path.join(app_dir, f)
            installers.append((p, os.path.getmtime(p)))
            
    # En yeni bastan sirala
    installers.sort(key=lambda x: x[1], reverse=True)
    
    # 5'ten fazla varsa eskileri sil
    deleted_count = 0
    if len(installers) > 6:
        for old_file_path, _ in installers[6:]:
            try:
                os.remove(old_file_path)
                deleted_count += 1
            except:
                pass
                
    msg = 'Uygulama basariyla guncellendi.'
    if deleted_count > 0:
        msg += f' {deleted_count} adet eski surum silindi (max 6 surum korunuyor).'
        
    return jsonify({'success': True, 'message': msg})

@installations_manager_bp.route('/update_zero_image', methods=['POST'])
@require_editor
def update_zero_image():
    data = request.json
    if not data or 'selected_ids' not in data:
        return jsonify({'error': 'Gecersiz istek'}), 400
        
    selected_ids = data['selected_ids']
    
    # Iterate all items in INSTALL_DIR
    try:
        items = os.listdir(INSTALL_DIR)
        for item in items:
            item_path = os.path.join(INSTALL_DIR, item)
            if not os.path.isdir(item_path):
                continue
                
            sifir_file = os.path.join(item_path, 'sifirimaj.txt')
            if item in selected_ids:
                if not os.path.exists(sifir_file):
                    with open(sifir_file, 'w') as f:
                        f.write('1')
            else:
                if os.path.exists(sifir_file):
                    os.remove(sifir_file)
                    
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
