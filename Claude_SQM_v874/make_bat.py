# -*- coding: utf-8 -*-
import sys
bat = "@echo off\n" 
bat += "F:\n" 
bat += "cd \"���α׷�\\Sqm �������\\Claude_SQM_v868\"\n" 
bat += "if not exist react_api\\main.py (echo FAIL: react_api not found & pause & exit /b 1)\n" 
bat += "echo OK: react_api found\n" 
bat += "if not exist .env (echo FAIL: .env not found & pause & exit /b 1)\n" 
bat += "echo OK: .env found\n" 
bat += "if not exist scripts\\telegram_bridge.py (echo FAIL: bridge not found & pause & exit /b 1)\n" 
bat += "echo ALL PASSED\n" 
bat += "echo 1. Telegram Bridge\n" 
bat += "echo 2. Claude Direct\n" 
bat += "set /p MODE=Choice (1/2/3): \n" 
bat += "if \"%MODE%\"==\"1\" python scripts\\telegram_bridge.py\n" 
bat += "if \"%MODE%\"==\"2\" claude --dangerously-skip-permissions -p \"Execute MASTER_FINAL_v868\"\n" 
bat += "pause\n" 
open("run_master.bat","w",encoding="cp949").write(bat) 
print("Done") 
