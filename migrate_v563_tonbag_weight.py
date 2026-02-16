# -*- coding: utf-8 -*-
"""
SQM v5.6.3 DB 마이그레이션 — 톤백 무게 보정
기존 DB: per_bag = total_w / bag_count (샘플 미차감 → 500.1kg)
수정 후: 톤백 = 500kg, 샘플 = 1kg

사용법: python migrate_v563_tonbag_weight.py
"""
import sqlite3
import os
import shutil
from datetime import datetime

DB_PATH = 'data/db/sqm_inventory.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"❌ DB 파일 없음: {DB_PATH}")
        return
    
    # 백업
    backup = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(DB_PATH, backup)
    print(f"✅ 백업 완료: {backup}")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 1. 현재 상태 진단
    print("\n📊 현재 톤백 무게 분포:")
    cur.execute("""
        SELECT 
            CASE WHEN is_sample = 1 THEN '샘플' ELSE '톤백' END as type,
            COUNT(*) as cnt,
            MIN(weight) as min_w,
            MAX(weight) as max_w,
            AVG(weight) as avg_w
        FROM inventory_tonbag
        GROUP BY is_sample
    """)
    for row in cur.fetchall():
        print(f"  {row['type']}: {row['cnt']}개, "
              f"최소={row['min_w']:.1f}kg, 최대={row['max_w']:.1f}kg, 평균={row['avg_w']:.1f}kg")
    
    # 2. LOT별 대원칙 기반 보정
    cur.execute("""
        SELECT DISTINCT lot_no FROM inventory_tonbag
    """)
    lots = [r['lot_no'] for r in cur.fetchall()]
    
    fixed_count = 0
    for lot_no in lots:
        # LOT의 inventory 무게
        cur.execute("SELECT net_weight, mxbg_pallet FROM inventory WHERE lot_no = ?", (lot_no,))
        inv = cur.fetchone()
        if not inv:
            continue
        
        lot_weight = inv['net_weight'] or 0
        bag_count = inv['mxbg_pallet'] or 0
        
        if bag_count <= 0 or lot_weight <= 0:
            continue
        
        # 대원칙: per_bag = (lot_weight - 1) / bag_count
        correct_per_bag = (lot_weight - 1.0) / bag_count
        
        # 톤백(is_sample=0) 무게 보정
        cur.execute("""
            UPDATE inventory_tonbag 
            SET weight = ?
            WHERE lot_no = ? AND COALESCE(is_sample, 0) = 0
        """, (correct_per_bag, lot_no))
        
        # 샘플(is_sample=1) 무게 = 1kg 확인
        cur.execute("""
            UPDATE inventory_tonbag 
            SET weight = 1.0
            WHERE lot_no = ? AND is_sample = 1
        """, (lot_no,))
        
        fixed_count += 1
    
    conn.commit()
    print(f"\n✅ {fixed_count}개 LOT 톤백 무게 보정 완료")
    
    # 3. 보정 후 검증
    print("\n📊 보정 후 톤백 무게 분포:")
    cur.execute("""
        SELECT 
            CASE WHEN is_sample = 1 THEN '샘플' ELSE '톤백' END as type,
            COUNT(*) as cnt,
            MIN(weight) as min_w,
            MAX(weight) as max_w,
            AVG(weight) as avg_w
        FROM inventory_tonbag
        GROUP BY is_sample
    """)
    for row in cur.fetchall():
        print(f"  {row['type']}: {row['cnt']}개, "
              f"최소={row['min_w']:.1f}kg, 최대={row['max_w']:.1f}kg, 평균={row['avg_w']:.1f}kg")
    
    # 4. 크로스 검증
    print("\n📊 크로스 검증 (inventory vs tonbag 합계):")
    cur.execute("""
        SELECT 
            i.lot_no,
            i.current_weight AS inv_w,
            COALESCE(SUM(t.weight), 0) AS tb_sum
        FROM inventory i
        LEFT JOIN inventory_tonbag t ON i.lot_no = t.lot_no AND t.status = 'AVAILABLE'
        GROUP BY i.lot_no
        HAVING ABS(i.current_weight - COALESCE(SUM(t.weight), 0)) > 0.5
    """)
    mismatches = cur.fetchall()
    if mismatches:
        for m in mismatches:
            print(f"  ⚠️ {m['lot_no']}: inventory={m['inv_w']:.0f}kg, tonbag합계={m['tb_sum']:.0f}kg")
    else:
        print("  ✅ 전체 LOT 정합성 일치!")
    
    conn.close()
    print(f"\n🎉 마이그레이션 완료 (v5.6.3)")

if __name__ == '__main__':
    migrate()
