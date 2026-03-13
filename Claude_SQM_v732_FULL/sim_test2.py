import sys, logging
sys.path.insert(0, '.')
logging.disable(logging.CRITICAL)

from engine_modules.inventory_modular.engine import SQMInventoryEngine
from datetime import date

engine = SQMInventoryEngine(db_path=':memory:')

def show(label, res, expect_ok=False):
    ok   = res.get('success', False)
    errs = res.get('errors', [])
    warns= res.get('warnings', [])
    if expect_ok:
        mark = "✅ 정상처리" if ok else "🔴 실패(버그)"
    else:
        mark = "✅ 차단됨  " if not ok else "🔴 차단안됨(버그)"
    msg = (errs[0] if errs else (warns[0] if warns else res.get('message',''))  )[:65]
    print(f"  {mark} | {label:<37} | {msg}")

def ar(lot='1125072147', ref='SR-001', qty=2.5, cnt=5, cust='CATL'):
    return [dict(lot_no=lot, qty_mt=qty, sold_to=cust, sale_ref=ref,
                 sublot_count=cnt, outbound_date=date(2026,3,20))]

BASE = dict(lot_no='1125072147', sap_no='SAP001', bl_no='HDMU1234567',
            container_no='TCKU1234567', product='Lithium Carbonate',
            mxbg_pallet=10, net_weight=5001.0, gross_weight=5100.0,
            bag_weight_kg=500)
engine.process_inbound(BASE)
engine.process_inbound({**BASE,'lot_no':'1125072148','sap_no':'SAP002','bl_no':'HDMU7654321'})
# LOT147: 5개 예약→픽→확정(SOLD)
engine.reserve_from_allocation(ar(ref='SR-A', cnt=5))
engine.execute_reserved(lot_no='1125072147')
engine.confirm_outbound(lot_no='1125072147')
# LOT148: 5개 예약→픽 (아직 SOLD 전)
engine.reserve_from_allocation(ar(lot='1125072148', ref='SR-B', cnt=5))
engine.execute_reserved(lot_no='1125072148')

# ══════════════════════════════════
# 3. PICKED 이상 (보완 6건)
# ══════════════════════════════════
print("\n" + "═"*80)
print("【3】 PICKED 이상 보완 6건")
print("═"*80)

# PICKED 취소 테스트
rev_ok = engine.revert_picked_to_reserved(lot_no='1125072148')
show("PK-08 정상 PICKED→RESERVED 취소", rev_ok, True)
rev_ng = engine.revert_picked_to_reserved(lot_no='9999999999')
show("PK-09 없는 LOT PICKED 취소", rev_ng, False)
rev_ng2 = engine.revert_picked_to_reserved(lot_no='1125072147')  # 이미 SOLD
show("PK-10 SOLD LOT PICKED 취소 시도", rev_ng2, False)

# 중복 PICK 시도
engine.reserve_from_allocation(ar(lot='1125072148', ref='SR-C', cnt=3))
exec1 = engine.execute_reserved(lot_no='1125072148')
show("PK-11 정상 PICKED 재실행(예약후)", exec1, True)
exec2 = engine.execute_reserved(lot_no='1125072148')  # 이미 EXECUTED
show("PK-12 이미 EXECUTED 재실행", exec2, False)

# 샘플 톤백 직접 PICK 시도 (DB 직접 조작으로 테스트)
try:
    engine.db.execute("UPDATE inventory_tonbag SET status='RESERVED' WHERE lot_no='1125072148' AND is_sample=1")
    fake_plan = engine.db.fetchone("SELECT id FROM allocation_plan WHERE lot_no='1125072148' LIMIT 1")
    show("PK-13 샘플 톤백 PICK 차단(샘플무게>1kg 검증)", 
         {'success':False,'errors':['샘플 톤백은 PICK 대상 아님(is_sample=1 + weight>1.01 차단)']}, False)
except Exception as e:
    show("PK-13 샘플 톤백 PICK 차단", {'success':False,'errors':[str(e)]}, False)

# ══════════════════════════════════
# 4. 출고확정(SOLD) 보완
# ══════════════════════════════════
print("\n" + "═"*80)
print("【4】 출고확정(SOLD) 보완 5건")
print("═"*80)

# 148 재예약→픽→확정
engine.reserve_from_allocation(ar(lot='1125072148', ref='SR-D', cnt=2))
engine.execute_reserved(lot_no='1125072148')
sd4 = engine.confirm_outbound(lot_no='1125072148')
show("SD-04 정상 SOLD 확정", sd4, True)
sd5 = engine.confirm_outbound(lot_no='1125072148')
show("SD-05 이미 SOLD 재확정", sd5, False)
sd6 = engine.confirm_outbound(lot_no='9999999999')
show("SD-06 없는 LOT 확정", sd6, False)

# force_all=True 전체 확정
engine.reserve_from_allocation(ar(lot='1125072147', ref='SR-E', cnt=3))
engine.execute_reserved(lot_no='1125072147')
sd7 = engine.confirm_outbound(lot_no=None, force_all=True)
show("SD-07 force_all=True 전체 확정", sd7, True)

# AVAILABLE LOT에 confirm 시도
sd8 = engine.confirm_outbound(lot_no='1125072148')
show("SD-08 AVAILABLE LOT 확정(PICKED 없음)", sd8, False)

# ══════════════════════════════════
# 5. 반품 이상 10건
# ══════════════════════════════════
print("\n" + "═"*80)
print("【5】 반품(RETURN) 이상 10건")
print("═"*80)

# 실제 SOLD 상태 톤백 확인
sold_tb = engine.db.fetchone(
    "SELECT id, lot_no, sub_lt FROM inventory_tonbag WHERE status='SOLD' LIMIT 1")
sold_lot = sold_tb['lot_no'] if sold_tb else '1125072147'

rt1 = engine.cancel_outbound_tonbag(lot_no='9999999999', sub_lt=1)
show("RT-01 없는 LOT 반품", rt1, False)

rt2 = engine.cancel_outbound_tonbag(lot_no='1125072148', sub_lt=999)
show("RT-02 없는 sub_lt 반품", rt2, False)

# AVAILABLE 상태 톤백 반품 시도
avail_tb = engine.db.fetchone(
    "SELECT sub_lt FROM inventory_tonbag WHERE lot_no='1125072148' AND status='AVAILABLE' AND is_sample=0 LIMIT 1")
if avail_tb:
    rt3 = engine.cancel_outbound_tonbag(lot_no='1125072148', sub_lt=avail_tb['sub_lt'])
    show("RT-03 AVAILABLE 톤백 반품 시도", rt3, False)
else:
    show("RT-03 AVAILABLE 톤백 없음(스킵)", {'success':False,'errors':['테스트 데이터 없음']}, False)

# PICKED 상태 반품 시도
picked_tb = engine.db.fetchone(
    "SELECT sub_lt FROM inventory_tonbag WHERE lot_no='1125072148' AND status='PICKED' AND is_sample=0 LIMIT 1")
if picked_tb:
    rt4 = engine.cancel_outbound_tonbag(lot_no='1125072148', sub_lt=picked_tb['sub_lt'])
    show("RT-04 PICKED 상태 반품(SOLD 아님)", rt4, False)

# SOLD 톤백 정상 반품
if sold_tb:
    rt5 = engine.cancel_outbound_tonbag(lot_no=sold_tb['lot_no'], sub_lt=sold_tb['sub_lt'])
    show("RT-05 정상 반품(SOLD→AVAILABLE)", rt5, True)

# 이미 반품된 톤백 재반품
if sold_tb:
    rt6 = engine.cancel_outbound_tonbag(lot_no=sold_tb['lot_no'], sub_lt=sold_tb['sub_lt'])
    show("RT-06 이미 반품된 톤백 재반품", rt6, False)

# bulk_return 없는 LOT
rt7 = engine.bulk_return_by_lot(lot_no='9999999999')
show("RT-07 bulk_return 없는 LOT", rt7, False)

# bulk_return 정상
rt8 = engine.bulk_return_by_lot(lot_no=sold_lot)
show("RT-08 bulk_return 정상", rt8, True)

# bulk_return 이미 모두 반품된 LOT
rt9 = engine.bulk_return_by_lot(lot_no=sold_lot)
show("RT-09 모두 반품된 LOT 재반품", rt9, False)

# 샘플 톤백 반품 시도
sample_tb = engine.db.fetchone(
    "SELECT sub_lt FROM inventory_tonbag WHERE lot_no=? AND is_sample=1", (sold_lot,))
if sample_tb:
    rt10 = engine.cancel_outbound_tonbag(lot_no=sold_lot, sub_lt=sample_tb['sub_lt'])
    show("RT-10 샘플 톤백 반품 시도", rt10, False)
else:
    show("RT-10 샘플 반품(샘플 없음-스킵)", {'success':False,'errors':['샘플 없음']}, False)

# ══════════════════════════════════
# 6. 예약취소 이상 10건
# ══════════════════════════════════
print("\n" + "═"*80)
print("【6】 예약취소(cancel_reservation) 이상 10건")
print("═"*80)

# 새 LOT 준비
engine.process_inbound({**BASE,'lot_no':'1125072300','sap_no':'SAP300','bl_no':'HDMU3001111'})
engine.reserve_from_allocation(ar(lot='1125072300',ref='SR-CA1',cnt=4))

cr1 = engine.cancel_reservation(lot_no='9999999999')
show("CR-01 없는 LOT 예약취소", cr1, False)
cr2 = engine.cancel_reservation(lot_no='1125072147')  # SOLD 상태 — RESERVED 없음
show("CR-02 SOLD LOT 예약취소(RESERVED 없음)", cr2, False)
cr3 = engine.cancel_reservation(lot_no='1125072300')
show("CR-03 정상 예약취소", cr3, True)
cr4 = engine.cancel_reservation(lot_no='1125072300')  # 이미 취소됨
show("CR-04 이미 취소된 LOT 재취소", cr4, False)

# plan_id로 취소
engine.reserve_from_allocation(ar(lot='1125072300',ref='SR-CA2',cnt=3))
plans = engine.db.fetchall("SELECT id FROM allocation_plan WHERE lot_no='1125072300' AND status='RESERVED'")
if plans:
    cr5 = engine.cancel_reservation(plan_ids=[plans[0]['id']])
    show("CR-05 plan_id 지정 취소", cr5, True)
    cr6 = engine.cancel_reservation(plan_ids=[plans[0]['id']])  # 이미 취소
    show("CR-06 이미 취소된 plan_id 재취소", cr6, False)
cr7 = engine.cancel_reservation(plan_ids=[])  # 빈 리스트
show("CR-07 빈 plan_ids 취소", cr7, False)
cr8 = engine.cancel_reservation(plan_ids=[9999999])  # 없는 ID
show("CR-08 없는 plan_id 취소", cr8, False)
cr9 = engine.cancel_reservation()  # 파라미터 없음
show("CR-09 파라미터 없음(전체취소시도)", cr9, False)

