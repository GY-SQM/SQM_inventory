SQM v6.3.5 — WinError 32 완전 수정 통합 패치
==============================================
작성: Ruby  /  날짜: 2026-03-06

## 수정 파일 5개

1. engine_modules/database.py
   - close_all(): 모든 스레드 연결 + WAL checkpoint(TRUNCATE)
   - _all_connections 추적 리스트 추가

2. gui_app_modular/mixins/keybindings_mixin.py
   - _reset_test_db(): close() → close_all() 변경
   - os.remove 실패 시 0.5초 대기 후 1회 재시도

3. gui_app_modular/mixins/window_mixin.py   ← NEW
   - _on_closing(): 앱 종료 시 close_all() 호출
   - 자동 백업 스케줄러 먼저 stop() 후 close_all()

4. engine_modules/inventory_modular/engine.py   ← NEW
   - SqmEngine.close(): close_all() 우선 호출 (fallback: close())

5. gui_app_modular/dialogs/auto_backup.py   ← NEW
   - _execute_backup(): 백업 직후 WAL checkpoint(PASSIVE) 추가
   - PASSIVE: 진행 중 트랜잭션 차단 없음 → 성능 영향 없음
   - 효과: WAL 파일 무한 증가 방지, 백업 파일 크기 안정화

## 적용 방법 (5개 파일 덮어쓰기)
  engine_modules/database.py
  engine_modules/inventory_modular/engine.py
  gui_app_modular/mixins/keybindings_mixin.py
  gui_app_modular/mixins/window_mixin.py
  gui_app_modular/dialogs/auto_backup.py

## WinError 32 완전 해결 흐름 (수정 후)
  [테스트 DB 초기화 버튼 클릭]
  → _reset_test_db()
  → engine.db.close_all()
      ① WAL checkpoint(TRUNCATE): WAL 내용 main DB 병합, WAL 파일 잠금 해제
      ② _all_connections 전체 종료: 모든 스레드 SQLite 연결 닫힘
      ③ gc.collect(): Python 순환참조 정리
  → os.remove(path)  ← 이제 파일이 완전히 열려있지 않아 삭제 성공 ✅
  → (실패 시) 0.5초 대기 후 1회 재시도

## 앱 종료 흐름 (수정 후)
  [X 버튼 클릭]
  → _on_closing()
  → auto_backup_scheduler.stop()  ← 백업 타이머 정리
  → engine.db.close_all()         ← 전체 스레드 + WAL
  → root.destroy()
  → WAL 찌꺼기 파일 없이 깔끔한 종료 ✅
