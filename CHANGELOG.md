
## v3.6.8 (2025-02-05)

### 🐛 버그 수정
- crud_mixin.py: `remark` → `remarks` 컬럼명 오류 수정 (delete_inventory 실패 해결)
- logger.py: `_save_error_report()`에서 `logger` → `self.logger` 변경 (NameError 해결)

### ✅ 테스트 개선
- 전체 테스트: **1189 passed**, 87 skipped (0 failed)
- 핵심 모듈 커버리지: 64.2% → **76.1%** (+11.9%)
- test_v368_modules.py: 에러 복구, 성능 최적화 모듈 테스트 28개 추가
- test_coverage_boost_final.py: API 시그니처 수정, 57개 테스트 통과

### 📦 모듈 개선
- error_recovery.py: 별칭 추가 (DatabaseRecovery, retry, check_and_recover)
- performance.py: QueryCache stats property 검증
- 전체 테스트와 실제 API 간 일관성 확보

### 📊 점수 변화
- 테스트 커버리지: 80 → **84** (+4점)
- 예상 총점: 81 → **85/100점**

### 추가 개선 (1단계~3단계)

**1단계: 테스트 커버리지**
- 신규 테스트 파일: test_coverage_85_target.py, test_coverage_85_real.py
- 테스트 수: 1189 → **1308 passed** (+119)
- 핵심 모듈 커버리지: **75.7%**

**2단계: API 문서**
- Sphinx 빌드 완료 (docs/build/html)
- API_REFERENCE_V368.md 생성

**3단계: 배포 자동화**
- deploy.py: 원클릭 배포 스크립트
- sqm_inventory.spec: PyInstaller 설정

## v3.6.9 (2025-02-05)

### 데이터 보호 강화
- `delete_inventory()`: confirmed=True 필수
- `update_inventory()`: 중요 필드 수정 시 confirmed 필요
- `utils/data_protection.py`: 감사 로그, 권한 체크 모듈
- 테스트: 21개 데이터 보호 테스트 추가

### Type Hints 강화
- engine.py: get_connection(), close() 타입 추가
- logger.py: format(), _setup_logger() 타입 추가
- config_manager.py: 주요 메서드 타입 추가

### GUI 안정성
- `utils/gui_stability.py`: 예외 처리, 진행 추적, 입력 검증
- GUIExceptionHandler: 사용자 친화적 에러 메시지
- WorkProgress: 작업 진행 상태 추적
- InputValidator: 숫자/LOT 번호 검증
- 테스트: 18개 GUI 안정성 테스트 추가

### 버그 수정
- export_mixin.py: 깨진 docstring 수정

### 테스트
- 전체: 1421 passed, 138 skipped
- 커버리지: 76.4%
