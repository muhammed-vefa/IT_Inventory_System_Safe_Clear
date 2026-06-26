import urllib.request
import base64

url = "https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.1.66/fonts/Roboto/Roboto-Regular.ttf"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
font_data = urllib.request.urlopen(req).read()

b64 = base64.b64encode(font_data).decode('utf-8')

with open("static/turkish_font.js", "w", encoding='utf-8') as f:
    f.write(f'window.RobotoBase64 = "{b64}";\n')
print("Font downloaded and js file created successfully!")
