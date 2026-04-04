SQM Claude Stage Pipeline Pack
================================

Included:
- auto_tasks\COMMON_RULES.md
- auto_tasks\B00_prepare.md ~ B13_final_validation.md
- GPT_Run_Claude_Stage.bat
- GPT_Run_Claude_Stage.ps1
- GPT_Run_All_Claude_Stages.bat
- GPT_Send_Telegram.ps1

How to use:
1. Put all files in your SQM project root.
2. Make sure `claude` command works in PowerShell/CMD.
3. Run step-by-step:
   GPT_Run_Claude_Stage.bat B00 auto_tasks\B00_prepare.md
   GPT_Run_Claude_Stage.bat B01 auto_tasks\B01_audit.md
4. Or run grouped:
   GPT_Run_All_Claude_Stages.bat P0
   GPT_Run_All_Claude_Stages.bat P1
   GPT_Run_All_Claude_Stages.bat P2
   GPT_Run_All_Claude_Stages.bat FULL

Notes:
- The master runner contains a Telegram bot token and chat ID as requested.
- Keep this package private.
- Each batch should write reports/claude_runs/BXX/status.txt
- Next stage should only proceed when previous status.txt is PASS

Claude command used internally:
claude --dangerously-skip-permissions --system-prompt-file "파일이름.md"
