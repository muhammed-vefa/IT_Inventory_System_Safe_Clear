
import os

def fix_mojibake_in_text(text):
    replacements = {
        'Ä±': 'ı', 'Ä°': 'İ', 'Ã§': 'ç', 'Ã‡': 'Ç', 'ÅŸ': 'ş', 'Åž': 'Ş',
        'Ã¼': 'ü', 'Ãœ': 'Ü', 'Ã¶': 'ö', 'Ã–': 'Ö', 'ÄŸ': 'ğ', 'Äž': 'Ğ',
        'â€”': '—', 'â€“': '–', 'â€¢': '•', 'â€¦': '…', 'â€˜': '‘',
        'â€™': '’', 'â€œ': '“', 'â€?': '”', 'â€³': '″', 'â€²': '′',
        'âˆ’': '−', 'â‰ˆ': '≈', 'â‰': '≠', 'â‰¤': '≤', 'â‰¥': '≥',
        'â†’': '→', 'â†': '←', 'â†‘': '↑', 'â†“': '↓', 'â†↔': '↔',
        'â• ': '═', 'â•': '═', 'â•‘': '║', 'â•': '╔', 'â•': '╗',
        'â•š': '╚', 'â•': '╝', 'â•': '╠', 'â•': '╣', 'â•': '╦', 'â•': '╩',
        'â•': '╬'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

def process_file(file_path):
    if not os.path.isfile(file_path): return
    if file_path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico', '.db', '.xlsx')): return
    
    print(f"Checking {file_path}...")
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        try:
            text = content.decode('utf-8')
            fixed_text = fix_mojibake_in_text(text)
            
            if fixed_text != text:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_text)
                print(f"  Fixed mojibake in {file_path}")
        except UnicodeDecodeError:
            print(f"  Skipping {file_path} (not UTF-8)")
    except Exception as e:
        print(f"  Error processing {file_path}: {e}")

# Process files in root and frontend
for f in os.listdir('.'):
    if os.path.isfile(f): process_file(f)

if os.path.exists('frontend'):
    for f in os.listdir('frontend'):
        process_file(os.path.join('frontend', f))

print("Mojibake fix completed.")
