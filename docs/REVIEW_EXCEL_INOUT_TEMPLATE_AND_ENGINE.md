# 엑셀 입·출고 템플릿 및 엔진 통일 검토

## 1. 대화 요약이 말하는 내용

- **입고**: 지금까지는 4종 서류 파싱 → DB 업로드만 있었고, 앞으로는 **사람이 엑셀/템플릿으로 직접 입력·취합한 경우**도 지원해야 함.
- **제안**: 엑셀 템플릿 방식 — 템플릿 다운로드 → 사용자가 채우거나 복붙 → 같은 메뉴에서 업로드.
- **출고**: Allocation Table 말고도 **간단한 출고 템플릿**으로 LOT·톤백 수·고객 등만 넣고 출고하고 싶음.
- **원칙**: 입구(파싱 vs 엑셀 vs Allocation)가 달라도 **같은 엔진(process_inbound / process_outbound)**을 타면, 톤백 증감·재고 정합성·stock_movement·All-or-Nothing이 동일하게 적용된다.

---

## 2. 설계 검토 — 맞는 부분

| 항목 | 검토 |
|------|------|
| **엑셀 템플릿이 최선** | 사용자 익숙함, 복붙 용이, 시트에 검증/설명 넣기 좋음. 동의. |
| **1 LOT = N 톤백 + 1 샘플** | 입고 엔진이 이미 그렇게 동작하므로, 엑셀에서 읽은 데이터를 packing_dict로만 잘 넘기면 됨. |
| **입고: process_inbound 재사용** | `engine.process_inbound(packing_data)` 한 곳만 통과하면 톤백 생성·샘플·정합성 동일. |
| **출고: process_outbound 재사용** | `engine.process_outbound(allocation_data)` 한 곳만 통과하면 FIFO·PICKED·current_weight 감소·이력 동일. |
| **엔진/UI 분리** | 입고: 파싱(onestop) / 엑셀 템플릿 / (레거시 add_inventory_from_dict). 출고: Allocation Table / 심플 엑셀 출고. 모두 최종적으로 process_inbound 또는 process_outbound를 호출하면 톤백 증감·재고에 동일 반영. |

즉, **“어떤 경로로 들어오든 process_inbound / process_outbound 한 곳을 통과하니까 데이터 무결성이 보장된다”**는 Ruby 의견은 설계상 맞습니다.

---

## 3. 현재 코드베이스(SQM_v587) 상태

- **출고 엑셀**: `_import_outbound_excel_auto`에서 이미 **process_outbound(allocation_data)** 호출. LOT 전량 출고 시 weight_kg를 current_weight로 채우는 로직 있음. 설계와 일치.
- **입고 엑셀**: `_import_inbound_excel_auto`는 현재 **add_inventory_from_dict(data)** 호출(행 단위).  
  - 즉, **“v5.8.7 수동 입고 템플릿” 감지 후 process_inbound로 넘기는 경로**는 이 저장소의 `import_handlers.py`에는 없음.
  - 대화에서 말한 “새 템플릿 + process_inbound + 미리보기” 업그레이드는 **SQM_v587_FINAL_PATCH** 등 별도 패치에 구현돼 있을 수 있음.

정리하면:

- **설계·의도**: 입고도 엑셀 템플릿 → process_inbound 로 보내는 것이 맞고, 그렇게 하면 톤백 증감 등이 파싱 입고와 동일하게 반영됨.
- **구현 위치**: 메인 브랜치의 `import_handlers.py`에는 아직 그 경로가 없으므로, 패치/ZIP에만 있다면 메인에 반영(또는 병합)이 필요함.

---

## 4. “엑셀 입고/출고도 톤백 증감에 포함되는가?”

- **맞습니다.**  
  - 입고: process_inbound → 톤백 생성 + 샘플 1kg → inventory/tonbag/stock_movement 동일.  
  - 출고: process_outbound → 톤백 FIFO PICKED, current_weight 감소, 이력 기록.  
- 따라서 **Allocation Table이 아닌 “간편 출고 템플릿”으로 처리한 출고도** 동일 엔진을 타면 톤백 수·재고 증감에 그대로 반영됩니다.

---

## 5. 권장 사항

1. **입고 엑셀**:  
   - “수동 입고 템플릿(v5.8.7)” 형식 감지 → **process_inbound** 호출 경로를 `import_handlers.py`에 두는 것이 좋음.  
   - 기존 엑셀은 계속 add_inventory_from_dict(레거시)로 두고, 새 템플릿만 process_inbound로 분기하면 됨.
2. **출고 엑셀**:  
   - 이미 process_outbound 사용 중이므로, “간편 출고 템플릿” 컬럼(톤백 수 등)만 엔진 시그니처에 맞게 넣어 주면 됨.
3. **문서화**:  
   - “입고: 파싱 / 엑셀 템플릿 / (레거시)”  
   - “출고: Allocation Table / 엑셀 출고”  
   - “공통: process_inbound / process_outbound → 톤백·재고·이력 동일”  
   을 한 줄로 정리해 두면 유지보수에 도움이 됨.

---

*검토일: 2026-02-17 | SQM v5.8.9*
