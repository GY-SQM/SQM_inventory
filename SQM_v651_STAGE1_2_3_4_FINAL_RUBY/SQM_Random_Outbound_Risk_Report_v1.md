# SQM Random Outbound Risk Report v1

## 핵심 결론
Random + 톤백단위 출고 자체는 유지 가능하다.
문제는 랜덤이 아니라 식별체계 혼용(sub_lt / tonbag_no / tonbag_uid)과 요약재고/실재고 혼합 갱신이다.

## 주요 위험
1. 식별체계 혼용
2. LOT 계획 / TONBAG 확정 로그 혼선
3. LOT 내부 swap 허용으로 인한 추적 혼선
4. inventory.current_weight와 실제 tonbag 합계 불일치 위험

## 이번 Stage3 반영
- tonbag_uid 우선 조회
- tonbag_no 직접 조회 지원
- 상태 검증 추가
- 중복 스캔 기본 차단/경고 보강

## 다음 Stage4 목표
- inventory.current_weight 무결성 자동검사
- LOT/TONBAG/WEIGHT/LOCATION 일치 검증
