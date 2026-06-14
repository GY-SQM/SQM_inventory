Set WshShell = CreateObject("WScript.Shell")
' [fix] pythonw + 숨김(0) 은 WebView2 윈도우 스테이션 문제로 창이 안 뜨고
'       포트 8765 만 점유한 headless 좀비를 만든다.
'       검증된 r1.vbs(python 방식)로 위임해 단일 실행 경로로 통일.
sDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)
WshShell.CurrentDirectory = sDir
WshShell.Run "wscript //nologo """ & sDir & "\r1.vbs""", 0, False
Set WshShell = Nothing
