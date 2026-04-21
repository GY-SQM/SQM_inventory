#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
테스트 배정 데이터 정리 스크립트
- allocation_plan에서 RESERVED/STAGED 레코드 삭제
- inventory_tonbag 상태를 AVAILABLE로 복원
- inventory(LOT) 상태를 AVAILABLE로 복원

★ 프로그램 종료 후 실행할 것
★ 실행 전 DB 백업 자동 생성
"""
import sqlite3
import shutil
import os
from datetime import datetime

DB_PATH = "data/db/sqm_inventory.db"

def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] DB 파일 없음: {DB_PATH}")
        return

    # 1. 자동 백업
    backup_name = f"data/db/sqm_inventory_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(DB_PATH, backup_name)
    print(f"[OK] 백업 완료: {backup_name}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 2. 현황 확인
    plans = conn.execute("""
        SELECT sale_ref, customer, status, COUNT(*) as cnt
        FROM allocation_plan
        WHERE status IN ('RESERVED','PENDING_APPROVAL','STAGED')
        GROUP BY sale_ref, customer, status
    """).fetchall()

    if not plans:
        print("[INFO] 정리할 활성 배정 없음")
        conn.close()
        return

    print("\n=== 정리 대상 ===")
    total = 0
    for r in plans:
        print(f"  {r['sale_ref']} / {r['customer']} / {r['status']} → {r['cnt']}건")
        total += r['cnt']
    print(f"  합계: {total}건")

    confirm = input("\n위 배정을 전부 삭제하시겠습니까? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("[취소] 아무것도 변경하지 않았습니다.")
        conn.close()
        return

    # 3. 정리 실행
    try:
        conn.execute("BEGIN")

        # 3-1. 해당 LOT 번호 수집
        lot_rows = conn.execute("""
            SELECT DISTINCT lot_no FROM allocation_plan
            WHERE status IN ('RESERVED','PENDING_APPROVAL','STAGED')
        """).fetchall()
        lot_nos = [r['lot_no'] for r in lot_rows]

        # 3-2. allocation_plan 삭제
        deleted = conn.execute("""
            DELETE FROM allocation_plan
            WHERE status IN ('RESERVED','PENDING_APPROVAL','STAGED')
        """).rowcount
        print(f"[OK] allocation_plan {deleted}건 삭제")

        # 3-3. inventory_tonbag: RESERVED → AVAILABLE 복원
        if lot_nos:
            ph = ','.join('?' * len(lot_nos))
            tb_updated = conn.execute(f"""
                UPDATE inventory_tonbag
                SET status = 'AVAILABLE', updated_at = datetime('now')
                WHERE lot_no IN ({ph})
                  AND status = 'RESERVED'
            """, lot_nos).rowcount
            print(f"[OK] inventory_tonbag {tb_updated}건 RESERVED → AVAILABLE")

            # 3-4. inventory(LOT): RESERVED → AVAILABLE 복원
            lot_updated = conn.execute(f"""
                UPDATE inventory
                SET status = 'AVAILABLE'
                WHERE lot_no IN ({ph})
                  AND status = 'RESERVED'
            """, lot_nos).rowcount
            print(f"[OK] inventory {lot_updated}건 RESERVED → AVAILABLE")

        conn.execute("COMMIT")
        print(f"\n[완료] 테스트 배정 {deleted}건 정리 완료!")
        print(f"  백업: {backup_name}")
        print(f"  → 프로그램을 다시 실행하고 배정 엑셀을 재업로드하세요.")

    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"[ERROR] 롤백됨: {e}")

    conn.close()


if __name__ == "__main__":
    main()
