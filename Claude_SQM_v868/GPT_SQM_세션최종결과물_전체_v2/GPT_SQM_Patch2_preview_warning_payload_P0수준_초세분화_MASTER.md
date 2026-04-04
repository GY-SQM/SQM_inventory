# GPT_SQM_Patch2_preview_warning_payload_P0수준_초세분화_MASTER.md
생성일: 2026-04-04 17:45 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
연결 문서:
- `GPT_SQM_P2_Patch2_통합MASTER.md`
- `GPT_SQM_Patch2_초상세_작업지시서.md`
- `GPT_SQM_Patch2_테스트체크리스트.md`

---

## [질문]
외부에 있는 동안 Q2도 진행해서,  
**Patch 2의 preview / warning / create_payload 흐름을 P0 수준으로 초세분화한 MASTER**를 작성해 달라는 요청

## [질문의도]
Patch 2 전체를 개요 수준으로 두지 말고,  
실제 사용자가 가장 많이 보게 되는 preview / warning / create_payload 구조를  
**parser 출력 / API 응답 / UI 표시 / create 입력 기준**까지 초세분화해서  
다음 실행 세션에서 바로 기준 문서로 쓸 수 있게 만든다.

---

# [응답]

# 1. 이 문서의 역할

이 문서는 Patch 2의 핵심 축 3개를 P0 수준으로 확대한 세부 MASTER다.

```text
1. preview 구조를 세분화
2. warning 구조를 세분화
3. create_payload 구조를 세분화
4. parser → API → UI → create 흐름의 일관성 기준을 고정
```

---

# 2. 공통 원칙

## 2-1. 절대 원칙
- parser 원본 로직을 불필요하게 크게 바꾸지 않는다
- preview는 UI 표시용 구조이면서 create 검토용 구조여야 한다
- warning은 error와 반드시 구분한다
- create_payload는 실제 create 요청에 바로 사용할 수 있어야 한다
- preview와 create_payload가 서로 다른 의미를 가지면 안 된다
- 필드명이 다르면 normalize layer에서 흡수한다

## 2-2. 공통 대상 파일
```text
parsers/*
react_api/services/action_service.py
react_api/schemas/actions.py
web/src/components/modals/InboundParseModal.jsx
web/src/api/actionApi.js
```

---

# 3. preview 초세분화

# 3-1. preview의 목적

preview는 단순 미리보기가 아니라,
**사용자가 create 전에 판단할 수 있게 해 주는 검토 화면 데이터**다.

즉 preview는 아래 3가지를 동시에 만족해야 한다.

```text
1. 사람이 읽기 쉬워야 한다
2. parser가 무엇을 추론했는지 보여줘야 한다
3. create_payload와 연결되어 있어야 한다
```

---

# 3-2. preview 권장 상위 구조

```json
{
  "success": true,
  "message": "Preview generated",
  "data": {
    "file_type": "pdf",
    "parser_type": "inbound",
    "preview": {
      "document_info": {},
      "items": [],
      "lot_candidates": [],
      "summary_cards": {}
    },
    "summary": {},
    "warnings": [],
    "create_payload": {}
  }
}
```

---

# 3-3. preview 세부 블록 정의

## A. document_info
문서 전체에서 추출한 핵심 식별값

권장 필드 예시:
```json
{
  "source_filename": "sample.pdf",
  "document_no": "ABC123",
  "bl_no": "MEDU1234567",
  "sap_no": "SAP001",
  "inbound_date": "2026-04-04",
  "parser_confidence": "medium"
}
```

## B. items
실제 입고 대상 후보 목록

권장 필드 예시:
```json
[
  {
    "product_name": "Sample Product",
    "lot_no": "LOT001",
    "quantity": 10,
    "unit": "BAG",
    "weight_mt": 10.0,
    "sample_exists": true
  }
]
```

## C. lot_candidates
LOT 수준 요약

권장 필드 예시:
```json
[
  {
    "lot_no": "LOT001",
    "expected_bag_count": 10,
    "sample_count": 1,
    "source_line_refs": [12, 13]
  }
]
```

## D. summary_cards
UI 상단 요약 카드용

권장 필드 예시:
```json
{
  "item_count": 1,
  "lot_count": 1,
  "total_weight_mt": 10.0,
  "warning_count": 2
}
```

---

# 4. warning 초세분화

# 4-1. warning의 목적

warning은 "실패"가 아니라,
**사용자가 주의해서 봐야 하는 추정/모호성/누락 후보**를 표시하는 구조다.

즉 warning은 아래 목적을 가진다.

```text
1. parser 추정 결과를 숨기지 않는다
2. create 전에 사용자가 확인할 포인트를 보여준다
3. 시스템 오류(error)와 구분한다
```

---

# 4-2. warning 권장 구조

```json
[
  {
    "level": "warning",
    "code": "LOT_INFERRED",
    "field": "lot_no",
    "message": "LOT number inferred from nearby text",
    "source_ref": "page 1 line 32",
    "blocking": false
  }
]
```

---

# 4-3. warning 필드 설명

| 필드 | 의미 |
|---|---|
| `level` | warning / info / caution |
| `code` | 기계 판독용 코드 |
| `field` | 어떤 필드 문제인지 |
| `message` | 사용자용 설명 |
| `source_ref` | 어디서 추론했는지 |
| `blocking` | create 차단 필요 여부 |

---

# 4-4. warning 분류 기준

## A. info
- 가벼운 참고
- create 막지 않음

## B. warning
- 사용자가 보고 판단해야 함
- create 막지 않음

## C. caution
- 거의 차단 수준
- 정책에 따라 create 전 확인 필요

## D. error
- preview 생성은 실패 또는 create 차단
- warning과 분리

---

# 5. create_payload 초세분화

# 5-1. create_payload의 목적

create_payload는 preview 화면에서 확인한 내용을
**실제 `/inbound/create`에 그대로 전달할 수 있는 구조**여야 한다.

즉 create_payload는 아래를 만족해야 한다.

```text
1. 사람이 확인한 내용과 의미가 같아야 한다
2. 실제 create에 바로 쓸 수 있어야 한다
3. parser 내부 구조를 노출하지 말고 API 입력 구조에 맞아야 한다
```

---

# 5-2. create_payload 권장 구조

```json
{
  "source_type": "pdf",
  "document_info": {
    "bl_no": "MEDU1234567",
    "sap_no": "SAP001"
  },
  "items": [
    {
      "product_name": "Sample Product",
      "lot_no": "LOT001",
      "quantity": 10,
      "unit": "BAG",
      "weight_mt": 10.0,
      "sample_exists": true
    }
  ],
  "confirmed": false
}
```

---

# 5-3. create_payload 필수 기준

- LOT 번호가 실제 create 기준과 일치
- quantity / weight 의미가 실제 create 기준과 일치
- sample 정보가 있으면 create와 일관
- 문서 식별값이 create 후 추적 가능
- preview에서 보인 item 순서/내용과 크게 다르지 않음

---

# 6. parser → API → UI → create 연결 규칙

## 6-1. parser 출력
- parser 원본 출력은 자유
- 하지만 service에서 normalize 가능

## 6-2. API 응답
- API는 preview / warnings / create_payload를 표준 구조로 보낸다

## 6-3. UI 표시
- UI는 `summary_cards`, `items`, `warnings`, `create_payload 핵심값`을 표시한다

## 6-4. create 요청
- UI는 `create_payload`를 그대로 또는 최소 보정 후 `/inbound/create`에 전달한다

---

# 7. 세부 테스트 기준

# 7-1. preview 테스트
- [ ] document_info 표시
- [ ] items 표시
- [ ] lot_candidates 표시
- [ ] summary_cards 표시
- [ ] 빈 블록 처리

# 7-2. warning 테스트
- [ ] level 표시
- [ ] message 표시
- [ ] field 표시
- [ ] blocking 분기 가능
- [ ] error와 구분

# 7-3. create_payload 테스트
- [ ] create 전에 핵심 값 확인 가능
- [ ] 실제 create payload로 사용 가능
- [ ] preview와 내용 일관
- [ ] 필드 누락 시 warning 또는 error 처리

---

# 8. 실패 시 조치

## 유형 A. preview는 예쁘지만 create_payload와 다름
- create_payload 기준을 먼저 고정
- preview는 create 기준에 맞춰 재구성

## 유형 B. warning이 너무 추상적
- code / field / source_ref 추가
- 사용자 메시지 구체화

## 유형 C. PDF/Excel 구조가 너무 다름
- parser 원본은 달라도 normalize 결과는 최대한 통일

## 유형 D. UI에서 무엇을 확인해야 할지 모름
- summary_cards와 warning_count를 상단에 노출
- create 직전 핵심 payload 블록 노출

---

# 9. 완료 기준

- [ ] preview 구조 표준 확정
- [ ] warning 구조 표준 확정
- [ ] create_payload 구조 표준 확정
- [ ] parser → API → UI → create 흐름 일관성 확보
- [ ] InboundParseModal이 실제 판단 도구 역할 수행

---

# 10. 루비 최종 판단

```text
Patch 2의 진짜 핵심은 parser 정확도만이 아니다.
사용자가 preview를 보고 "이제 create 해도 된다"라고 판단할 수 있게 만드는
표현 구조와 입력 구조의 일관성이 핵심이다.
```

---

# 11. 다음 단계 권장

```text
1. P4 + Patch 4 통합 세트 생성
2. 또는 실제 실행 후 막히는 필드만 추가 세분화
```
