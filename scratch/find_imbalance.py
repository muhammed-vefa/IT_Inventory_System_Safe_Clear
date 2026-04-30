
import os

def find_imbalance(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    balance = 0
    for i, line in enumerate(lines):
        # Ignore braces in strings or comments (very simple check)
        # We'll just count them for now
        balance += line.count('{')
        balance -= line.count('}')
        if balance < 0:
            print(f"Negative balance at line {i+1}: {balance}")
            # Reset balance to continue
            balance = 0
            
    print(f"Final balance: {balance}")

find_imbalance('frontend/UI_controller.js')
