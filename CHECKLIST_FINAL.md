# SQM Final Execution Checklist
작성일: 2026-04-07
인코딩: UTF-8

## 1. 사무실 도착 후 즉시 체크
- [ ] 프로젝트 루트 확인
- [ ] Python 실행 확인
- [ ] Node 실행 확인
- [ ] Claude Code 실행 확인
- [ ] Git 상태 확인
- [ ] 백업 또는 브랜치 생성
- [ ] `.env` 존재 확인
- [ ] logs 폴더 준비
- [ ] Telegram 토큰 / Chat ID 준비

## 2. Patch A Quick Check
- [ ] inbound 관련 파일 존재 확인
- [ ] 프로그램 실행 확인
- [ ] 입고 1회 테스트
- [ ] 결과/DB 저장 확인
- [ ] 이상 없으면 Patch B로 이동

## 3. Patch B 실행 전
- [ ] outbound_mixin 백업
- [ ] B01~B08 TASK 파일 준비
- [ ] verify script 위치 확인
- [ ] pytest 환경 확인

## 4. Patch B 실행 중
- [ ] Step별로 하나씩만 수행
- [ ] py_compile PASS
- [ ] pytest PASS
- [ ] verify PASS
- [ ] 결과 md 기록
- [ ] FAIL 시 debug 문서 작성

## 5. Patch C 실행 전
- [ ] Patch B 최종 PASS
- [ ] outbound 정책 유지 확인
- [ ] direct SQL 잔존 여부 재확인

## 6. Patch C 실행 중
- [ ] BaseRepository 도입
- [ ] Inventory → Inbound → Outbound 순 적용
- [ ] commit/rollback 정책 통일
- [ ] verify_batch_c.py PASS

## 7. 종료 전
- [ ] 결과 보고서 저장
- [ ] logs 저장
- [ ] Git diff 확인
- [ ] Telegram 완료 알림
