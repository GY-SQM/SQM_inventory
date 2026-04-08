# GPT P2 Batch C Execution Package

작성일: 2026-04-07  
목적: SQM 프로젝트의 Batch C(Repository Pattern 도입)를 바로 실행할 수 있도록 문서, 코드 스켈레톤, 테스트, 검증 스크립트, 배치 실행 파일을 한 번에 제공

## 포함 파일
- GPT_P2_BATCH_C_ALL_IN_ONE.md
- run_batch_c.bat
- scripts/verify_batch_c.py
- repositories/base_repository.py
- repositories/inventory_repository.py
- repositories/inbound_repository.py
- repositories/outbound_repository.py
- tests/test_base_repository.py
- tests/test_inventory_repository.py

## 권장 사용 순서
1. 프로젝트 루트에 각 파일을 대응 위치로 복사
2. `run_batch_c.bat` 실행
3. FAIL 발생 시 `GPT_P2_BATCH_C_ALL_IN_ONE.md` 기준으로 수정
4. PASS 후 `docs/p2/reports/batch_c_report.md` 작성

## 핵심 원칙
- business rule 변경 금지
- DB 접근만 repository 경유로 통일
- commit / rollback 정책 통일
