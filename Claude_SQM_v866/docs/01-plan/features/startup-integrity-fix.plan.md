---
feature: startup-integrity-fix
version: 1.0
created: 2026-03-31
author: Claude
status: active
---

# Plan: 시작 시 정합성 경고 수정

## 1. 문제 정의

프로그램 시작 시 아래 3가지 경고/문제가 발생:

| # | 문제 | 심각도 | 유형 |
|---|------|--------|------|
| P1 | stock_movement 테이블 lot_no 중복 5건 (5~13행씩) | HIGH | DB 데이터 |
| P2 | 위치 미지정 톤백 880개 경고 | LOW | 운영 데이터 (코드 문제 아님) |
| P3 | "중복 감지 5건" 로그가 매 60초 반복 출력 | MEDIUM | 코드 버그 |

## 2. 영향 범위

- `engine_modules/validators.py` — 정합성 검사
- `gui_app_modular/utils/duplicate_guard.py` — 중복 스캔
- `gui_app_modular/main_app.py` — 중복 감지 타이머 루프
- DB: `stock_movement` 테이블

## 3. 해결 방안

### P1: stock_movement 중복 정리
- 원인: 입고 시 동일 lot_no로 여러 movement 레코드 INSERT (INBOUND 이벤트 중복)
- 해결: stock_movement는 이력 테이블이므로 lot_no 중복은 정상일 수 있음 → duplicate_guard의 _KEY_RULES에서 stock_movement 규칙 확인/조정

### P2: 위치 미지정 톤백 880개
- 운영 데이터 문제 — 톤백 탭에서 위치 업로드 엑셀로 매핑
- 코드 수정 불필요

### P3: 중복 감지 반복 로그 억제
- 현재: 동일 결과여도 `_set_status()` 매번 호출 → 매 60초 로그 출력
- 수정: signature 비교 후 동일하면 status bar만 유지, 로그 재출력 안 함

## 4. 작업 항목

- [ ] P1: stock_movement duplicate_guard 규칙 분석 및 조정
- [ ] P3: main_app.py 중복 감지 반복 로그 억제
- [ ] 검증: 프로그램 시작 시 불필요한 반복 로그 없는지 확인
