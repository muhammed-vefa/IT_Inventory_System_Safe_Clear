import re

with open('modules/printers_printers.py', 'r', encoding='utf-8') as f:
    content = f.read()

batch_action_code = """
import requests
from flask import request, jsonify

@printers_printers_bp.route('/batch_action', methods=['POST'])
@require_editor
def batch_action():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.json
        action = data.get('action') # 'add' or 'remove'
        bim_function = data.get('bim_function')
        command = data.get('command')
        printer_id = data.get('printer_id')
        targets = data.get('targets', [])
        bim_user = data.get('bim_user')
        bim_pass = data.get('bim_pass')
        user = data.get('user', 'system')

        cursor.execute("SELECT pr_no FROM printers WHERE id = ?", (printer_id,))
        pr_row = cursor.fetchone()
        pr_no = pr_row[0] if pr_row else ''
        if not pr_no and command:
            pr_no = command.split('/')[0]

        success_count = 0
        failed_targets = []

        for target in targets:
            pc_id = target.get('value')
            cursor.execute("SELECT id, ip, pc_no FROM pcs WHERE id = ?", (pc_id,))
            pc_row = cursor.fetchone()
            if not pc_row:
                failed_targets.append(f"PC ID {pc_id} bulunamadi.")
                continue
            
            p_id, p_ip, p_name = pc_row
            if not p_ip:
                failed_targets.append(f"{p_name} (IP yok)")
                continue

            base_url = "http://bim.kocaelish.com/Handler.ashx"
            login_data = {
                "Functions": "Login",
                "UserName": bim_user,
                "Password": bim_pass
            }
            browser_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            
            try:
                login_resp = requests.post(base_url, data=login_data, headers=browser_headers, timeout=10)
                if login_resp.status_code != 200 or login_resp.text.strip() == "Error" or not login_resp.text.strip():
                    failed_targets.append(f"{p_name} (BIM Giris Basarisiz)")
                    continue
                ipa_session = login_resp.text.strip()
            except Exception as e:
                failed_targets.append(f"{p_name} (BIM Login Hatasi)")
                continue

            if bim_function in ["AddPrinter", "RemovePrinter"]:
                send_data = {
                    "Functions": bim_function,
                    "IpAddress": p_ip,
                    "Parameter": command,
                    "IpaSession": ipa_session
                }
            else:
                send_data = {
                    "Functions": "ExecuteCommand",
                    "IpAddress": p_ip,
                    "Command": command,
                    "IpaSession": ipa_session
                }

            try:
                cmd_resp = requests.post(base_url, data=send_data, headers=browser_headers, timeout=15)
                if cmd_resp.status_code != 200 or "Error" in cmd_resp.text:
                    failed_targets.append(f"{p_name} (BIM Hatasi: {cmd_resp.text.strip()})")
                    continue
            except Exception as e:
                failed_targets.append(f"{p_name} (BIM Cmd Hatasi)")
                continue


            success_count += 1

        conn.commit()
        
        return jsonify({
            "success": True,
            "success_count": success_count,
            "failed": failed_targets
        })
    except Exception as e:
        print("Batch action error:", e)
        return jsonify({"error": str(e)}), 500
"""

if "@printers_printers_bp.route('/batch_action'" not in content:
    with open('modules/printers_printers.py', 'a', encoding='utf-8') as f:
        f.write('\n' + batch_action_code + '\n')
    print("Added batch_action route")
else:
    print("batch_action already exists")
