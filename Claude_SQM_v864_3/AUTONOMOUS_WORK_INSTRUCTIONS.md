# 🤖 자율 모드 작업 설명서 — 외출 중 진행할 일

> **이 문서를 첫 메시지로 입력하면 Claude Code 가 외출 중 자율로 다음 작업을 진행합니다.**

## 🎯 진행할 최종 검증 단계 (Optional, 권장)

v864-3 포팅 자체는 **100% 완료** + **139/139 Playwright 테스트 통과** 상태입니다.
운영 투입 가능. 하지만 더 견고하게 만들려면 다음을 자율 진행해주세요.

---

## Phase A: 실 PDF 파일 업로드 검증 (1~2h)

### 목표
실제 v864-2 가 처리하던 PDF 4종 (BL/PL/INV/DO) 을 v864-3 OneStop Inbound 에 업로드해서 동등 결과인지 확인.

### 진행 방법
1. 서버 띄우기:
   ```
   PYTHONIOENCODING=utf-8 python -m uvicorn backend.api:app --host 127.0.0.1 --port 8765 --log-level warning > /tmp/sqm_run.log 2>&1 &
   ```
2. 테스트 PDF 위치 찾기:
   ```
   find D:/program/SQM_inventory/Claude_SQM_v864_2 -name "*.pdf" -path "*test*" 2>&1 | head -10
   find D:/program/SQM_inventory -maxdepth 3 -name "*.pdf" 2>&1 | head -10
   ```
3. 4종 PDF 가 있다면 Playwright 자동 업로드 시나리오 작성 후 실행
4. 파싱 결과 + 크로스체크 결과 검증

### 결과물
- `scripts/test_real_pdf_upload_playwright.py` 신규 작성
- `REPORTS/playwright_real_pdf.json` 결과
- 100% PASS 안 되면 자동 수정 루프 (최대 5회)

---

## Phase B: 부하 테스트 — 큰 데이터셋 (1h)

### 목표
1000+ LOT, 10K+ 톤백 환경에서 응답 속도 / 메모리 검증.

### 진행 방법
1. 테스트 DB 생성 스크립트 작성:
   - `scripts/seed_load_test_db.py` — 1000 LOT × 10 sub_lt 자동 생성
2. API 응답 시간 측정:
   - `/api/inventory` (24열)
   - `/api/q/global-search`
   - `/api/action/integrity-report`
3. 결과 정리: `REPORTS/load_test.json`

### 임계값
- 모든 endpoint 응답 < 3초
- /api/q/global-search < 500ms

---

## Phase C: PyInstaller EXE 빌드 검증 (30분)

### 목표
`빌드.bat` 실행 → 실 EXE 동작 확인.

### 진행 방법
1. 빌드 스펙 확인:
   ```
   ls D:/program/SQM_inventory/Claude_SQM_v864_3/*.spec
   cat D:/program/SQM_inventory/Claude_SQM_v864_3/빌드.bat
   ```
2. 빌드 실행 (필요시 PYTHONIOENCODING):
   ```
   cd D:/program/SQM_inventory/Claude_SQM_v864_3 && cmd /c 빌드.bat
   ```
3. 빌드 산출물 확인:
   ```
   ls dist/
   ```
4. 결과 정리: `REPORTS/exe_build.json`

---

## Phase D: 사용자 매뉴얼 작성 (1h)

### 목표
v864-2 사용자가 v864-3 사용 시 학습할 새 기능 안내.

### 결과물
- `USER_MANUAL_v864_3.md` 신규
- 챕터:
  1. v864-2 와 동일한 점 (메뉴/워크플로우)
  2. 새로 추가된 기능 (전역 검색, AI 채팅, preview-edit-save)
  3. 단축키
  4. 트러블슈팅

---

## Phase E: 모든 작업 commit + push (5분)

```bash
cd D:/program/SQM_inventory/Claude_SQM_v864_3
git add -A
git commit -m "test+docs: Phase A-D 자율 검증 완료"
git push origin claude/v864-3-sprint0
```

---

## 🔄 자동 수정 루프 정책

각 Phase 에서:
- 실패 발견 → 즉시 fix 시도
- 최대 5회 재시도
- 5회 후에도 fail → `ISSUES_FOUND.md` 에 기록 후 다음 Phase 진행
- 모든 코드 수정은 git commit 으로 보존 (rollback 가능)

---

## 🛡️ 절대 하지 말 것

- ❌ `git reset --hard` (이전 작업 보호)
- ❌ `git push --force`
- ❌ `data/db/sqm_inventory.db` 삭제 (실 LOT 데이터)
- ❌ `data/proof_docs/` 삭제 (90일 보관 파일)
- ❌ `.env`, `settings.ini` 같은 비밀파일 commit
- ❌ v864-2 (`Claude_SQM_v864_2/`) 폴더 수정 — Golden Reference

---

## ✅ 완료 기준

모든 Phase 완료 시 다음 파일 생성:
- `REPORT_4TH_FINAL_VERIFICATION.md` — Phase A~E 종합 결과
- 모든 변경사항 GitHub push 완료
- `🎯 v864-3 운영 투입 최종 검증 완료` 문구

---

## 💡 진행 중 막히면

- v864-2 코드 참조: `D:/program/SQM_inventory/Claude_SQM_v864_2/`
- 기존 보고서 참조: `REPORT_1ST_PHASE`, `REPORT_2ND_AUDIT`, `REPORT_3RD_PLAYWRIGHT`
- 누적 핸드오프: `HANDOFF_SESSION_2026-04-25.md`
- 마스터 정리: `FINAL_PORTING_COMPLETE.md`

---

**남기동님, 다녀오세요. 작업 진행하다가 막히면 `ISSUES_FOUND.md` 에 기록 후 다음 단계 계속합니다.**
