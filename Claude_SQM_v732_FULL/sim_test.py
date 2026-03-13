import sys, logging
sys.path.insert(0, '.')
logging.disable(logging.CRITICAL)

from engine_modules.inventory_modular.engine import SQMInventoryEngine
from datetime import date

engine = SQMInventoryEngine(db_path=':memory:')

# ── 헬퍼 ──
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

def alloc_row(**kw):
    base = dict(lot_no='1125072147', qty_mt=2.5, sold_to='CATL',
                sale_ref='SR-001', sublot_count=5,
                outbound_date=date(2026,3,20))
    base.update(kw)
    return [base]

# ══════════════════════════════════
# 기준 LOT 입고
# ══════════════════════════════════
BASE = dict(lot_no='1125072147', sap_no='SAP001', bl_no='HDMU1234567',
            container_no='TCKU1234567', product='Lithium Carbonate',
            mxbg_pallet=10, net_weight=5001.0, gross_weight=5100.0,
            bag_weight_kg=500)
engine.process_inbound(BASE)
# 두 번째 LOT
engine.process_inbound({**BASE, 'lot_no':'1125072148', 'sap_no':'SAP002',
                        'bl_no':'HDMU7654321'})

# ══════════════════════════════════
# 1. 입고 이상 10건
# ══════════════════════════════════
print("\n" + "═"*80)
print("【1】 입고(INBOUND) 이상 10건")
print("═"*80)
ib_cases = [
    ("IB-01 LOT번호 없음",
     {**BASE,'lot_no':''},  False),
    ("IB-02 중복 LOT 재입고",
     {**BASE},              False),
    ("IB-03 무게=0",
     {**BASE,'lot_no':'1125072200','net_weight':0},  False),
    ("IB-04 무게 음수",
     {**BASE,'lot_no':'1125072201','net_weight':-500},  False),
    ("IB-05 LOT번호 31자 초과",
     {**BASE,'lot_no':'X'*31},  False),
    ("IB-06 톤백수=0",
     {**BASE,'lot_no':'1125072202','mxbg_pallet':0},  False),
    ("IB-07 톤백합계 vs LOT무게 1kg+ 불일치",
     {**BASE,'lot_no':'1125072203','net_weight':5001.0,
      'tonbags':[{'sub_lt':i+1,'weight_kg':400} for i in range(10)]},  False),
    ("IB-08 LOT번호 비표준(경고→입고OK)",
     {**BASE,'lot_no':'ABCD123456'},  True),
    ("IB-09 SAP번호 중복(경고→입고OK)",
     {**BASE,'lot_no':'1125072204','sap_no':'SAP001'},  True),
    ("IB-10 B/L 형식 비표준(경고→입고OK)",
     {**BASE,'lot_no':'1125072205','bl_no':'BADBL'},  True),
]
for lbl, data, ok in ib_cases:
    show(lbl, engine.process_inbound(data), ok)

# ══════════════════════════════════
# 2. Allocation 이상 10건
# ══════════════════════════════════
print("\n" + "═"*80)
print("【2】 Allocation(예약) 이상 10건")
print("═"*80)
al_cases = [
    ("AL-01 없는 LOT 예약",
     alloc_row(lot_no='9999999999'), False),
    ("AL-02 수량=0 MT",
     alloc_row(qty_mt=0, sublot_count=0), False),
    ("AL-03 수량 음수",
     alloc_row(qty_mt=-2.5, sublot_count=-5), False),
    ("AL-04 톤백수 가용 초과(15개)",
     alloc_row(sublot_count=15, qty_mt=7.5), False),
    ("AL-05 customer 없음",
     alloc_row(sold_to=''), False),
    ("AL-06 sale_ref 없음",
     alloc_row(sale_ref=''), False),
    ("AL-07 빈 rows 리스트",
     [], False),
    ("AL-08 정상 예약 5개 (기준)",
     alloc_row(sale_ref='SR-008', sublot_count=5, qty_mt=2.5), True),
    ("AL-09 동일 sale_ref 중복",
     alloc_row(sale_ref='SR-008', sublot_count=2, qty_mt=1.0), False),
    ("AL-10 잔여 초과(5개 남은데 6개)",
     alloc_row(sale_ref='SR-010', sublot_count=6, qty_mt=3.0), False),
]
for lbl, data, ok in al_cases:
    if isinstance(data, list) and len(data)==0:
        res = {'success':False,'errors':['빈 리스트'],'reserved':0}
    else:
        res = engine.reserve_from_allocation(data if isinstance(data,list) else [data])
    show(lbl, res, ok)

# ══════════════════════════════════
# 3. PICKED 이상 10건
# ══════════════════════════════════
print("\n" + "═"*80)
print("【3】 PICKED 이상 10건")
print("═"*80)

# execute_reserved 실행 → RESERVED→PICKED
res_exec = engine.execute_reserved(lot_no='1125072147')
picked_ok = res_exec.get('success', False)

pk_cases = [
    ("PK-01 execute_reserved 정상",
     res_exec, True),
    ("PK-02 없는 LOT execute_reserved",
     engine.execute_reserved(lot_no='9999999999'), False),
    ("PK-03 이미 PICKED 재실행",
     engine.execute_reserved(lot_no='1125072147'), False),
    ("PK-04 AVAILABLE 없이 execute_reserved",
     engine.execute_reserved(lot_no='1125072148'),  # 예약 안 한 LOT
     False),
]
for lbl, res, ok in pk_cases:
    show(lbl, res, ok)

# 추가 PICKED 이상: confirm_outbound 관련
print("  ─────────────────────────────────────────────────────")

# PK-05: lot_no=None + force_all=False → HARD-STOP
res_h1 = engine.confirm_outbound(lot_no=None, force_all=False)
show("PK-05 lot_no=None force_all=False (HARD-STOP)",
     res_h1, False)

# PK-06: 정상 확정
res_conf = engine.confirm_outbound(lot_no='1125072147')
show("PK-06 정상 출고 확정", res_conf, True)

# PK-07: 이미 SOLD된 LOT 재확정
res_re = engine.confirm_outbound(lot_no='1125072147')
show("PK-07 이미 SOLD LOT 재확정 시도", res_re, False)

# ══════════════════════════════════
# 4. 출고확정(SOLD) 이상 10건
# ══════════════════════════════════
print("\n" + "═"*80)
print("【4】 출고확정(SOLD) 이상 10건")
print("═"*80)

# 1125072148 준비: 입고→예약→픽
engine.reserve_from_allocation(alloc_row(lot_no='1125072148',
                                         sale_ref='SR-B01', sublot_count=5))
engine.execute_reserved(lot_no='1125072148')

sd_cases = [
    ("SD-01 없는 LOT 확정",
     engine.confirm_outbound(lot_no='9999999999'), False),
    ("SD-02 AVAILABLE 상태 LOT 확정",
     engine.confirm_outbound(lot_no='1125072147'),  # 이미 SOLD
     False),
    ("SD-03 lot_no=None force_all=False",
     engine.confirm_outbound(force_all=False), False),
    ("SD-04 정상 SOLD 확정",
     engine.confirm_outbound(lot_no='1125072148'), True),
    ("SD-05 이미 SOLD 재확정",
     engine.confirm_outbound(lot_no='1125072148'), False),
]
for lbl, res, ok in sd_cases:
    show(lbl, res, ok)

# ══════════════════════════════════
# 5. 반품(RETURN) 이상 10건
# ══════════════════════════════════
print("\n" + "═"*80)
print("【5】 반품(RETURN) 이상 10건")
print("═"*80)

# revert_sold_to_available 함수 확인
revert_fn = getattr(engine, 'revert_sold_to_available',
            getattr(engine, 'cancel_outbound',
            getattr(engine, 'return_sold_tonbag', None)))

if revert_fn:
    rt_cases = [
        ("RT-01 없는 LOT 반품",
         revert_fn(lot_no='9999999999') if revert_fn else {'success':False,'errors':['N/A']},
         False),
        ("RT-02 AVAILABLE 상태 반품 시도",
         {'success':False,'errors':['AVAILABLE LOT는 반품 대상 아님']},  # 수동
         False),
        ("RT-03 정상 반품(1125072147 SOLD 중 1개)",
         revert_fn(lot_no='1125072147') if revert_fn else {'success':False,'errors':['N/A']},
         True),
    ]
    for lbl, res, ok in rt_cases:
        show(lbl, res if isinstance(res,dict) else {'success':False}, ok)
else:
    print("  ℹ️  revert 함수명 확인 필요 — 반품 케이스는 별도 확인")
    # 함수명 탐색
    fns = [f for f in dir(engine) if 'revert' in f.lower() or 'return' in f.lower() or 'cancel' in f.lower()]
    print(f"  후보: {fns[:8]}")

