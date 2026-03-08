# RELEASE NOTES — SQM v6.5.1 Stage1~Stage4 Final

## Summary
이번 패키지는 Stage1~Stage4 누적 패치 최종 검토본이다.

## Stage1
- tonbag_no 3자리 고정
- sample=S00
- tonbag_uid=lot_no-tonbag_no
- sub_lt legacy only

## Stage2
- 기존 계산식 공식화: (총 LOT 무게 - 1kg sample) / mxbg_pallet
- 500kg / 1000kg 모두 기존 계산식 유지

## Stage3
- Random outbound scan validation 보강
- 허용 상태/차단 상태 정리
- tonbag_uid 우선 조회 강화

## Stage4
- Inventory Integrity Engine 보강
- Rack capacity 20 검사
- A/B 창고 3500씩, 총 7000 capacity 검사
- Location 형식 검사(A-03-05-02)
- 공식 운영/DB/무결성 문서 docs 폴더 추가
