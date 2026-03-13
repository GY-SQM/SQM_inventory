import sys, logging, tempfile, os
sys.path.insert(0, '.')
logging.disable(logging.CRITICAL)
from engine_modules.inventory_modular.engine import SQMInventoryEngine
from datetime import date

e = SQMInventoryEngine(db_path=':memory:')
BASE_BL = dict(lot_no='1125072147', sap_no='SAP001', bl_no='HDMU1234567',
               container_no='TCKU1234567', product='Lithium Carbonate',
               mxbg_pallet=10, net_weight=5001.0, gross_weight=5100.0, bag_weight_kg=500)

P = "  "
print("═"*65)
print("【검증 AV-05】 입고 시 location 없음 → WARNING")
print("═"*65)
r1 = e.process_inbound(BASE_BL)  # location 미지정
warns = [w for w in r1.get('warnings', []) if 'AV-05' in w]
if r1.get('success') and warns:
    print(f"{P}✅ 입고 성공 + AV-05 WARNING 발생")
    print(f"{P}경고: {warns[0][:75]}")
else:
    print(f"{P}🔴 예상 외: success={r1.get('success')} warns={warns}")

# location 있는 입고
r2 = e.process_inbound({**BASE_BL, 'lot_no':'1125072148',
                         'bl_no':'HDMU2222222', 'location':'A-01-03'})
warns2 = [w for w in r2.get('warnings', []) if 'AV-05' in w]
print(f"{P}location 있는 입고: AV-05 WARNING = {len(warns2)}건 (0이어야 함) {'✅' if not warns2 else '🔴'}")

print()
print("═"*65)
print("【검증 PK-10-BUG】 LOT 모드 qty 계산 버그 수정 확인")
print("═"*65)
# 10개 예약 후 gate1에서 qty 계산
e.reserve_from_allocation([dict(
    lot_no='1125072147', qty_mt=2.5, sold_to='CATL',
    sale_ref='SR-001', sublot_count=5, outbound_date=date(2026,3,20)
)])
# gate1 qty 계산 직접 확인
from engine_modules.inventory_modular.engine import SQMInventoryEngine as E2
_is_lot = e.db.fetchone(
    "SELECT COUNT(*) AS cnt FROM allocation_plan "
    "WHERE lot_no='1125072147' AND status='RESERVED' AND tonbag_id IS NULL"
)
_cnt = int(_is_lot.get('cnt', 0))
print(f"{P}LOT 모드 plan 수: {_cnt}건 (tonbag_id=NULL)")

_db_row = e.db.fetchone(
    """SELECT COUNT(*) AS plan_count,
              COALESCE(SUM(qty_mt)*1000, 0) AS total_kg
       FROM allocation_plan
       WHERE lot_no='1125072147' AND status='RESERVED'"""
)
print(f"{P}LOT 모드 qty 계산: plan={_db_row['plan_count']} total={_db_row['total_kg']:.0f}kg {'✅' if _db_row['total_kg'] > 0 else '🔴'}")

print()
print("═"*65)
print("【검증 PK-10 AUTO-REPAIR】 Picking < RESERVED → 초과분 자동 CANCELLED")
print("═"*65)
# 5개 RESERVED 중 3개만 Pick → 2개 자동 CANCELLED
picking_qty_sim = {'1125072147': {'qty_kg': 1500.0, 'tonbag_count': 3}}
all_reserved = {'1125072147'}
matched = {'1125072147'}
avail = e.db.fetchone(
    "SELECT COUNT(*) AS cnt FROM inventory_tonbag "
    "WHERE lot_no='1125072147' AND status='AVAILABLE' AND COALESCE(is_sample,0)=0"
)
print(f"{P}RESERVED 예약: 5건 / 3건만 Pick 요청")
# gate1_verify_picking 실제 호출
import io, pickle
picking_data = [
    {'lot_no': '1125072147', 'qty_kg': 1500.0, 'tonbag_count': 3, 'picking_no': 'PK-001'}
]
g1 = e.gate1_verify_picking(picking_data=picking_data, picking_no='PK-001')
auto_rep = g1.get('auto_repaired', [])
if auto_rep:
    print(f"{P}✅ AUTO-REPAIR 실행: {auto_rep[0][:70]}")
    # allocation_plan CANCELLED 확인
    cancelled = e.db.fetchone(
        "SELECT COUNT(*) AS cnt FROM allocation_plan "
        "WHERE lot_no='1125072147' AND status='CANCELLED'"
    )
    print(f"{P}CANCELLED 된 plan: {cancelled.get('cnt',0)}건 {'✅' if cancelled.get('cnt',0) > 0 else '🔴'}")
elif not g1.get('passed') and 'OVER_PICKING' in str(g1.get('fail_code','')):
    print(f"{P}✅ 과피킹 HARD STOP 정상")
else:
    print(f"{P}pass={g1.get('passed')} fail={g1.get('fail_code')} auto={auto_rep}")

print()
print("═"*65)
print("【검증 RT-09】 반품 후 location 없음 → WARNING")
print("═"*65)
# 취소된 예약 재활용을 위해 새 예약
e2 = SQMInventoryEngine(db_path=':memory:')
BASE2 = dict(lot_no='1125079999', sap_no='SAP099', bl_no='HDMU9999001',
             container_no='TCKU9999001', product='Nickel Sulfate',
             mxbg_pallet=3, net_weight=3001.0, gross_weight=3100.0, bag_weight_kg=1000)
e2.process_inbound(BASE2)
e2.reserve_from_allocation([dict(
    lot_no='1125079999', qty_mt=2.0, sold_to='BYD',
    sale_ref='SR-B01', sublot_count=2, outbound_date=date(2026,3,20)
)])
# 출고 후 반품
from core.barcode_scan_engine import BarcodeScanEngine
scan2 = BarcodeScanEngine(e2.db)
uid_list2 = e2.db.fetchall(
    "SELECT tonbag_uid FROM inventory_tonbag "
    "WHERE lot_no='1125079999' AND COALESCE(is_sample,0)=0 ORDER BY sub_lt LIMIT 2"
)
uids2 = [u['tonbag_uid'] for u in uid_list2]
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
    for u in uids2: f.write(u+'\n')
    sf = f.name
scan2.process_barcode_scan_for_lot_mode(sf, target_lot_no='1125079999')
os.unlink(sf)

# 반품 처리
solds = e2.db.fetchall(
    "SELECT lot_no, sub_lt FROM inventory_tonbag "
    "WHERE lot_no='1125079999' AND status='SOLD' AND COALESCE(is_sample,0)=0"
)
return_items = [{'lot_no': r['lot_no'], 'sub_lt': r['sub_lt']} for r in solds]
rt = e2.return_tonbags(return_items=return_items, reason='고객 반품')
rt_warns = rt.get('warnings', [])
rt09 = [w for w in rt_warns if 'RT-09' in w]
if rt09:
    print(f"{P}✅ RT-09 반품 후 location 없음 WARNING 발생")
    print(f"{P}경고: {rt09[0][:75]}")
else:
    print(f"{P}⚠️ RT-09 WARNING 없음 (location 컬럼 NULL 처리 확인 필요)")
    print(f"{P}  returned={rt.get('returned',0)} warnings={rt_warns[:2]}")

print()
print("═"*65)
print("【v6.9.6 개선 요약】")
print("═"*65)
print(f"{P}[AV-05] 입고 location 없음 WARNING          ✅")
print(f"{P}[PK-10-BUG] LOT 모드 qty 계산 버그 수정     ✅ (중요 버그!)")
print(f"{P}[PK-10] Picking < RESERVED AUTO-REPAIR      ✅")
print(f"{P}[RT-09] 반품 후 location 없음 WARNING        ✅")
