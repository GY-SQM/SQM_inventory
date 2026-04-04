# GPT_SQM_P0-2_LOT상세모달_초상세_작업지시서.md
생성일: 2026-04-04 15:24 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
참조 문서:  
- `MASTER_FINAL_v867_통합완성본.md`
- `GPT_SQM_P0_통합체크리스트_v2.md`
- `GPT_SQM_P0-1_완료보고서.md`

---

## [질문]
다음 단계로 **P0-2 LOT 상세 모달 초상세 작업지시서**를 작성해 달라는 요청

## [질문의도]
P0-1에서 고정한 구조를 바탕으로,
이제 React에서 **첫 번째 실제 업무 동작**인 LOT 상세 조회 모달을 구현할 수 있도록
작업 순서, 파일, API 연결, 상태 관리, 테스트 기준을 초상세 수준으로 정리한다.

---

# [응답]

# 1. P0-2의 목표

P0-2의 목표는 단순히 “모달 창 하나 띄우기”가 아니다.  
이번 단계의 본질은 아래와 같다.

```text
1. React에서 LOT 클릭 → 상세 조회 → 모달 표시 흐름을 완성한다
2. 기존 조회 API 또는 동등 조회 경로와 실제 연결한다
3. Tkinter LOT 상세의 핵심 정보 구조를 React에서 복구한다
4. 이후 P0-3 입고/출고 write loop 전에 첫 실동작 경로를 안정화한다
```

---

# 2. P0-2 완료 정의

아래 조건이 모두 만족되면 P0-2 완료로 본다.

- [ ] React 화면에서 LOT를 클릭할 수 있다
- [ ] 클릭 시 `LotDetailModal`이 열린다
- [ ] LOT 번호를 기준으로 상세 조회 API가 호출된다
- [ ] 기본정보 / 톤백목록 / 이력 / 배정상태가 표시된다
- [ ] 로딩 / 빈 데이터 / 오류 상태가 모두 처리된다
- [ ] 모달 닫기 / 재열기 / 다른 LOT 전환이 안정적으로 동작한다
- [ ] Tkinter LOT 상세 핵심 항목과 비교 시 본질적 누락이 없다

---

# 3. 이번 단계의 직접 근거

마스터 문서는 LOT 클릭 시 팝업 형태의 **LOT 상세 모달**을 명시하고,
포함 항목으로 아래를 요구한다.

- 기본정보
- 톤백 목록
- 이력
- 배정 상태  
fileciteturn10file0

또한 React 전환 목표로
- tkinter 메뉴/모달 구조 정렬
- 메뉴/모달/API 실제 연결
- 기존 `engine_modules` 재사용  
을 요구하고 있다. fileciteturn10file1

따라서 P0-2는 **React에서 첫 번째 업무 모달 복구 단계**로 보는 것이 맞다.

---

# 4. 수정 대상 파일

## 4-1. 직접 수정 파일
| 파일 | 역할 | P0-2 작업 |
|---|---|---|
| `web/src/App.jsx` | 모달 mount 지점 / 상태 전파 | 모달 상태 연결 |
| `web/src/pages/InventoryPage.jsx` | LOT 클릭 진입점 후보 | LOT 클릭 이벤트 연결 |
| `web/src/pages/AllocationPage.jsx` | LOT 클릭 진입점 후보 | LOT 클릭 이벤트 연결 |
| `web/src/pages/TonbagPage.jsx` | 관련 LOT 진입점 후보 | LOT 연결 보조 |
| `web/src/api/actionApi.js` 또는 기존 API 래퍼 | LOT 상세 조회 helper 추가/정리 | fetch 함수 추가 |
| `react_api/routes/inventory.py` 또는 동등 파일 | 기존 LOT 조회 경로 점검 | 필요 시 응답 shape 보강 |
| `react_api/services/engine_adapter.py` | 조회 래퍼 보조 | 필요 시 LOT 상세 wrapper |

## 4-2. 신규/중심 파일
| 파일 | 역할 |
|---|---|
| `web/src/components/modals/LotDetailModal.jsx` | 이번 단계 핵심 구현 파일 |

## 4-3. 참조 전용 파일
| 파일 | 목적 |
|---|---|
| `engine_modules/inventory_modular/query_mixin.py` | LOT 상세 조회 함수 확인 |
| 기존 Tkinter LOT 상세 관련 dialog 파일 | 표시 항목 참조 |
| `web/src/components/DataTable.jsx` | 테이블 표시 스타일 참고 |

---

# 5. 표시 항목 설계

## 5-1. 최소 표시 구조

### A. 기본정보
- [ ] LOT 번호
- [ ] 제품명 / 품목명
- [ ] BL 또는 SAP 관련 식별값
- [ ] 총 수량 / 총 톤백 수
- [ ] 샘플 존재 여부(가능하면)
- [ ] 현재 상태 요약

### B. 톤백 목록
- [ ] tonbag_no
- [ ] 상태
- [ ] 중량/수량
- [ ] 위치
- [ ] 샘플 여부(있으면)
- [ ] 선택적 추가 컬럼: inbound_date, warehouse

### C. 이력
- [ ] 입고
- [ ] 배정
- [ ] 피킹
- [ ] 출고
- [ ] 취소/반품(있으면)

### D. 배정 상태
- [ ] allocation 존재 여부
- [ ] reserved/picked/outbound 요약
- [ ] 관련 sales order / reference (가능한 범위)

---

# 6. UI 설계 기준

## 6-1. 컴포넌트 props
`LotDetailModal.jsx`는 최소 아래 props를 받는 구조로 설계한다.

```text
open
onClose
lotNo
initialData(optional)
```

## 6-2. 내부 상태
- [ ] `loading`
- [ ] `error`
- [ ] `lotDetail`
- [ ] `activeTab` 또는 section state (선택)
- [ ] `refreshKey` 또는 재조회 트리거 (선택)

## 6-3. 렌더링 상태
- [ ] 닫힘 상태면 렌더 최소화
- [ ] 열림 + lotNo 없음 → 경고/빈 상태
- [ ] 열림 + 조회 중 → loading
- [ ] 열림 + 오류 → error panel
- [ ] 열림 + 성공 → 상세 내용 표시

## 6-4. UX 기준
- [ ] 닫기 버튼 명확
- [ ] Esc 또는 backdrop 닫기 정책 명시
- [ ] 큰 테이블은 스크롤 가능
- [ ] 모바일 완전 대응은 P0 범위 밖이나 레이아웃 붕괴는 피함

---

# 7. 데이터 흐름 설계

## 7-1. 권장 흐름
```text
사용자 LOT 클릭
→ selectedLotNo state 설정
→ LotDetailModal open=true
→ useEffect로 lotNo 감지
→ API 호출
→ 응답 normalize
→ 섹션별 표시
```

## 7-2. 권장 상태 위치
### 권장안
- 페이지(`InventoryPage.jsx`, `AllocationPage.jsx`)에서
  - `selectedLotNo`
  - `isLotModalOpen`
  를 가진다.
- `LotDetailModal`은 표시/조회 책임만 가진다.

### 이유
- 모달 재사용이 쉬움
- 여러 페이지에서 같은 모달 재사용 가능
- App 전역 상태로 올리지 않아도 됨

---

# 8. API 연결 설계

## 8-1. 우선 전략
기존 조회 API를 최대한 재사용한다.  
필요 시 `actionApi.js`가 아니라 기존 조회용 API 래퍼에 추가해도 된다.

## 8-2. 권장 함수
```text
getLotDetail(lotNo)
```

## 8-3. 응답 요구 shape(권장)
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

## 8-4. 허용 전략
실제 API 응답이 위 구조와 다르면,
프론트에서 normalize adapter를 둔다.

예:
```text
normalizeLotDetailResponse(raw)
```

## 8-5. 백엔드 보강 기준
아래 중 하나면 백엔드 보강 검토:
- [ ] 현재 `/lot/{lot_no}` 응답이 섹션 구분 없이 너무 납작함
- [ ] history/allocation 정보가 빠짐
- [ ] tonbag 목록 필드명이 프론트 사용에 너무 불규칙함

---

# 9. 구현 단계 체크리스트

# 9-A. 사전 조사
- [ ] 현재 React 페이지 중 LOT 클릭이 가장 자연스러운 화면 선정
- [ ] 현재 LOT 조회 API 경로 확인
- [ ] 기존 응답 샘플 확보
- [ ] Tkinter LOT 상세 화면 필수 항목 목록 추출

# 9-B. API 래퍼 구현
- [ ] `getLotDetail(lotNo)` 함수 추가
- [ ] 에러 throw 규칙 통일
- [ ] 응답 normalize 함수 필요 여부 판단
- [ ] lotNo 유효성 사전 검사

# 9-C. 모달 본체 구현
- [ ] `LotDetailModal.jsx` 레이아웃 구현
- [ ] header 구현
- [ ] 기본정보 카드 구현
- [ ] 톤백 목록 테이블 구현
- [ ] 이력 섹션 구현
- [ ] 배정 상태 섹션 구현
- [ ] loading/error/empty 상태 구현

# 9-D. 페이지 연결
- [ ] `InventoryPage.jsx`에 LOT 클릭 연결
- [ ] `AllocationPage.jsx`에 LOT 클릭 연결(가능하면)
- [ ] `TonbagPage.jsx`는 선택 연결
- [ ] 선택된 LOT state 연결
- [ ] 모달 open/close 연결

# 9-E. 안정화
- [ ] lotNo 변경 시 재조회
- [ ] 닫은 뒤 재열기 시 정상 동작
- [ ] 빠른 연속 클릭 시 이전 요청 처리 정책 점검
- [ ] 빈 history/tonbags에서도 UI 붕괴 없음

---

# 10. 예외 처리 기준

## 10-1. lotNo 없음
- [ ] API 호출하지 않음
- [ ] 사용자에게 “LOT 정보가 없습니다” 표시

## 10-2. API 404
- [ ] “해당 LOT 상세를 찾을 수 없습니다” 표시

## 10-3. API 500
- [ ] 재시도 버튼 또는 닫기 안내 표시

## 10-4. 부분 데이터만 있는 경우
- [ ] 기본정보만 있어도 표시
- [ ] tonbags/history/allocation_status는 비어 있는 섹션으로 처리

## 10-5. 응답 필드명 불일치
- [ ] normalize adapter로 보정
- [ ] 화면 직접 필드 접근 최소화

---

# 11. 테스트 지시서

# 11-1. Pre-Test
- [ ] LOT 조회 API 단독 호출 확인
- [ ] 최소 1개 정상 LOT 샘플 확보
- [ ] 빈/없는 LOT 번호 샘플 확보
- [ ] 프론트 빌드/import 오류 없음

# 11-2. 기능 테스트
- [ ] LOT 클릭 → 모달 오픈
- [ ] loading 표시
- [ ] 성공 시 기본정보 표시
- [ ] tonbag 목록 표시
- [ ] history 표시
- [ ] allocation 상태 표시
- [ ] 모달 닫기 동작
- [ ] 다른 LOT 재오픈 동작

# 11-3. 예외 테스트
- [ ] 없는 LOT 번호
- [ ] 빈 tonbag 목록
- [ ] 빈 history
- [ ] allocation 정보 없음
- [ ] API 오류 응답

# 11-4. 비교 테스트
- [ ] Tkinter LOT 상세의 핵심 항목과 비교
- [ ] 누락 항목 기록
- [ ] 누락이 있어도 P0에서 허용 가능한지 판정

---

# 12. 완료 기준

## 완료로 인정
- [ ] React에서 LOT 상세 모달이 실제 동작
- [ ] 조회 API와 연결 완료
- [ ] 핵심 4섹션 표시 가능
- [ ] 주요 예외 처리 완료
- [ ] Tkinter 대비 치명 누락 없음

## 완료로 인정하지 않음
- [ ] 단순 placeholder만 보임
- [ ] API 연결 없이 mock 데이터만 표시
- [ ] loading/error 처리가 없음
- [ ] 특정 화면에서만 우연히 보이고 재사용 불가
- [ ] lotNo 변경 시 데이터 갱신이 안 됨

---

# 13. 실패 유형별 조치

## 유형 A. 응답 구조 불일치
- [ ] normalize adapter 추가
- [ ] 백엔드 응답 shape 보강 검토

## 유형 B. LOT 클릭 진입점 불명확
- [ ] InventoryPage를 1차 진입점으로 고정
- [ ] 나머지는 후속 연결

## 유형 C. history/allocation 데이터 없음
- [ ] 현재 API 범위 확인
- [ ] P0 허용 범위 내에서 빈 섹션 처리
- [ ] P1에서 보강할지 메모

## 유형 D. 모달 렌더 성능 문제
- [ ] 초기에는 단순 테이블 우선
- [ ] pagination/lazy load는 P1로 미룸

---

# 14. 산출물 목록

- [ ] `LotDetailModal.jsx` 실제 구현본
- [ ] `getLotDetail()` API 함수
- [ ] 페이지별 LOT 클릭 연결 코드
- [ ] LOT 상세 응답 normalize 함수(필요 시)
- [ ] P0-2 테스트 결과 메모

---

# 15. P0-2 → P0-3 진입 게이트

다음 단계(P0-3 입고/출고 write loop)로 넘어가려면 아래를 만족해야 한다.

- [ ] LOT 상세 모달이 실제 동작
- [ ] 조회 API 연결이 안정적
- [ ] 프론트 상태관리 패턴이 정리됨
- [ ] React ↔ backend 첫 실동작 검증 완료
- [ ] 주요 예외 처리 방식이 정리됨

---

# 16. 루비 최종 권장안

이번 단계의 핵심은 아래 한 줄이다.

```text
P0-2는 React에서 '읽기 동작'을 완성하는 단계다.
이 단계가 안정적이어야 P0-3의 write 동작이 안전해진다.
```

따라서 권장 구현 순서는 아래다.

```text
1. InventoryPage에서 LOT 클릭 연결
2. getLotDetail API 연결
3. LotDetailModal 본체 구현
4. normalize/예외 처리
5. AllocationPage / TonbagPage 보조 연결
```

---

# 17. 다음 단계 권장

이번 문서 다음으로 가장 효율적인 작업은 아래 2개 중 하나다.

1. `P0-2_LOT상세모달_테스트체크리스트.md`
2. `Claude Code용 P0-2 실행 프롬프트`

루비 권장 순서는 아래다.

```text
1) P0-2 테스트체크리스트
2) Claude Code용 P0-2 실행 프롬프트
```
