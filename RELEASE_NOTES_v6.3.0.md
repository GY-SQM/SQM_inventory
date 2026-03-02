# SQM v6.3.0 릴리즈 노트
**릴리즈 날짜: 2026-03-02**

## 🧹 코드 품질 대청소 + 기능 강화

v6.2.5 → v6.3.0 (Stage 1~8 통합)

---

### 핵심 수치

| 항목 | Before | After | 변화 |
|------|--------|-------|------|
| 테스트 | 181건 | 493건 | +312건 |
| outbound 커버리지 | 24.3% | 80.1% | +55.8%p |
| 데드코드 | ~4,648줄 | 0줄 | -4,648줄 |
| pyflakes 경고 | 18건 | 3건 | -15건 |
| bare except | 40건+ | 0건 | 전량 제거 |

---

### 1. 데드코드 삭제 (4,648줄)

- **데드 함수 52개 삭제**: 엔진 4개 + GUI 48개
- **데드 파일 5개 삭제**: inbound_handlers(978줄), help_dialogs(718줄), inbound_preview_dialog(221줄), query_cache(139줄), barcode_label_generator(93줄)
- **미사용 import 10건, 변수 3건, f-string 8건** 정리

### 2. 보안 & 안정성

- **SQL 화이트리스트**: `_insert_lot()` 허용 컬럼 26개 명시, 임의 키 INSERT 차단
- **Python 3.12 호환**: sqlite3 date/datetime 어댑터 명시 등록 (DeprecationWarning 해소)

### 3. 제품 마스터 시스템

- **8종 기본 제품 내장**: LCA, MIC9000, MIC5000, HCA, LiOH, KHSO4, K2SO4, Li2SO4
- **입고 자동감지**: PDF 파싱 시 제품명 → product_code 자동 매칭
- **출고 탭 필터**: 제품별 필터 콤보박스 추가
- **제품별 재고 리포트**: 도구 메뉴 > 📊 제품별 재고 현황

### 4. CI/CD

- **GitHub Actions**: push/PR 시 Python 3.10/3.11/3.12 매트릭스 테스트
- **커버리지 게이트**: 70% 미만 → 빌드 실패
- **로컬 CI 스크립트**: `./run_tests.sh` (quick/coverage/module/full 모드)

### 5. 테스트 확장 (+312건)

- P0 안전성 3건, P1 방어 4건, 잘못된 데이터 방어 48건
- 파서 방어 42건, 부하 10건, outbound 커버리지 46건
- 제품 마스터 18건, outbound 확장 44건 (confirm/gate1/quick/cancel/revert)

---

### 적용 방법

1. `patched_files/` 전체를 프로젝트 루트에 덮어쓰기
2. 아래 파일 삭제 (데드코드):
   - `gui_app_modular/handlers/inbound_handlers.py`
   - `gui_app_modular/dialogs/help_dialogs.py`
   - `gui_app_modular/dialogs/inbound_preview_dialog.py`
   - `engine_modules/query_cache.py`
   - `core/barcode_label_generator.py`
3. `python -m pytest tests/` 로 검증 (493 passed 확인)

---

### 안정성 검증

```
493 passed, 4 skipped, 2 xfailed — 0 failed
pyflakes 잔여: 3건 (의도적 관례)
outbound_mixin 커버리지: 80.1%
```
