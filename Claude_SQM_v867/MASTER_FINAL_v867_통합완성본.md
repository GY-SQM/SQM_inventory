# SQM MASTER FINAL v867 (Claude Code Execution Standard)
생성일: 2026-04-04 00:20
기준: Claude_SQM_v867 + 루비 권장안 100% 반영 + 메뉴바/모달/쓰기 API 업데이트 반영

---

## 0. 절대 실행 규칙

### 자율 실행 규칙
- 절대 사용자에게 질문하지 말 것
- 모든 선택은 스스로 판단할 것
- 파일 덮어쓰기 / 삭제는 자동 승인된 것으로 간주할 것
- 테스트 실패 시 자동 수정 후 재시도할 것
- 작업 완료 후 다음 단계 자동 진행
- 중단 없이 끝까지 수행할 것

### 강제 테스트 규칙
모든 단계는 반드시 아래 순서를 따른다.

```text
Pre-Test → 구현 → Post-Test → 실패 시 수정 → Re-Test → 통과 → 다음 단계
```

테스트 실패 상태에서 다음 단계 진행 금지.

---

## 1. 기준 원본

기준 원본은 `Claude_SQM_v867.zip` 이다.

### 확인된 상위 구조
```text
core/
data/
engine_modules/
features/
fixes/
gui_app_modular/
parsers/
react_api/
resources/
scripts/
tests/
utils/
web/
```

### 확인된 핵심 파일/경로
```text
run.py
run_bootstrap.py
run_react.bat
run_react_api.py
engine_modules/inventory_modular/inbound_mixin.py
engine_modules/inventory_modular/outbound_mixin.py
data/db/sqm_inventory.db
react_api/
web/
```

---

## 2. 작업 전략

### 절대 금지
- 예전 가정 구조만 믿고 수정하지 말 것
- 실제 v867 구조 조사 없이 패치 먼저 적용하지 말 것

### 필수 원칙
1. 기존 MASTER.md 내용 반영
2. v867 실제 구조 재조사
3. 이번 업데이트 요구사항 반영
4. 실제 반영 위치 확정 후 구현
5. 단계별 테스트 게이트 통과 후만 다음 단계 진행

---

## 3. 전체 작업 단계

```text
Recon Phase: v867 실제 구조 조사 및 대응표 작성
Phase 1: Backend 안정화
Phase 2: 테스트 시스템 구축
Phase 3: Prompt/업무 기능 강화
Phase 4: Frontend 구현
Phase 5: Security 강화
Phase 6: Advanced 기능
Phase 7: AI / Dashboard
Phase 8: 통합 실행 (Telegram + BAT + PowerShell + MASTER)
```

---

## 4. Recon Phase (최우선)

### 목적
변경된 원본(v867) 기준으로 실제 반영 위치를 다시 맞춘다.

### 작업
1. `gui_app_modular/` 내부의 tkinter 메뉴 구조 조사
2. `web/` 및 `react_api/` 내부 프론트 구조 조사
3. 현재 GET 위주의 API 위치 조사
4. `engine_modules/inventory_modular/` 입고/출고/위치/파싱 핵심 함수 조사
5. tkinter 다이얼로그 ↔ React 모달 대응표 작성
6. 메뉴 ↔ 모달 ↔ API ↔ engine 연결표 작성

### 산출물
```text
docs/RECON_V867_WEB_MIGRATION_MAP.md
```

### 완료 기준
- 메뉴 대응표 완성
- 다이얼로그 대응표 완성
- 쓰기 API 연결 후보 함수 표 완성
- 실제 수정 파일 목록 확정

---

## 5. 메뉴바 구현 기준

### 목표
tkinter 메뉴바 구조를 React 상단 웹 네비게이션 + 드롭다운 메뉴로 구현한다.

### 최소 메뉴 구조
```text
검색
도구
입고
출고
현재 탭 표시
```

### 기능
- 검색: 키워드 / 기간 / 상태 통합 검색 팝업
- 도구: Excel 내보내기, 정합성 체크
- 입고: 입고 파싱 다이얼로그 열기
- 출고: 출고 처리 다이얼로그 열기
- 현재 탭: 현재 화면 또는 현재 작업 맥락 표시

### Claude Code 작업 원칙
- tkinter 메뉴바 정의 파일/함수 먼저 찾기
- React 상단바 컴포넌트 위치 찾기
- 이름/역할/호출 흐름을 동일하게 맞추기
- 링크만 있는 상단바면 드롭다운 메뉴 구조로 확장

### 완료 기준
- 상단 메뉴바에서 검색/도구/입고/출고 드롭다운이 보인다
- 각 메뉴 클릭 시 대응 팝업 또는 기능이 열린다
- 현재 탭 표시가 작동한다

---

## 6. 다이얼로그 구현 기준

### A. LOT 상세 모달
LOT 클릭 시 팝업

포함 항목:
- 기본정보
- 톤백 목록
- 이력
- 배정 상태

### B. 입고 파싱 모달
엑셀/PDF 업로드 → 자동 파싱 → LOT 생성 확인

포함 항목:
- 파일 업로드
- 파싱 결과 미리보기
- 생성 예정 LOT 요약
- 사용자 확인 후 생성 실행

### C. 출고 처리 모달
톤백 선택 → 수량 / 출고처 입력 → 출고 실행

포함 항목:
- 대상 톤백 선택
- 출고 수량
- 출고처 입력
- 실행 버튼
- 실행 결과 표시

### 원칙
- tkinter `Toplevel` 또는 기존 다이얼로그 역할 파일을 먼저 찾는다
- 입력값 / 출력값 / 호출 시점 / 후처리를 표로 정리한다
- 그 다음 React 모달로 옮긴다

### 완료 기준
- LOT 클릭 시 LOT 상세 모달
- 입고 메뉴 클릭 시 입고 파싱 모달
- 출고 메뉴 클릭 시 출고 처리 모달
- 닫기 / 확인 / 취소 동작 정상

---

## 7. 쓰기 API 구현 기준

### 추가 대상 API
```text
POST /inbound/create
POST /outbound/execute
PUT  /outbound/cancel
PUT  /location/update
POST /files/upload
```

### 연결 원칙
가능하면 기존 `engine_modules` 로직을 재사용한다.

우선 연결 후보:
- `process_inbound`
- `reserve_from_allocation`
- `inbound_mixin`
- `outbound_mixin`
- 위치 변경 관련 함수
- 파일 파싱 관련 함수

### 강제 원칙
- FastAPI에서 완전 신규 업무 로직을 만들지 말 것
- 기존 engine_modules 핵심 로직을 감싸는 방식으로 연결할 것
- 모든 쓰기 API는 트랜잭션 보호
- 실패 시 rollback
- 성공/실패 로그 남기기

### 최소 응답 구조
```json
{
  "success": true,
  "message": "Operation completed",
  "data": {}
}
```

### 완료 기준
- 위 5개 API가 `/docs` 에 표시
- 정상 요청 시 실제 로직 연결
- 실패 시 rollback 확인 가능
- 잘못된 입력에 4xx 응답

---

## 8. Security / 안정성 기준
- `.env` 분리
- BOT_TOKEN / CHAT_ID / ADMIN_TOKEN 분리
- 입력값 validation
- 최소 보호막 적용
- 예외 처리 공통화
- 로그 기록 강화

---

## 9. Telegram Bridge 기준

### 지원 응답
```text
y / n
yes / no
1 / 2
1 / 2 / 3
자유 문장 명령
```

### 처리해야 할 멈춤 유형
1. 질문형 멈춤
2. 선택형 멈춤
3. 다음 단계 대기형
4. idle timeout 기반 무출력 대기형

### 사용자가 텔레그램에서 보낼 수 있는 명령 예
```text
y
n
1
2
3
그냥 작업을 진행해 줘
다음 단계 진행
테스트 실패 원인 먼저 수정해 줘
로그까지 정리하고 계속해 줘
```

### Telegram 메시지에는 반드시 포함할 것
- Claude 최근 출력 300~500자
- 현재 질문/선택/다음 단계 문맥
- 가능한 응답 방법 안내

---

## 10. BAT / PowerShell / MASTER 통합 기준

### 구조
```text
BAT / PS1
→ 사전 테스트
→ Telegram Bridge 실행
→ bridge 내부에서 Claude 실행
→ Claude는 MASTER.md 기준으로 작업
```

### Pre-Test 필수 항목
- `.env` 존재 확인
- backend 테스트
- frontend 테스트
- frontend build
- logs/docs 폴더 확인
- bridge 파일 존재 확인
- MASTER.md 존재 확인

### 실패 시 원칙
- 즉시 중단
- run_log.txt 기록
- 다음 단계 진행 금지

---

## 11. Claude 실행 기준 문구
Claude는 아래 원칙으로 실행한다.

```text
현재 작업 기준 원본은 Claude_SQM_v867 이다.
기존 가정 구조만 믿고 진행하지 말고 반드시 실제 v867 코드 구조를 먼저 조사한 뒤 수정하라.
이번 작업의 신규 핵심 목표는:
1. React 상단 메뉴바를 tkinter 메뉴 구조와 동일한 드롭다운 웹 네비게이션으로 확장
2. LOT 상세 / 입고 파싱 / 출고 처리 다이얼로그를 React 모달로 구현
3. GET 중심 API에 쓰기 엔드포인트를 추가하고 기존 engine_modules 로직과 연결
4. 모든 쓰기 API는 트랜잭션 보호 및 rollback 필수
5. Recon Phase에서 실제 반영 위치를 먼저 확정한 뒤 단계별 테스트 게이트를 거쳐 진행
```

---

## 12. 최종 목표

```text
1. Tkinter ↔ React 전환 구조 정렬
2. 메뉴/모달/API 실제 연결
3. 기존 engine_modules 재사용
4. 단계별 테스트 통과형 개발
5. Telegram 원격 재개 가능
6. 무중단 밤샘 디버깅 가능
```

---

## 13. 금지 사항
- 테스트 생략
- 사용자 질문 발생
- 부분 완료 상태 종료
- 실제 구조 조사 없이 임의 패치 우선 적용
- rollback 없는 쓰기 API 구현

---

## 14. 실행 선언
이 문서를 기준으로 Claude Code는:
- 질문 없이
- 중단 없이
- 실제 v867 코드 기준으로
- 단계별 테스트를 통과하며
작업을 수행해야 한다.