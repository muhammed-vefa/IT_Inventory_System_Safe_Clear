
import os

def trace_braces(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    balance = 0
    for i, line in enumerate(lines):
        prev_balance = balance
        balance += line.count('{')
        balance -= line.count('}')
        if balance != prev_balance:
            # Sadece denge deitiinde yazdıralım (çok kalabalık olmasın diye sadece riskli bölgelere odaklanabiliriz)
            # Ama kesin çözüm için her adımı kontrol etmek en iyisi
            pass
        
        # Eer denge negatife düerse veya dosya sonunda 0 deilse sorun var
        if balance < 0:
            print(f"ERROR: Negative balance at line {i+1}: {line.strip()}")
            return
            
    print(f"Final total balance: {balance}")
    # Detaylı tarama: Denge nerede 1'e çıktı ve bir daha 0'a inmedi?
    balance = 0
    for i, line in enumerate(lines):
        balance += line.count('{')
        balance -= line.count('}')
        if balance == 0:
            last_zero = i + 1
            
    print(f"Last line where balance was zero: {last_zero}")

trace_braces('frontend/UI_controller.js')
