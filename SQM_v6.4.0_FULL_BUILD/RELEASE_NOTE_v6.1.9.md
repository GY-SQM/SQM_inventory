# SQM v6.1.9 Release Notes

## 핵심 변경
- PC Guard 다중 PC 허용을 기본 동작으로 변경
  - `--register-pc` 실행 시 기존 목록 유지 + 현재 PC 추가/갱신
  - 강제 교체가 필요할 때만 `--replace-pc-list` 사용
- PC 보안 허용 목록 업데이트
  - `대흥남기동2025` PC의 MAC 주소 4종 추가
- 런타임 안정화 핫픽스 적용
  - `inventory_tab.py` `_TC` 미정의 참조 제거
  - `outbound_scheduled_tab.py` `END` 참조 안정화
  - `help_dialogs.py` logger 선언 보강
  - `refresh_mixin.py`, `onestop_inbound.py` `CustomMessageBox` 참조 보강
- 완전 패치 전 기준선 문서 추가
  - `docs/PHASE1_BASELINE_20260227.md`

## 보안 동작 참고
- 인증 규칙:
  - MAC+GUID 모두 일치: 인증 완료
  - MAC 또는 GUID 하나 일치: 경고 후 실행(부분 인증)
  - 모두 불일치: 실행 차단

## 운영 권장
- 대상 PC에서 `python run.py --register-pc`를 1회 실행해 GUID까지 등록 권장
- 완전 패치(Phase 2~4) 진행 전 `data/db` 백업 필수

