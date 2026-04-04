파일 설명
1) GPT_Run_All_Claude_Stages.bat
   - B00 ~ B13 을 순차 실행하는 마스터 배치 파일
   - 각 단계 시작/통과/실패를 텔레그램으로 알림
   - 내부적으로 GPT_Run_Claude_Stage.bat 를 호출함

2) GPT_Send_Telegram.ps1
   - 텔레그램 bot API 로 메시지 전송

필수 준비
1. 아래 파일들을 같은 프로젝트 루트에 둡니다.
   - GPT_Run_All_Claude_Stages.bat
   - GPT_Send_Telegram.ps1
   - GPT_Run_Claude_Stage.bat
   - GPT_Run_Claude_Stage.ps1

2. auto_tasks 폴더에 단계 프롬프트 파일을 둡니다.
   - B00_prepare.md
   - B01_audit.md
   - B02_tx_guard.md
   - B03_status_guard.md
   - B04_integrity_guard.md
   - ... B13_final_validation.md

3. GPT_Run_All_Claude_Stages.bat 안의 아래 값을 실제 값으로 바꿉니다.
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID

중요
- 이 배치 파일은 이전 단계가 PASS 일 때만 다음 단계로 진행하는 구조를 전제로 합니다.
- 각 단계는 내부적으로 다음 명령 형식을 사용합니다.
  claude --dangerously-skip-permissions --system-prompt-file "파일이름.md"
- 실제 Claude 실행은 GPT_Run_Claude_Stage.bat 쪽에서 수행됩니다.

실행 예시
1) 전체 실행
   GPT_Run_All_Claude_Stages.bat
   GPT_Run_All_Claude_Stages.bat FULL

2) P0 만 실행
   GPT_Run_All_Claude_Stages.bat P0

3) P1 만 실행
   GPT_Run_All_Claude_Stages.bat P1

4) P2 만 실행
   GPT_Run_All_Claude_Stages.bat P2
