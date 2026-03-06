SQM v6.4.1 핫픽스 — 빠른 PDF 스캔 파일명 탐지 수정
====================================================
날짜: 2026-03-07

【원인】
  _detect_inbound_docs_from_folder()에서
  re.sub(r"[\s_\-]+", " ", name.lower()) 적용 후
  "2200034276_BL.pdf" → "2200034276 bl pdf" 가 되는데
  기존 키워드 "_bl", "bl_" 은 매칭 실패 (공백이 들어가 버림)

【수정】
  1) key_name 앞뒤에 공백 추가 → " 2200034276 bl pdf "
  2) 키워드를 공백 경계 방식으로 변경:
     "_bl" / "bl_"  →  " bl "  (공백+bl+공백)
  3) 마침표도 구분자로 추가: re.sub(r"[\s_\-\.]+" ...)

【수정 후 탐지 결과】
  ✅ 2200034276_BL.pdf  → BL
  ✅ 2200034275_PL.pdf  → PACKING_LIST
  ✅ 2200034274_Invoice.pdf → INVOICE
  ✅ 2200034273_DO.pdf  → DO
  ✅ FA_2024_001.pdf    → INVOICE
  ✅ MEDUFP963996.pdf   → BL (MSC 선사 번호)
  ⚠️ 스캔001.pdf        → 미탐지 (파일명에 서류 정보 없음 — 정상)

【적용 내용】
  - gui_app_modular/handlers/inbound_processor.py 반영 (탐지 로직 수정)
  - onestop_inbound.py는 기존 FULL_BUILD 유지 (창 크기 저장 등 보존)
