# SQM v864.3 — 엔진 건강성 확인 가이드

> **작성**: Ruby (Senior Software Architect)  
> **일자**: 2026-04-21  
> **대상**: Nam Ki-dong 사장님 (비개발자도 읽을 수 있게 작성)

---

## 🩺 /api/health 란?

`/api/health` 는 SQM v864.3 의 "진단 엔드포인트"입니다.  
병원에서 혈압·맥박 체크하는 것처럼, 서버가 정상 작동 중인지 1초 안에 확인합니다.

브라우저 주소창에 `http://127.0.0.1:8765/api/health` 입력 → Enter 하면 즉시 결과 확인.

---

## 📊 응답 필드 해석표 (6개)

| 필드 | 타입 | 정상값 | 의미 |
|------|------|--------|------|
| `status` | string | `"ok"` | 서버 전체 상태. `"ok"` 가 아니면 재시작 필요 |
| `engine` | bool | `true` | v864.2 엔진 로드 성공 여부 (legacy 호환 필드) |
| `engine_available` | bool | `true` | 엔진 사용 가능 여부 (sqm-inline.js 기준 필드) |
| `modules_loaded` | int | `8` | 로드 성공한 모듈 수. 8이면 전부 정상 |
| `modules_total` | int | `8` | 전체 모듈 수 (v864.3 기준 고정값 8) |
| `version` | string | `"8.6.4"` | 현재 실행 중인 버전 |

---

## ✅ 정상 응답 예시

```json
{
  "status": "ok",
  "engine": true,
  "engine_available": true,
  "modules_loaded": 8,
  "modules_total": 8,
  "version": "8.6.4"
}
```

상태바에는 `🟢 Engine 8/8` 로 표시됩니다.

---

## ⚠️ 이상 응답 예시 및 대처법

### 엔진 로드 실패 시

```json
{
  "status": "ok",
  "engine": false,
  "engine_available": false,
  "modules_loaded": 0,
  "modules_total": 8,
  "version": "8.6.4"
}
```

상태바: `🔴 Engine 0/8`

**대처법:**
1. `실행.bat` 로 재시작
2. `logs/` 폴더의 최신 로그 파일 열어서 "Engine load failed" 라인 확인
3. 해결 안 되면 → Ruby 에게 로그 공유

---

## 🕐 언제 확인하나?

| 상황 | 확인 시점 |
|------|-----------|
| 프로그램 시작 후 | 상태바 `🟢 Engine 8/8` 확인 (자동 표시됨) |
| 기능 클릭 시 오류 발생 | 가장 먼저 `/api/health` 응답 확인 |
| 느리거나 응답 없을 때 | `engine_available: false` 인지 체크 |
| 에러 리포트 시 | 이 화면 스크린샷 1장 첨부 |

---

## 🔧 빠른 진단 체크리스트

```
[ ] 브라우저에서 http://127.0.0.1:8765/api/health 열림?
    → NO → 실행.bat 재시작 필요

[ ] status: "ok" ?
    → NO → 서버 오류, 로그 확인

[ ] engine_available: true ?
    → NO → 엔진 로드 실패, 로그에서 "Engine load failed" 검색

[ ] modules_loaded == modules_total ?
    → NO → 일부 모듈 손상, Ruby 에게 보고
```

---

**버전**: v864.3 · **Phase 3 Q3 산출물** · **작성**: Ruby
