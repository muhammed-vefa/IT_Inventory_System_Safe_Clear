
import re

def find_mojibake(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Common mojibake patterns
    patterns = [
        'Ä±', 'Ä°', 'Ã§', 'Ã‡', 'ÅŸ', 'Åž', 'Ã¼', 'Ãœ', 'Ã¶', 'Ã–', 'ÄŸ', 'Äž', 'â•', 'Ã', 'â€”'
    ]
    
    found = {}
    for p in patterns:
        count = text.count(p)
        if count > 0:
            found[p] = count
            
    return found

print(find_mojibake('frontend/UI_controller.js'))
