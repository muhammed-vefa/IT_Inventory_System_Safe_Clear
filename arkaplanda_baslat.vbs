Set WshShell = CreateObject("WScript.Shell")
' 0 parametresi pencereyi tamamen gizli (hidden) modda açar
WshShell.Run "cmd.exe /c baslat.bat", 0, False
WshShell.Run "cmd.exe /c python otomatik_guncelle.py", 0, False
