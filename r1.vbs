Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)
' [v8.7.4] pythonw(콘솔 없음) + 전체경로로 실행.
'   - 과거 "pythonw 는 창이 안 뜸" 은 WebView2 문제가 아니라 main_webview.py 가
'     stdout/stderr(None) 를 frozen 일 때만 리다이렉트해서 uvicorn/print 가 크래시한 것.
'     이제 None 이면 무조건 로그파일로 리다이렉트하도록 수정됨 → pythonw 정상.
'   - cmd 래퍼 제거: 검은 콘솔 깜빡임 없음.
'   - 전체경로(C:\Python314\pythonw.exe): PATH 순서/WindowsApps 스텁 영향 차단.
'   - Python 위치를 옮기면 아래 PY 경로만 수정.
PY = "C:\Python314\pythonw.exe"
WshShell.Run """" & PY & """ main_webview.py", 0, False
Set WshShell = Nothing
