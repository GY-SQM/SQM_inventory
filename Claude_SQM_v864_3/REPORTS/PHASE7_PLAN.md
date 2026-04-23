# Phase 7 작업 지시서 — 사장님 실사용 1주

> **목적**: Nam Ki-dong 사장님이 GY Logis 광양창고에서 매일 SQM v864.3 을 실사용하며 발견한 버그/UX 이슈를 수집하고 즉시 핫픽스.
> **예상 소요**: 7일
> **담당**:
>  - 사장님: 실사용 + 이슈 리포트
>  - Claude Code: 핫픽스 + 일일 리포트 작성
> **선행 조건**: Phase 6 완료 (tag `v864.3-phase6`)

---

## 🎯 Definition of Done (DoD)

- [ ] 7일 연속 실사용 로그 (`REPORTS/PHASE7_DAY1.md` ~ `DAY7.md`)
- [ ] Critical 버그 0 건 또는 모두 핫픽스됨
- [ ] 사장님 승인 ("Phase 8 릴리스 GO")
- [ ] `REPORTS/PHASE7_SUMMARY.md` 최종 요약
- [ ] git 태그 `v864.3-phase7`

---

## 📋 일일 루틴 (매일 반복)

### 🌅 아침 (사장님 주도, 09:00)

```
1. SQM_v864_3.exe 실행
2. 전일 sqm_debug.log 확인 (오류 라인 유무)
3. 오늘 작업 대상 업무 파악 (입고 예정 컨테이너 수 등)
```

### 🌞 일과 (실사용)

사장님이 아래 기능을 **실제 업무로** 사용:

| 시점 | 기능 | 체크 포인트 |
|---|---|---|
| 컨테이너 도착 | F001 PDF 스캔 입고 | 파일 업로드 → LOT 자동 생성 확인 |
| 수동 보정 필요 시 | F002 수동 입고 (Excel) | Excel 업로드 → 재고 등록 |
| D/O 도착 | F003 D/O 후속 연결 | LOT + 필드 업데이트 |
| 위치 할당 시 | F004 톤백 위치 매핑 | Excel 업로드 |
| 출고 계획 | F014 Allocation 입력 (Excel) | Excel 업로드 |
| 픽업 전 | F017 Picking List PDF | PDF 업로드 → picking_table 반영 |
| 출고 시 | F015 즉시 출고 | LOT 선택 → 확정 |
| 여러 LOT 출고 | F016 빠른 출고 (붙여넣기) | 텍스트 붙여넣기 → 확정 |
| 출고 완료 | F028 출고 확정 | PICKED → OUTBOUND |
| 반품 입고 | F007 반품 입고 Excel | Excel 업로드 |
| 정기 검증 | F013 정합성 검사 | 결과 확인 |

### 🌆 저녁 (18:00, Claude Code 리포트 작성)

```bash
python scripts/daily_report.py <DAY_NUM>  # 예: 1, 2, ...
# 또는 수동으로 REPORTS/PHASE7_DAY{N}.md 작성
```

**일일 리포트 템플릿** (`REPORTS/PHASE7_DAY{N}.md`):
```markdown
# Phase 7 — Day {N} 실사용 보고

**일자**: YYYY-MM-DD (요일)
**실행 시간**: HH:MM ~ HH:MM
**사용자**: Nam Ki-dong

## 사용한 기능
| 기능 | 횟수 | 결과 |
|------|------|------|
| F001 PDF 스캔 입고 | 3건 | ✅ 모두 성공 |
| F015 즉시 출고 | 5건 | ⚠️ 1건 실패 (톤백 부족 정상 거절) |
| ...

## 발견한 이슈
1. **[P1/Critical]** <증상> → 즉시 핫픽스 필요
2. **[P2/High]** <증상> → Phase 8 전 수정
3. **[P3/Medium]** <개선 제안> → 후속 릴리스
4. **[P4/Low]** <코스메틱> → 기록만

## 핫픽스 적용 내역
- 커밋 <hash>: <제목>

## 스크린샷
- screenshots/day{N}_issue1.png
- ...

## 내일 계획
- <계획>

## 사장님 만족도
⭐⭐⭐⭐☆ (5점 만점, 간단 피드백)
```

---

## 🚨 Critical 버그 핫픽스 절차 (사장님이 "당장 안 됨" 신고 시)

```bash
# 1. 현재 상태 커밋 (진행 중 작업 보호)
git stash -u -m "WIP: before hotfix day{N}"

# 2. 디버그 로그 수집
cp dist/sqm_debug.log REPORTS/hotfix_day{N}_debug.log

# 3. 사장님에게 Q&A
#    "정확히 어떤 메뉴 눌렀어요?"
#    "몇 시쯤 발생?"
#    "에러 메시지 스샷?"
#    "이전엔 됐나요?"

# 4. 원인 특정 (로그 분석)
grep -E "ERROR|CRITICAL|UNCAUGHT|Traceback" REPORTS/hotfix_day{N}_debug.log

# 5. 수정 + 스모크 테스트
#    해당 엔드포인트 / 모달 수정
python scripts/verify_endpoints.py  # 회귀 없는지 확인

# 6. EXE 재빌드 (핫픽스 제공 위해)
python scripts/build_exe.py

# 7. 사장님에게 새 EXE 전달
cp dist/SQM_v864_3.exe \\gy-logis\공유\sqm_hotfix_day{N}.exe

# 8. 커밋 + 태그
git add -A
git commit -m "fix(v864.3-day{N}): <증상> 핫픽스"
git tag v864.3-day{N}-hotfix

# 9. 리포트에 기록
echo "- 핫픽스 <hash>: <제목>" >> REPORTS/PHASE7_DAY{N}.md
```

**P1 목표**: 발견 → 핫픽스 → EXE 재빌드 → 사장님 재시작 **60분 이내**.

---

## 🔁 중단 복구 시나리오

| 상황 | 대응 |
|---|---|
| EXE 실행 즉시 꺼짐 | `dist/sqm_debug.log` 확인 → Traceback 분석 |
| API 포트 8765 점유 | `netstat -ano \| findstr :8765` → taskkill /F /PID XXX |
| DB 손상 | `backup/` 폴더의 최근 sqm_backup_*.db 로 교체 |
| 특정 LOT 이상 | `/api/action/integrity-check` → 보고서 확인 |
| 전체 시스템 복구 불가 | v864.2 EXE 로 임시 전환 (24h 병행) → 원인 조사 후 v864.3 재시작 |

---

## 📊 주간 누적 지표

**추적할 KPI** (매일 DAY{N} 리포트 하단에):

- 총 실행 시간 (min)
- 처리한 LOT 수
- 발생한 에러 수 (Critical/High/Medium 분리)
- 핫픽스 수
- 사장님 피드백 (1-5점)

---

## 🔄 자동 진입 조건 (Phase 8)

다음이 모두 만족되면 Phase 8 릴리스로 진입:

- [x] 7일 연속 실사용 완료
- [x] Critical 버그 0 (또는 모두 핫픽스)
- [x] 사장님 "GO" 승인 (DAY7 리포트에 명시)
- [x] `REPORTS/PHASE7_SUMMARY.md` 작성
- [x] `git tag v864.3-phase7`

**사장님 승인 방법**:
```
DAY7 리포트 말미에:
## 🎯 Phase 8 릴리스 GO/NO-GO
- [x] GO — 공식 전환 진행
- [ ] NO-GO — 추가 안정화 필요 (이유: ...)

서명: Nam Ki-dong (2026-XX-XX)
```

GO 확인되면 → `REPORTS/PHASE8_PLAN.md` 로 자동 이동.
