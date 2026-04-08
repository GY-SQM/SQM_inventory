SQM Telegram 무중단 작업 패키지
================================
생성일: 2026-04-04

[포함 파일]
scripts/
  telegram_bridge.py          - Telegram Bridge v3 (5분 알림 + 멈춤 감지)
  telegram_notify.py          - 진행 상태 알림 유틸리티
  test_telegram_connection.py - 연결 테스트

.env                          - Telegram 설정 (BOT_TOKEN, CHAT_ID)
run_master.bat                - Windows 실행 배치 파일
SQM_무중단_작업지시서.md      - 범용 작업 지시서
MASTER_FINAL_v868_통합완성본.md - v868 MASTER 문서

[설치 방법]
1. 이 패키지 전체를 SQM 프로젝트 루트에 복사
   예: F:\프로그램\Sqm 재고관리\Claude_SQM_v868\

2. 연결 테스트
   python scripts\test_telegram_connection.py

3. 실행
   run_master.bat 더블클릭
   -> 1번 선택 (Telegram Bridge)

[Telegram 명령어]
   y/n     - 예/아니오
   1/2/3   - 선택
   진행    - 계속 진행
   상태    - 현재 상태 조회
   재시작  - Claude 재시작
   중지    - 종료

[알림 시점]
   - 작업 시작 시
   - 5분마다 정기 보고
   - 2분 무응답 시 경고
   - Phase 완료 시
   - 오류 발생 시
   - 작업 완료 시
