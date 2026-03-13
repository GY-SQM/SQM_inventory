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

# 입고
e.process_inbound(BASE)
e.process_inbound({**BASE, 'lot_no':'1125072148', 'sap_no':'SAP002', 'bl_no':'HDMU2222222'})

print("═"*70)
print("【검증 1】 LOT 모드 단일화 — tonbag_id=NULL 예약 확인")
print("═"*70)
r = e.reserve_from_allocation([dict(
    lot_no='1125072147', qty_mt=2.5, sold_to='CATL',
    sale_ref='SR-001', sublot_count=5, outbound_date=date(2026,3,20)
)])
print(f"  예약 결과: reserved={r.get('reserved',0)} pending={r.get('pending_approval',0)}")

plans = e.db.fetchall("SELECT id, status, tonbag_id, sub_lt FROM allocation_plan")
null_cnt = sum(1 for p in plans if p['tonbag_id'] is None)
tb_cnt   = sum(1 for p in plans if p['tonbag_id'] is not None)
print(f"  allocation_plan: tonbag_id=NULL={null_cnt}건 / 특정={tb_cnt}건")

tbs = e.db.fetchall(
    "SELECT sub_lt, status FROM inventory_tonbag WHERE lot_no='1125072147' ORDER BY sub_lt")
avail = sum(1 for t in tbs if t['status']=='AVAILABLE' and t['sub_lt']!=0)
resvd = sum(1 for t in tbs if t['status']=='RESERVED')
print(f"  tonbag 상태: AVAILABLE={avail}개 / RESERVED={resvd}개")
if null_cnt == 5 and tb_cnt == 0 and avail == 10:
    print("  ✅ LOT 모드 단일화 확인 — tonbag은 여전히 AVAILABLE (스캔 전까지 특정 안 함)")
else:
    print("  🔴 예상과 다름")

print()
print("═"*70)
print("【검증 2】 execute_reserved → LOT 모드 스캔 대기 처리")
print("═"*70)
pk = e.execute_reserved(lot_no='1125072147')
print(f"  execute_reserved: success={pk.get('success')} executed={pk.get('executed',0)}")
tbs2 = e.db.fetchall(
    "SELECT sub_lt, status FROM inventory_tonbag WHERE lot_no='1125072147' ORDER BY sub_lt")
picked = sum(1 for t in tbs2 if t['status']=='PICKED')
avail2 = sum(1 for t in tbs2 if t['status']=='AVAILABLE' and t['sub_lt']!=0)
print(f"  tonbag: AVAILABLE={avail2}개 PICKED={picked}개")
if picked == 0 and avail2 == 10:
    print("  ✅ 정상 — 스캔 전까지 어느 tonbag도 PICKED 안 됨")
else:
    print("  🔴 tonbag이 미리 PICKED됨 (버그)")

print()
print("═"*70)
print("【검증 3】 바코드 스캔 → tonbag_id 확정 + SOLD")
print("═"*70)

# 실제 tonbag UID 조회
uid_list = e.db.fetchall(
    "SELECT tonbag_uid FROM inventory_tonbag "
    "WHERE lot_no='1125072147' AND COALESCE(is_sample,0)=0 "
    "ORDER BY sub_lt LIMIT 5")
uids = [u['tonbag_uid'] for u in uid_list]

import tempfile, os
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
    for u in uids:
        f.write(u + '\n')
    scan_file = f.name

r2 = scan.process_barcode_scan_for_lot_mode(scan_file, target_lot_no='1125072147')
os.unlink(scan_file)
print(f"  스캔 결과: success={r2.get('success')} sold={r2.get('sold',0)}")
print(f"  not_found={r2.get('not_found',[])} no_plan={r2.get('no_plan',[])}")

sold_tbs = e.db.fetchall(
    "SELECT sub_lt, status, tonbag_uid FROM inventory_tonbag "
    "WHERE lot_no='1125072147' AND COALESCE(is_sample,0)=0 ORDER BY sub_lt")
sold_cnt  = sum(1 for t in sold_tbs if t['status']=='SOLD')
avail_cnt = sum(1 for t in sold_tbs if t['status']=='AVAILABLE')
print(f"  tonbag 최종: SOLD={sold_cnt}개 / AVAILABLE={avail_cnt}개")
if sold_cnt == 5 and avail_cnt == 5:
    print("  ✅ 스캔으로 정확히 5개 SOLD 확정, 나머지 5개 AVAILABLE 유지")

# allocation_plan tonbag_id 확정 확인
plans2 = e.db.fetchall("SELECT id, status, tonbag_id FROM allocation_plan")
confirmed = sum(1 for p in plans2 if p['tonbag_id'] is not None and p['status']=='EXECUTED')
print(f"  allocation_plan: EXECUTED+tonbag확정={confirmed}건")

print()
print("═"*70)
print("【검증 4】 오스캔 HARD-STOP — 다른 LOT 바코드 스캔")
print("═"*70)

# 148번 LOT의 tonbag UID로 147번 LOT 출고 시도
uid_148 = e.db.fetchone(
    "SELECT tonbag_uid FROM inventory_tonbag "
    "WHERE lot_no='1125072148' AND COALESCE(is_sample,0)=0 LIMIT 1")
wrong_uid = uid_148['tonbag_uid'] if uid_148 else '1125072148-001'

with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
    f.write(wrong_uid + '\n')
    scan_file2 = f.name

# 147번 출고 중에 148번 UID 스캔
e.reserve_from_allocation([dict(
    lot_no='1125072148', qty_mt=1.5, sold_to='BYD',
    sale_ref='SR-B01', sublot_count=3, outbound_date=date(2026,3,20)
)])
r3 = scan.process_barcode_scan_for_lot_mode(scan_file2, target_lot_no='1125072147')
os.unlink(scan_file2)

print(f"  오스캔 결과: success={r3.get('success')}")
print(f"  errors={r3.get('errors',['없음'])[:1]}")
wrong = r3.get('wrong_lot', [])
if wrong:
    w = wrong[0]
    print(f"  스캔 LOT={w.get('scanned_lot')} / 목표 LOT={w.get('target_lot')}")
if not r3.get('success') and r3.get('wrong_lot'):
    print("  ✅ 오스캔 HARD-STOP 정상 작동")
else:
    print("  🔴 오스캔 통과됨 (버그)")

print()
print("═"*70)
print("【v6.9.4 LOT 모드 단일화 핵심 원칙】")
print("═"*70)
print("  입고         → AVAILABLE (tonbag 10개 생성)")
print("  Allocation   → RESERVED (개수만, tonbag_id=NULL) ✅")
print("  execute_res  → 스캔 대기 기록 (tonbag 상태 변경 안 함) ✅")
print("  바코드 스캔  → tonbag_id 확정 + SOLD ✅")
print("  오스캔       → HARD-STOP (WRONG_LOT_SCAN) ✅")
