# v864_1 자체 검증 리포트 (Track C Self-Verify)

작성 시작: 2026-04-19
작성자: Ruby (자기주도 검증 모드)
원칙: 확실한 것만 코드 반영, 불확실·애매한 것은 이 문서에 기록 → 추후 사용자 검토

---

## Round 1 — Phase 3-B 대칭 완성 + 기존 작업 자체 검증

### 1-1. 실행 항목 (코드 반영 완료)

- ✅ **Phase 3-B 완성**: `document_bl`(36컬럼), `document_pl`(22컬럼), `document_do`(30컬럼) 테이블 신설
  - `_migrate_v870_document_bl/pl/do` 마이그레이션 3건 추가
  - `_insert_document_bl/pl/do` 엔진 메서드 3개 추가 (`inbound_mixin.py` L984, L1093, L1192)
  - `process_inbound`에서 호출 추가 (L346~348)
  - GUI 파이프라인 확장: `bl_dict`에 22필드, `do_dict`에 17필드 추가

- ✅ **Chunk A (점수 로직 제거) 자체 검증**:
  - `bl_mixin._detect_carrier_from_words`: explicit 없으면 "" 반환 — 확인 완료
  - `multi_template_registry.guess_carrier`: 항상 None 반환 — 확인 완료
  - `onestop_inbound._start_parsing`: 선사 미선택 시 경고 다이얼로그 후 차단 — 확인 완료

- ✅ **Chunk B (YAML 플러그인) 자체 검증**:
  - `features/ai/carrier_profiles/` 디렉터리 및 4개 YAML(msc/maersk/hmm/zim) 생성 확인
  - `carrier_profile_loader.py`: pyyaml ImportError graceful fallback 확인
  - `bl_carrier_registry.py` 끝의 merge 블록: 3중 예외 방벽 확인

- ✅ **Chunk C-1 (document_invoice) 자체 검증**:
  - 33컬럼 테이블 생성, `_insert_document_invoice` 메서드 `inbound_mixin.py` 내부 확인
  - `process_inbound`에서 호출 연결됨
  - `inv_dict`에 customer_*/product_*/quantity_mt/payment_term/incoterm 확장 확인

### 1-2. 불확실 / 애매 사항 (코드 확정 보류 — 사용자 리뷰 필요)

#### U-1. PackingListData.lots[] 저장 방식 ✅ 결정 완료 (2026-04-19)
- **결정**: (b) **`document_pl.lots_json` TEXT 컬럼 추가** — JSON 직렬화로 lots[] 통째 보존
- **수정 파일**:
  - `engine_modules/db_migration_mixin.py:_migrate_v870_document_pl` — CREATE TABLE에 `lots_json` 추가 + ALTER TABLE ADD COLUMN(기존 DB 호환)
  - `engine_modules/db_schema_mixin.py` — 신규 설치 DDL에 `lots_json TEXT DEFAULT ''` 추가
  - `engine_modules/inventory_modular/inbound_mixin.py:_insert_document_pl` — `_serialize_lots()` 헬퍼 + INSERT에 lots_json 바인딩
  - `gui_app_modular/dialogs/inbound_upload_mixin.py` — `packing_dict['_pl_lots_raw']`로 `pl.lots` 전달
- **직렬화 규칙**:
  - LOTInfo dataclass → `asdict()` → JSON
  - dict는 그대로
  - date/datetime은 `isoformat()` 문자열로
  - 직렬화 실패 시 빈 문자열 저장(본 입고 블로킹 금지)
- **주석 태그**: `v8.7.0 [U-1 b]`
- **향후 승격 경로**: JSON 쿼리 빈도 높아지면 `document_pl_lot` 자식테이블로 전환 가능 (JSON → 행 변환 스크립트 간단)

#### U-2. BLData.containers[] / freight_charges[] 보존 방식 ✅ 결정 완료 (2026-04-19)
- **결정**: (c) **현재 상태 유지** — BL containers는 DO container_info와 중복 실물, freight_charges는 별도 요구 발생 시 재검토
- **코드 변경 없음**
- **참고**: `document_bl` 헤더 테이블만 저장, 상세 컨테이너 리스트는 `container_info`(DO 기반)로 커버

#### U-3. InvoiceData.package_type 필드 inv_dict 미전달 ✅ 결정 완료 (2026-04-19)
- **결정**: **패치 반영** — `inbound_upload_mixin.py`의 `inv_dict` 생성부에 1줄 추가
- **코드 위치**: `gui_app_modular/dialogs/inbound_upload_mixin.py:426` (inv_dict 끝)
- **주석 태그**: `v8.7.0 [FIX U-3]`
- **효과**: document_invoice.package_type 컬럼에 실제 파싱값 저장됨 (기존엔 항상 빈값)

#### U-4. carrier_profile YAML 로더 캐시 ✅ 결정 완료 (2026-04-19)
- **결정**: **현상 유지** — 선사 추가 = 계획적 재시작 허용 시나리오
- **코드 변경 없음**

---

## Round 2 — v864 메뉴 전수검사 + CRITICAL 패치

### 2-1. 메뉴 감사 결과 (`docs/menu_audit_v864.md` 545줄)

- 전체 메뉴 **약 115개** 분석
- 끊어진 링크 **3건 (CRITICAL)**
- 경고 **14건 (WARNING)**

### 2-2. CRITICAL 조치 완료

#### CRIT-1 ✅ FIXED — 클래스 메서드가 `if __name__ == '__main__':` 블록 안에 들여쓰기 되어 있어 dead code
- **영향 메뉴**: 🔧 도구 > 제품 마스터 관리, 제품별 재고 리포트, 수동 DB 마이그레이션
- **수정 파일**: `gui_app_modular/main_app.py`
- **수정 내용**: 4개 메서드(`_on_run_v530_migration`, `_read_ui_settings`, `_show_product_inventory_report`, `_show_product_master`)를 클래스 `SQMInventoryAppFull` 내부로 이동. `main()`과 `if __name__` 블록은 모듈 최하단에 정리.
- **주석 태그**: `v8.7.0 [FIX CRIT-1]`

#### CRIT-2 ✅ FIXED — Action Bar 라벨-핸들러 불일치
- **영향**: `💾 백업` 버튼, `⚙️ 설정` 버튼 클릭 무반응
- **수정 파일**: `gui_app_modular/mixins/toolbar_mixin.py:204-205`
- **수정 내용**:
  - `_on_backup_db` → `_on_backup_click` (backup_handlers.py:34 실제 존재)
  - `_show_settings_dialog` → `_show_api_settings` (settings_dialog.py:34 실제 존재)
- **주석 태그**: `v8.7.0 [FIX CRIT-2]`

#### CRIT-3 ✅ FIXED — 사이드바 ⚙ 설정 버튼 동일 fallback 실패
- **영향**: 사이드바 ⚙ 설정 아이콘 클릭 무반응
- **수정 파일**: `gui_app_modular/mixins/toolbar_mixin.py:960~969`
- **수정 내용**: `_open_settings_from_sidebar` 내부 if-elif 체인에 `_show_api_settings` 우선 분기 추가. 기존 `_show_settings_dialog` fallback은 그대로 유지(하위 호환).
- **주석 태그**: `v8.7.0 [FIX CRIT-3]`

### 2-3. 경고 14건 — 코드 반영 보류

Menu 감사 리포트(`menu_audit_v864.md`)의 WARNING 14건은 스타일 기반·컨벤션 이슈로 CRITICAL보다 낮음. **사용자 리뷰 후 조치** 권장:
- 상세는 `menu_audit_v864.md` 섹션 6 참조.
- 일괄 자동 패치보다 케이스별 판단이 필요.
- **결정 주체**: 사용자

### 2-4. 불확실 / 애매 사항 (Round 2)

#### U-5. menu_audit_v864.md 고아 핸들러 목록
- **현상**: 감사 결과 일부 핸들러가 메뉴에서 호출되지 않음(section 7). 실제로 deprecated인지, 재연결이 필요한지 코드만 봐서는 판단 불가.
- **Ruby 의견**: 전수 검토가 필요하지만 대부분은 과거 버전의 잔존물로 보임. 제거 전 각 함수의 docstring/주석에서 "v6.X에 사용됨" 등 흔적 확인 필요.
- **결정 주체**: 사용자 + 차후 리팩터 세션

#### U-6. DEPRECATED 표시 메뉴 처리
- **현상**: 주석에 "v5.X deprecated" 표시된 메뉴가 여전히 enable 상태인 케이스 있음(section 8).
- **Ruby 의견**: 사용 중이면 제거 말고 주석만 업데이트, 실제 미사용이면 disable 처리.
- **결정 주체**: 사용자

---

## 최종 요약

### ✅ 확정 반영된 변경 (코드 패치 완료)
1. Phase 3-B 완성: document_bl(36), document_pl(22), document_do(30) 테이블 + insert 메서드 + GUI 확장
2. CRIT-1: `main_app.py`의 4개 dead 메서드를 클래스 내부로 복귀
3. CRIT-2: Action Bar `💾 백업` / `⚙️ 설정` 핸들러명 정정
4. CRIT-3: 사이드바 ⚙ 설정 fallback 체인에 `_show_api_settings` 추가
5. (Chunk A/B/C-1 이전 세션 누적분) 자체 검증 통과

### ✅ Track D 유사 버그 전수검사 조치 완료 (2026-04-19)
6. **D-1.5 CRITICAL**: `preflight_mixin.py:309` — `net_weight` → `net_weight_kg` (Preflight 중량 검증 무력화 해제)
7. **D-1.3 CRITICAL**: `inbound_upload_mixin.py:492` — `getattr(do, 'free_time', '')` → `free_time_info[].storage_free_days` 실제 추출
8. **G-1.2 CRITICAL**: `tonbag_tab.py` — `_refresh_tonbag_list` 메서드 신규 추가 (기존 `_refresh_tonbag` 위임) → outbound_handlers 5지점 + tonbag_tab 1지점 silent skip 해소
9. **D-1.1 HIGH**: `do_update_dialog.py:216` — `'warehouse'` → `'warehouse_name'/'warehouse_code'` fallback
10. **D-1.2 HIGH**: `do_update_dialog.py:230` — dead fallback 제거
11. **D-1.4 HIGH**: `onestop_inbound.py:2908` `free_time_until` dead fallback 제거
12. **D-1.4 HIGH**: `onestop_inbound.py:2932` `getattr(do, 'free_time', None)` 블록 → `free_time_info[0].storage_free_days` 루프로 교체
13. **C-3 HIGH**: `outbound_scheduled_tab.py:94` — bind에 hasattr 방어 추가 (`_on_select_outbound_no` 미정의 silent AttributeError 방지)

### ✅ MEDIUM/LOW 정리 (2026-04-19 추가 세션)
14. **G-1.1 MEDIUM**: `main_app.py:439~441` — `_setup_summary_tab_content` hasattr 가드 3줄 완전 제거 (v3.8.8 요약 탭 제거 잔재)
15. **G-1.4 MEDIUM**: `theme_mixin.py:213~215` — `_reapply_dashboard_card_colors` 첫 분기 제거, 기존 else 로직을 단일 if로 승격
16. **B-1 MEDIUM**: `menu_registry.py:147` — 도구 메뉴에 "🔔 재고 알림 조회" 항목 신규 추가 (`_show_stock_alerts` 호출 연결) → `features_v2_mixin`의 재고 알림 기능 UI 노출
17. **B-3 MEDIUM**: `dashboard_tab.py` — 중복 정의된 `_refresh_dashboard_chart` 및 `_refresh_dashboard_return_rate` shadow 제거. `DashboardDataMixin`의 신 버전(헬퍼 분리/빈값 UI/그리드)이 MRO로 실제 호출되도록 전환

### ⏸️ 보류된 결정 (사용자 확인 필요)
- ~~U-1~~: ✅ 2026-04-19 결정 완료 — (b) lots_json TEXT 컬럼 추가
- ~~U-2~~: ✅ 2026-04-19 결정 완료 — 현상 유지
- ~~U-3~~: ✅ 2026-04-19 결정 완료 — package_type 1줄 패치 반영
- ~~U-4~~: ✅ 2026-04-19 결정 완료 — 현상 유지
- U-5: 고아 핸들러 제거 여부
- U-6: DEPRECATED 메뉴 실제 상태 확인

### 📋 권장 후속 조치
1. `docs/menu_audit_v864.md` 리뷰 후 WARNING 14건 중 실제 문제되는 것 추출 (대부분 숨겨진 cosmetic issue일 것)
2. U-1, U-2 결정 후 필요 시 Phase 3-C 추가 스키마 작업
3. `carrier_profile` YAML 추가 시나리오 실제 테스트: ZIM 1개로 end-to-end 입고 재현
4. 다음 세션에서 PDF 샘플로 파싱→DB 저장 end-to-end 검증 수행
