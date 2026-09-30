import subprocess
import sys
import threading
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.console import Group
from collections import deque
import time

ASCII_ART = """\
     :::    ::: :::::::::: :::   ::: :::::::::      ::: ::::::::::: :::
     :+:   :+:  :+:        :+:   :+: :+:    :+:   :+: :+:   :+:   :+: :+:
     +:+  +:+   +:+         +:+ +:+  +:+    +:+  +:+   +:+  +:+  +:+   +:+
     +#++:++    +#++:++#     +#++:   +#+    +:+ +#++:++#++: +#+ +#++:++#++:
     +#+  +#+   +#+           +#+    +#+    +#+ +#+     +#+ +#+ +#+     +#+
     #+#   #+#  #+#           #+#    #+#    #+# #+#     #+# #+# #+#     #+#
     ###    ### ##########    ###    #########  ###     ### ### ###     ###\
"""

MAX_LOG_LINES = 100
log_lines = deque(maxlen=MAX_LOG_LINES)
log_lines.append("[+] Veritabani baglantilari kontrol ediliyor...")
log_lines.append("[+] Web Arayuzu hazirlaniyor...")
log_lines.append("[+] Flask Sunucusu (Port 5000) AKTIF ediliyor...")
log_lines.append("--------------------------------------------------")

def generate_layout():
    layout = Layout()
    layout.split(
        Layout(name="header", size=13),
        Layout(name="logs")
    )
    
    header_content = Group(
        Align.center(Text(ASCII_ART, style="cyan bold")),
        Text(""),
        Align.center(Text("KEYDATA IT INVENTORY SISTEMI - ANA SUNUCU", style="yellow bold")),
        Align.center(Text("[!] Bu pencereyi kapatirsaniz site erisime kapanir.", style="red bold")),
    )
    
    layout["header"].update(Panel(header_content, style="blue", border_style="blue"))
    
    log_text = Text("\n".join(log_lines))
    layout["logs"].update(Panel(log_text, title="Sunucu Loglari", border_style="green", style="white"))
    return layout

def read_output(pipe):
    # Read line by line from subprocess
    for line in iter(pipe.readline, ''):
        if line:
            log_lines.append(line.rstrip('\n'))

if __name__ == "__main__":
    # Start the Flask app as a subprocess with unbuffered output (-u)
    process = subprocess.Popen(
        [sys.executable, "-u", "tools/main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8',
        errors='replace'
    )
    
    # Thread to read stdout without blocking the UI
    t = threading.Thread(target=read_output, args=(process.stdout,))
    t.daemon = True
    t.start()
    
    main_layout = generate_layout()
    try:
        # Create Live dashboard that takes over the screen
        with Live(main_layout, refresh_per_second=10, screen=True) as live:
            while process.poll() is None:
                # Adjust visible log lines based on terminal size
                term_height = live.console.size.height
                visible_log_lines = max(1, term_height - 16) # Header is 13 + borders
                
                display_lines = list(log_lines)[-visible_log_lines:]
                log_text = Text("\n".join(display_lines))
                
                main_layout["logs"].update(Panel(log_text, title="Sunucu Loglari", border_style="green", style="white"))
                time.sleep(0.1)
                
            # Subprocess ended
            log_lines.append("[!] Sunucu kapandi. Cikiliyor...")
            display_lines = list(log_lines)[-visible_log_lines:]
            main_layout["logs"].update(Panel(Text("\n".join(display_lines)), title="Sunucu Loglari", border_style="red", style="white"))
            time.sleep(2)
            
    except KeyboardInterrupt:
        process.terminate()
