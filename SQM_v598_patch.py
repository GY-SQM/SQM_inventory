"""
SQM v5.9.8 패치 스크립트
========================
📅 2026-02-18 | Ruby

3건 수정:
  [P1] 경로③ Excel출고 — sale_ref/sold_to/qty_mt 누락 (import_handlers.py)
  [P2] AllocationParser — CATL/Panasonic 등 고객명 미인식 (allocation_parser.py)
  [P3] 반품 Excel — SOLD/RESERVED 상태 반품 허용 (advanced_dialogs_mixin.py)

사용법:
  1. SQM 프로그램 종료
  2. 이 파일을 SQM 루트 폴더에 복사
  3. python SQM_v598_patch.py
  4. 프로그램 재시작

롤백:
  각 파일의 .bak 백업으로 복원
"""

import os
import shutil
import sys

PATCH_VERSION = "5.9.8"
PATCH_DATE = "2026-02-18"

# SQM 루트 자동 감지
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SQM_ROOT = SCRIPT_DIR

# ═══════════════════════════════════════════════════════════
# 패치 대상 파일
# ═══════════════════════════════════════════════════════════
PATCHES = []

# ───────────────────────────────────────────────────────────
# [P1] 경로③ Excel출고 — sale_ref/sold_to/qty_mt 누락
# 파일: gui_app_modular/handlers/import_handlers.py
# ───────────────────────────────────────────────────────────
PATCHES.append({
    'id': 'P1',
    'desc': '경로③ Excel출고 — sale_ref/sold_to/qty_mt 누락',
    'file': 'gui_app_modular/handlers/import_handlers.py',
    'old': """\
                    result = self.engine.process_outbound([{
                        'lot_no': lot_no,
                        'weight_kg': weight_kg,
                        'customer': customer,
                    }])""",
    'new': """\
                    # v5.9.8 P1: sold_to/sale_ref/qty_mt 추가 (출고 이력 추적용)
                    sale_ref = ''
                    col_sale_ref = next((c for c in cols if c in ('sale_ref', 'saleref', 'sale_reference')), None)
                    if col_sale_ref:
                        sale_ref = safe_str(row.get(col_sale_ref, '')).strip()
                    result = self.engine.process_outbound([{
                        'lot_no': lot_no,
                        'weight_kg': weight_kg,
                        'qty_mt': weight_kg / 1000.0,
                        'customer': customer,
                        'sold_to': customer,
                        'sale_ref': sale_ref,
                    }])""",
})

# ───────────────────────────────────────────────────────────
# [P2] AllocationParser — CATL/Panasonic 등 고객명 미인식
# 파일: parsers/allocation_parser.py
# ───────────────────────────────────────────────────────────
PATCHES.append({
    'id': 'P2',
    'desc': 'AllocationParser — CATL/Panasonic 등 고객명 미인식',
    'file': 'parsers/allocation_parser.py',
    'old': """\
        # 고객명 추출\r
        if "PT LBM" in title or "PT_LBM" in title:\r
            header.customer = "PT LBM"\r
        elif "POSCO" in title:\r
            header.customer = "POSCO"\r
        elif "SAMSUNG" in title:\r
            header.customer = "Samsung SDI"\r
        elif "LG" in title:\r
            header.customer = "LG Energy"\r
        elif "SK" in title:\r
            header.customer = "SK On"\r""",
    'new': """\
        # 고객명 추출 (v5.9.8 P2: CATL/Panasonic/BYD 등 추가)
        customer_patterns = [
            ("PT LBM", "PT LBM"), ("PT_LBM", "PT LBM"),
            ("POSCO", "POSCO Future M"),
            ("SAMSUNG", "Samsung SDI"),
            ("LG ENERGY", "LG Energy Solution"), ("LG ", "LG Energy Solution"),
            ("SK ON", "SK On"), ("SK ", "SK On"),
            ("CATL", "CATL Korea"),
            ("PANASONIC", "Panasonic Energy"),
            ("BYD", "BYD"),
            ("NORTHVOLT", "Northvolt"),
        ]
        for pattern, name in customer_patterns:
            if pattern in title:
                header.customer = name
                break\r""",
})

# ───────────────────────────────────────────────────────────
# [P3] 반품 Excel — SOLD/RESERVED 상태도 반품 허용
# 파일: gui_app_modular/mixins/advanced_dialogs_mixin.py
# ───────────────────────────────────────────────────────────
PATCHES.append({
    'id': 'P3',
    'desc': '반품 Excel — SOLD/RESERVED 상태도 반품 허용',
    'file': 'gui_app_modular/mixins/advanced_dialogs_mixin.py',
    'old': """\
                    # 검증
                    is_ok = (status == 'PICKED')""",
    'new': """\
                    # 검증 (v5.9.8 P3: SOLD/RESERVED/CONFIRMED/SHIPPED도 반품 허용)
                    is_ok = status in ('PICKED', 'SOLD', 'RESERVED', 'CONFIRMED', 'SHIPPED')""",
})


# ═══════════════════════════════════════════════════════════
# 패치 실행
# ═══════════════════════════════════════════════════════════
def apply_patches():
    print("=" * 60)
    print(f"  SQM v{PATCH_VERSION} 패치 ({PATCH_DATE})")
    print(f"  패치 {len(PATCHES)}건")
    print("=" * 60)

    success = 0
    fail = 0

    for patch in PATCHES:
        pid = patch['id']
        desc = patch['desc']
        filepath = os.path.join(SQM_ROOT, patch['file'])

        print(f"\n[{pid}] {desc}")
        print(f"     파일: {patch['file']}")

        if not os.path.exists(filepath):
            print("     ❌ 파일 없음!")
            fail += 1
            continue

        # 백업
        bak_path = filepath + '.bak'
        if not os.path.exists(bak_path):
            shutil.copy2(filepath, bak_path)
            print(f"     💾 백업: {os.path.basename(bak_path)}")

        # 파일 읽기
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        old_text = patch['old']
        new_text = patch['new']

        # \r 정규화 — 파일에 \r이 있을 수도 없을 수도
        if old_text not in content:
            old_text = old_text.replace('\r\n', '\n').replace('\r', '')
        if old_text not in content:
            # 역방향: content에 \r이 있는 경우
            old_text = patch['old'].replace('\n', '\r\n')

        if old_text not in content:
            print("     ⚠️  이미 패치됨 또는 코드 변경됨 (스킵)")
            continue

        count = content.count(old_text)
        if count > 1:
            print(f"     ⚠️  패턴이 {count}회 발견 — 첫 번째만 교체")

        content = content.replace(old_text, new_text, 1)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print("     ✅ 패치 완료")
        success += 1

    # ═══════════════════════════════════════════════════════
    # version.py 업데이트
    # ═══════════════════════════════════════════════════════
    ver_path = os.path.join(SQM_ROOT, 'version.py')
    if os.path.exists(ver_path):
        with open(ver_path, 'r', encoding='utf-8') as f:
            ver_content = f.read()
        if f"'{PATCH_VERSION}'" not in ver_content:
            # __version__ 업데이트
            import re
            ver_content = re.sub(
                r"__version__\s*=\s*'[^']*'",
                f"__version__ = '{PATCH_VERSION}'",
                ver_content
            )
            # VERSION_HISTORY에 추가
            history_entry = (
                f"    '{PATCH_VERSION}': "
                f"'🐛 v{PATCH_VERSION}: P1 Excel출고 sale_ref/sold_to 누락 수정, "
                f"P2 AllocationParser 고객명 확장, "
                f"P3 반품 SOLD/RESERVED 허용',"
            )
            ver_content = ver_content.replace(
                "VERSION_HISTORY = {",
                f"VERSION_HISTORY = {{\n{history_entry}"
            )
            with open(ver_path, 'w', encoding='utf-8') as f:
                f.write(ver_content)
            print(f"\n📌 version.py → v{PATCH_VERSION}")

    print(f"\n{'=' * 60}")
    print(f"  결과: ✅ {success}건 성공 / ❌ {fail}건 실패")
    if success == len(PATCHES):
        print("  🎉 모든 패치 적용 완료!")
    print(f"{'=' * 60}")

    return success == len(PATCHES)


if __name__ == '__main__':
    ok = apply_patches()
    sys.exit(0 if ok else 1)
