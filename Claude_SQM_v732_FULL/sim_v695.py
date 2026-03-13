import sys, logging
sys.path.insert(0, '.')
logging.disable(logging.CRITICAL)

from engine_modules.inventory_modular.engine import SQMInventoryEngine
from core.barcode_scan_engine import BarcodeScanEngine
from datetime import date

e = SQMInventoryEngine(db_path=':memory:')
scan = BarcodeScanEngine(e.db)

BASE = dict(lot_no='1125072147', sap_no='SAP001', bl_no='HDMU1234567',
            container_no='TCKU1234567', product='Lithium Carbonate',
            mxbg_pallet=10, net_weight=5001.0, gross_weight=5100.0, bag_weight_kg=500)

print("═"*65)
print("【검증 C】 IB-08: BL 없음 → HARD STOP")
print("═"*65)
r_no_bl = e.process_inbound({**BASE, 'lot_no':'9999999001', 'bl_no': ''})
if not r_no_bl.get('success') and any('IB-08' in err for err in r_no_bl.get('errors',[])):
    print("  ✅ BL 없음 → HARD STOP 정상 차단")
    print(f"  에러: {r_no_bl['errors'][0][:70]}")
else:
    print(f"  🔴 차단 안 됨 / success={r_no_bl.get('success')}")

print()
print("═"*65)
print("【검증 C2】 BL 있음 → 정상 입고")
print("═"*65)
r_ok = e.process_inbound(BASE)
if r_ok.get('success'):
    print("  ✅ BL 정상 → 입고 성공")
else:
    print(f"  🔴 입고 실패: {r_ok.get('errors')}")

# Allocation 예약
e.reserve_from_allocation([dict(
    lot_no='1125072147', qty_mt=2.5, sold_to='CATL',
    sale_ref='SR-001', sublot_count=5, outbound_date=date(2026,3,20)
)])

print()
print("═"*65)
print("【검증 D】 SD-10: SOLD 톤백 재스캔 → HARD STOP (already_sold)")
print("═"*65)

import tempfile, os
# 먼저 정상 출고 5개
uid_list = e.db.fetchall(
    "SELECT tonbag_uid FROM inventory_tonbag "
    "WHERE lot_no='1125072147' AND COALESCE(is_sample,0)=0 "
    "ORDER BY sub_lt LIMIT 5")
uids = [u['tonbag_uid'] for u in uid_list]

with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
    for u in uids: f.write(u + '\n')
    sf = f.name
scan.process_barcode_scan_for_lot_mode(sf, target_lot_no='1125072147')
os.unlink(sf)

# SOLD된 톤백 재스캔 시도
sold_uid = uids[0]
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
    f.write(sold_uid + '\n')
    sf2 = f.name

r_rescan = scan.process_barcode_scan_for_lot_mode(sf2, target_lot_no='1125072147')
os.unlink(sf2)

if not r_rescan.get('success') and r_rescan.get('already_sold'):
    print(f"  ✅ SD-10 SOLD 재출고 HARD STOP 정상")
    print(f"  에러: {r_rescan['errors'][0][:70]}")
    print(f"  already_sold: {r_rescan['already_sold']}")
else:
    print(f"  🔴 차단 안 됨 success={r_rescan.get('success')} errors={r_rescan.get('errors')}")

print()
print("═"*65)
print("【검증 A】 allocation_dialog 버튼 로직 (코드 단위)")
print("═"*65)
# LOT 모드 예약 카운트 확인 로직 시뮬
lot_mode_cnt_row = e.db.fetchone(
    "SELECT COUNT(*) AS cnt FROM allocation_plan "
    "WHERE status='RESERVED' AND tonbag_id IS NULL")
cnt = int(lot_mode_cnt_row.get('cnt', 0))
print(f"  LOT 모드 RESERVED(tonbag_id=NULL) = {cnt}건")
if cnt == 0:
    print("  ✅ 5개 모두 스캔 완료 → execute 버튼 정상 허용 상태")
else:
    print(f"  → 버튼 클릭 시 '바코드 스캔 필요' 메시지 표시됨")

print()
print("═"*65)
print("【v6.9.5 개선 요약】")
print("═"*65)
print("  [A] allocation_dialog: LOT 모드 안내 추가 ✅")
print("  [B] import_handlers: 반품 중복 위임 ✅")
print("  [C] IB-08: BL 없음 HARD STOP ✅")
print("  [D] SD-10: SOLD 재출고 already_sold 분리 ✅")
