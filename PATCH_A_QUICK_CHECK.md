# PATCH_A_QUICK_CHECK.md
작성일: 2026-04-07
인코딩: UTF-8

## 목적
Patch A를 깊게 검토하지 않고, 사무실 도착 후 10~20분 내 빠르게 확인하여
Patch B 시작 가능 여부를 판정한다.

## 체크 단계

### A-01 파일 확인
- [ ] inbound_parser.py 존재
- [ ] inbound_validator.py 존재
- [ ] inbound_repository.py 존재
- [ ] inbound_service.py 존재

### A-02 연결 여부 확인
- [ ] onestop_inbound 또는 대응 흐름에서 service/parser/repository 호출 흔적 확인
- [ ] direct SQL 감소 여부 확인

### A-03 실행 확인
- [ ] 프로그램 실행
- [ ] 입고 업로드/등록 1회 실행
- [ ] 에러 여부 확인

### A-04 결과 확인
- [ ] DB 저장 정상
- [ ] 기존 기대 결과와 크게 다르지 않음

## 판정
- 위 4개 중 핵심 3개 이상 OK → Patch A 통과, Patch B 진행
- 실행/저장 불가 → Patch A 최소 보완 후 재확인

## 핵심 원칙
Patch A는 지금 시점에 “완벽 검토”가 아니라 “빠른 통과 게이트”다.
