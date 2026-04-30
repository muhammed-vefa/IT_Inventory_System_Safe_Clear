
import os

def fix_bytes(path):
    with open(path, 'rb') as f:
        data = f.read()
    
    # Normal Turkish characters
    chars = "ıİçÇşŞüÜöÖğĞ"
    for c in chars:
        # What it looks like if UTF-8 was read as Latin-1 and then saved as UTF-8
        bad = c.encode('utf-8').decode('latin-1').encode('utf-8')
        if bad in data:
            print(f"Found bad sequence for {c} in {path}")
            data = data.replace(bad, c.encode('utf-8'))
    
    # Special case for some that might be slightly different or triple-encoded
    extra = {
        'â€”': '—',
        'â€“': '–',
        'â•': '═',
        'ÄŸ': 'ğ',
        'Äž': 'Ğ',
        'ÅŸ': 'ş',
        'Åž': 'Ş',
        'Ä°': 'İ',
        'Ä±': 'ı',
        'Ã§': 'ç',
        'Ã‡': 'Ç',
        'Ã¼': 'ü',
        'Ãœ': 'Ü',
        'Ã¶': 'ö',
        'Ã–': 'Ö'
    }
    
    # Try text-based replacement for these
    try:
        text = data.decode('utf-8')
        for k, v in extra.items():
            text = text.replace(k, v)
        data = text.encode('utf-8')
    except:
        pass

    with open(path, 'wb') as f:
        f.write(data)

fix_bytes('frontend/UI_controller.js')
fix_bytes('index.html')
