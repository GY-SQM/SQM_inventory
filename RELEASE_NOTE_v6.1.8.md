# 🚀 v6.1.8: SQM Inventory System (Clean Build)

> **"가볍고 강력해진 SQM 시스템의 새로운 시작"**

이번 릴리즈는 시스템의 **경량화(Clean Build)**와 대량 출고 처리를 위한 **Fast Out 엔진** 탑재에 중점을 두었습니다. 불필요한 레거시 데이터와 백업 파일을 제거하여 저장소 크기를 최적화했습니다.

---

## ✨ 주요 변경 사항 (Highlights)

### 1. 🧹 Clean Build & Repository Optimization
- **저장소 최적화**: `SQM_v701_FULL-1`, `BACKUP`, `LEGACY` 등 개발 과정에서 생성된 중복/임시 폴더를 제거하고 `.gitignore`를 통해 영구 제외 처리했습니다.
- **필수 파일 선별**: 프로그램 구동에 필수적인 `engine_modules`, `gui_app_modular`, `core` 등 핵심 모듈만 포함하여 배포 용량을 획기적으로 줄였습니다.

### 2. ⚡ Fast Out (빠른 출고) 엔진 탑재
- **대량 처리**: 수백 개의 스캔 데이터를 일괄 처리할 수 있는 `FastOutService`가 도입되었습니다.
- **Batch Processing**: 스캔 데이터 업로드 시 별도의 `scan_batch_id`를 발급하여 트랜잭션 단위로 관리합니다.
- **Direct Sold**: 복잡한 예약(Allocation) 절차 없이 즉시 확정(SOLD) 처리 가능한 패스트 트랙을 지원합니다.

### 3. 🛡️ 보안 및 무결성 강화
- **PBKDF2 Hashing**: 관리자 비밀번호 등 민감 정보에 대한 암호화 방식을 강화했습니다.
- **Integrity Center**: 데이터 정합성을 실시간으로 모니터링하고 진단하는 모듈이 통합되었습니다.

---

## 🛠️ 기술적 변경 사항 (Technical Details)

- **Database**: `proof_document`, `scan_batch_registry` 등 Fast Out 관련 신규 테이블 9종 추가.
- **Modules**:
    - `engine_modules/services/fast_out_service.py`: 독립적인 출고 서비스 로직.
    - `features/parsers/qr_decoder.py`: 고성능 QR 코드 파싱 모듈.
- **Configuration**: `.gitignore` 업데이트를 통한 자동 백업/로그 파일 추적 방지.

---

## 📦 설치 및 실행 방법

1. **Clone**: `git clone https://github.com/kidongnam1/SQM_inventory.git`
2. **Dependency**: `pip install -r requirements.txt`
3. **Run**: `python run.py`

---

*Release created by SQM AI Assistant*
