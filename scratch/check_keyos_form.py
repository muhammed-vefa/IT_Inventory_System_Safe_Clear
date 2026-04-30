import requests
from bs4 import BeautifulSoup

LOGIN_URL = "https://keyosmgt.kocaelish.com/login"

try:
    resp = requests.get(LOGIN_URL, timeout=15, verify=False)
    soup = BeautifulSoup(resp.text, 'html.parser')
    inputs = soup.find_all('input')
    print("Form Inputs:")
    for i in inputs:
        print(f"Name: {i.get('name')}, Type: {i.get('type')}, ID: {i.get('id')}")
except Exception as e:
    print(f"Error: {e}")
