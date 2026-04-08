================================================================
Claude AutoPilot
Claude Code + Telegram 자동화 범용 모듈 패키지
================================================================

이 패키지는 어떤 프로젝트에도 붙일 수 있는 범용 모듈입니다.
SQM, 웹개발, 데이터분석, 문서작업 등 모든 Claude Code 프로젝트에 사용 가능합니다.

================================================================
[패키지 구성]
================================================================

Claude_AutoPilot/
├── README.txt                   이 파일
├── run_master.bat               실행 진입점
├── .env                         (설치 후 생성) Telegram 설정
│
├── scripts/
│   ├── telegram_bridge.py       핵심: Telegram 양방향 통신
│   ├── telegram_notify.py       단순 알림 발송
│   ├── watchdog.py              Bridge 자동 재시작
│   ├── wait_confirm.py          y/n 응답 대기
│   └── test_connection.py       연결 테스트
│
├── config/
│   └── .env.template            설정 파일 템플릿
│
├── templates/
│   └── MASTER_TEMPLATE.md       작업 지시서 템플릿
│
└── logs/                        로그 자동 저장

================================================================
[설치 순서 — 딱 5단계]
================================================================

STEP 1. 복사
  이 Claude_AutoPilot 폴더를 프로젝트 폴더 안에 복사

  예시:
  내프로젝트/
  ├── Claude_AutoPilot/   <-- 여기
  ├── src/
  └── ...

STEP 2. .env 설정
  config\.env.template → .env 복사 후 수정

  .env 파일:
    BOT_TOKEN=봇토큰입력
    CHAT_ID=채팅ID입력
    CLAUDE_PATH=claude  (또는 전체 경로)

  Telegram Bot 만들기:
    1. @BotFather 검색 → /newbot
    2. 토큰 복사 → BOT_TOKEN 에 입력

  Chat ID 확인:
    1. @userinfobot 검색 → /start
    2. 숫자 복사 → CHAT_ID 에 입력

  연결 테스트:
    python scripts	est_connection.py

STEP 3. MASTER.md 작성
  templates\MASTER_TEMPLATE.md → 프로젝트 루트에 MASTER.md 복사 후 수정

  핵심 규칙 (반드시 포함):
    - 중단 없이 끝까지 수행
    - 한 단계 완료 즉시 다음 단계 시작
    - input() 절대 금지

  각 단계 완료 시 반드시:
    python -c "open('logs/completed_steps.txt','a').write('단계ID_PASS\n')"
    python Claude_AutoPilot\scripts	elegram_notify.py "완료 메시지"

STEP 4. run_master.bat 수정
  메모장으로 열어서 두 줄만 수정:

    set PROJECT=F:\내프로젝트  (프로젝트 루트 경로)
    set CLAUDE=claude          (claude.exe 경로)

  claude.exe 경로 확인 (PowerShell):
    (Get-Command claude).Source

STEP 5. 실행
  run_master.bat 더블클릭
  → [ALL PRE-TESTS PASSED] 나오면 성공
  → Telegram에 시작 메시지 오면 퇴근!

================================================================
[Telegram 명령어]
================================================================

/help      전체 명령어
/status    현재 상태 + 진행률
/progress  진행률 막대
/log       최근 로그 10줄
/error     오류 목록
/restart   Claude Code 재시작
/stop      전체 중단

y / n      예/아니오 응답
1/2/3      선택지 응답
자유문장   Claude에 직접 지시

================================================================
[자동 알림]
================================================================

시작 시     : 시작 + 현재 진행률
단계 완료   : 즉시 알림 + 진행률
5분마다     : 정기 보고
오류 발생   : 즉시 알림
무응답 2분  : 알림
완료 시     : 최종 보고

================================================================
[멈출 때 해결 방법]
================================================================

Telegram 에서 입력:
  "멈추지 말고 다음 단계 계속 진행하라"
  또는 /restart

================================================================
[주의사항]
================================================================

1. 작업 중 창 닫지 말 것
   Claude Code 창 + Bridge 창 모두 유지

2. PC 절전 모드 OFF 필수
   powercfg /change standby-timeout-ac 0
   powercfg /change monitor-timeout-ac 0

3. .env 파일 외부 공유 금지 (BOT_TOKEN 포함)

================================================================
버전: 1.0 | 2026-04-05
================================================================
