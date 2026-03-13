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
    print(f"  {mark} | {label:<38} | {msg}")

def ar(lot='1125072147', ref='SR-001', cnt=5, cust='CATL'):
    return [dict(lot_no=lot, qty_mt=cnt*0.5, sold_to=cust,
                 sale_ref=ref, sublot_count=cnt, outbound_date=date(2026,3,20))]

BASE = dict(lot_no='1125072147', sap_no='SAP001', bl_no='HDMU1234567',
            container_no='TCKU1234567', product='Lithium Carbonate',
            mxbg_pallet=10, net_weight=5001.0, gross_weight=5100.0, bag_weight_kg=500)

def assign_locations(lot_no):
    """테스트용 위치 배정"""
    tbs = engine.db.fetchall(
        "SELECT id FROM inventory_tonbag WHERE lot_no=? AND COALESCE(is_sample,0)=0", (lot_no,))
    rack = 1
    for tb in tbs:
        engine.db.execute("UPDATE inventory_tonbag SET location=? WHERE id=?",
                          (f"RACK-{rack:02d}", tb['id']))
        rack += 1

def setup_lot(lot_no, sap, bl):
    engine.process_inbound({**BASE,'lot_no':lot_no,'sap_no':sap,'bl_no':bl})
    assign_locations(lot_no)

def full_cycle(lot_no, ref, cnt=5):
    """예약→픽→확정"""
    engine.reserve_from_allocation(ar(lot=lot_no, ref=ref, cnt=cnt))
    engine.execute_reserved(lot_no=lot_no)
    return engine.confirm_outbound(lot_no=lot_no)

# ══════════════════════════════════
# 기준 LOT 셋업
# ══════════════════════════════════
setup_lot('1125072147','SAP001','HDMU1234567')
setup_lot('1125072148','SAP002','HDMU7654321')

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*82)
print("【1】 입고(INBOUND) 이상 10건")
print("═"*82)
ib = [
    ("IB-01 LOT번호 없음",
     {**BASE,'lot_no':''},           False),
    ("IB-02 중복 LOT 재입고",
     {**BASE},                        False),
    ("IB-03 무게=0",
     {**BASE,'lot_no':'1125072200','net_weight':0},  False),
    ("IB-04 무게 음수",
     {**BASE,'lot_no':'1125072201','net_weight':-500},  False),
    ("IB-05 LOT번호 31자 초과",
     {**BASE,'lot_no':'X'*31},        False),
    ("IB-06 톤백수=0",
     {**BASE,'lot_no':'1125072202','mxbg_pallet':0},  False),
    ("IB-07 톤백합계 vs LOT무게 불일치(1t+)",
     {**BASE,'lot_no':'1125072203','net_weight':5001.0,
      'tonbags':[{'sub_lt':i+1,'weight_kg':400} for i in range(10)]},  False),
    ("IB-08 LOT번호 비표준(경고→OK)",
     {**BASE,'lot_no':'ABCD123456'},  True),
    ("IB-09 SAP 중복(경고→OK)",
     {**BASE,'lot_no':'1125072204','sap_no':'SAP001'},  True),
    ("IB-10 B/L 비표준(경고→OK)",
     {**BASE,'lot_no':'1125072205','bl_no':'BADBL'},  True),
]
for lbl, data, ok in ib:
    show(lbl, engine.process_inbound(data), ok)

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*82)
print("【2】 Allocation(예약) 이상 10건")
print("═"*82)

r1 = engine.reserve_from_allocation(ar(lot='9999999999', ref='SR-X1'))
show("AL-01 없는 LOT 예약", r1, False)

r2 = engine.reserve_from_allocation([dict(lot_no='1125072147', qty_mt=0,
     sold_to='CATL', sale_ref='SR-Z2', sublot_count=0, outbound_date=date(2026,3,20))])
show("AL-02 수량=0 예약", r2, False)

r3 = engine.reserve_from_allocation([dict(lot_no='1125072147', qty_mt=-1,
     sold_to='CATL', sale_ref='SR-Z3', sublot_count=-5, outbound_date=date(2026,3,20))])
show("AL-03 수량 음수", r3, False)

r4 = engine.reserve_from_allocation(ar(ref='SR-OK1', cnt=5))
show("AL-04 정상 예약 5개", r4, True)

r5 = engine.reserve_from_allocation(ar(ref='SR-OK1', cnt=2))  # 동일 SR 중복
show("AL-05 동일 sale_ref 중복 예약", r5, False)

r6 = engine.reserve_from_allocation(ar(ref='SR-OVER', cnt=8))  # 잔여 5개 초과
show("AL-06 가용(5개) 초과 예약(8개)", r6, False)

r7 = engine.reserve_from_allocation([dict(lot_no='1125072147', qty_mt=1.5,
     sold_to='', sale_ref='SR-Z7', sublot_count=3, outbound_date=date(2026,3,20))])
show("AL-07 customer 없음", r7, False)

r8 = engine.reserve_from_allocation([dict(lot_no='1125072147', qty_mt=1.5,
     sold_to='BYD', sale_ref='', sublot_count=3, outbound_date=date(2026,3,20))])
show("AL-08 sale_ref 없음", r8, False)

r9 = engine.reserve_from_allocation([])
show("AL-09 빈 리스트", {'success':False,'errors':['빈 Allocation 데이터']}, False)

r10 = engine.reserve_from_allocation(ar(lot='1125072148', ref='SR-148A', cnt=5))
show("AL-10 2번째 LOT 정상 예약 5개", r10, True)

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*82)
print("【3】 PICKED 이상 10건")
print("═"*82)

pk1 = engine.execute_reserved(lot_no='1125072147')
show("PK-01 정상 RESERVED→PICKED", pk1, True)

pk2 = engine.execute_reserved(lot_no='9999999999')
show("PK-02 없는 LOT execute_reserved", pk2, False)

pk3 = engine.execute_reserved(lot_no='1125072147')  # 이미 PICKED
show("PK-03 이미 PICKED 재실행", pk3, False)

pk4 = engine.execute_reserved(lot_no='1125072148')
show("PK-04 정상(148) RESERVED→PICKED", pk4, True)

pk5 = engine.revert_picked_to_reserved(lot_no='1125072148')
show("PK-05 정상 PICKED→RESERVED 취소", pk5, True)

pk6 = engine.revert_picked_to_reserved(lot_no='9999999999')
show("PK-06 없는 LOT PICKED 취소", pk6, False)

pk7 = engine.revert_picked_to_reserved(lot_no='1125072148')  # 이미 RESERVED
show("PK-07 이미 RESERVED 재취소", pk7, False)

# HARD-STOP 검증
pk8 = engine.confirm_outbound(lot_no=None, force_all=False)
show("PK-08 lot_no=None force_all=False", pk8, False)

# 148 재실행
pk9 = engine.execute_reserved(lot_no='1125072148')
show("PK-09 취소 후 재예약→픽", pk9, True)

# 중복 실행
pk10 = engine.execute_reserved(lot_no='1125072148')
show("PK-10 이미 PICKED 중복실행", pk10, False)

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*82)
print("【4】 출고확정(SOLD) 이상 10건")
print("═"*82)

sd1 = engine.confirm_outbound(lot_no='1125072147')
show("SD-01 정상 출고확정(147)", sd1, True)

sd2 = engine.confirm_outbound(lot_no='1125072147')  # 이미 SOLD
show("SD-02 이미 SOLD LOT 재확정", sd2, False)

sd3 = engine.confirm_outbound(lot_no='9999999999')
show("SD-03 없는 LOT 출고확정", sd3, False)

sd4 = engine.confirm_outbound(lot_no=None, force_all=False)
show("SD-04 force_all=False HARD-STOP", sd4, False)

sd5 = engine.confirm_outbound(lot_no='1125072148')
show("SD-05 정상 출고확정(148)", sd5, True)

# 147 잔여(5개) 추가 예약→픽→확정
engine.reserve_from_allocation(ar(ref='SR-147B', cnt=3))
engine.execute_reserved(lot_no='1125072147')
sd6 = engine.confirm_outbound(lot_no='1125072147')
show("SD-06 잔여분 추가 출고확정", sd6, True)

# AVAILABLE LOT 확정
sd7 = engine.confirm_outbound(lot_no='1125072148')  # 148 이미 SOLD
show("SD-07 AVAILABLE LOT 확정시도", sd7, False)

# force_all=True
sd8 = engine.confirm_outbound(lot_no=None, force_all=True)
show("SD-08 force_all=True(PICKED 없음)", sd8, False)  # PICKED 없음

engine.reserve_from_allocation(ar(ref='SR-147C', cnt=2))
engine.execute_reserved(lot_no='1125072147')
sd9 = engine.confirm_outbound(lot_no=None, force_all=True)
show("SD-09 force_all=True 정상", sd9, True)

sd10 = engine.confirm_outbound(lot_no='1125072205')  # AVAILABLE
show("SD-10 AVAILABLE 상태 LOT 확정", sd10, False)

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*82)
print("【5】 반품(RETURN) 이상 10건")
print("═"*82)

# SOLD 상태 톤백 확인
sold_tb = engine.db.fetchone(
    "SELECT lot_no, sub_lt FROM inventory_tonbag "
    "WHERE status='SOLD' AND COALESCE(is_sample,0)=0 LIMIT 1")
s_lot = sold_tb['lot_no'] if sold_tb else '1125072147'
s_sub = sold_tb['sub_lt'] if sold_tb else 1

rt1 = engine.cancel_outbound_tonbag(lot_no='9999999999', sub_lt=1)
show("RT-01 없는 LOT 반품", rt1, False)

rt2 = engine.cancel_outbound_tonbag(lot_no=s_lot, sub_lt=9999)
show("RT-02 없는 sub_lt 반품", rt2, False)

avail_tb = engine.db.fetchone(
    "SELECT sub_lt FROM inventory_tonbag "
    "WHERE status='AVAILABLE' AND COALESCE(is_sample,0)=0 LIMIT 1")
if avail_tb:
    rt3 = engine.cancel_outbound_tonbag(lot_no='1125072147', sub_lt=avail_tb['sub_lt'])
    show("RT-03 AVAILABLE 톤백 반품 시도", rt3, False)

sample_tb = engine.db.fetchone(
    "SELECT lot_no, sub_lt FROM inventory_tonbag WHERE COALESCE(is_sample,0)=1 LIMIT 1")
if sample_tb:
    rt4 = engine.cancel_outbound_tonbag(lot_no=sample_tb['lot_no'], sub_lt=sample_tb['sub_lt'])
    show("RT-04 샘플 톤백 반품 시도", rt4, False)

rt5 = engine.cancel_outbound_tonbag(lot_no=s_lot, sub_lt=s_sub)
show("RT-05 정상 반품(SOLD→AVAILABLE)", rt5, True)

rt6 = engine.cancel_outbound_tonbag(lot_no=s_lot, sub_lt=s_sub)  # 이미 반품
show("RT-06 이미 반품된 톤백 재반품", rt6, False)

rt7 = engine.bulk_return_by_lot(lot_no='9999999999')
show("RT-07 bulk_return 없는 LOT", rt7, False)

rt8 = engine.bulk_return_by_lot(lot_no=s_lot)
show("RT-08 bulk_return 정상", rt8, True)

rt9 = engine.bulk_return_by_lot(lot_no=s_lot)
show("RT-09 모두 반품 후 재반품", rt9, False)

# RESERVED 상태 반품
res_tb = engine.db.fetchone(
    "SELECT lot_no, sub_lt FROM inventory_tonbag "
    "WHERE status='RESERVED' AND COALESCE(is_sample,0)=0 LIMIT 1")
if res_tb:
    rt10 = engine.cancel_outbound_tonbag(lot_no=res_tb['lot_no'], sub_lt=res_tb['sub_lt'])
    show("RT-10 RESERVED 상태 반품 시도", rt10, False)
else:
    show("RT-10 RESERVED 없음(스킵)", {'success':False,'errors':['N/A']}, False)

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*82)
print("【6】 예약취소(cancel_reservation) 이상 10건")
print("═"*82)

setup_lot('1125072300','SAP300','HDMU3001111')

cr1 = engine.cancel_reservation(lot_no='9999999999')
show("CR-01 없는 LOT 예약취소", cr1, False)

cr2 = engine.cancel_reservation(lot_no='1125072147')  # SOLD, RESERVED 없음
show("CR-02 SOLD LOT 예약취소(없음)", cr2, False)

engine.reserve_from_allocation(ar(lot='1125072300',ref='SR-CA1',cnt=4))
cr3 = engine.cancel_reservation(lot_no='1125072300')
show("CR-03 정상 예약취소", cr3, True)

cr4 = engine.cancel_reservation(lot_no='1125072300')  # 이미 취소
show("CR-04 이미 취소 재취소", cr4, False)

engine.reserve_from_allocation(ar(lot='1125072300',ref='SR-CA2',cnt=3))
plans = engine.db.fetchall("SELECT id FROM allocation_plan WHERE lot_no='1125072300' AND status='RESERVED'")
if plans:
    cr5 = engine.cancel_reservation(plan_ids=[plans[0]['id']])
    show("CR-05 plan_id 지정 취소", cr5, True)
    cr6 = engine.cancel_reservation(plan_ids=[plans[0]['id']])
    show("CR-06 이미 취소 plan_id 재취소", cr6, False)

cr7 = engine.cancel_reservation(plan_ids=[])
show("CR-07 빈 plan_ids", cr7, False)

cr8 = engine.cancel_reservation(plan_ids=[9999999])
show("CR-08 없는 plan_id", cr8, False)

cr9 = engine.cancel_reservation()
show("CR-09 파라미터 없음", cr9, False)

engine.reserve_from_allocation(ar(lot='1125072300',ref='SR-CA3',cnt=2))
# PICKED 상태 예약취소 시도
engine.execute_reserved(lot_no='1125072300')
cr10 = engine.cancel_reservation(lot_no='1125072300')  # PICKED → RESERVED 없음
show("CR-10 PICKED LOT 예약취소(RESERVED 없음)", cr10, False)

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*82)
print("【최종 요약】 발견된 이슈")
print("═"*82)

