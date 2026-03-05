## 🚀 Release Notes: SQM Inventory System v6.1.8

**"Clean Build & Feature Integration Release"**

이 릴리즈는 기존의 복잡한 개발 폴더 구조를 정리하고, 최신 기능 패치(v7.0.1 Patch Set)를 완전히 통합하여 단일 실행 환경으로 구축한 버전입니다. 
FastOut(대량 출고), 바코드 스캔, API 서버, 무결성 검증, 반품 관리 등 핵심 기능이 모두 포함되었습니다.

---

### 🌟 주요 변경 사항 (Highlights)

#### 1. FastOut (대량 출고) 엔진 탑재
- **독립 서비스 아키텍처**: 기존 UI와 충돌 없이 독립적으로 작동하는 `FastOutService` 도입
- **배치 처리(Batch Processing)**: 수천 건의 출고 데이터를 단일 트랜잭션으로 안전하게 처리
- **스캔 데이터 업로드**: 엑셀/이미지 기반의 QR/바코드 데이터를 일괄 업로드 및 프리뷰 제공

#### 2. 현장 바코드 스캔 검증 (Gate-1 & Barcode Scan)
- **Gate-1 교차 검증**: Picking List의 LOT와 수량을 Allocation Plan(예약)과 엄격하게 대조
- **현장 스캔 Hard Stop**: `PICKED` 상태의 톤백과 현장 스캔 UID를 대조하여, 누락/오류 발생 시 출고 절대 불가 (Hard Stop)
- **바코드 라벨 생성**: A6 사이즈의 현장 부착용 바코드 라벨 PDF 생성 기능 추가

#### 3. API 서버 및 보안 강화
- **FastAPI 기반 API 서버**: 외부 시스템 연동을 위한 RESTful API 서버 탑재 (`/api`)
- **보안 인증**: JWT 기반 인증, RBAC(역할 기반 접근 제어), PBKDF2 비밀번호 해싱 적용
- **실시간 알림**: WebSocket을 통한 실시간 재고 변동 알림 지원

#### 4. 데이터 무결성 및 AI 파싱 (Integrity & AI)
- **Integrity Center**: 500kg/1000kg 단위 무게 검증, 샘플 톤백 정책, LOT 무결성 자동 진단 리포트
- **Gemini AI Parser**: 구글 Gemini AI를 활용한 인보이스/패킹리스트 자동 파싱 (유럽식 숫자 포맷 완벽 지원)

#### 5. 반품 관리 고도화 (Return Management)
- **반품 통계 및 리포트**: 기간별/LOT별 반품 현황 통계 및 PDF 리포트 생성
- **상태 동기화**: 반품 시 `allocation_plan`, `picking_table`, `sold_table` 간의 상태 자동 동기화

---

### 🛠 기술적 변경 사항 (Technical Details)

- **Clean Build**: 불필요한 레거시/백업/Git 파일 제거 및 최적화된 폴더 구조 적용
- **DB Schema**: `proof_document`, `scan_batch_registry`, `ship_batch`, `app_config`, `uid_verify_history` 등 신규 테이블 추가
- **Config**: KST 시간대 표준화, 비밀번호 암호화 강화
- **Refactoring**: `engine_modules` 내 기능별 Mixin 분리 및 모듈화 강화

---

### 📦 설치 및 실행 방법

1. **사전 요구 사항**: Python 3.10+, SQLite3
2. **라이브러리 설치**: `pip install -r requirements.txt` (필요 시)
3. **DB 초기화**: 최초 실행 시 자동으로 DB 및 테이블 생성/마이그레이션 수행
4. **실행**: `python run.py`

---

**Commit**: `Clean build with v7.0.1 patches applied (FastOut, Barcode, API, Integrity)`
**Date**: 2026-02-26
