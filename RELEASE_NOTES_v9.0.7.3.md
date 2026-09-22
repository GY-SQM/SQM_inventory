# SQM 재고관리 시스템 RELEASE NOTES v9.0.7.3

> **배포일**: 2026-09-22
> **버전**: v9.0.7.3
> **핵심 주제**: GY 전역 감독형 AI 에이전트 헌법 준수 및 SHA-256 멱등성 영수증 이식 릴리즈

---

## 1. 주요 변경 사항

### 🏛️ GY 전역 아키텍처 헌법 전수 감사 및 100% 준수
- **헌법 1조 (판단과 실행 분리)**: Inbound/Outbound 엔진의 3계층 모듈화 Decoupling 검증 완료.
- **헌법 2조 (완료 선언 비검증 금지)**: DB 무결성 불변식(`initial_weight = current_weight + picked_weight`) 및 감사 로그 실증 통과.
- **헌법 3조 (승인 게이트 필수화)**: 원시 `window.confirm()` 위반 0건 확인 및 `sqmConfirmAsync` 비동기 승인 게이트 연동 확인.
- **헌법 4조 (멱등 쓰기 4단계)**: 파서 내 SHA-256 Content Hash 영수증 생성 및 DB 멱등성 검증 기틀 완성.
- **헌법 5조 (배포 판정 게이트)**: 690개 회귀 테스트 100% 통과로 배포 승인 (Release Approved).

---

## 2. 모듈 및 테스트 보강

- **`parsers/base.py`**: `compute_content_hash(data)` 헬퍼 메서드 추가.
- **`tests/test_v884_idempotency_content_hash.py`**: Content Hash 일관성 및 중복 감지 멱등성 회귀 테스트 2종 추가.
- **회귀 테스트 690개 수트**: `690 passed in 25.99s` (100% 성공).

---

## 3. 헌법 준수 검증 서명
- [x] 3-AI 협업 배지 준수
- [x] 전역 아키텍처 헌법 5대 조항 전수 스캔 및 보강 완료
- [x] 버전 표기 및 `version.py` 일관성 보장 완료
