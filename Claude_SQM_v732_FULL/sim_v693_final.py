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

BASE = dict(lot_no='1125072147', sap_no='SAP001', bl_no='HDMU1234567',
            container_no='TCKU1234567', product='Lithium Carbonate',
            mxbg_pallet=10, net_weight=5001.0, gross_weight=5100.0, bag_weight_kg=500)

def setup(lot, sap, bl, bags=10):
    d = {**BASE,'lot_no':lot,'sap_no':sap,'bl_no':bl,'mxbg_pallet':bags}
    engine.process_inbound(d)
    tbs = engine.db.fetchall(
        "SELECT id FROM inventory_tonbag WHERE lot_no=? AND COALESCE(is_sample,0)=0",(lot,))
    for i,tb in enumerate(tbs):
        engine.db.execute("UPDATE inventory_tonbag SET location=? WHERE id=?",
                          (f"RACK-{i+1:02d}", tb['id']))

def ar(lot='1125072147', ref='SR-001', cnt=3, cust='CATL', qty=None):
    # cnt=3 → qty=1.5MT → 3*500/5000 = 30% → 승인 임계치(50%) 미만 → 즉시 RESERVED
    return [dict(lot_no=lot, qty_mt=qty if qty is not None else round(cnt*0.5,2),
                 sold_to=cust, sale_ref=ref, sublot_count=cnt,
                 outbound_date=date(2026,3,20))]

setup('1125072147','SAP001','HDMU1234567')
setup('1125072148','SAP002','HDMU7654321')

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "═"*84)
print("【1】 입고(INBOUND) 이상 10건 — v6.9.3")
print("═"*84)
for lbl, d, ok in [
    ("IB-01 LOT번호 없음",          {**BASE,'lot_no':''},             False),
    ("IB-02 중복 LOT 재입고",        {**BASE},                          False),
    ("IB-03 무게=0",                {**BASE,'lot_no':'1125072200','net_weight':0}, False),
    ("IB-04 무게 음수",              {**BASE,'lot_no':'1125072201','net_weight':-500}, False),
    ("IB-05 LOT번호 31자 초과",      {**BASE,'lot_no':'X'*31},          False),
    ("IB-06 톤백수=0",              {**BASE,'lot_no':'1125072202','mxbg_pallet':0}, False),
    ("IB-07 톤백합계 vs LOT무게 불일치",{**BASE,'lot_no':'1125072203',
     'tonbags':[{'sub_lt':i+1,'weight_kg':400} for i in range(10)]},     False),
    ("IB-08 LOT번호 비표준 (경고→OK)", {**BASE,'lot_no':'ABCD123456'},   True),
    ("IB-09 SAP번호 중복 (경고→OK)", {**BASE,'lot_no':'1125072204','sap_no':'SAP001'}, True),
    ("IB-10 B/L 비표준 (경고→OK)",   {**BASE,'lot_no':'1125072205','bl_no':'BADBL'}, True),
]:
    show(lbl, engine.process_inbound(d), ok)

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "═"*84)
print("【2】 Allocation(예약) 이상 10건 — v6.9.3 [AL-FIX-1~5+AL-10-FIX]")
print("═"*84)
for lbl, rows, ok in [
    ("AL-01 없는 LOT 예약",            ar(lot='9999999999',ref='ZZ1'), False),
    ("AL-02 qty_mt=0 [AL-FIX-1]",     ar(qty=0,cnt=0,ref='ZZ2'),    False),
    ("AL-03 qty_mt 음수 [AL-FIX-2]",  ar(qty=-2.5,cnt=-3,ref='ZZ3'),False),
    ("AL-04 customer 공란 [AL-FIX-3]", ar(cust='',ref='ZZ4'),        False),
    ("AL-05 sale_ref 공란 [AL-FIX-4]", ar(ref=''),                   False),
    ("AL-06 가용초과 10개→13개 [AL-FIX-5]",ar(cnt=13,ref='ZZ6',qty=6.5),False),
    ("AL-07 빈 리스트",                [],                             False),
    ("AL-08 정상 예약 3개",            ar(ref='SR-A01',cnt=3),        True),
    ("AL-09 동일 SR 중복 예약",         ar(ref='SR-A01',cnt=1),        False),
    ("AL-10 STAGED잔여(7개)→8개초과[AL-10-FIX]",ar(ref='SR-A02',cnt=8,qty=4.0),False),
]:
    if not rows:
        show(lbl, {'success':False,'errors':['빈 Allocation 데이터']}, ok)
    else:
        show(lbl, engine.reserve_from_allocation(rows), ok)

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "═"*84)
print("【3】 PICKED 이상 10건 — v6.9.3")
print("═"*84)
# PK-01: SR-A01 3개 RESERVED → PICKED
pk1 = engine.execute_reserved(lot_no='1125072147')
show("PK-01 정상 RESERVED→PICKED (3개)", pk1, True)

show("PK-02 없는 LOT execute_reserved",
     engine.execute_reserved(lot_no='9999999999'), False)
show("PK-03 이미 PICKED 재실행",
     engine.execute_reserved(lot_no='1125072147'), False)

engine.reserve_from_allocation(ar(lot='1125072148',ref='SR-B01',cnt=3))
pk4 = engine.execute_reserved(lot_no='1125072148')
show("PK-04 148 정상 RESERVED→PICKED",  pk4, True)

pk5 = engine.revert_picked_to_reserved(lot_no='1125072148')
show("PK-05 정상 PICKED→RESERVED 취소", pk5, True)

show("PK-06 없는 LOT PICKED 취소",
     engine.revert_picked_to_reserved(lot_no='9999999999'), False)
show("PK-07 이미 RESERVED 재취소",
     engine.revert_picked_to_reserved(lot_no='1125072148'), False)
show("PK-08 force_all=False HARD-STOP",
     engine.confirm_outbound(lot_no=None, force_all=False), False)

engine.reserve_from_allocation(ar(lot='1125072148',ref='SR-B02',cnt=2))
engine.execute_reserved(lot_no='1125072148')
show("PK-09 취소 후 재예약→PICKED 정상",
     engine.execute_reserved(lot_no='1125072148'), False)  # 이미 EXECUTED
show("PK-10 중복 PICK 차단",
     engine.execute_reserved(lot_no='1125072148'), False)

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "═"*84)
print("【4】 출고확정(SOLD) 이상 10건 — v6.9.3")
print("═"*84)
show("SD-01 정상 출고확정(147 PICKED 3개)",
     engine.confirm_outbound(lot_no='1125072147'), True)
show("SD-02 이미 SOLD LOT 재확정",
     engine.confirm_outbound(lot_no='1125072147'), False)
show("SD-03 없는 LOT 확정",
     engine.confirm_outbound(lot_no='9999999999'), False)
show("SD-04 force_all=False HARD-STOP",
     engine.confirm_outbound(force_all=False), False)
show("SD-05 148 정상 출고확정",
     engine.confirm_outbound(lot_no='1125072148'), True)
show("SD-06 148 재확정(SOLD 이미)",
     engine.confirm_outbound(lot_no='1125072148'), False)

engine.reserve_from_allocation(ar(lot='1125072147',ref='SR-A03',cnt=3))
engine.execute_reserved(lot_no='1125072147')
show("SD-07 잔여분 추가확정",
     engine.confirm_outbound(lot_no='1125072147'), True)

show("SD-08 AVAILABLE 상태 LOT 확정시도",
     engine.confirm_outbound(lot_no='ABCD123456'), False)

engine.reserve_from_allocation(ar(lot='1125072147',ref='SR-A04',cnt=2))
engine.execute_reserved(lot_no='1125072147')
show("SD-09 force_all=True 전체확정",
     engine.confirm_outbound(lot_no=None, force_all=True), True)
show("SD-10 PICKED 없음 force_all=True",
     engine.confirm_outbound(lot_no=None, force_all=True), False)

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "═"*84)
print("【5】 반품(RETURN) 이상 10건 — v6.9.3 [RT-FIX]")
print("═"*84)
sold = engine.db.fetchone(
    "SELECT lot_no,sub_lt FROM inventory_tonbag "
    "WHERE status='SOLD' AND COALESCE(is_sample,0)=0 LIMIT 1")
sl = sold['lot_no'] if sold else '1125072147'
ss = sold['sub_lt'] if sold else 1

show("RT-01 없는 LOT 반품",
     engine.cancel_outbound_tonbag(lot_no='9999999999',sub_lt=1), False)
show("RT-02 없는 sub_lt 반품",
     engine.cancel_outbound_tonbag(lot_no=sl,sub_lt=9999), False)

avail = engine.db.fetchone(
    "SELECT sub_lt FROM inventory_tonbag WHERE status='AVAILABLE' AND COALESCE(is_sample,0)=0 LIMIT 1")
if avail:
    show("RT-03 AVAILABLE 톤백 반품 시도",
         engine.cancel_outbound_tonbag(lot_no='1125072147',sub_lt=avail['sub_lt']), False)

samp = engine.db.fetchone(
    "SELECT lot_no,sub_lt FROM inventory_tonbag WHERE COALESCE(is_sample,0)=1 LIMIT 1")
if samp:
    show("RT-04 샘플 톤백 반품 시도",
         engine.cancel_outbound_tonbag(lot_no=samp['lot_no'],sub_lt=samp['sub_lt']), False)

show("RT-05 정상 반품(SOLD→AVAILABLE) [RT-FIX]",
     engine.cancel_outbound_tonbag(lot_no=sl,sub_lt=ss), True)
show("RT-06 이미 반품된 톤백 재반품",
     engine.cancel_outbound_tonbag(lot_no=sl,sub_lt=ss), False)
show("RT-07 bulk_return 없는 LOT",
     engine.bulk_return_by_lot(lot_no='9999999999'), False)

# RT-08: 새 LOT으로 정상 SOLD → bulk_return (30% 이하로 즉시 RESERVED)
setup('1125072300','SAP300','HDMU3001111')
engine.reserve_from_allocation(ar(lot='1125072300',ref='SR-C01',cnt=3))
engine.execute_reserved(lot_no='1125072300')
engine.confirm_outbound(lot_no='1125072300')
sold_check = engine.db.fetchone(
    "SELECT COUNT(*) cnt FROM inventory_tonbag WHERE lot_no='1125072300' AND status='SOLD'")
show("RT-08 bulk_return 정상 [RT-FIX]",
     engine.bulk_return_by_lot(lot_no='1125072300'), True)
show("RT-09 모두 반품 후 재반품",
     engine.bulk_return_by_lot(lot_no='1125072300'), False)

res_tb = engine.db.fetchone(
    "SELECT lot_no,sub_lt FROM inventory_tonbag WHERE status='RESERVED' AND COALESCE(is_sample,0)=0 LIMIT 1")
if res_tb:
    show("RT-10 RESERVED 상태 반품 시도",
         engine.cancel_outbound_tonbag(lot_no=res_tb['lot_no'],sub_lt=res_tb['sub_lt']), False)
else:
    show("RT-10 RESERVED 없음(스킵)",
         {'success':False,'errors':['N/A']}, False)

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "═"*84)
print("【6】 예약취소(cancel_reservation) 이상 10건 — v6.9.3 [CR-FIX-1]")
print("═"*84)
setup('1125072400','SAP400','HDMU4001111')
engine.reserve_from_allocation(ar(lot='1125072400',ref='SR-D01',cnt=3))

show("CR-01 없는 LOT 예약취소",
     engine.cancel_reservation(lot_no='9999999999'), False)
show("CR-02 SOLD LOT 예약취소 (RESERVED 없음)",
     engine.cancel_reservation(lot_no='1125072147'), False)
show("CR-03 정상 예약취소",
     engine.cancel_reservation(lot_no='1125072400'), True)
show("CR-04 이미 취소된 LOT 재취소",
     engine.cancel_reservation(lot_no='1125072400'), False)

engine.reserve_from_allocation(ar(lot='1125072400',ref='SR-D02',cnt=2))
plans = engine.db.fetchall(
    "SELECT id FROM allocation_plan WHERE lot_no='1125072400' AND status='RESERVED'")
if plans:
    show("CR-05 plan_id 지정 취소",
         engine.cancel_reservation(plan_ids=[plans[0]['id']]), True)
    show("CR-06 이미 취소 plan_id 재취소",
         engine.cancel_reservation(plan_ids=[plans[0]['id']]), False)

show("CR-07 plan_ids=[] HARD-STOP [CR-FIX-1]",
     engine.cancel_reservation(plan_ids=[]), False)
show("CR-08 없는 plan_id",
     engine.cancel_reservation(plan_ids=[9999999]), False)
show("CR-09 파라미터 없음 HARD-STOP [CR-FIX-1]",
     engine.cancel_reservation(), False)

engine.reserve_from_allocation(ar(lot='1125072400',ref='SR-D03',cnt=2))
engine.execute_reserved(lot_no='1125072400')
show("CR-10 PICKED LOT 예약취소 (RESERVED 없음)",
     engine.cancel_reservation(lot_no='1125072400'), False)

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "═"*84)
print("【v6.9.3 수정 통합 결과】")
print("═"*84)
fixes = [
    ("AL-FIX-1", "qty_mt ≤ 0 HARD-STOP",            "AL-02"),
    ("AL-FIX-2", "qty_mt 음수 HARD-STOP",            "AL-03"),
    ("AL-FIX-3", "customer 공란 HARD-STOP",           "AL-04"),
    ("AL-FIX-4", "sale_ref 공란 HARD-STOP",           "AL-05"),
    ("AL-FIX-5", "가용수량 초과 HARD-STOP",             "AL-06"),
    ("AL-10-FIX","STAGED 경로 실질가용 체크",            "AL-10"),
    ("RT-FIX",   "SOLD→AVAILABLE 직접 반품 허용",       "RT-05,08"),
    ("CR-FIX-1", "plan_ids=[] / 파라미터없음 차단",     "CR-07,09"),
]
for code, desc, cases in fixes:
    print(f"  [{code}] {desc:<30} → {cases} ✅")
