# GPT_SQM_P2_핵심화면_P0수준_초세분화_MASTER.md
생성일: 2026-04-04 17:45 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
연결 문서:
- `GPT_SQM_MASTER_P2_to_Patch5_통합실행본.md`
- `GPT_SQM_P2_초상세_작업지시서.md`
- `GPT_SQM_P2_테스트체크리스트.md`

---

## [질문]
외부에 있는 동안 Q1부터 진행해서,  
**P2 핵심 화면(Return / Move / Scan)을 P0 수준으로 초세분화한 MASTER**를 작성해 달라는 요청

## [질문의도]
P2 전체를 한 번에 P0 수준으로 쪼개기보다,  
실제 영향도가 큰 핵심 화면 3개(Return / Move / Scan)만 먼저  
**파일 / 상태 / API / 이벤트 / 테스트 / 실패 시 조치 수준**으로 세분화해서  
다음 실행 세션에서 바로 투입 가능한 기준 문서로 만든다.

---

# [응답]

# 1. 이 문서의 역할

이 문서는 P2의 핵심 화면 3개를 **P0 수준으로 확대**한 세부 MASTER다.

즉, 아래 역할을 수행한다.

```text
1. Return 화면을 파일 단위 / 상태 단위로 세분화
2. Move 화면을 파일 단위 / 상태 단위로 세분화
3. Scan 화면을 파일 단위 / 상태 단위로 세분화
4. 각 화면의 API / payload / response / UX / 테스트 기준 확정
5. Claude Code / Cursor / 수동 작업 공통 기준 제공
```

---

# 2. 공통 원칙

## 2-1. 절대 원칙
- 기존 `engine_modules` 핵심 로직 직접 수정 금지
- 기존 API가 있으면 재사용 우선
- 새 route 추가가 필요해도 service/adapter 구조 유지
- loading / error / empty / success 상태를 반드시 분리
- mock 데이터 완료 처리 금지
- 테스트 없이 다음 화면으로 넘어가지 않음

## 2-2. 공통 대상 파일
```text
web/src/pages/*
web/src/components/*
web/src/components/modals/*
web/src/api/*
react_api/routes/*
react_api/services/*
react_api/schemas/*
```

## 2-3. 공통 UI 상태 규칙
- `loading`
- `error`
- `result`
- `selectedItem`
- `refreshKey`
- 필요 시 `filters`

---

# 3. Return 화면 초세분화

# 3-1. Return 화면 목표

Return 화면은 **반품 / 재입고 / 복귀 처리** 흐름을 React에서 usable 수준으로 복구하는 것이 목표다.

## 핵심 사용자 흐름
```text
반품 대상 조회
→ 대상 선택
→ 반품 정보 입력
→ Return 실행
→ 결과 확인
→ 재조회
```

---

# 3-2. Return 화면 예상 파일 구조

## 직접 수정/생성 후보
```text
web/src/pages/ReturnPage.jsx
web/src/components/return/*
web/src/api/actionApi.js
react_api/routes/actions.py
react_api/schemas/actions.py
react_api/services/action_service.py
react_api/services/engine_adapter.py
```

## 참조 파일
```text
engine_modules/inventory_modular/return_mixin.py
engine_modules/inventory_modular/query_mixin.py
기존 Tkinter return dialog / menu
```

---

# 3-3. Return 화면 상태 설계

## 페이지 상태
```text
filters
selectedReturnTarget
isReturnModalOpen
loading
error
result
refreshKey
```

## 모달 상태(필요 시)
```text
target
returnReason
quantity
location(optional)
submitLoading
submitError
submitResult
```

---

# 3-4. Return API 설계 기준

## 권장 API
```text
GET /return/search            (필요 시)
POST /return/execute          또는 action endpoint 내 return 실행
POST /return/reinbound        (필요 시)
```

## 최소 입력 payload 예시
```json
{
  "target_id": "string",
  "lot_no": "string",
  "tonbag_no": "string",
  "quantity": 1,
  "reason": "return",
  "requested_by": "user"
}
```

## 최소 응답 구조 예시
```json
{
  "success": true,
  "message": "Return processed",
  "data": {
    "restored": [],
    "summary": {}
  }
}
```

---

# 3-5. Return 구현 순서

1. 현재 Tkinter Return 흐름 조사
2. React 진입점 결정
3. 검색/대상 선택 UI 작성
4. Return 실행 모달 또는 액션 패널 작성
5. API 래퍼 연결
6. service/adapter 연결
7. 결과/재조회 연결
8. rollback/실패 응답 점검

---

# 3-6. Return 테스트 기준

- [ ] 대상 검색 가능
- [ ] 대상 선택 가능
- [ ] Return 실행 가능
- [ ] 성공 결과 표시
- [ ] 실패 결과 표시
- [ ] rollback 시 중간 상태 미잔존
- [ ] 재조회 시 상태 반영

---

# 3-7. Return 실패 시 조치

- 대상 검색이 없으면 최소 대상 직접 입력 구조 허용
- reinbound와 pure return을 구분해야 하면 단계 분리
- location 복귀 정책이 불명확하면 reason 우선 기록 후 후속 확장
- return 정책이 복잡하면 1차 usable 범위만 먼저 구현

---

# 4. Move 화면 초세분화

# 4-1. Move 화면 목표

Move 화면은 **톤백/재고 위치 이동**을 React에서 명확하게 수행할 수 있도록 복구하는 것이 목표다.

## 핵심 사용자 흐름
```text
이동 대상 검색
→ 현재 위치 확인
→ 새 위치 입력
→ Move 실행
→ 결과 확인
→ 재조회
```

---

# 4-2. Move 화면 예상 파일 구조

## 직접 수정/생성 후보
```text
web/src/pages/MovePage.jsx
web/src/components/move/*
web/src/api/actionApi.js
react_api/routes/actions.py
react_api/schemas/actions.py
react_api/services/action_service.py
react_api/services/engine_adapter.py
```

## 참조 파일
```text
engine_modules/inventory_modular/tonbag_mixin.py
engine_modules/inventory_modular/query_mixin.py
기존 Tkinter move/location upload 관련 화면
```

---

# 4-3. Move 화면 상태 설계

## 페이지 상태
```text
filters
selectedMoveTarget
currentLocation
newLocation
loading
error
result
refreshKey
```

## 모달 상태(필요 시)
```text
target
oldLocation
newLocation
reason
submitLoading
submitError
submitResult
```

---

# 4-4. Move API 설계 기준

## 권장 API
```text
PUT /location/update
GET /move/search      (필요 시)
```

## 최소 입력 payload 예시
```json
{
  "target_id": "string",
  "lot_no": "string",
  "tonbag_no": "string",
  "old_location": "A-01",
  "new_location": "B-02",
  "reason": "manual_move"
}
```

## 최소 응답 구조 예시
```json
{
  "success": true,
  "message": "Location updated",
  "data": {
    "target": {},
    "old_location": "A-01",
    "new_location": "B-02",
    "summary": {}
  }
}
```

---

# 4-5. Move 구현 순서

1. 기존 location/update API 확인
2. 검색/대상 선택 UI 작성
3. 현재 위치 표시
4. 새 위치 입력 UI 작성
5. updateLocation API 래퍼 연결
6. 결과 메시지 및 재조회 연결
7. rollback 및 실패 응답 점검

---

# 4-6. Move 테스트 기준

- [ ] 대상 검색 가능
- [ ] 현재 위치 표시
- [ ] 새 위치 입력 가능
- [ ] 위치 변경 성공
- [ ] 실패 시 rollback
- [ ] 재조회 시 위치 반영
- [ ] audit_log 기록 확인 가능

---

# 4-7. Move 실패 시 조치

- 대상 선택이 복잡하면 LOT/TONBAG 직접 입력 fallback 허용
- 위치 포맷 검증이 복잡하면 1차는 문자열 입력 허용
- 현재 위치가 빈 값인 경우 별도 경고 처리
- 다중 이동은 후속 단계로 미룸

---

# 5. Scan 화면 초세분화

# 5-1. Scan 화면 목표

Scan 화면은 **바코드/식별자 스캔 기반 처리 흐름**을 React에서 usable 수준으로 복구하는 것이 목표다.

## 핵심 사용자 흐름
```text
스캔 입력
→ 대상 식별
→ 유효성 검증
→ 상태 반영 또는 후속 액션
→ 결과 확인
→ 다음 스캔
```

---

# 5-2. Scan 화면 예상 파일 구조

## 직접 수정/생성 후보
```text
web/src/pages/ScanPage.jsx
web/src/components/scan/*
web/src/api/actionApi.js
react_api/routes/actions.py
react_api/schemas/actions.py
react_api/services/action_service.py
react_api/services/engine_adapter.py
```

## 참조 파일
```text
기존 Tkinter scan 관련 탭/handler
engine_modules/inventory_modular/outbound_mixin.py
engine_modules/inventory_modular/query_mixin.py
```

---

# 5-3. Scan 화면 상태 설계

## 페이지 상태
```text
scanInput
loading
error
lastResult
history
mode
refreshKey
```

## 권장 모드
```text
outbound_scan
lookup_scan
validation_scan
```

---

# 5-4. Scan API 설계 기준

## 권장 API
```text
POST /scan/resolve         (필요 시)
POST /scan/outbound        (필요 시)
기존 execute/cancel/lookup API 재사용 가능
```

## 최소 입력 payload 예시
```json
{
  "scan_code": "ABC123",
  "mode": "outbound_scan"
}
```

## 최소 응답 구조 예시
```json
{
  "success": true,
  "message": "Scan accepted",
  "data": {
    "resolved_target": {},
    "action": "outbound",
    "summary": {}
  }
}
```

---

# 5-5. Scan 구현 순서

1. 기존 Tkinter scan 로직 조사
2. 현재 React에서 필요한 최소 mode 정의
3. scan input + submit UX 작성
4. 결과 표시 패널 작성
5. 유효성 실패/중복 스캔 처리
6. scan history 표시
7. 후속 액션 연결(필요 시)

---

# 5-6. Scan 테스트 기준

- [ ] 정상 스캔 처리
- [ ] 잘못된 코드 처리
- [ ] 중복 스캔 처리
- [ ] 결과 메시지 표시
- [ ] history 표시
- [ ] 다음 스캔으로 빠르게 이어짐

---

# 5-7. Scan 실패 시 조치

- 카메라/하드웨어 직접 연동보다 텍스트 입력 우선
- lookup 모드부터 먼저 구현 가능
- outbound_scan은 P0 write loop와 연결된 최소 기능만 먼저 복구
- scan history는 단순 리스트부터 시작

---

# 6. 공통 테스트 게이트

```text
Pre-Test
→ 구현
→ Post-Test
→ 실패 시 수정
→ Re-Test
→ PASS
→ 다음 화면
```

---

# 7. 공통 완료 기준

- [ ] Return usable 1차 복구
- [ ] Move usable 1차 복구
- [ ] Scan usable 1차 복구
- [ ] loading/error/result UX 일관성
- [ ] 기존 P0 회귀 없음

---

# 8. 공통 실패 대응

- 화면 단위로 끊어서 구현
- 하나의 공통 mega page로 합치지 않음
- API 미확정 부분은 wrapper/adapter로 흡수
- 실무 규칙 모호한 부분은 1차 usable 기준 우선

---

# 9. 루비 최종 판단

```text
P2 핵심 화면을 P0 수준으로 세분화한다는 것은
화면 이름만 정하는 것이 아니라
파일 / 상태 / API / 이벤트 / 테스트 / 실패 대응까지
각 화면을 하나의 작은 프로젝트처럼 다루는 것을 의미한다.
```

---

# 10. 다음 단계 권장

```text
1. Patch 2 preview/warning/create_payload를 P0 수준으로 초세분화
2. 그 다음 P4 + Patch 4 세트로 이동
```
