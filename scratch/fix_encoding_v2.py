
import os

def solve_mojibake(text):
    # This pattern handles most common Turkish mojibake from UTF-8 -> Latin-1
    try:
        # If it's already "double encoded", this will fix it
        return text.encode('latin-1').decode('utf-8')
    except:
        # If it fails, try manual replacements for specific leftovers
        replacements = {
            'Ä±': 'ı', 'Ä°': 'İ', 'Ã§': 'ç', 'Ã‡': 'Ç', 'ÅŸ': 'ş', 'Åž': 'Ş',
            'Ã¼': 'ü', 'Ãœ': 'Ü', 'Ã¶': 'ö', 'Ã–': 'Ö', 'ÄŸ': 'ğ', 'Äž': 'Ğ',
            'â€”': '—', 'â€“': '–', 'Â': ''
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text

def fix_file(path):
    with open(path, 'rb') as f:
        data = f.read()
    
    # Try to see if it's already broken
    try:
        text = data.decode('utf-8')
        fixed = solve_mojibake(text)
        if fixed != text:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(fixed)
            print(f"Fixed {path}")
            return True
    except:
        pass
    return False

fix_file('frontend/UI_controller.js')
fix_file('index.html')
