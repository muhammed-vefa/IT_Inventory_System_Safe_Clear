
import os

def check_syntax(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We can't use python to check JS syntax, but we can look for suspicious characters
    # Check for any unexpected non-ASCII chars
    for i, line in enumerate(content.split('\n')):
        for char in line:
            if ord(char) > 127 and char not in "ıİçÇşŞüÜöÖğĞ—–•…‘’“”″′−≈≠≤≥→←↑↓↔═║╔╗╚╝╠╣╦╩╬ ":
                print(f"Suspicious char {char} (ord {ord(char)}) at line {i+1}")
                print(f"Line content: {line}")

check_syntax('frontend/UI_controller.js')
