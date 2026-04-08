# GPT_P2_BATCH_C_ALL_IN_ONE
작성일: 2026-04-07  
목적: Repository Pattern을 SQM 전체 DB 접근에 점진 도입하고, Batch C를 자동 실행 가능한 형태로 표준화한다.

---

## 0. 절대 규칙
- Batch C 동안 business rule 동시 변경 금지
- DB schema 전면 개편 금지
- 모든 DB 접근은 단계적으로 repository 경유로 치환
- 기존 운영 기능 삭제 금지
- commit/rollback 정책은 단일 기준으로 통일
- Batch C는 반드시 Pilot → 확장 순서로 진행

---

## 1. 단계 구성
- P2-C-01 : DB 접근 전수조사
- P2-C-02 : BaseRepository / DB helper 도입
- P2-C-03 : Inventory 조회 Pilot 전환
- P2-C-04 : Inbound repository 정식 전환
- P2-C-05 : Outbound repository 정식 전환
- P2-C-06 : commit/rollback/예외 정책 통일

---

## 2. 산출물
```text
repositories/base_repository.py
repositories/inventory_repository.py
repositories/inbound_repository.py
repositories/outbound_repository.py
scripts/verify_batch_c.py
tests/test_base_repository.py
tests/test_inventory_repository.py
docs/p2/maps/db_access_map.md
docs/p2/reports/batch_c_report.md
docs/p2/reports/db_repository_migration_checklist.md
run_batch_c.bat
```

---

## 3. 완료 기준
- [ ] BaseRepository 도입 완료
- [ ] Inventory repository pilot 완료
- [ ] Inbound repository 전환 완료
- [ ] Outbound repository 전환 완료
- [ ] commit/rollback 정책 통일 완료
- [ ] verify_batch_c.py PASS
- [ ] run_batch_c.bat PASS

---

## 4. Claude Code 실행 지시문
```text
Claude_SQM_v871 기준으로 P2 Batch C를 수행하라.
목표는 Repository Pattern을 프로젝트 DB 접근에 점진 도입하고, BaseRepository 기준으로 commit/rollback 정책을 통일하는 것이다.
다음 파일을 생성 또는 갱신하라:
- repositories/base_repository.py
- repositories/inventory_repository.py
- repositories/inbound_repository.py
- repositories/outbound_repository.py
- tests/test_base_repository.py
- tests/test_inventory_repository.py
- scripts/verify_batch_c.py
- docs/p2/maps/db_access_map.md
- docs/p2/reports/batch_c_report.md
- docs/p2/reports/db_repository_migration_checklist.md
- run_batch_c.bat

Pilot은 inventory read부터 시작하고, inbound/outbound 순으로 확장하라.
business rule 변경은 금지하고, DB 접근 경로만 정리하라.
각 단계 후 py_compile, pytest, verify_batch_c.py를 실행하고 결과를 보고서에 기록하라.
```
