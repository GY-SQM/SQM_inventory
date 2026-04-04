# GPT_ClaudeCode_P0-2_실행프롬프트.md
생성일: 2026-04-04 15:33 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
참조 문서:  
- `MASTER_FINAL_v867_통합완성본.md`
- `GPT_SQM_P0-2_LOT상세모달_초상세_작업지시서.md`
- `GPT_SQM_P0-2_LOT상세모달_테스트체크리스트.md`
- `GPT_SQM_P0-1_완료보고서.md`

---

## [질문]
계속 진행해서 **Claude Code용 P0-2 실행 프롬프트**를 작성해 달라는 요청

## [질문의도]
Claude Code가 바로 실행할 수 있도록  
P0-2 단계인 **LOT 상세 모달 구현 작업**을
실행 지시문 형태로 정리한다.

이번 문서의 목적은 아래와 같다.

```text
1. Claude Code가 P0-2 목표를 정확히 이해하게 한다
2. 실제 수정 파일과 구현 순서를 고정한다
3. 테스트 게이트를 포함해 단계별로 멈추지 않고 진행하게 한다
4. mock 수준이 아니라 실제 read 동작이 되도록 강제한다
```

---

# [응답]

# 1. Claude Code 실행 프롬프트

아래 내용을 Claude Code에 그대로 투입한다.

---

## SYSTEM / MASTER EXECUTION PROMPT

현재 작업 기준 원본은 `Claude_SQM_v867` 이다.  
기존 가정 구조만 믿고 진행하지 말고 반드시 실제 v867 코드 구조를 먼저 조사한 뒤 수정하라.

이번 작업은 **P0-2: LOT 상세 모달 구현 단계**다.  
목표는 React에서 **LOT 클릭 → 상세 조회 → 모달 표시** 흐름을 실제로 완성하는 것이다.

### 절대 목표
다음 4가지를 반드시 만족해야 한다.

```text
1. React 화면에서 LOT 클릭 시 LOT 상세 모달이 열린다
2. 모달은 실제 조회 API 또는 동등 조회 경로와 연결된다
3. 기본정보 / 톤백 목록 / 이력 / 배정 상태 4개 섹션이 표시된다
4. loading / empty / error / 재조회 흐름이 처리된다
```

### 절대 금지
다음은 금지한다.

```text
- mock 데이터만으로 완료 처리 금지
- placeholder만 띄우고 완료 처리 금지
- API 연결 없이 하드코딩으로 완료 처리 금지
- 기존 engine/query 경로 조사 없이 임의 API 새로 만들기 금지
- 테스트 실패 상태에서 다음 단계로 넘어가기 금지
```

### 구현 원칙
- 기존 조회 API가 있으면 최대한 재사용하라
- 필요 시 응답 normalize adapter를 프론트에 두어도 된다
- 가능하면 `InventoryPage`를 첫 진입점으로 사용하라
- `AllocationPage`, `TonbagPage`는 보조 연결 대상으로 보라
- 전역 상태 과도 사용 금지, 페이지 상태 + 모달 props 패턴 우선
- 기존 프로젝트 스타일과 구조를 유지하라

---

# 2. 실제 조사 대상

먼저 아래 파일/경로를 조사하라.

```text
web/src/App.jsx
web/src/pages/InventoryPage.jsx
web/src/pages/AllocationPage.jsx
web/src/pages/TonbagPage.jsx
web/src/components/modals/LotDetailModal.jsx
web/src/api/
react_api/routes/
react_api/main.py
engine_modules/inventory_modular/query_mixin.py
gui_app_modular/dialogs/ 내 LOT 상세 관련 파일
```

조사 후 아래를 확정하라.

- LOT 클릭이 가장 자연스러운 진입 페이지
- 기존 LOT 상세 조회 API 경로
- 응답 데이터 shape
- Tkinter LOT 상세에 들어가야 할 최소 표시 항목

---

# 3. 수정 대상 파일

이번 단계의 직접 수정 대상은 아래를 기준으로 한다.

```text
web/src/App.jsx
web/src/pages/InventoryPage.jsx
web/src/pages/AllocationPage.jsx            (가능하면)
web/src/pages/TonbagPage.jsx                (선택)
web/src/components/modals/LotDetailModal.jsx
web/src/api/actionApi.js 또는 기존 조회 API 래퍼
react_api/routes/inventory.py 또는 동등 조회 route 파일
react_api/services/engine_adapter.py        (필요 시 조회 wrapper 보조)
```

신규 파일 추가가 필요하면 최소 범위로 진행하라.

---

# 4. 구현 순서

아래 순서를 반드시 지켜라.

## Step 1. Recon
- 현재 LOT 상세 조회 경로를 찾는다
- 현재 React 페이지에서 LOT 클릭 가능 지점을 찾는다
- 현재 API 응답 샘플 구조를 파악한다
- Tkinter LOT 상세 항목과 비교해 필수 항목 목록을 작성한다

## Step 2. API 래퍼 정리
- `getLotDetail(lotNo)` 함수를 만든다
- 기존 API 호출 패턴과 동일한 스타일을 따른다
- 필요 시 `normalizeLotDetailResponse(raw)`를 만든다
- lotNo 유효성 검사를 추가한다

## Step 3. `LotDetailModal.jsx` 실제 구현
다음 섹션을 모두 구현한다.

### A. 기본정보
- LOT 번호
- 품목명/제품명
- BL/SAP/식별값
- 총 수량 또는 총 톤백 수
- 상태 요약
- 샘플 정보(가능하면)

### B. 톤백 목록
- tonbag_no
- 상태
- 중량/수량
- 위치
- 샘플 여부(있으면)

### C. 이력
- 입고
- 배정
- 피킹
- 출고
- 취소/반품/기타 이력(있으면)

### D. 배정 상태
- allocation 존재 여부
- reserved 요약
- picked 요약
- outbound 요약
- 관련 reference/sales order (가능한 범위)

## Step 4. 페이지 연결
- 최소한 `InventoryPage`에서 LOT 클릭 시 모달 열리게 만든다
- 가능하면 `AllocationPage`도 같은 모달 재사용으로 연결한다
- `TonbagPage`는 시간이 허용되면 보조 연결한다

## Step 5. 예외/상태 처리
다음을 반드시 처리하라.

- loading
- lotNo 없음
- 404
- 500
- 빈 tonbag 목록
- 빈 history
- 빈 allocation_status
- LOT 전환 재조회

## Step 6. 안정화
- 빠른 연속 클릭에서 데이터 꼬임이 없는지 점검
- 이전 요청이 늦게 와도 최신 LOT 기준으로 표시되게 한다
- 닫았다가 다시 열어도 정상 동작하게 한다

---

# 5. 권장 상태 구조

권장 구조는 아래와 같다.

## 페이지 상태
```text
selectedLotNo
isLotModalOpen
```

## 모달 props
```text
open
onClose
lotNo
initialData(optional)
```

## 모달 내부 상태
```text
loading
error
lotDetail
activeTab(optional)
```

이 구조를 우선 사용하되, 실제 프로젝트 구조에 맞게 최소 수정으로 적용하라.

---

# 6. 백엔드 보강 기준

기존 `/lot/{lot_no}` 또는 동등 API가 아래를 충분히 주면 재사용한다.

```json
{
  "success": true,
  "message": "OK",
  "data": {
    "basic_info": {},
    "tonbags": [],
    "history": [],
    "allocation_status": {}
  }
}
```

응답이 이 구조가 아니어도 프론트 normalize로 처리 가능하면 백엔드 변경 최소화.

백엔드 보강이 필요한 경우는 아래뿐이다.

- history 정보가 전혀 없음
- allocation_status가 전혀 없음
- tonbag 필드명이 너무 불규칙해 프론트 처리 비용이 과도함
- LOT 식별 기준이 불안정함

---

# 7. 테스트 게이트

각 단계는 아래 순서를 반드시 따른다.

```text
Pre-Test → 구현 → Post-Test → 실패 시 수정 → Re-Test → 통과 → 다음 단계
```

## Pre-Test
- LOT 조회 API 단독 호출 확인
- 정상 LOT 샘플 확보
- 없는 LOT 샘플 확보
- 프론트 빌드/import 오류 없음 확인

## Post-Test
다음을 모두 확인하라.

- LOT 클릭 → 모달 오픈
- API 호출 발생
- loading 표시
- 기본정보 표시
- 톤백 목록 표시
- 이력 표시
- 배정 상태 표시
- 닫기 동작
- 다른 LOT 전환 시 재조회
- 없는 LOT 처리
- API 오류 처리

## 비교 테스트
반드시 Tkinter LOT 상세와 비교하라.

아래 항목은 React에도 반드시 있어야 한다.

- LOT 번호
- 제품명/품목명
- 톤백 목록
- 상태 요약
- 이력
- 배정 상태

표시 방식이 다른 것은 허용하되, 핵심 축 누락은 허용하지 않는다.

---

# 8. 완료 기준

다음 조건이 모두 만족되면 이번 단계를 완료로 본다.

```text
1. React에서 LOT 상세 모달이 실제 동작한다
2. 조회 API와 실제 연결된다
3. 기본정보 / 톤백 / 이력 / 배정 상태가 보인다
4. loading / empty / error / 재조회가 된다
5. Tkinter 대비 본질적 누락이 없다
```

다음 중 하나라도 해당하면 완료로 인정하지 않는다.

```text
- mock 데이터만 보인다
- API 연결이 간헐적으로 실패한다
- lotNo 전환 시 데이터가 꼬인다
- 핵심 축(톤백/이력/배정상태) 중 하나가 통째로 없다
- 모달이 열려도 실사용이 불가능하다
```

---

# 9. 출력 형식

작업 종료 후 아래 형식으로 결과를 정리하라.

## 1) 수정 파일 목록
- 실제 수정한 파일 경로
- 신규 생성 파일 경로
- 변경 이유 1줄 요약

## 2) 구현 요약
- LOT 진입점
- API 경로
- 응답 normalize 여부
- 표시 섹션 구현 여부

## 3) 테스트 결과
- PASS/FAIL 목록
- 실패 후 수정한 내용
- Tkinter 비교 결과

## 4) 남은 이슈
- P0에서 허용 가능한 보류 항목
- P1로 넘길 항목

---

# 10. 최종 실행 선언

이번 작업은 **P0-2 LOT 상세 모달 실제 구현**이다.  
질문 없이, 중단 없이, 테스트 게이트를 통과하며 진행하라.

필요한 경우에만 최소 범위로 백엔드를 보강하되,
가능한 한 기존 조회 구조와 기존 engine/query 로직을 재사용하라.

작업 완료 후에는 반드시
- 수정 파일 목록
- 테스트 결과
- Tkinter 비교 결과
를 남겨라.

---

# 3. 루비 최종 권장안

이번 프롬프트의 핵심은 아래 한 줄이다.

```text
P0-2는 "모달을 보이게 하는 작업"이 아니라,
React에서 첫 번째 실사용 가능한 read 동작을 완성하는 작업이다.
```

---

# 4. 다음 단계 권장

이 문서 다음으로 가장 자연스러운 작업은 아래다.

1. **P0-3 입고/출고 write loop 초상세 작업지시서**
2. **Claude Code용 P0-3 실행 프롬프트**

루비 권장 순서는 아래다.

```text
1) P0-3 초상세 작업지시서
2) P0-3 실행 프롬프트
```
