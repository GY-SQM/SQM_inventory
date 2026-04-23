# Phase 8 작업 지시서 — v864.3 공식 릴리스

> **목적**: SQM v864.2 → v864.3 공식 전환. GY Logis 광양창고 메인 시스템으로 승격.
> **예상 소요**: 1일
> **담당**: Claude Code (자동 실행) + 사장님 (최종 승인)
> **선행 조건**: Phase 7 완료 (GO 승인, tag `v864.3-phase7`)

---

## 🎯 Definition of Done (DoD)

- [ ] `CHANGELOG.md` 작성 (v864.2 → v864.3 주요 변경)
- [ ] `RELEASE_NOTES_v864.3.md` 작성 (사용자용 안내)
- [ ] GitHub Release 생성 (선택 — 사내 배포만 해도 무방)
- [ ] `dist/SQM_v864_3.exe` 최종 빌드 (Phase 7 핫픽스 반영)
- [ ] GY Logis 현장 PC 에 EXE 배포
- [ ] v864.2 EXE 백업 유지 (롤백 대비, 최소 30일)
- [ ] git 태그 `v864.3-RELEASE`

---

## 📋 작업 단계

### Step 1 — Phase 7 핫픽스 통합 (15분)

```bash
# Phase 7 기간 중 발생한 모든 핫픽스 태그 확인
git tag -l 'v864.3-day*-hotfix'
# 예: v864.3-day2-hotfix, v864.3-day5-hotfix

# 누적 변경 확인
git log v864.3-phase6..HEAD --oneline

# 최종 EXE 재빌드 (모든 핫픽스 포함)
python scripts/build_exe.py
```

**검증**:
```bash
python scripts/verify_endpoints.py  # 62개 PASS
python scripts/verify_exe.py         # EXE 실행 OK
```

---

### Step 2 — CHANGELOG.md 작성 (10분)

**파일**: `CHANGELOG.md` (프로젝트 루트)

```markdown
# Changelog

## [v864.3] — YYYY-MM-DD

### 🎉 Highlight
- **Tkinter → PyWebView 전환 완료**
- 12 개 핵심 기능 네이티브 구현 (입고-배정-출고 End-to-End)
- 정직한 NOT_READY 투명화 (44개 저순위 메뉴)
- 디버그 가시성 4-레이어 시스템

### ✨ Added
- F001 PDF 스캔 입고 (Packing List 자동 파싱)
- F002 수동 입고 (Excel 드래그앤드롭)
- F003 D/O 후속 연결 (필드 업데이트 폼)
- F004 톤백 위치 매핑 (Excel 업로드)
- F007 반품 입고 (Excel, 트랜잭션 롤백)
- F014 Allocation 입력 (Excel)
- F015 즉시 출고 (LOT + 수량 + 고객 폼)
- F016 빠른 출고 (텍스트 붙여넣기 다중 LOT)
- F017 Picking List PDF 업로드
- F022 Allocation 승인분 반영
- F028 출고 확정 (PICKED → OUTBOUND)
- 전역 예외 훅 + JS 에러 브리지
- uvicorn debug log + access_log

### 🔧 Changed
- tkinter filedialog → HTML `<input type="file">` + multipart
- 44 개 POST 메뉴의 가짜 성공 토스트 → 명시적 NOT_READY 안내
- FastAPI 에러 응답 포맷 표준화 (`ok, data, error, detail, message`)
- sqm-inline.js 버전: 864.3.12 → 864.3.19+

### 🐛 Fixed
- 메뉴 클릭 시 백그라운드 tkinter 핸들러 무반응 → 명시적 UI 피드백
- API 서버 스레드 에러 은폐 → 전역 excepthook 으로 포획
- PyWebView devtools 기본 활성화 (F12 가능)

### 🚨 Breaking Changes
- 일부 tkinter 전용 핸들러는 NOT_READY 로 유지 (Phase 4-B 이후 순차 구현 예정)

### 📦 Deployment
- 단일 실행 파일: `dist/SQM_v864_3.exe` (약 120 MB)
- 요구 사항: Windows 10 이상, 메모리 4GB 이상
- DB: SQLite (data/db/sqm_inventory.db, 자동 생성)

### 🔄 Migration from v864.2
- DB 스키마 자동 마이그레이션 (엔진 기동 시)
- 기존 데이터 100% 호환
- 롤백: v864.2 EXE 로 복귀 가능 (24시간 병행 운영 권장)

---

## [v864.2] — 이전 버전
- Tkinter 기반 (레거시)
```

---

### Step 3 — RELEASE_NOTES 작성 (사용자용, 10분)

**파일**: `RELEASE_NOTES_v864.3.md`

```markdown
# SQM Inventory v864.3 — Release Notes

**릴리스 일자**: YYYY-MM-DD
**대상**: GY Logis 광양창고 사용자

## 🎉 주요 변경점

### 1. 최신 웹 기반 UI
기존 창(Tkinter) → 현대적인 웹뷰(PyWebView) 로 전환했습니다.
- 더 빠른 반응 속도
- 드래그 앤 드롭 파일 업로드
- 실시간 로그/디버그 패널 (F8)

### 2. 매일 업무 핵심 12개 기능 완성
- 📄 PDF 스캔 입고 (컨테이너 도착)
- 📊 수동 Excel 입고
- 📋 D/O 정보 업데이트
- 📍 톤백 위치 지정
- 🔄 반품 입고
- 📋 Allocation 예약
- 🚀 즉시 출고 / 빠른 출고 / 출고 확정
- 📋 Picking List PDF
- ✅ 정합성 검사
- 💾 백업 생성

### 3. 에러가 숨겨지지 않음
- 모든 에러가 `sqm_debug.log` 에 자동 기록
- 실패 시 정직한 "준비 중" 메시지 (가짜 성공 제거)

## 🛡 안전성
- 출고 확정 전 대상 톤백 미리보기
- 전체 확정 시 `force_all` 명시 필요 (실수 차단)
- 모든 트랜잭션 All-or-Nothing (실패 시 자동 롤백)

## 🚀 설치 방법

### 새 설치
1. `SQM_v864_3.exe` 를 바탕화면에 복사
2. 더블클릭 실행
3. Windows Defender 경고 시 "실행" 클릭

### v864.2 에서 업그레이드
1. v864.2 종료
2. 기존 데이터 자동 인식 (같은 폴더의 data/db/ 사용)
3. `SQM_v864_3.exe` 실행

## 🆘 문제 발생 시
1. `sqm_debug.log` 파일 확인 (EXE 옆)
2. 창 내부 우클릭 → "검사" → Console 탭
3. 사장님(Nam Ki-dong) 에게 로그 파일 전달

## 📅 향후 계획
- 남은 73개 메뉴 기능 순차 추가 (필요 우선순위 기준)
- 리포트 엔진 개선
- 모바일 앱 (iOS/Android) 연동 검토
```

---

### Step 4 — GitHub Release (선택, 10분)

사내 배포만 할 경우 생략 가능. 버전 관리용으로 권장.

```bash
# GitHub CLI 사용 (선택)
gh release create v864.3-RELEASE \
  dist/SQM_v864_3.exe \
  --title "SQM v864.3 — Web Edition" \
  --notes-file RELEASE_NOTES_v864.3.md

# 또는 수동: github.com/<owner>/<repo>/releases/new
# - Tag: v864.3-RELEASE
# - Title: SQM v864.3 — Web Edition
# - Body: RELEASE_NOTES_v864.3.md 내용 복사
# - Attach: dist/SQM_v864_3.exe
```

---

### Step 5 — 현장 배포 (20분)

**배포 전 체크리스트**:
- [ ] 현재 v864.2 EXE 백업 보관 (`\\gy-logis\backup\v864_2_backup_YYYYMMDD\`)
- [ ] 사장님 외 현장 사용자에게 공지 (있을 시)
- [ ] 공지 문서 출력해서 벽에 부착 (선택)

**배포 명령**:
```bash
# 광양 PC(네트워크 공유 경로로 가정):
copy dist\SQM_v864_3.exe \\gy-logis\apps\SQM_v864_3.exe
# 또는 USB 로 직접 복사
```

**초기 검증** (현장 PC 에서):
1. SQM_v864_3.exe 실행
2. 기존 재고 데이터 조회 (Inventory 탭)
3. 간단한 수동 입고 1건 테스트
4. 로그 파일 생성 확인

---

### Step 6 — 롤백 계획 (24시간 병행)

**24시간 규칙**:
- v864.3 공식 전환 후 **24시간** 은 v864.2 도 실행 가능 상태 유지
- Critical 버그 발견 시 즉시 v864.2 로 복귀
- 24시간 후 Critical 없으면 v864.2 제거 (백업만 유지)

**롤백 명령** (긴급 시):
```bash
# 현장 PC
taskkill /F /IM SQM_v864_3.exe
# v864.2 EXE 실행
\\gy-logis\backup\v864_2_backup_YYYYMMDD\SQM_v864_2.exe
```

---

### Step 7 — 최종 커밋 + 태그 (5분)

```bash
git add CHANGELOG.md RELEASE_NOTES_v864.3.md REPORTS/PHASE8_COMPLETE.md
git commit -m "$(cat <<'EOF'
release(v864.3): 🏆 공식 릴리스 — v864.2 → v864.3 전환 완료

[주요 변경]
- Tkinter → PyWebView 전환 (웹 기반 UI)
- 12개 핵심 기능 네이티브 (F001/F002/F003/F004/F007/F013/F014/F015/F016/F017/F022/F028)
- 정직한 NOT_READY 투명화 (44개 저순위 메뉴)
- 디버그 가시성 4-레이어 (전역 훅 + 파일 로거 + uvicorn debug + JS 에러 브리지)

[산출물]
- dist/SQM_v864_3.exe (~120 MB, Windows 10+)
- CHANGELOG.md + RELEASE_NOTES_v864.3.md

[배포]
- GY Logis 광양창고 메인 시스템 전환 완료
- v864.2 EXE 백업 유지 (24h 병행 + 30일 보관)

누적 세션 (Phase 0 → 8):
- Phase 0-3: 안전망 + UI Manifest + TOP3 엔드포인트 + Dashboard KPI
- Phase 4-B: 12개 기능 네이티브 실구현 (입출고 End-to-End)
- Phase 5: 회귀 테스트 62 PASS
- Phase 6: PyInstaller EXE 빌드
- Phase 7: 7일 실사용 + 핫픽스
- Phase 8: 공식 릴리스 (본 커밋)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"

git tag v864.3-RELEASE -m "SQM Inventory v864.3 — Web Edition 공식 릴리스"

# GitHub 등 리모트 푸시 (사장님 선택)
# git push origin main --tags
```

---

### Step 8 — PHASE8_COMPLETE.md 최종 보고서

**파일**: `REPORTS/PHASE8_COMPLETE.md`

```markdown
# SQM v864.3 — Phase 8 RELEASE Report 🏆
**Date**: YYYY-MM-DD
**Status**: ✅ 공식 릴리스 완료

## 최종 성과
- 버전: v864.2 (tkinter) → **v864.3 (PyWebView)**
- 실구현 기능: 12개 (일일 운영 Top 10 포함)
- 투명 NOT_READY: 44개
- 전체 엔드포인트: 62+ (50 기존 + 12 신규)

## 산출물
- dist/SQM_v864_3.exe (XXX MB)
- CHANGELOG.md / RELEASE_NOTES_v864.3.md
- 8 Phase 전체 리포트 (REPORTS/PHASE0 ~ PHASE8)

## 타임라인
- Phase 0-3: YYYY-MM-DD ~ YYYY-MM-DD (기반 구축)
- Phase 4-B: YYYY-MM-DD ~ YYYY-MM-DD (기능 구현)
- Phase 5-6: YYYY-MM-DD (테스트 + 빌드)
- Phase 7: YYYY-MM-DD ~ YYYY-MM-DD (실사용)
- Phase 8: YYYY-MM-DD (릴리스)

## 핵심 교훈
1. 리포트 "완료" ≠ 실제 작동 — 실사용 검증이 핵심
2. 정직한 NOT_READY 가 거짓 성공보다 유용
3. 디버그 가시성은 초반에 설치해야 나중 수 십배 절약
4. 패턴 1개 완성 → 복제가 가장 빠른 확장
5. 사장님(실사용자) 주도 Phase 7 이 진짜 QA

## 사장님 메시지
감사합니다. 🏌️ "Ruby 스타일로, 현장에서 쓸 수 있는 시스템."
```

---

## ✅ Phase 8 완료 확인

```
✅ CHANGELOG.md
✅ RELEASE_NOTES_v864.3.md
✅ dist/SQM_v864_3.exe (최신)
✅ GitHub Release (선택)
✅ 현장 배포
✅ v864.2 백업 유지
✅ git tag v864.3-RELEASE
```

**🎉 프로젝트 완료!** v864.3 Web Edition 이 GY Logis 광양창고 메인 시스템으로 공식 전환되었습니다.

---

## 📅 Post-Release (릴리스 이후)

1. **Day +1~7**: 일일 모니터링 (sqm_debug.log 스폿 체크)
2. **Day +30**: v864.2 백업 최종 정리 (보관만)
3. **Month +1**: Phase 4-B 잔여 기능 필요 시 추가 (F005/F008/F011 등)
4. **Month +3**: 회고 + 다음 메이저 버전 (v865 또는 이름 변경) 계획
