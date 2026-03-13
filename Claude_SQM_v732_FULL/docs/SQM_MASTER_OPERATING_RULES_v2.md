# SQM 운영 마스터 규칙 v2 (v7.0.0 기준)

## 1. 입고 흐름

```
문서 업로드 (Invoice/PL/B/L/D·O)
  → Gemini Vision AI 파싱 (max_output_tokens=65536)
  → 3-way/4-way 크로스체크
  → DB 저장 (inventory + inventory_tonbag)
```

## 2. 출고 흐름 (One-Stop 4단계)

```
Step1: LOT 선택 + 고객/수량 입력
Step2: 톤백 선택 (AVAILABLE 필터)
Step3: 바코드 스캔 검증
  - actual = expected → FINALIZED ✅
  - actual < expected → REVIEW_REQUIRED ⚠
  - actual > expected → ERROR (hard-stop) ❌
Step4: 완료 → outbound_log 기록
```

## 3. 반품 흐름 (RETURN_AS_REINBOUND — v7.0.0)

```
우클릭 메뉴 → 🔄 반품(재입고)
  → outbound_log에서 최근 출고 자동 조회
  → ReturnReinboundDialog (PDA 스캔 위치 입력)
  → ReturnReinboundEngine.process()
      ① Preflight: 이중반품·LOT불일치 차단
      ② inventory_tonbag UPDATE (status=AVAILABLE, location=새위치)
      ③ inventory.current_weight 복구
      ④ return_log 기록 (outbound_id 연결)
  → inventory/tonbag 뷰 자동 갱신
```

**RETURN_AS_REINBOUND 5대 원칙:**
1. 반품 톤백은 INSERT 금지 — UPDATE 전용
2. 중량 불변 — 원본 중량 그대로 복원
3. outbound_log 불변 — 절대 수정 금지
4. All-or-Nothing 트랜잭션
5. 모든 반품 audit_log 기록

## 4. 시스템 시작 시 자동 실행

- DB 스키마 마이그레이션 (`_run_all_migrations()`)
- return_log 컬럼 자동 추가 (v7.0.0: processed_as, new_location, operator_id)
- SQLite WAL 모드, busy_timeout=30000 설정

## 5. 보안

- MAC 주소 기반 접근 제어 (`security/mac_guard.py`)
- API Key: `keyring` 또는 환경변수로 관리 (settings.ini 평문 저장 금지)
- GitHub push 시 `data/db/*.db` `.gitignore` 필수 적용
