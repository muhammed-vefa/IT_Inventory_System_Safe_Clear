import subprocess
import os

def run_git():
    cwd = r"C:\Users\MUHAMMED-VEFA-IS\.gemini\antigravity\scratch\IT_Inventory_System"
    cmds = [
        ["git", "add", "."],
        ["git", "commit", "-m", "Emergency Fix - DB Connection and UI Restoration"],
        ["git", "push", "origin", "main", "-f"]
    ]
    for cmd in cmds:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        print(result.stdout)
        print(result.stderr)

if __name__ == "__main__":
    run_git()
