# RELEASE NOTE — v6.2.2

배포일: 2026-02-27  
버전: `6.2.2`

## 핵심 변경

- 원스톱 입고 고도화
  - `↻ 다시 파싱` 버튼 추가 (파일 재업로드 없이 동일 파일 재파싱)
  - 재파싱 확인 문구 강화: 기존 미리보기 덮어쓰기 안내
  - 업로드 완료 후 요약 팝업 추가(저장 LOT/수정행/SAP·BL·컨테이너/총 NET)
  - 후속 액션 플로우 추가: 화면 정리 → `추가 입고(예) / 종료(아니오)` 선택
  - 업로드 완료 시 업로드1/업로드2 미리보기 데이터 즉시 CLEAR

- 크로스체크 엔진 운영 코드 이식
  - `parsers/cross_check_engine.py` 신규 추가
  - 파서/원스톱/업로드 흐름에 크로스체크 결과 연동
  - CRITICAL 불일치 시 업로드 전 사용자 재확인 단계 추가
  - 행 단위 하이라이트 태그(`xc_critical/warning/info`) 적용

- 정규화 품질 보강
  - 날짜 정규화: `DD-Mon-YYYY`(`29-Jan-2026`) 지원 추가
  - 비날짜 정규화:
    - `norm_digits_only`의 Excel float 접미사(`.0`, `.00`) 보정
    - `parse_euro_weight("100.020")` 유럽식 천단위 해석 보강

## 테스트

- `python -m pytest tests/test_cross_check_engine.py -q` 통과
- `python -m pytest tests/test_normalize_non_date.py -q` 통과
- 샘플 날짜/정규화 케이스 수동 검증 완료

## 운영 메모

- 이번 릴리즈는 파싱 재작업 UX와 데이터 정합성 방어를 함께 강화한 버전입니다.
- DB 파일(`data/db/sqm_inventory.db`)은 릴리즈 커밋에서 제외했습니다.
