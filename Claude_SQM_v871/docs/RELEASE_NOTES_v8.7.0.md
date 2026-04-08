# SQM v8.7.0 Release Notes

**릴리즈 날짜:** 2026-04-07  
**커밋:** `3f69935`  
**브랜치:** main  

---

## 개요

SQM 재고관리 시스템 v8.7.0 — **React 웹 UI Phase1 완성** 릴리즈.  
기존 PyQt 데스크톱 앱과 병행하여, 웹 브라우저에서 전체 재고/입출고 관리가 가능한 React + FastAPI 기반 웹 시스템 완성.

---

## 주요 변경사항

### NEW — React 웹 프론트엔드 (v871)

| 항목 | 수량 |
|------|------|
| 페이지 | 23개 |
| 컴포넌트 | 11개 |
| API 모듈 | 8개 |

- **대시보드**: 상태 요약 바, 제품별 통계, 자동 새로고침(30초)
- **재고 조회**: 필터, 검색, LOT 상세 모달
- **톤백 관리**: 톤백 단위 추적
- **판매 배정(Allocation)**: 입력 모달, 배정 관리
- **화물 결정(Picked)**: 출고 준비 화물 관리
- **출고**: 즉시 출고(원스톱), 출고 이력
- **반품**: 단건/엑셀 반품, 이력 조회
- **이동**: 위치 변경
- **스캔**: 바코드 스캔 처리
- **총괄 재고(Cargo Overview)**: 제품별 전체 현황
- **보고서/로그/설정/도움말**: 운영 관리

### NEW — FastAPI 백엔드 (v871)

- **18개 라우터**: dashboard, inventory, tabs, inbound, outbound_write, location, files, search, advanced, ai_dashboard, return_tab, return_write, do_update, location_bulk, tools, reports, products, approval, ai_chat, templates
- **보안 미들웨어**: Rate Limit (IP당 분당 120회), 쓰기 API 토큰 검증, 요청 크기 제한(100MB)
- **CORS**: localhost + LAN IP 자동 감지
- **서버 시작 시 엔진 1회 초기화** (P1 성능 개선)

### NEW — 통합 실행 시스템

- `run_react_network.bat`: 백엔드(8000) + 프론트엔드(5173) 동시 기동
- 자동 포트 정리, LAN IP 감지, 브라우저 자동 열기
- PC + 핸드폰(같은 네트워크) 동시 접속 지원

### ENHANCED — v868 보강

- PDCA 상태 관리 대폭 갱신
- Telegram Bridge 강화 (자동 보고, 오류 알림)
- React API 쓰기 엔드포인트 보강
- 통합 완성본 문서 갱신

### FIX — v8.7.0 버그 수정

- `client.js` fetchJson export 누락 → 화이트 스크린 수정
- `App.jsx` useContext 순환 참조 제거
- `react_api/main.py` os import + uvicorn 진입점 수정
- `MenuBar.jsx` div 닫기 태그 수정

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Frontend | React 19, Vite 8, React Router 7 |
| Backend | Python 3.10+, FastAPI, Uvicorn |
| Database | SQLite (WAL 모드) |
| 통신 | Telegram Bot API |
| 인프라 | Windows 데스크톱, LAN 네트워크 |

---

## 파일 통계

- **변경 파일**: 1,517개
- **추가 라인**: 447,031줄
- **삭제 라인**: 1,924줄

---

## 업그레이드 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt
cd web && npm install && cd ..

# 2. 실행
run_react_network.bat
```

---

## 알려진 이슈

- React 웹 UI 첫 로드 시 브라우저 캐시로 인한 빈 페이지 가능 → Ctrl+Shift+R로 해결
- `.env` 파일이 없으면 기본값으로 동작 (ADMIN_TOKEN 비활성)

---

*SQM 재고관리 시스템 — (주) 지와이로지스 2026*
