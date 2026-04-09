# GPT_P2_BATCH_A_FULL_WORKFLOW.md
작성일: 2026-04-07

====================================================
[1] STEP 1 - Batch A 결과 점검
====================================================

## 목적
Batch A 수행 결과가 기존 시스템과 동일한지 검증

## 점검 항목

| 항목 | 내용 | 결과 |
|---|---|---|
| 파싱 | BL / PL / FA / DO 동일성 | ☐ |
| DB 저장 | inventory_detail 동일 | ☐ |
| UI 동작 | 입고 버튼 정상 | ☐ |
| 예외 처리 | 오류 동일 처리 | ☐ |

## 실행 명령

python run.py
pytest

====================================================
[2] STEP 2 - Batch A 검증표
====================================================

## 검증 체크리스트

- [ ] Parser 결과 동일
- [ ] Validator 오류 동일
- [ ] Repository insert 동일
- [ ] Service 흐름 동일
- [ ] 속도 저하 없음

## 결과 기록

PASS / FAIL:

문제 발생 위치:
- Parser / Validator / Repository / Service

====================================================
[3] STEP 3 - Batch A 보완 수정
====================================================

## 수정 대상

- import 정리
- 중복 코드 제거
- dead code 제거
- 로그 추가

## 코드 예시

```python
import logging
logger = logging.getLogger("inbound")

logger.info("Inbound started")
```

## 테스트 보강

```python
def test_inbound_service():
    assert True
```

====================================================
[4] STEP 4 - Batch B 착수
====================================================

## 목표
outbound_mixin 구조 분해

## 작업 단계

P2-B-01 흐름 맵 작성
P2-B-02 Query 분리
P2-B-03 상태전이 정의
P2-B-04 Repository 분리
P2-B-05 Service 도입
P2-B-06 Transaction 정리
P2-B-07 Scan 테스트
P2-B-08 전체 검증

## 핵심 코드

```python
class OutboundService:
    def scan(self, tonbag_no):
        data = self.repo.get(tonbag_no)
        if data["status"] != "PICKED":
            raise Exception("Invalid state")
        self.repo.mark_sold(tonbag_no)
```

====================================================
[5] 최종 실행 순서
====================================================

1. Batch A 검증
2. Batch A 수정
3. 테스트 PASS 확인
4. Batch B 진행

====================================================
[결론]
====================================================

Batch A → 안정화 → Batch B 진입이 가장 안전한 구조
