# Picking List 파싱/피킹 로직 참고 검토

> 다른 AI가 제안한 “절대 실패하지 않는” 파싱·피킹 설계와 현재 SQM 구현을 비교한 요약.

---

## 1) 참고할 만한 점 (도입 가치 높음)

| 제안 항목 | 요약 | SQM 반영 가치 |
|----------|------|----------------|
| **문서 구조 고정 패턴** | Header → Item(본품/샘플) → Batch 반복 → Packing/Weight. “표”가 아니라 **라벨-라인 기반** 파싱이 안정적 | ✅ 파서가 기대하는 패턴을 docstring/상수로 명시하면 유지보수에 유리 |
| **절대 실패 정의** | 예외로 죽지 않음 / 없으면 `errors[]` + 빈 값 / 이상하면 **하드스톱**으로 틀린 값 유입 차단 | ✅ 이미 `PickingListResult.errors` + `success=False` 사용 중. 하드스톱 규칙만 추가하면 됨 |
| **파이프라인 고정** | PDF 타입 → Text/OCR 추출 → Header → Item Section → Packing/Weight → 정규화 → **강제 검증** | ✅ 단계를 나누고, 검증을 “파싱 직후” 한곳에 모으면 재현성 좋음 |
| **7가지 하드스톱** | 본품 존재·총량=배치합·샘플 존재·총량=배치합·본품배치=샘플배치·600백 검증·컨테이너 중량 근접·단위 kg 통일 | ✅ **현재는 LOT 일치만 검증**. 여기에 “총량=배치합”, “포장 수(600백)” 검증 추가하면 실수 방지에 효과적 |
| **Item 단위 파싱** | 자재코드(30000008/30000026) 라인으로 본품/샘플 구분, 그 아래 Batch 라인 수집 | ⚠️ 선택. 지금은 MT/KG로 톤백/샘플 구분만 함. 자재코드 고정 문서면 Item 블록으로 검증 강화 가능 |
| **피킹 플랜(컨테이너)** | 15×40ft → 컨테이너당 20,000kg → 4배치/컨테이너, 결정론적 round-robin | ✅ **현재 없음**. `expand_tonbags`는 LOT→행만 생성. 컨테이너 배치 계획이 필요하면 `build_pick_plan` 스타일 도입 가치 있음 |
| **OCR 폴백** | 텍스트 부족 시 “페이지 렌더링 → 전처리 → OCR” | ⚠️ 장기. 지금은 Text + PyMuPDF 폴백만. 스캔본 대응 시 동일 상태머신에 OCR 텍스트만 넣으면 됨 |

---

## 2) 현재 SQM vs 제안 비교

| 구분 | 현재 SQM (picking_mixin + outbound_mixin) | 제안 로직 |
|------|------------------------------------------|-----------|
| **텍스트 추출** | 원시 `(…)Tj` → 실패 시 **PyMuPDF** 줄 단위 | Text Parser + OCR 폴백 |
| **데이터 모델** | `PickingListMeta` + `PickingLotItem`(lot_no, weight_kg, unit, storage), tonbag/sample 리스트 | `PickingDoc` + `ItemBlock`(material_code, total_qty, batches) + `BatchLine` |
| **파싱 방식** | 블록 순회 → `Quantity: X MT/KG` + 다음 줄 Batch number / Storage location | Item 라인 정규식 + Batch 라인 정규식(상태머신) |
| **메타** | `PICKING LIST` 위치 기준 고정 인덱스 + 200,000kg 이상 KG 라인으로 NW/GW | Header 후보 라인별 매칭(customer_ref, requisition, sales_order, creation_date, container_plan, ports 등) |
| **검증** | 톤백 LOT 집합 vs 샘플 LOT 집합 일치 → 불일치 시 `errors` + `success=False` | 위 + **본품 총량=배치합**, **샘플 총량=배치합**, **600백**, **컨테이너당 중량** |
| **피킹 실행** | `expand_tonbags()` → LOT별 톤백/샘플 행 리스트. Gate-1: 피킹 LOT ⊆ RESERVED | `build_pick_plan()` → 컨테이너별 배치 리스트 + tonbag_count/sample_kg |
| **하드스톱** | Gate-1 실패 시 실행 중단. 파싱 단계에서는 LOT 일치만 | 7개 정책(본품/샘플 존재·총량·배치 1:1·포장·컨테이너·단위) |

---

## 3) 구현 틀 권장 (기존 호환 전제)

- **호환 유지**: 상위에서 쓰는 `PickingListResult`(meta, tonbag, sample, summary, errors, success)와 `expand_tonbags()` 시그니처 유지.
- **추가할 것**  
  1. **파싱 직후 하드스톱 4개** (파서 내부 또는 Gate-0로 일원화)  
     - 본품 총 MT = Σ(배치 MT)  
     - 샘플 총 KG = Σ(배치 KG)  
     - (선택) 문서 기재 Big bag 500kg × 600 = 300,000 kg  
     - (선택) 본품 자재코드 30000008 / 샘플 30000026 존재  
  2. **정규화**  
     - 숫자: 천단위 콤마 제거 후 float.  
     - 단위: MT → kg(×1000) 후 내부는 kg 고정(이미 weight_kg로 하고 있음).  
  3. **피킹 플랜(선택)**  
     - `containers` 또는 `container_plan` 파싱값이 있으면, `build_pick_plan` 스타일로 “컨테이너당 배치/톤백/샘플” 계산해 두고, 보고/출고 지시에만 사용. DB 스키마는 기존 allocation_plan/execute_from_picking 유지.

- **OCR**  
  - “텍스트 부족” 판단(예: 추출 글자 수 < 임계값) 시 동일 상태머신에 넘길 **문자열**만 OCR로 채우면 됨. 파서 인터페이스는 `parse_from_text(all_text)` + `parse_picking_list(pdf_path)` 이중 진입점으로 두면 됨.

---

## 4) 결론

- **참고할 만한 핵심**: (1) 문서 구조를 “라벨-라인 고정 패턴”으로 명시, (2) **7가지 하드스톱** 중 총량=배치합·포장 수(600백)·(필요 시 컨테이너)를 파싱/Gate 직후에 넣기, (3) 컨테이너 배치가 필요하면 **배치 단위 피킹 플랜**을 결정론적으로 생성하는 `build_pick_plan` 스타일 도입.
- **현재 구조 유지**: 데이터는 기존 `PickingListResult` + `expand_tonbags()`로 출고 실행까지 그대로 두고, **검증 단계만 강화**하면 “절대 실패하지 않게” 데이터를 읽고 하드스톱으로 틀린 출고를 막는 목표에 잘 맞음.
- ItemBlock/자재코드 기반 파싱은 “동일 양식 고정”일 때만 도입해도 되고, 지금은 MT/KG 구분만으로도 동작하므로 **우선은 검증 규칙 추가**를 권장.
