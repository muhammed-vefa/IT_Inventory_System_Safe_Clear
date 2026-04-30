
import os

def fix_mojibake(file_path):
    with open(file_path, 'rb') as f:
        content = f.read()
    
    try:
        # Try to decode as utf-8
        text = content.decode('utf-8')
        
        # If the file contains patterns like "Ä±", it means it's double-encoded.
        # "Ä±" is the UTF-8 representation of "ı" (C4 B1) but viewed as Latin-1.
        
        # Common patterns:
        replacements = {
            'Ä±': 'ı',
            'Ä°': 'İ',
            'Ã§': 'ç',
            'Ã‡': 'Ç',
            'ÅŸ': 'ş',
            'Åž': 'Ş',
            'Ã¼': 'ü',
            'Ãœ': 'Ü',
            'Ã¶': 'ö',
            'Ã–': 'Ö',
            'ÄŸ': 'ğ',
            'Äž': 'Ğ',
            'â•': '═', # Box drawing characters often get hit too
            'â• ': '═',
            'â•': '═',
            'â•': '═'
        }
        
        # Actually, let's try the more robust way:
        try:
            # Re-encode as latin-1 and decode as utf-8
            # This works if the file is UTF-8 bytes that were mis-read as Latin-1 and saved.
            new_text = text.encode('latin-1').decode('utf-8')
            print(f"Fixed {file_path} using latin-1 -> utf-8 re-encoding")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_text)
            return True
        except:
            # Fallback to manual replacement if re-encoding fails
            original_text = text
            for k, v in replacements.items():
                text = text.replace(k, v)
            
            if text != original_text:
                print(f"Fixed {file_path} using manual replacements")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                return True
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
    return False

fix_mojibake('frontend/UI_controller.js')
