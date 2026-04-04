# SQM_PRIORITY_CHECKLIST.md

> SQM 프로젝트 우선순위별 초간단 체크리스트  
> 기준 시점: 2026-04-02 22:42 (Asia/Seoul)  
> 인코딩: UTF-8

---

## P0 — 즉시 진행

- [ ] `outbound_mixin.py` 리팩토링 결과 **별도 커밋 여부 확인**
- [ ] `outbound_mixin.py` 리팩토링 결과 **별도 push 여부 확인**
- [ ] `SOLD` 참조 전역 검색
- [ ] `SOLD`를 아래 기준으로 분류
  - [ ] write-path
  - [ ] read-path
  - [ ] UI 표시
  - [ ] report/export
  - [ ] legacy compatibility
- [ ] 새 `SOLD` write-path 금지 확인
- [ ] `OUTBOUND`를 현재 write-state 기준으로 고정
- [ ] `onestop_inbound.py` giant file 분석 착수
- [ ] `onestop_inbound.py` 대형 함수 상위 3개 추출
- [ ] `onestop_inbound.py`의 UI / parser / review / apply 혼합 구간 식별

---

## P1 — 단기 진행

- [ ] 40개+ mixin 실제 목록 전수 추출
- [ ] mixin 기능 그룹별 분류
  - [ ] UI 프레임/윈도우
  - [ ] 메뉴/툴바
  - [ ] 탭/refresh
  - [ ] 대화상자
  - [ ] 업무 오케스트레이션
  - [ ] 유틸/진단
- [ ] 서비스 계층 분리 후보 정리
  - [ ] outbound
  - [ ] allocation
  - [ ] picking
- [ ] parser / 예외 처리 구조 분석
- [ ] hard-stop vs warn-only 기준 정리
- [ ] `except pass` / broad exception 전수 검색

---

## P2 — 장기 진행

- [ ] UI refresh / `after()` 호출 구조 정리
- [ ] TreeView 대량 갱신 공통화 후보 정리
- [ ] 테스트 기반 확대
- [ ] release / manifest 기준 정리
- [ ] `v864`, `v866` 관계 정리
- [ ] release snapshot vs backup snapshot 구분

---

## 현재 기준 한줄 요약

- [x] `outbound_mixin.py` 1차 리팩토링 완료
- [x] 정적 검증 통과 (PASS 27 / WARN 1 / FAIL 0)
- [x] `py_compile` 통과
- [x] `run.py --check` 통과
- [ ] 다음 핵심: `SOLD` 분류 → `onestop_inbound.py` → mixin 구조 정리

---

## 새 세션 첫 작업 추천 순서

1. [ ] `outbound_mixin.py` 결과 커밋 여부 확인
2. [ ] `SOLD` 참조 분류 시작
3. [ ] `onestop_inbound.py` 분석 시작
4. [ ] mixin 인벤토리 초안 작성
