# SQM v9.0.7.2 릴리즈 노트
> 릴리즈 날짜: 2026-07-26
> 저장소: D:\program\sqm\SQM_inventory (GitHub: GY-SQM/SQM_inventory)

---

## 변경 사항

### [FIX] pythonw 경로 정정 (v9.0.7.2)
- SQM.vbs / r1.vbs / run.bat의 pythonw.exe 경로를 `C:\Users\kidon\...`에서 `C:\Users\남기동\...`로 정정
- kidon 사용자 경로는 현재 호스트(남기동)에서 작동하지 않는 회귀 버그였음
- run_debug_console.bat 신규 추가: 디버그 콘솔용 python 실행 런처
- run.bat에 pythonw.exe 미존재 시 PATH의 pythonw.exe로 fallback 로직 포함

### [SECURITY] security/ 폴더 추가
- allowed_pcs.json: 광양 PC 2대 등록 (광양대흥남기동, 광양남기동)
  - MAC 주소 + MachineGuid 기반 인증
- allowed_pcs_backups/: 최초 백업 (2026-07-22)
- core/pc_guard.py (v9.0.7에서 이미 추가됨)와 연동

### [CHORE] gitignore 정정
- sqm_debug.log* 패턴 추가 (로그 파일이 untracked로 노출되는 문제 해결)

### [VERSION] 버전 통일 (GLOBAL-4)
- version.py: 8.8.5 → 9.0.7.2
- git HEAD 커밋 메시지(v9.0.7.1)와 version.py(8.8.5) 불일치 해소
- RELEASE_DATE / BUILD_DATE: 2026-07-26

### [MERGE] 분열 저장소 통합
- D:\program\SQM-inventory (하이픈 클론)의 2c5f0f4 커밋 cherry-pick
  - AGENTS.md, docs/release-checklist.md, docs/verify-report.md 추가
- SQM-inventory 폴더는 _archive로 이동 (분열 해소)

### [ARCHIVE] 백업/샘플 폴더 정리
- D:\program\sqm\_archive\에 11개 항목 정리
- 보관 정책: 30일 후 폴더 삭제, 90일 후 ZIP 삭제, SQM-inventory 영구 보관

---

## 파일 변경 목록

| 파일 | 변경 유형 | 내용 |
|---|---|---|
| SQM.vbs | 수정 | pythonw 경로 남기동 정정 |
| r1.vbs | 수정 | pythonw 경로 남기동 정정 |
| run.bat | 수정 | pythonw 직접 실행 + fallback |
| run_debug_console.bat | 신규 | 디버그 콘솔 런처 |
| security/allowed_pcs.json | 신규 | 광양 PC 2대 등록 |
| security/allowed_pcs_backups/ | 신규 | allowed_pcs 백업 |
| .gitignore | 수정 | sqm_debug.log* 추가 |
| version.py | 수정 | 8.8.5 → 9.0.7.2 |
| AGENTS.md | 신규 | cherry-pick from 2c5f0f4 |
| docs/release-checklist.md | 신규 | cherry-pick from 2c5f0f4 |
| docs/verify-report.md | 신규 | cherry-pick from 2c5f0f4 |

---

## 커밋 히스토리

```
bb5a691 fix(version): 8.8.5 → 9.0.7.2 버전 통일 (GLOBAL-4)
ad966d1 chore: sqm_debug.log* gitignore 추가
d30dad1 fix(v9.0.7.2): pythonw 경로 남기동 정정 + security/allowed_pcs 추가
487c530 chore: add harness documentation gates (cherry-pick from SQM-inventory)
bcc93ec feat(v9.0.7.1): config_local.py fallback (PC Guard 회사 PC 명단)
```

---

## 검증 항목

- [x] pythonw.exe 경로 존재 확인: C:\Users\남기동\AppData\Local\Programs\Python\Python313\pythonw.exe ✅
- [x] version.py VERSION = 9.0.7.2 ✅
- [x] git push origin main 완료 ✅
- [x] 분열 저장소 통합 (진본 1개) ✅
- [x] 백업 폴더 _archive 정리 ✅
- [ ] 앱 기동 테스트 (진행 중)
