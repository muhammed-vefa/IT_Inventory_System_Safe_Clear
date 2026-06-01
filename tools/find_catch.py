import os

js_path = os.path.join("frontend", "UI_controller.js")
with open(js_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "catch" in line and "{}" in line:
        print(f"Line {i+1}: {line.strip()}")
    elif "catch" in line and "{" in line and "}" in line:
        if line.find("{") + 1 == line.find("}") or line.find("{") + 2 == line.find("}"):
            print(f"Line {i+1}: {line.strip()}")
