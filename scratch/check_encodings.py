
import os

def check_encoding(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            f.read()
        return True
    except UnicodeDecodeError:
        return False

files_to_check = ['main.py', 'index.html', 'frontend/UI_controller.js', 'style.css']
for f in files_to_check:
    if os.path.exists(f):
        res = check_encoding(f)
        print(f"{f}: {'UTF-8 OK' if res else 'ENCODING ERROR'}")
