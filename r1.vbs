Set WshShell = CreateObject("WScript.Shell")
sDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)
py = "C:\Users\남기동\AppData\Local\Programs\Python\Python313\pythonw.exe"
cmd = """" & py & """ """ & sDir & "\main_webview.py" & """"
WshShell.CurrentDirectory = sDir
WshShell.Run cmd, 0, False
Set WshShell = Nothing
