# CSS 린터 설치/실행 가이드 (stylelint)

> **목적**: `\!important` 같은 silent parse failure 를 자동 검출.
> **도입 배경**: 2026-04-21 Phase 2 Step 3 에서 HARDEN 블록 9곳이 silent drop 되던 사건.

---

## 🎯 1회 설치 (사장님 1회만 실행)

```cmd
cd D:\program\SQM_inventory\Claude_SQM_v864_3\frontend
npm install
```

설치되는 패키지 (devDependencies):
- `stylelint` (^16.2.1) — 린터 본체
- `stylelint-config-standard` (^36.0.0) — 표준 룰셋

약 60MB, 30초 이내 완료.

---

## ▶️ 실행 (언제든)

```cmd
cd D:\program\SQM_inventory\Claude_SQM_v864_3\frontend
npm run lint:css
```

에러가 있으면 파일명 + 라인 번호 + 룰 이름 형식으로 출력:

```
css/v864-layout.css
 416:15  ✖  Unknown word       no-invalid-double-slash-comments
```

---

## 🔧 자동 수정 (가능한 것만)

```cmd
npm run lint:css:fix
```

수정 가능한 것: 들여쓰기, 공백, 세미콜론 누락 등.
수정 불가능한 것: `\!important`, 잘못된 속성명 등 → 사람이 직접 수정.

---

## 📋 활성화된 주요 룰

| 룰 | 목적 | Phase 2 Step 3 사건 방지? |
|---|---|---|
| `no-invalid-double-slash-comments` | `//` 를 CSS 주석으로 오인 방지 | 보조 |
| `declaration-property-value-no-unknown` | `\!important` 같은 잘못된 값 검출 | ✅ |
| `property-no-unknown` | 오타난 CSS 속성 검출 | ✅ |
| `unit-no-unknown` | 잘못된 단위 검출 | ✅ |
| `at-rule-no-unknown` | 잘못된 `@` 지시자 검출 | ✅ |
| `no-duplicate-selectors` | 실수로 같은 셀렉터 중복 | 보조 |
| `block-no-empty` | 빈 `{}` 블록 방지 | 보조 |

---

## ⚠️ Node.js 필요

stylelint 는 Node.js 환경에서 실행됩니다. 설치 안 되어 있다면:
- https://nodejs.org/ → LTS 버전 설치
- CMD 재시작 후 `node -v` 확인

---

## 💡 Pre-commit hook (선택사항)

git commit 시 자동 검사하고 싶으면 `.git/hooks/pre-commit` 파일 생성:

```bash
#!/bin/sh
cd frontend && npm run lint:css
```

실행 권한 부여 (Windows Git Bash):
```bash
chmod +x .git/hooks/pre-commit
```

---

**작성**: Ruby (Senior Software Architect)
**일자**: 2026-04-21 21:13 KST
**관련 사건**: `REPORTS/PHASE2_STEP3.md` §7 Prevention Plan
