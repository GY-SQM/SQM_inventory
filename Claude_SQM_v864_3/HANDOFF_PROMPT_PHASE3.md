# 🚀 Phase 3 새 세션 시작 — 복붙용 프롬프트

## 📋 사용법 (3단계)

1. **Claude 데스크톱 → "+ 새 채팅"**
2. **모델 선택 → "Claude Opus 4.6"**
3. **아래 파란 박스 내용을 첫 메시지에 그대로 복붙 → Enter**

---

## 🎯 [복붙용 프롬프트 — 여기부터]

```
나는 Nam Ki-dong 사장님이고, SQM v864.3 마이그레이션 프로젝트의 Phase 3 를 시작한다.
프로젝트 폴더: D:\program\SQM_inventory\Claude_SQM_v864_3

작업 착수 전에 다음 5개 파일을 순서대로 읽고 완전히 파악해줘:
1. CLAUDE.md (프로젝트 영구 메모리 + Phase 3 Next Target 섹션)
2. REPORTS/PHASE3_PLAN.md (Q1/Q2/Q3 상세 실행 계획 — 이번 세션의 마스터 지시서)
3. REPORTS/PHASE2_STEP3.md (직전 단계 종료 보고서 — 증거 확보)
4. frontend/index.html (UI 현 상태)
5. backend/main.py (라우터 등록 현 상태)

현재 상태 (2026-04-21 21:45 KST):
- Phase 2 Step 3 완전 종료: HTTP 200 전환, favicon 200, F039/F050 headless, CSS 수정
- 런타임 검증 완료: Network 13/13 요청 200, Console 빨간 에러 0건
- 🏆 Bonus: /health 응답으로 modules_loaded=8/8, engine_available=true 확인
- 다음 단계: Phase 3 Q1 (Dashboard KPI 실데이터) → Q2 (상태바 엔진 카운터) → Q3 (health guide)

Phase 3 실행 원칙:
- PHASE3_PLAN.md 의 SQL 쿼리/응답 스펙을 그대로 따를 것
- backend/legacy/* 수정 금지 (CLAUDE.md Rule 1)
- /api/dashboard/kpi 는 wrap_engine_call 로 래핑하여 NotReady/SQL 에러 모두 소프트 실패 처리
- 각 Q 완료 후 스모크 테스트 (curl 또는 TestClient) 결과를 보고

내 페르소나: Ruby (Senior Software Architect + PGA Tour Golfer).
응답 형식: [Question] [Intent] [Response], Deep-Dive 3 follow-ups with Best Practice first,
영어/베트남어 한 줄로 마무리. "The old situation was X, my current opinion is Y" 형식으로 의견 제시.
Professional Debugging Protocol 7섹션 + 3 Mandatory Checks 준수.

지금 Phase 3 Q1 부터 착수해줘.
```

## 🎯 [복붙용 프롬프트 — 여기까지]

---

## 📊 이전 세션에서 새 세션으로 넘어가는 컨텍스트 요약

**Phase 2 Step 3 최종 상태 (Ruby 가 넘겨주는 배턴):**

| 영역 | 상태 | 증거 파일 |
|---|---|---|
| HTTP 200 전환 | ✅ | `backend/common/errors.py` NotReadyError 재설계 |
| favicon 200 | ✅ | `frontend/favicon.ico` (1118 bytes ICO) |
| F039/F050 headless | ✅ | `backend/api/menubar.py` openpyxl 직접 생성 |
| CSS 파싱 버그 | ✅ | `frontend/css/v864-layout.css` `!important` 9곳 정정 |
| stylelint 도입 | ✅ | `frontend/.stylelintrc.json` + `package.json` |
| 모듈 로드 | ✅ 8/8 | `/health` Preview JSON |
| Console 에러 | ✅ 0건 | Network 13/13 요청 200 |

**남은 Phase 3 Q1-Q3:**
1. `GET /api/dashboard/kpi` 신설 + Dashboard 4카드 실데이터 (60분)
2. 상태바 `🟢 Engine 8/8` 상시 표시 (15분)
3. `docs/health_check_guide.md` 작성 (5분)

---

## 💡 Tips for 새 세션 Opus

1. **첫 5개 파일 Read 는 병렬로** — 시간 절약
2. **PHASE3_PLAN.md §1-B 의 SQL 4개 쿼리** 는 이미 검증 전제로 작성됨 → 그대로 사용
3. **wrap_engine_call 래퍼** 는 Phase 2 에서 검증됨 → 재사용
4. **스모크 테스트** 는 `python -c "from fastapi.testclient import TestClient; ..."` 한 줄로 가능

---

**작성**: Ruby (Senior Software Architect)
**일자**: 2026-04-21 21:45 KST
**다음 세션 기대 개시 시각**: 사장님 복붙 직후
