import os
import json
from flask import Blueprint, jsonify, request, send_file, render_template_string, Response, send_from_directory
import urllib.parse
from core.auth import require_admin, require_editor

isvec_service_bp = Blueprint('isvec_service', __name__)
# Sabit yol (IT_Inventory dizini icindeki static/kurulum_dosyalari)
INSTALL_DIR = os.path.join(os.getcwd(), 'static', 'kurulum_dosyalari')

@isvec_service_bp.route('/apps', methods=['GET'])
def list_apps():
    if not os.path.exists(INSTALL_DIR):
        os.makedirs(INSTALL_DIR, exist_ok=True)
    
    apps = []
    # Bazi bilinen uygulamalar icin ozel silent install argumanlari. 
    known_args = {
        'ANYDESK': '/sAll /rs /qn',
        'MSI': '/quiet /norestart',
        'ZOIPER': '--mode unattended',
        'ZOİPER': '--mode unattended',
        'CHROME': '/silent /install'
    }

    for item in os.listdir(INSTALL_DIR):
        item_path = os.path.join(INSTALL_DIR, item)
        if os.path.isdir(item_path):
            args = "/S" # Genel varsayilan
            item_upper = item.upper()
            
            # Sifir imaj kontrolu
            is_sifir_imaj = False
            if item_upper.endswith('_SI') or os.path.exists(os.path.join(item_path, 'sifirimaj.txt')):
                is_sifir_imaj = True
                
            # Ozel script kontrolu
            is_custom = False
            if os.path.exists(os.path.join(item_path, 'isvec.ps1')):
                is_custom = True
            
            for key, val in known_args.items():
                if key in item_upper:
                    args = val
                    break
            
            # Klasor isminden okunakli isim uret, _SI takisini gizle
            display_name = item
            if item_upper.endswith('_SI'):
                display_name = item[:-3]
            display_name = display_name.replace('_', ' ').title()
            
            apps.append({
                'id': item,
                'name': display_name,
                'args': args,
                'is_sifir_imaj': is_sifir_imaj,
                'is_custom': is_custom
            })
    
    return jsonify({'apps': apps})

@isvec_service_bp.route('/<app_id>/manifest', methods=['GET'])
def get_manifest(app_id):
    app_dir = os.path.join(INSTALL_DIR, app_id)
    if not os.path.exists(app_dir) or not os.path.isdir(app_dir):
        return jsonify({'error': 'App not found'}), 404
        
    files = []
    for root, dirs, filenames in os.walk(app_dir):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, app_dir)
            files.append(rel_path.replace('\\', '/'))
            
    return jsonify({'files': files})

@isvec_service_bp.route('/<app_id>/file/<path:subpath>', methods=['GET'])
def get_file(app_id, subpath):
    app_dir = os.path.join(INSTALL_DIR, app_id)
    if not os.path.exists(app_dir) or not os.path.isdir(app_dir):
        return "App not found", 404
    return send_from_directory(app_dir, subpath)

@isvec_service_bp.route('/<app_id>/download', methods=['GET'])
def download_installer(app_id):
    app_dir = os.path.join(INSTALL_DIR, app_id)
    if not os.path.exists(app_dir) or not os.path.isdir(app_dir):
        return "App not found", 404
        
    # Klasordeki exe, msi veya jar dosyasini bulur (Custom script yoksa)
    for ext in ['.exe', '.msi', '.jar']:
        for f in os.listdir(app_dir):
            if f.lower().endswith(ext):
                file_path = os.path.join(app_dir, f)
                return send_file(file_path, as_attachment=True, download_name=f)
    
    # Eger bulamazsa, en buyuk dosyayi dondur
    largest_file = None
    max_size = -1
    for f in os.listdir(app_dir):
        file_path = os.path.join(app_dir, f)
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            if size > max_size:
                max_size = size
                largest_file = f
                
    if largest_file:
        file_path = os.path.join(app_dir, largest_file)
        return send_file(file_path, as_attachment=True, download_name=largest_file)

    return "Installer not found in directory", 404

@isvec_service_bp.route('/bulk', methods=['GET'])
def generate_bulk_script():
    ids = request.args.get('ids', '')
    if not ids:
        return "No IDs provided", 400
        
    id_list = ids.split(',')
    
    ps1_template = """
$ProgressPreference = 'SilentlyContinue'
$ErrorActionPreference = 'SilentlyContinue'
$WarningPreference = 'SilentlyContinue'
$env:ISVEC_SERVER_ROOT = "{{SERVER_ROOT}}"

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
$form.Size = New-Object System.Drawing.Size(400,200)
$form.StartPosition = "CenterScreen"
$form.TopMost = $true
$form.FormBorderStyle = "FixedToolWindow"

$label = New-Object System.Windows.Forms.Label
$label.Location = New-Object System.Drawing.Point(20,20)
$label.Size = New-Object System.Drawing.Size(340,30)
$label.Text = "Toplu kurulum baslatiliyor..."
$form.Controls.Add($label)

$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Location = New-Object System.Drawing.Point(20,60)
$progressBar.Size = New-Object System.Drawing.Size(340,30)
$progressBar.Style = "Blocks"
$progressBar.Minimum = 0
$progressBar.Maximum = {{TOTAL_COUNT}}
$form.Controls.Add($progressBar)

$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Location = New-Object System.Drawing.Point(20,100)
$logBox.Size = New-Object System.Drawing.Size(340,50)
$logBox.Multiline = $true
$logBox.ReadOnly = $true
$logBox.ScrollBars = "Vertical"
$form.Controls.Add($logBox)

$form.Show() | Out-Null
$form.Refresh()

function Add-Log($msg) {
    $logBox.AppendText($msg + "`r`n")
    $logBox.ScrollToCaret()
    $label.Text = $msg
    $form.Refresh()
}

$apps = @(
{{APPS_ARRAY}}
)
$sharePathB64 = "XFwxMC4yNDEuMS4xOTlca3VydWx1bV9kb3N5YWxhcmk="
$sharePath = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($sharePathB64))

foreach ($app in $apps) {
    Add-Log "Kuruluyor: $($app.Name)"
    $progressBar.Value += 1
    
    $env:SEE_MASK_NOZONECHECKS = 1

    try {
        $appShareDir = "$sharePath\$($app.Id)"
        if (!(Test-Path $appShareDir)) {
            Add-Log "HATA: Ag yolu bulunamadi"
            continue
        }

        if ($app.IsCustom) {
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
                $argsArray = $app.Args -split ' ' | Where-Object { $_ -ne '' }
                $process = Start-Process -FilePath $exeFile.FullName -ArgumentList $argsArray -Wait -PassThru -NoNewWindow
            } else {
                Add-Log "HATA: Kurulum dosyasi bulunamadi."
            }
        }
        Add-Log "Kurulum tamamlandi!"
    } catch {
        Add-Log "HATA: $($_.Exception.Message)"
    }
}
Remove-Item Env:\SEE_MASK_NOZONECHECKS -ErrorAction SilentlyContinue
    
    Add-Log "Tamamlandi: $($app.Name)"
}

Add-Log "TUM KURULUMLAR TAMAMLANDI!"
Start-Sleep -Seconds 3
$form.Close()
"""
    
    base_url = request.url_root.rstrip('/') + '/isvec'
    
    apps_array_str = ""
    
    if not os.path.exists(INSTALL_DIR):
        os.makedirs(INSTALL_DIR, exist_ok=True)
    
    # Argumanlari yeniden hesaplayalim veya list_apps icindeki mantigi kopyalayalim
    known_args = {
        'ANYDESK': '/sAll /rs /qn',
        'MSI': '/quiet /norestart',
        'ZOIPER': '--mode unattended',
        'ZOİPER': '--mode unattended',
        'CHROME': '/silent /install'
    }
    
    count = 0
    for app_id in id_list:
        app_dir = os.path.join(INSTALL_DIR, app_id)
        if os.path.exists(app_dir):
            count += 1
            item_upper = app_id.upper()
            args = "/S"
            for key, val in known_args.items():
                if key in item_upper:
                    args = val
                    break
            
            is_custom = "$false"
            if os.path.exists(os.path.join(app_dir, 'isvec.ps1')):
                is_custom = "$true"
            
            display_name = app_id.replace('_SI', '').replace('_', ' ').title()
            safe_app_id = app_id.replace(' ', '%20')
            apps_array_str += f"    @{{ Id='{app_id}'; Name='{display_name}'; BaseUrl='{base_url}/{safe_app_id}'; Args='{args}'; IsCustom={is_custom} }},\n"

    ps1_content = ps1_template.replace('{{TOTAL_COUNT}}', str(count)).replace('{{APPS_ARRAY}}', apps_array_str.rstrip(',\n')).replace('{{SERVER_ROOT}}', base_url)
    return Response(ps1_content, mimetype='text/plain')

@isvec_service_bp.route('/<app_id>/', methods=['GET'])
def generate_script(app_id):
    # Bu endpoint tekli kurulumlar icindir. Sadece bulk scriptin kucultulmus halidir.
    return generate_bulk_script_for_single(app_id)

def generate_bulk_script_for_single(app_id):
    ps1_template = """
$ProgressPreference = 'SilentlyContinue'
$ErrorActionPreference = 'SilentlyContinue'
$WarningPreference = 'SilentlyContinue'

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
$form.TopMost = $true
$form.FormBorderStyle = "FixedToolWindow"

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

$sharePathB64 = "XFwxMC4yNDEuMS4xOTlca3VydWx1bV9kb3N5YWxhcmk="
$sharePath = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($sharePathB64))

try {
    $env:SEE_MASK_NOZONECHECKS = 1
    
    $appShareDir = "$sharePath\{{APP_ID}}"
    if (!(Test-Path $appShareDir)) {
        Add-Log "HATA: Ag yolu bulunamadi"
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
            $process = Start-Process -FilePath $exeFile.FullName -ArgumentList $argsArray -Wait -PassThru -NoNewWindow
        } else {
            Add-Log "HATA: Kurulum dosyasi bulunamadi."
        }
    }
    Add-Log "Kurulum tamamlandi!"
} catch {
    Add-Log "HATA: $($_.Exception.Message)"
} finally {
    Remove-Item Env:\SEE_MASK_NOZONECHECKS -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2
$form.Close()
"""
    safe_app_id = app_id.replace(' ', '%20')
    base_url = request.url_root.rstrip('/') + '/isvec/' + safe_app_id
    
    app_dir = os.path.join(INSTALL_DIR, app_id)
    if not os.path.exists(app_dir):
        return "App not found", 404
        
    known_args = {
        'ANYDESK': '/sAll /rs /qn',
        'MSI': '/quiet /norestart',
        'ZOIPER': '--mode unattended',
        'ZOİPER': '--mode unattended',
        'CHROME': '/silent /install'
    }
    
    item_upper = app_id.upper()
    args = "/S"
    for key, val in known_args.items():
        if key in item_upper:
            args = val
            break
            
    is_custom = "$false"
    if os.path.exists(os.path.join(app_dir, 'isvec.ps1')):
        is_custom = "$true"
        
    display_name = app_id.replace('_SI', '').replace('_', ' ').title()
    
    ps1_content = ps1_template.replace('{{APP_ID}}', app_id)\
                              .replace('{{APP_NAME}}', display_name)\
                              .replace('{{BASE_URL}}', base_url)\
                              .replace('{{ARGS}}', args)\
                              .replace('{{IS_CUSTOM}}', is_custom)
                              
    return Response(ps1_content, mimetype='text/plain')
