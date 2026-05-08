import os
import sys
import datetime
import time

# IT Inventory System yollarını ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from modules.keyos_service import get_all_mismatches_internal, get_keyos_session
from modules.printer_manager import CUPSHelper

def test_keyos():
    print("\n--- Testing KeyOS Login ---")
    user = os.getenv('KEYOS_USER')
    password = os.getenv('KEYOS_PASS')
    url = os.getenv('KEYOS_URL')
    
    print(f"Target: {url}")
    print(f"User: {user}")
    
    session = get_keyos_session(user, password)
    if session:
        print("SUCCESS: KeyOS Login Successful!")
        # Try fetching mismatches
        print("Fetching mismatches...")
        mismatches, error = get_all_mismatches_internal()
        if error:
            print(f"ERROR fetching mismatches: {error}")
        else:
            print(f"SUCCESS: Found {len(mismatches)} mismatches.")
    else:
        print("FAILED: KeyOS Login Failed.")

def test_cups():
    print("\n--- Testing CUPS Connectivity ---")
    print(f"Target: {CUPSHelper.BASE_URL}")
    
    print("Fetching all printer locations...")
    cups_data = CUPSHelper.get_all_locations()
    if cups_data:
        print(f"SUCCESS: Found {len(cups_data)} printers in CUPS.")
        # Print first 5
        for i, (name, loc) in enumerate(cups_data.items()):
            if i >= 5: break
            print(f"  - {name}: {loc}")
    else:
        print("FAILED: Could not fetch data from CUPS.")

if __name__ == "__main__":
    test_keyos()
    test_cups()
