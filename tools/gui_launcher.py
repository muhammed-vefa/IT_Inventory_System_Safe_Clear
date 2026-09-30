import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import sys
import queue
import time

ASCII_ART = """\
     :::    ::: :::::::::: :::   ::: :::::::::      ::: ::::::::::: :::
     :+:   :+:  :+:        :+:   :+: :+:    :+:   :+: :+:   :+:   :+: :+:
     +:+  +:+   +:+         +:+ +:+  +:+    +:+  +:+   +:+  +:+  +:+   +:+
     +#++:++    +#++:++#     +#++:   +#+    +:+ +#++:++#++: +#+ +#++:++#++:
     +#+  +#+   +#+           +#+    +#+    +#+ +#+     +#+ +#+ +#+     +#+
     #+#   #+#  #+#           #+#    #+#    #+# #+#     #+# #+# #+#     #+#
     ###    ### ##########    ###    #########  ###     ### ### ###     ###
"""

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("IT INVENTORY SISTEMI - ANA SUNUCU")
        window_width = 1000
        window_height = 700
        
        # Ekranin tam ortasinda acilmasi icin matematiksel hesaplama
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.root.configure(bg="#0d1117")
        
        # Queue for thread-safe UI updates
        self.log_queue = queue.Queue()
        
        self.setup_ui()
        self.start_server()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_queue()

    def setup_ui(self):
        # Header Frame
        self.header_frame = tk.Frame(self.root, bg="#0d1117", pady=10)
        self.header_frame.pack(fill=tk.X)
        
        # ASCII Logo
        self.logo_label = tk.Label(
            self.header_frame, 
            text=ASCII_ART, 
            font=("Consolas", 10, "bold"), 
            fg="#00d2ff", 
            bg="#0d1117",
            justify=tk.LEFT
        )
        self.logo_label.pack()
        
        # Title Label
        self.title_label = tk.Label(
            self.header_frame, 
            text="KEYDATA IT INVENTORY SISTEMI - ANA SUNUCU", 
            font=("Consolas", 12, "bold"), 
            fg="#facc15", 
            bg="#0d1117"
        )
        self.title_label.pack(pady=(5, 0))
        
        # Warning Label
        self.warn_label = tk.Label(
            self.header_frame, 
            text="[!] Bu pencereyi kapatirsaniz site erisime kapanir.", 
            font=("Consolas", 10, "bold"), 
            fg="#ef4444", 
            bg="#0d1117"
        )
        self.warn_label.pack(pady=(2, 5))
        
        # Log Text Area
        self.log_text = scrolledtext.ScrolledText(
            self.root, 
            state='disabled', 
            bg="#010409", 
            fg="#e6edf3", 
            font=("Consolas", 10),
            padx=10,
            pady=10
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Renk Etiketleri (Tags)
        self.log_text.tag_config("error", foreground="#ff7b72", font=("Consolas", 10, "bold"))
        self.log_text.tag_config("warn", foreground="#d2a8ff")
        self.log_text.tag_config("info", foreground="#79c0ff")
        self.log_text.tag_config("success", foreground="#3fb950", font=("Consolas", 10, "bold"))
        self.log_text.tag_config("http", foreground="#8b949e")
        self.log_text.tag_config("default", foreground="#e6edf3")
        
        # Initial logs
        self.append_log("[+] Veritabani baglantilari kontrol ediliyor...\n", "info")
        self.append_log("[+] Web Arayuzu hazirlaniyor...\n", "info")
        self.append_log("[+] Flask Sunucusu (Port 5000) AKTIF ediliyor...\n", "success")
        self.append_log("-" * 80 + "\n", "default")

    def append_log(self, text, force_tag=None):
        self.log_text.configure(state='normal')
        
        if force_tag:
            self.log_text.insert(tk.END, text, force_tag)
        else:
            upper_text = text.upper()
            if "ERROR" in upper_text or "EXCEPTION" in upper_text or "TRACEBACK" in upper_text or "[FAIL]" in text:
                self.log_text.insert(tk.END, text, "error")
            elif "WARN" in upper_text or "[!]" in text:
                self.log_text.insert(tk.END, text, "warn")
            elif "[MATRIX]" in upper_text:
                self.log_text.insert(tk.END, text, "info")
            elif "[+]" in text or "[*]" in text or "INFO" in upper_text:
                self.log_text.insert(tk.END, text, "info")
            elif "HTTP/1" in upper_text or "GET /" in upper_text or "POST /" in upper_text or "PUT /" in upper_text or "DELETE /" in upper_text:
                self.log_text.insert(tk.END, text, "http")
            elif "SUCCESS" in upper_text or "HAZIR" in upper_text:
                self.log_text.insert(tk.END, text, "success")
            else:
                self.log_text.insert(tk.END, text, "default")
                
        self.log_text.configure(state='disabled')
        self.log_text.see(tk.END)
        
    def process_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                try:
                    # Gelen veriyi güvenli string'e çevir
                    if isinstance(msg, bytes):
                        safe_msg = msg.decode('utf-8', errors='replace')
                    else:
                        safe_msg = str(msg)
                    self.append_log(safe_msg)
                except Exception as e:
                    # Ekrana basılamayan özel karakterler gelirse GUI çökmesini önlemek için terminale yazdır
                    print(f"[GUI Log Processing Error] {e}")
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def read_stdout(self, pipe):
        import os
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file_path = os.path.join(log_dir, "server_console.log")
        
        try:
            with open(log_file_path, "w", encoding="utf-8") as f:
                f.write("[+] Sunucu Baslatildi - Canli Konsol Log Akisi\n")
        except Exception as e:
            print(f"Log file init error: {e}")

        for line in iter(pipe.readline, ''):
            if line:
                self.log_queue.put(line)
                try:
                    with open(log_file_path, "a", encoding="utf-8") as f:
                        f.write(line)
                except Exception as append_e:
                    print(f"[GUI File Append Error] {append_e}")
        pipe.close()
        
        try:
            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write("[!] Sunucu kapandi. Arayuz 3 saniye icinde kapatilacak...\n")
        except Exception as write_close_e:
            print(f"[GUI Write Close Message Error] {write_close_e}")
            
        self.log_queue.put("[!] Sunucu kapandi. Arayuz 3 saniye icinde kapatilacak...\n")
        time.sleep(3)
        self.root.after(0, self.root.destroy)
        
    def start_server(self):
        import os
        env_vars = os.environ.copy()
        env_vars['PYTHONIOENCODING'] = 'utf-8'
        env_vars['PYTHONUNBUFFERED'] = '1'
        
        self.process = subprocess.Popen(
            [sys.executable, "-u", "tools/main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace',
            env=env_vars,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        
        self.thread = threading.Thread(target=self.read_stdout, args=(self.process.stdout,))
        self.thread.daemon = True
        self.thread.start()
        
    def on_closing(self):
        if hasattr(self, 'process') and self.process.poll() is None:
            self.process.terminate()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ServerGUI(root)
    root.mainloop()
