# SQM 재고관리 시스템 — 개발 계획서 (초보자용)

> **버전**: v5.4.6 기준 | **작성일**: 2026-02-13 | **작성**: Ruby  
> **대상**: Python 초보 개발자 (프로그래밍 경험 0부터 시작 가능)

---

## 1. 프로그램 개요

### 1.1 이 프로그램은 뭘 하는 건가요?

창고에 들어오고 나가는 화학 제품(리튬 카보네이트)의 재고를 관리하는 **데스크톱 프로그램**입니다. 엑셀로 하던 재고 관리를 전용 프로그램으로 자동화한 것입니다.

### 1.2 핵심 기능 5가지

| 기능 | 설명 | 비유 |
|------|------|------|
| 입고(Inbound) | PDF 문서를 읽어서 자동 재고 등록 | 택배 송장 스캔 |
| 출고(Outbound) | 톤백 단위로 골라서 출고 처리 | 물건 꺼내기 |
| 재고 조회 | LOT별/톤백별 현황 조회 | 재고 목록 보기 |
| 통계 대시보드 | 총 재고, 입출고 현황, 차트 | 엑셀 피벗 |
| Excel 내보내기 | 재고 데이터를 Excel로 출력 | 보고서 생성 |

### 1.3 용어 정리 (★ 반드시 먼저 읽으세요)

| 용어 | 뜻 | 예시 |
|------|-----|------|
| **LOT** | 같은 날 같은 컨테이너로 들어온 제품 묶음 | 1125081447 |
| **톤백(MAXIBAG)** | LOT 안의 개별 큰 가방 (~500kg) | 1 LOT = 보통 10개 |
| **샘플(Sample)** | LOT당 1개 검사용 시료 (1kg) | 1 LOT = 1개 샘플 |
| **BL NO** | 선하증권 번호 | 258465668 |
| **SAP NO** | 고객사(SQM) 관리 번호 | 2200033057 |
| **NET WEIGHT** | 순 무게 (톤백 + 샘플) | 5,001kg = 5,000 + 1 |
| **Packing List** | 포장명세서 (★ 핵심 문서) | PDF |

### 1.4 데이터 구조

```
1건의 입고 = PDF 4종 (Invoice, Packing List, B/L, D/O)
    ↓ 파싱
inventory 테이블 (LOT 단위: 1 LOT = 1 행)
    └── inventory_tonbag (톤백 단위: 1 톤백 = 1 행)
            ├── 일반 톤백 10개 (각 500kg, is_sample=0)
            └── 샘플 1개 (1kg, is_sample=1)
```

---

## 2. 개발 환경 구성

### 2.1 설치할 프로그램

```bash
# 1. Python 3.10+ 설치 (python.org)
# 2. VS Code 설치 (code.visualstudio.com)
# 3. 라이브러리 설치 (cmd에서 한 줄씩 실행)
pip install ttkbootstrap       # UI 테마
pip install pandas             # 데이터 처리
pip install openpyxl           # Excel 읽기/쓰기
pip install pymupdf            # PDF 읽기
pip install google-genai       # Gemini AI OCR
pip install reportlab          # PDF 생성
```

### 2.2 폴더 구조

```
SQM_Inventory/
├── run_app.py              ← ★ 프로그램 시작점
├── version.py              ← 버전 정보
├── config.py               ← 설정 (DB 경로, API 키)
│
├── gui_app_modular/        ← ★ UI 코드
│   ├── main_app.py         ← 메인 앱 (모든 Mixin 조합)
│   ├── tabs/               ← 탭 화면들
│   │   ├── inventory_tab.py    ← 재고 리스트 (18컬럼)
│   │   ├── tonbag_tab.py       ← 톤백 리스트 (21컬럼)
│   │   ├── dashboard_tab.py    ← 통계 대시보드
│   │   └── log_tab.py          ← 로그
│   ├── mixins/             ← 기능 모듈
│   │   ├── toolbar_mixin.py    ← 상단 메뉴 버튼
│   │   └── theme_mixin.py      ← 테마 전환
│   └── utils/              ← UI 유틸리티
│       ├── ui_constants.py     ← 색상/폰트 상수
│       └── tree_enhancements.py ← 필터바, 합계바
│
├── engine_modules/         ← ★ 비즈니스 로직
│   ├── database.py             ← DB 생성/관리
│   └── inventory_modular/
│       ├── crud_mixin.py       ← 입고/수정/삭제
│       ├── outbound_mixin.py   ← 출고
│       ├── query_mixin.py      ← 조회/통계
│       └── export_mixin.py     ← Excel 내보내기
│
├── parsers/                ← ★ PDF 파싱
│   └── document_parser_modular/
│       ├── packing_mixin.py    ← Packing List 파싱
│       ├── invoice_mixin.py    ← Invoice 파싱
│       ├── bl_mixin.py         ← B/L 파싱
│       └── do_mixin.py         ← D/O 파싱
│
└── db/                     ← SQLite DB 파일
```

---

## 3. 데이터베이스 설계

### 3.1 핵심 테이블 — inventory (LOT 단위)

```sql
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id INTEGER,

    -- ★ 핵심 컬럼들
    sap_no TEXT,                              -- SQM 관리번호
    bl_no TEXT,                               -- 선하증권번호
    container_no TEXT,                        -- 컨테이너번호
    product TEXT,                             -- 제품명
    lot_no TEXT NOT NULL UNIQUE,              -- LOT번호 (유일값!)
    mxbg_pallet INTEGER DEFAULT 10,           -- 톤백 수
    net_weight REAL DEFAULT 0,                -- 순 무게(kg)
    salar_invoice_no TEXT,                    -- 인보이스 번호
    ship_date DATE,                           -- 선적일
    arrival_date DATE,                        -- 입항일
    free_time INTEGER DEFAULT 0,              -- 무료 장치 기간(일)
    warehouse TEXT DEFAULT 'GY',              -- 창고 코드
    customs TEXT,                             -- 통관 상태
    status TEXT DEFAULT 'AVAILABLE',          -- AVAILABLE / DEPLETED

    -- ★ 무게 관리 (입고/현재/출고)
    initial_weight REAL DEFAULT 0 CHECK(initial_weight >= 0),
    current_weight REAL DEFAULT 0 CHECK(current_weight >= 0),
    picked_weight REAL DEFAULT 0 CHECK(picked_weight >= 0),

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,

    FOREIGN KEY (shipment_id) REFERENCES shipment(id)
);
```

### 3.2 핵심 테이블 — inventory_tonbag (톤백 단위)

```sql
CREATE TABLE IF NOT EXISTS inventory_tonbag (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inventory_id INTEGER,

    -- ★ 복합 키
    sap_no TEXT,
    bl_no TEXT,
    lot_no TEXT NOT NULL,
    sub_lt INTEGER NOT NULL,          -- 순번 (1,2,3...)
    tonbag_no TEXT,                   -- "001"~"010" 또는 "S01"(샘플)
    tonbag_uid TEXT,                  -- "LOT번호-01" 전역 유니크

    -- ★ 핵심
    weight REAL DEFAULT 0 CHECK(weight >= 0),
    status TEXT DEFAULT 'AVAILABLE',  -- AVAILABLE / PICKED
    is_sample INTEGER DEFAULT 0,      -- 0=일반, 1=샘플

    -- 위치/출고 정보
    location TEXT,
    picked_date DATE,
    picked_to TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inventory_id) REFERENCES inventory(id),
    UNIQUE(sap_no, bl_no, lot_no, sub_lt)
);
```

### 3.3 출고 테이블

```sql
CREATE TABLE IF NOT EXISTS outbound (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outbound_no TEXT UNIQUE,
    customer TEXT,
    outbound_date DATE,
    total_qty_mt REAL,
    status TEXT DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outbound_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outbound_id INTEGER,
    inventory_id INTEGER,
    lot_no TEXT,
    qty_mt REAL,
    FOREIGN KEY (outbound_id) REFERENCES outbound(id)
);
```

### 3.4 관계도

```
inventory (1 LOT = 1행)
    │
    ├── 1:N → inventory_tonbag (1 LOT = 11행: 톤백10 + 샘플1)
    │
    └── 1:N → outbound_item (출고 항목)
                 └── N:1 → outbound (출고 건)
```


---

## 4. 개발 Phase 1 — 뼈대 만들기 (1~2일)

### 4.1 목표: "python run_app.py" → 빈 창이 뜬다

### 4.2 version.py

```python
# version.py
__version__ = '0.1.0'
APP_NAME = 'SQM 재고관리 시스템'
```

### 4.3 config.py

```python
# config.py
import os
from pathlib import Path

# ★ 프로그램이 있는 폴더 기준으로 경로 설정
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = BASE_DIR / 'db'
DB_PATH = DB_DIR / 'sqm_inventory.db'
BACKUP_DIR = BASE_DIR / 'backup'
OUTPUT_DIR = BASE_DIR / 'output'
LOG_DIR = BASE_DIR / 'logs'

# 폴더가 없으면 자동 생성
for d in [DB_DIR, BACKUP_DIR, OUTPUT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Gemini API (나중에 설정)
GEMINI_API_KEY = ''
GEMINI_MODEL = 'gemini-2.0-flash'
```

### 4.4 run_app.py — 프로그램 시작점

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 — 메인 실행 파일
★★★ 이 파일만 실행하면 됩니다 ★★★

실행: python run_app.py
"""
import os
import sys

# 패키지 경로 추가 (이 줄이 있어야 다른 폴더의 파일을 import 가능)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from version import __version__, APP_NAME


def check_dependencies():
    """필수 라이브러리 확인"""
    missing = []
    for module, pip_name in [
        ('pandas', 'pandas'),
        ('openpyxl', 'openpyxl'),
        ('fitz', 'pymupdf'),
        ('ttkbootstrap', 'ttkbootstrap'),
    ]:
        try:
            __import__(module)
            print(f"  ✅ {pip_name}")
        except ImportError:
            print(f"  ❌ {pip_name} — pip install {pip_name}")
            missing.append(pip_name)
    return len(missing) == 0


def main():
    print(f"{'='*50}")
    print(f"  {APP_NAME} v{__version__}")
    print(f"{'='*50}")

    if not check_dependencies():
        print("\n❌ 필수 라이브러리를 설치해주세요.")
        sys.exit(1)

    # GUI 실행
    from gui_app_modular import SQMInventoryApp
    app = SQMInventoryApp()
    app.run()


if __name__ == "__main__":
    main()
```

### 4.5 gui_app_modular/main_app.py — 메인 창

```python
# gui_app_modular/main_app.py
"""
★ 프로그램의 메인 창을 만드는 파일
★ 모든 탭과 기능이 여기에 조합됩니다
"""
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from version import __version__, APP_NAME


class SQMInventoryApp:
    """메인 앱 클래스"""

    def __init__(self):
        # ── 1단계: 윈도우 생성 ──
        self.root = ttk.Window(
            title=f"(주)지와이로지스 — {APP_NAME} v{__version__}",
            themename="flatly",      # 밝은 테마
            size=(1500, 900),
            minsize=(1200, 700),
        )
        self.root.place_window_center()  # 화면 중앙에 배치

        # ── 2단계: 상단 툴바 (Phase 2에서 구현) ──
        self._setup_toolbar()

        # ── 3단계: 탭 노트북 (Phase 2에서 구현) ──
        self._setup_tabs()

        # ── 4단계: 하단 상태바 ──
        self._setup_statusbar()

    def _setup_toolbar(self):
        """상단 툴바 — 빈 프레임으로 시작"""
        self.toolbar = tk.Frame(self.root, bg='#2c3e50', height=45)
        self.toolbar.pack(fill=X, side=TOP)

        tk.Label(self.toolbar, text=f"  {APP_NAME} v{__version__}",
                 bg='#2c3e50', fg='white',
                 font=('맑은 고딕', 11, 'bold')).pack(side=LEFT, padx=10)

    def _setup_tabs(self):
        """탭 — 빈 탭으로 시작"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=YES, padx=5, pady=5)

        # 빈 탭 추가 (Phase 2에서 내용 채움)
        self.tab_inventory = ttk.Frame(self.notebook)
        self.tab_tonbag = ttk.Frame(self.notebook)
        self.tab_dashboard = ttk.Frame(self.notebook)
        self.tab_log = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_inventory, text="📦 재고리스트")
        self.notebook.add(self.tab_tonbag, text="🎒 톤백리스트")
        self.notebook.add(self.tab_dashboard, text="📊 통계")
        self.notebook.add(self.tab_log, text="📝 로그")

    def _setup_statusbar(self):
        """하단 상태바"""
        self.statusbar = tk.Frame(self.root, bg='#ecf0f1', height=25)
        self.statusbar.pack(fill=X, side=BOTTOM)
        tk.Label(self.statusbar, text=f" v{__version__} | DB: sqm_inventory.db",
                 bg='#ecf0f1', fg='#7f8c8d',
                 font=('맑은 고딕', 9)).pack(side=LEFT)

    def run(self):
        """프로그램 실행"""
        self.root.mainloop()
```

### 4.6 gui_app_modular/__init__.py

```python
# gui_app_modular/__init__.py
from .main_app import SQMInventoryApp
__all__ = ['SQMInventoryApp']
```

**✅ Phase 1 확인**: `python run_app.py` → 4개 빈 탭이 있는 창이 뜨면 성공!

---

## 5. 개발 Phase 2 — DB + 엔진 (3~4일)

### 5.1 목표: DB에 데이터를 넣고 꺼낼 수 있다

### 5.2 engine_modules/database.py — DB 관리

```python
# engine_modules/database.py
"""
★ SQLite 데이터베이스 관리
★ 초보자 핵심: 이 파일이 DB 파일을 만들고, 테이블을 생성합니다
"""
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    """SQLite DB 래퍼"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """DB 연결"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, timeout=30)
        self.conn.row_factory = sqlite3.Row  # ★ 딕셔너리처럼 접근 가능
        self.conn.execute("PRAGMA journal_mode=WAL")  # 동시 접근 성능 향상
        self.conn.execute("PRAGMA foreign_keys=ON")

    def _create_tables(self):
        """테이블 생성 (첫 실행 시 자동)"""
        # ── inventory 테이블 (LOT 단위) ──
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sap_no TEXT,
                bl_no TEXT,
                container_no TEXT,
                product TEXT,
                lot_no TEXT NOT NULL UNIQUE,
                mxbg_pallet INTEGER DEFAULT 10,
                net_weight REAL DEFAULT 0 CHECK(net_weight >= 0),
                salar_invoice_no TEXT,
                ship_date DATE,
                arrival_date DATE,
                free_time INTEGER DEFAULT 0,
                warehouse TEXT DEFAULT 'GY',
                customs TEXT,
                status TEXT DEFAULT 'AVAILABLE',
                initial_weight REAL DEFAULT 0 CHECK(initial_weight >= 0),
                current_weight REAL DEFAULT 0 CHECK(current_weight >= 0),
                picked_weight REAL DEFAULT 0 CHECK(picked_weight >= 0),
                location TEXT,
                folio TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)

        # ── inventory_tonbag 테이블 (톤백 단위) ──
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory_tonbag (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER,
                sap_no TEXT,
                bl_no TEXT,
                lot_no TEXT NOT NULL,
                sub_lt INTEGER NOT NULL,
                tonbag_no TEXT,
                tonbag_uid TEXT,
                weight REAL DEFAULT 0 CHECK(weight >= 0),
                status TEXT DEFAULT 'AVAILABLE',
                is_sample INTEGER DEFAULT 0,
                location TEXT,
                picked_date DATE,
                picked_to TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (inventory_id) REFERENCES inventory(id),
                UNIQUE(sap_no, bl_no, lot_no, sub_lt)
            )
        """)

        # ── outbound 테이블 ──
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS outbound (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                outbound_no TEXT UNIQUE,
                customer TEXT,
                outbound_date DATE,
                total_qty_mt REAL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()
        logger.info("DB 테이블 생성/확인 완료")

    # ── 기본 DB 조작 메서드 ──

    def execute(self, sql: str, params=None):
        """SQL 실행 (INSERT, UPDATE, DELETE)"""
        cursor = self.conn.execute(sql, params or [])
        self.conn.commit()
        return cursor

    def fetchall(self, sql: str, params=None):
        """여러 행 조회"""
        return self.conn.execute(sql, params or []).fetchall()

    def fetchone(self, sql: str, params=None):
        """1행 조회"""
        return self.conn.execute(sql, params or []).fetchone()

    def close(self):
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
```

### 5.3 engine_modules/inventory_modular/crud_mixin.py — 입고

```python
# engine_modules/inventory_modular/crud_mixin.py
"""
★ CRUD = Create(생성), Read(읽기), Update(수정), Delete(삭제)
★ 이 파일은 LOT과 톤백을 DB에 넣는 핵심 로직입니다
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CrudMixin:
    """입고/수정/삭제 기능"""

    def add_inventory(self, lot_data: dict) -> int:
        """
        ★ LOT 1건 입고 (+ 톤백 자동 생성)

        lot_data 예시:
        {
            'lot_no': '1125081447',
            'sap_no': '2200033057',
            'bl_no': '258465668',
            'container_no': 'MRSU6643467',
            'product': 'LITHIUM CARBONATE',
            'mxbg_pallet': 10,        # 톤백 수
            'net_weight': 5001.0,      # 순 무게 (톤백 + 샘플)
            'salar_invoice_no': 'F4AU5050206',
            'ship_date': '2025-09-06',
            'arrival_date': '2025-10-17',
            'free_time': 25,
        }
        """
        lot_no = lot_data['lot_no']
        net_weight = lot_data.get('net_weight', 0)
        mxbg = lot_data.get('mxbg_pallet', 10)

        # ── 1. inventory 테이블에 LOT 등록 ──
        cursor = self.db.execute("""
            INSERT INTO inventory (
                lot_no, sap_no, bl_no, container_no, product,
                mxbg_pallet, net_weight, salar_invoice_no,
                ship_date, arrival_date, free_time,
                warehouse, status, customs,
                initial_weight, current_weight, picked_weight
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'GY', 'AVAILABLE', 'Cleared', ?, ?, 0)
        """, [
            lot_no, lot_data.get('sap_no'), lot_data.get('bl_no'),
            lot_data.get('container_no'), lot_data.get('product'),
            mxbg, net_weight, lot_data.get('salar_invoice_no'),
            lot_data.get('ship_date'), lot_data.get('arrival_date'),
            lot_data.get('free_time', 0),
            net_weight, net_weight,  # initial = current = net_weight
        ])
        inventory_id = cursor.lastrowid

        # ── 2. 톤백 생성 (★ 핵심 무게 계산) ──
        #
        # 패킹리스트 기준:
        #   NET WEIGHT 5,001kg = 톤백(5,000kg) + 샘플(1kg)
        #   톤백 개별 무게 = (net_weight - 샘플무게) / 톤백수
        #                  = (5,001 - 1) / 10 = 500kg
        #
        sample_weight = 1.0  # 샘플은 항상 1kg
        tonbag_weight = (net_weight - sample_weight) / mxbg  # ★ 핵심 공식

        for i in range(1, mxbg + 1):
            tonbag_no = f"{i:03d}"           # "001", "002", ..., "010"
            tonbag_uid = f"{lot_no}-{i:02d}" # "1125081447-01"

            self.db.execute("""
                INSERT INTO inventory_tonbag (
                    inventory_id, sap_no, bl_no, lot_no, sub_lt,
                    tonbag_no, tonbag_uid, weight, status, is_sample
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'AVAILABLE', 0)
            """, [
                inventory_id, lot_data.get('sap_no'), lot_data.get('bl_no'),
                lot_no, i, tonbag_no, tonbag_uid, tonbag_weight,
            ])

        # ── 3. 샘플 톤백 생성 (1kg, is_sample=1) ──
        sample_no = "S01"
        sample_uid = f"{lot_no}-S1"

        self.db.execute("""
            INSERT INTO inventory_tonbag (
                inventory_id, sap_no, bl_no, lot_no, sub_lt,
                tonbag_no, tonbag_uid, weight, status, is_sample
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'AVAILABLE', 1)
        """, [
            inventory_id, lot_data.get('sap_no'), lot_data.get('bl_no'),
            lot_no, mxbg + 1, sample_no, sample_uid, sample_weight,
        ])

        logger.info(f"입고 완료: {lot_no} (톤백 {mxbg}개 × {tonbag_weight}kg + 샘플 1kg)")
        return inventory_id

    def get_inventory(self) -> list:
        """전체 재고 조회"""
        rows = self.db.fetchall("""
            SELECT * FROM inventory ORDER BY lot_no
        """)
        return [dict(r) for r in rows]

    def get_tonbags(self, lot_no: str = None) -> list:
        """톤백 조회 (lot_no 지정 시 해당 LOT만)"""
        if lot_no:
            rows = self.db.fetchall(
                "SELECT * FROM inventory_tonbag WHERE lot_no=? ORDER BY sub_lt",
                [lot_no]
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM inventory_tonbag ORDER BY lot_no, sub_lt"
            )
        return [dict(r) for r in rows]
```

### 5.4 엔진 조합 — engine.py

```python
# engine.py
"""엔진 진입점 — 모든 Mixin을 조합"""
from engine_modules.database import Database
from engine_modules.inventory_modular.crud_mixin import CrudMixin
from config import DB_PATH


class InventoryEngine(CrudMixin):
    """재고 엔진 (모든 Mixin 합체)"""

    def __init__(self):
        self.db = Database(str(DB_PATH))

    def close(self):
        self.db.close()
```

**✅ Phase 2 확인**: Python 콘솔에서 테스트

```python
from engine import InventoryEngine

eng = InventoryEngine()
eng.add_inventory({
    'lot_no': 'TEST001',
    'product': 'LITHIUM CARBONATE',
    'net_weight': 5001.0,
    'mxbg_pallet': 10,
})
print(eng.get_inventory())   # LOT 1건 나오면 성공!
print(eng.get_tonbags('TEST001'))  # 톤백 11개 (10+샘플) 나오면 성공!
eng.close()
```


---

## 6. 개발 Phase 3 — 재고 리스트 탭 UI (5~7일)

### 6.1 목표: DB 데이터가 테이블에 표시된다

### 6.2 전체 화면 구조

```
┌─────────────────────────────────────────────────────────────┐
│ 🔽 필터: PRODUCT:[전체▼] LOT NO:[전체▼] CONTAINER:[전체▼]   │
│          BL NO:[전체▼] SAP NO:[전체▼] 상태:[전체▼] [✖초기화] │
├─────────────────────────────────────────────────────────────┤
│ 표시 컬럼: ☑SAP NO  ☑BL NO  ☑CONTAINER  ☑SHIP DATE ...    │
├─────────────────────────────────────────────────────────────┤
│ ┌───┬──────────┬─────────┬──────────┬───────────┬────┐     │
│ │No.│ LOT NO   │ SAP NO  │ BL NO    │CONTAINER  │MXBG│ ... │
│ ├───┼──────────┼─────────┼──────────┼───────────┼────┤     │
│ │ 1 │1125072729│220003305│258465668 │MRSU664346 │ 10 │     │
│ │ 2 │1125072730│220008305│258465668 │MRSU664546 │ 10 │     │
│ │...│          │         │          │           │    │     │
│ └───┴──────────┴─────────┴──────────┴───────────┴────┘     │
├─────────────────────────────────────────────────────────────┤
│ 📊 행수: 20  📦 NET: 100,020  💰 Balance: 100,020  MXBG:200│
└─────────────────────────────────────────────────────────────┘
```

### 6.3 inventory_tab.py — 재고 리스트 (★ 핵심 코드)

```python
# gui_app_modular/tabs/inventory_tab.py
"""
★★★ 프로그램에서 가장 중요한 화면 ★★★
★★★ 재고 현황을 18컬럼 테이블로 보여줍니다 ★★★

구조:
  1. 필터바 (HeaderFilterBar) — 드롭다운으로 검색
  2. 컬럼 토글바 — 컬럼 표시/숨김
  3. Treeview — 18컬럼 테이블 (메인)
  4. 합계바 (FooterTotalBar) — 행수, 무게 합계
"""
import tkinter as tk
from tkinter import ttk, END
import logging

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ★ 18개 컬럼 정의 (이것이 테이블의 뼈대)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# (컬럼ID, 표시명, 폭, 정렬, 기본표시여부)
INVENTORY_COLUMNS = [
    ('row_num',          'No.',           50, 'center', True),
    ('lot_no',           'LOT NO',       120, 'center', True),
    ('sap_no',           'SAP NO',       120, 'center', True),
    ('bl_no',            'BL NO',        140, 'center', True),
    ('container_no',     'CONTAINER',    130, 'center', True),
    ('product',          'PRODUCT',      160, 'center', True),
    ('mxbg_pallet',      'MXBG',          70, 'center', True),
    ('net_weight',       'NET(Kg)',      100, 'e',      True),
    ('salar_invoice_no', 'INVOICE NO',   100, 'center', True),
    ('ship_date',        'SHIP DATE',     95, 'center', True),
    ('arrival_date',     'ARRIVAL',       95, 'center', True),
    ('free_time',        'FREE TIME',     80, 'center', True),
    ('warehouse',        'WH',            80, 'center', True),
    ('status',           'STATUS',        90, 'center', True),
    ('customs',          'CUSTOMS',       90, 'center', True),
    ('current_weight',   'Balance(Kg)',  100, 'e',      True),
    ('initial_weight',   'Inbound(Kg)',  100, 'e',      True),
    ('outbound_weight',  'Outbound(Kg)', 100, 'e',      True),
]


class InventoryTabMixin:
    """재고 리스트 탭 — Mixin으로 main_app에 합체됨"""

    def _setup_inventory_tab(self):
        """
        ★ 탭 초기화 — 이 함수가 호출되면 재고 탭 화면이 만들어짐

        만드는 순서:
        1. 필터바 (상단 드롭다운)
        2. 컬럼 토글바
        3. Treeview (18컬럼 테이블)
        4. 합계바 (하단)
        """

        # ━━ 1. 필터바 ━━
        self._setup_inv_filter_bar()

        # ━━ 2. 컬럼 토글바 ━━
        self._setup_inv_column_toggle()

        # ━━ 3. Treeview (메인 테이블) ━━
        self._setup_inv_treeview()

        # ━━ 4. 합계바 ━━
        self._setup_inv_footer()

    # ──────────────────────────
    # 1. 필터바
    # ──────────────────────────
    def _setup_inv_filter_bar(self):
        """
        ★ 필터바: 각 컬럼별 드롭다운으로 데이터 필터링

        예: PRODUCT 드롭다운에서 "LITHIUM CARBONATE" 선택
            → 해당 제품만 테이블에 표시

        linked_pairs: BL NO와 SAP NO는 1:1 관계이므로
                      BL을 선택하면 SAP이 자동 비활성화
        """
        filter_frame = tk.Frame(self.tab_inventory, bg='#e8ecf0', pady=2)
        filter_frame.pack(fill='x')

        # 필터 순서 (v5.4.6: PRODUCT 먼저)
        filter_cols = [
            ('product',      'PRODUCT',    160),
            ('lot_no',       'LOT NO',     120),
            ('container_no', 'CONTAINER',  130),
            ('bl_no',        'BL NO',      140),
            ('sap_no',       'SAP NO',     120),
            ('status',       '상태',        90),
        ]

        tk.Label(filter_frame, text="🔽 필터:", bg='#e8ecf0',
                 font=('맑은 고딕', 10, 'bold')).pack(side='left', padx=5)

        self._inv_filter_vars = {}
        self._inv_filter_combos = {}

        for col_id, label, width in filter_cols:
            tk.Label(filter_frame, text=f"{label}:", bg='#e8ecf0',
                     font=('맑은 고딕', 9)).pack(side='left', padx=2)

            var = tk.StringVar(value="전체")
            combo = ttk.Combobox(filter_frame, textvariable=var,
                                 values=["전체"], state="readonly",
                                 width=max(width // 10, 8))
            combo.pack(side='left', padx=4)
            combo.bind('<<ComboboxSelected>>', lambda e: self._on_inv_filter_apply())

            self._inv_filter_vars[col_id] = var
            self._inv_filter_combos[col_id] = combo

        ttk.Button(filter_frame, text="✖ 초기화", width=8,
                   command=self._reset_inv_filters).pack(side='left', padx=5)

    # ──────────────────────────
    # 2. 컬럼 토글바
    # ──────────────────────────
    def _setup_inv_column_toggle(self):
        """컬럼 표시/숨김 체크박스"""
        toggle_frame = tk.Frame(self.tab_inventory, bg='#f0f2f5', pady=2)
        toggle_frame.pack(fill='x')

        tk.Label(toggle_frame, text="표시 컬럼:", bg='#f0f2f5',
                 font=('맑은 고딕', 9, 'bold')).pack(side='left', padx=5)

        self._col_toggle_vars = {}
        for col_id, label, width, anchor, visible in INVENTORY_COLUMNS:
            if col_id in ('row_num', 'lot_no'):  # 필수 컬럼은 숨길 수 없음
                continue
            var = tk.BooleanVar(value=visible)
            cb = tk.Checkbutton(toggle_frame, text=label, variable=var,
                                bg='#f0f2f5', font=('맑은 고딕', 8),
                                command=self._apply_column_toggle)
            cb.pack(side='left', padx=2)
            self._col_toggle_vars[col_id] = var

    # ──────────────────────────
    # 3. Treeview (★ 핵심)
    # ──────────────────────────
    def _setup_inv_treeview(self):
        """
        ★★★ 18컬럼 Treeview — 프로그램의 메인 테이블 ★★★

        Treeview란?
        - tkinter에서 엑셀 같은 표를 만드는 위젯
        - columns: 컬럼 ID 목록
        - heading: 컬럼 제목 (헤더)
        - insert: 행 추가
        """
        # 스크롤바 포함 프레임
        tree_frame = ttk.Frame(self.tab_inventory)
        tree_frame.pack(fill='both', expand=True, padx=5)

        # 수직 스크롤바
        vsb = ttk.Scrollbar(tree_frame, orient='vertical')
        vsb.pack(side='right', fill='y')

        # 수평 스크롤바
        hsb = ttk.Scrollbar(tree_frame, orient='horizontal')
        hsb.pack(side='bottom', fill='x')

        # ★ Treeview 생성
        col_ids = [c[0] for c in INVENTORY_COLUMNS]

        self.tree_inventory = ttk.Treeview(
            tree_frame,
            columns=col_ids,          # 컬럼 ID 목록
            show="headings",          # 헤더만 보기 (트리 아이콘 숨김)
            height=25,                # 보이는 행 수
            selectmode='extended',    # 다중 선택 가능
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )

        vsb.config(command=self.tree_inventory.yview)
        hsb.config(command=self.tree_inventory.xview)

        # ★ 컬럼별 헤더 설정
        for col_id, label, width, anchor, visible in INVENTORY_COLUMNS:
            self.tree_inventory.heading(
                col_id, text=label,
                command=lambda c=col_id: self._sort_inventory(c)
            )
            self.tree_inventory.column(
                col_id, width=width, anchor=anchor, minwidth=50
            )

        self.tree_inventory.pack(fill='both', expand=True)

        # ★ 더블클릭 이벤트 — 톤백 탭으로 이동
        self.tree_inventory.bind('<Double-1>', self._on_lot_double_click)

        # ★ 줄무늬 (홀수행/짝수행 배경색 다르게)
        self.tree_inventory.tag_configure('oddrow', background='#f8f9fa')
        self.tree_inventory.tag_configure('evenrow', background='#ffffff')

    # ──────────────────────────
    # 4. 합계바
    # ──────────────────────────
    def _setup_inv_footer(self):
        """하단 합계 바 — 행수, NET, Balance, MXBG"""
        footer = tk.Frame(self.tab_inventory, bg='#d5dbe0', height=30)
        footer.pack(fill='x', side='bottom')

        self._footer_labels = {}
        for key, label, default in [
            ('rows',       '📊 행수:',        '0'),
            ('net_kg',     '📦 NET(Kg):',     '0'),
            ('balance_kg', '💰 Balance(Kg):', '0'),
            ('mxbg',       '📦 MXBG:',        '0'),
        ]:
            tk.Label(footer, text=f" {label}", bg='#d5dbe0',
                     font=('맑은 고딕', 9, 'bold')).pack(side='left')
            lbl = tk.Label(footer, text=default, bg='#d5dbe0',
                           font=('맑은 고딕', 9), fg='#2c3e50')
            lbl.pack(side='left', padx=(0, 15))
            self._footer_labels[key] = lbl

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 데이터 로드 / 갱신
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _refresh_inventory(self):
        """
        ★ DB에서 데이터를 읽어 Treeview에 표시하는 핵심 함수

        호출 시점:
        - 프로그램 시작 시
        - 입고/출고 후
        - 필터 변경 시
        - F5(새로고침) 시
        """
        # 1. 기존 데이터 모두 삭제
        for item in self.tree_inventory.get_children():
            self.tree_inventory.delete(item)

        # 2. DB에서 재고 데이터 가져오기
        inventory = self.engine.get_inventory()

        # 3. 필터 적용
        filtered = self._apply_inv_filter(inventory)

        # 4. 필터 드롭다운 값 업데이트
        self._update_filter_values(inventory)

        # 5. Treeview에 행 추가
        for idx, item in enumerate(filtered, 1):
            tag = 'oddrow' if idx % 2 == 1 else 'evenrow'

            values = (
                idx,                                    # No.
                item.get('lot_no', ''),                 # LOT NO
                item.get('sap_no', ''),                 # SAP NO
                item.get('bl_no', ''),                  # BL NO
                item.get('container_no', ''),           # CONTAINER
                item.get('product', ''),                # PRODUCT
                item.get('mxbg_pallet', ''),            # MXBG
                f"{item.get('net_weight', 0):,.0f}",    # NET(Kg)
                item.get('salar_invoice_no', ''),       # INVOICE NO
                item.get('ship_date', ''),              # SHIP DATE
                item.get('arrival_date', ''),           # ARRIVAL
                item.get('free_time', ''),              # FREE TIME
                item.get('warehouse', ''),              # WH
                item.get('status', ''),                 # STATUS
                item.get('customs', ''),                # CUSTOMS
                f"{item.get('current_weight', 0):,.0f}",  # Balance
                f"{item.get('initial_weight', 0):,.0f}",  # Inbound
                f"{item.get('picked_weight', 0):,.0f}",   # Outbound
            )

            self.tree_inventory.insert('', END, values=values, tags=(tag,))

        # 6. 합계 업데이트
        self._update_inv_footer()

    def _apply_inv_filter(self, inventory: list) -> list:
        """필터 적용 — 선택된 드롭다운 값으로 데이터 걸러냄"""
        result = inventory

        for col_id, var in self._inv_filter_vars.items():
            selected = var.get()
            if selected == "전체":
                continue

            # 해당 컬럼의 값이 선택된 값과 일치하는 행만 남김
            result = [r for r in result if str(r.get(col_id, '')) == selected]

        return result

    def _update_filter_values(self, inventory: list):
        """필터 드롭다운에 선택 가능한 값 목록 업데이트"""
        for col_id, combo in self._inv_filter_combos.items():
            # 해당 컬럼의 고유값 추출
            unique_vals = sorted(set(
                str(r.get(col_id, '')) for r in inventory if r.get(col_id)
            ))
            combo['values'] = ["전체"] + unique_vals

    def _update_inv_footer(self):
        """합계 계산"""
        net_total = balance_total = mxbg_total = 0
        rows = 0

        for item_id in self.tree_inventory.get_children(''):
            vals = self.tree_inventory.item(item_id, 'values')
            rows += 1
            try:
                net_total += float(str(vals[7]).replace(',', ''))
            except (ValueError, IndexError):
                pass
            try:
                mxbg_total += int(float(str(vals[6]).replace(',', '')))
            except (ValueError, IndexError):
                pass
            try:
                balance_total += float(str(vals[15]).replace(',', ''))
            except (ValueError, IndexError):
                pass

        self._footer_labels['rows'].config(text=f"{rows:,}")
        self._footer_labels['net_kg'].config(text=f"{net_total:,.0f}")
        self._footer_labels['balance_kg'].config(text=f"{balance_total:,.0f}")
        self._footer_labels['mxbg'].config(text=f"{mxbg_total:,}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 이벤트 핸들러
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _on_inv_filter_apply(self):
        """필터 변경 시 호출"""
        self._refresh_inventory()

    def _reset_inv_filters(self):
        """필터 초기화"""
        for var in self._inv_filter_vars.values():
            var.set("전체")
        self._refresh_inventory()

    def _on_lot_double_click(self, event):
        """
        LOT 더블클릭 → 톤백탭 이동 + 해당 LOT 필터 설정

        ★ 사용자가 재고리스트에서 LOT을 더블클릭하면
          톤백탭으로 자동 이동하고, 해당 LOT의 톤백만 보여줌
        """
        selection = self.tree_inventory.selection()
        if not selection:
            return
        values = self.tree_inventory.item(selection[0], 'values')
        if not values or len(values) < 2:
            return

        lot_no = str(values[1]).strip()
        # 톤백 탭으로 전환
        if hasattr(self, 'notebook'):
            self.notebook.select(1)  # 톤백탭 인덱스

    def _sort_inventory(self, col):
        """컬럼 클릭 시 정렬"""
        items = [(self.tree_inventory.set(k, col), k)
                 for k in self.tree_inventory.get_children('')]
        items.sort()
        for idx, (val, k) in enumerate(items):
            self.tree_inventory.move(k, '', idx)

    def _apply_column_toggle(self):
        """컬럼 표시/숨김 적용"""
        for col_id, var in self._col_toggle_vars.items():
            if var.get():
                self.tree_inventory.column(col_id, width=100)
            else:
                self.tree_inventory.column(col_id, width=0, minwidth=0)
```

### 6.4 main_app.py 업데이트 — 엔진 연결

```python
# main_app.py에 추가할 내용

from engine import InventoryEngine
from .tabs.inventory_tab import InventoryTabMixin

class SQMInventoryApp(InventoryTabMixin):  # ★ Mixin 합체
    def __init__(self):
        # 엔진 초기화
        self.engine = InventoryEngine()

        # 윈도우 생성 (Phase 1 코드)
        self.root = ttk.Window(...)
        self._setup_toolbar()
        self._setup_tabs()
        self._setup_statusbar()

        # ★ 탭 내용 설정 (Phase 3)
        self._setup_inventory_tab()

        # ★ 데이터 로드
        self._refresh_inventory()
```

**✅ Phase 3 확인**: 프로그램 실행 → 재고 리스트에 18컬럼 테이블이 보이면 성공!


---

## 7. 개발 Phase 4 — 톤백 리스트 + 대시보드 (4~5일)

### 7.1 톤백 리스트 탭 — 21컬럼

재고 리스트 18열에 TONBAG NO, UID, LOCATION을 추가한 21열 테이블입니다.

```python
# gui_app_modular/tabs/tonbag_tab.py (핵심 부분)

class TonbagTabMixin:
    def _setup_tonbag_tab(self):
        # 21개 컬럼 정의
        self._tonbag_columns = [
            ('row_num',         'No.',          50, 'center'),
            ('lot_no',          'LOT NO',      120, 'center'),
            ('tonbag_no_print', 'TONBAG NO',    90, 'center'),  # ★ 001~010, S01
            ('tonbag_uid',      'UID',         150, 'center'),  # ★ LOT-01, LOT-S1
            ('sap_no',          'SAP NO',      120, 'center'),
            ('bl_no',           'BL NO',       140, 'center'),
            ('container_no',    'CONTAINER',   130, 'center'),
            ('product',         'PRODUCT',     160, 'center'),
            ('mxbg_pallet',     'MXBG',         70, 'center'),
            ('location',        'LOCATION',     90, 'center'),  # ★ 창고 위치
            ('net_weight',      'NET(Kg)',     100, 'e'),
            ('salar_invoice_no','INVOICE NO',  100, 'center'),
            ('ship_date',       'SHIP DATE',    95, 'center'),
            ('arrival_date',    'ARRIVAL',      95, 'center'),
            ('free_time',       'FREE TIME',    80, 'center'),
            ('warehouse',       'WH',           80, 'center'),
            ('tonbag_status',   'STATUS',       90, 'center'),
            ('customs',         'CUSTOMS',      90, 'center'),
            ('current_weight',  'Balance(Kg)', 100, 'e'),
            ('initial_weight',  'Inbound(Kg)', 100, 'e'),
            ('outbound_weight', 'Outbound(Kg)',100, 'e'),
        ]

        # Treeview 생성 (inventory_tab과 동일 패턴)
        col_ids = [c[0] for c in self._tonbag_columns]
        self.tree_sublot = ttk.Treeview(
            tree_frame, columns=col_ids, show="headings", height=20,
            selectmode='extended'
        )

        for col_id, label, width, anchor in self._tonbag_columns:
            self.tree_sublot.heading(col_id, text=label)
            self.tree_sublot.column(col_id, width=width, anchor=anchor)

    def _refresh_tonbag_list(self):
        """톤백 리스트 갱신 — inventory + inventory_tonbag JOIN"""
        for item in self.tree_sublot.get_children():
            self.tree_sublot.delete(item)

        # ★ SQL JOIN: 톤백에 LOT 정보를 결합
        rows = self.engine.db.fetchall("""
            SELECT
                t.lot_no, t.tonbag_no, t.tonbag_uid,
                i.sap_no, i.bl_no, i.container_no, i.product,
                i.mxbg_pallet, t.location, i.net_weight,
                i.salar_invoice_no, i.ship_date, i.arrival_date,
                i.free_time, i.warehouse, t.status AS tonbag_status,
                i.customs, t.weight, t.weight AS initial_w,
                CASE WHEN t.status='PICKED' THEN t.weight ELSE 0 END AS outbound_w
            FROM inventory_tonbag t
            JOIN inventory i ON t.lot_no = i.lot_no
            ORDER BY t.lot_no, t.sub_lt
        """)

        for idx, r in enumerate(rows, 1):
            tag = 'oddrow' if idx % 2 == 1 else 'evenrow'
            # 샘플 행은 다른 색상으로 표시
            if 'S' in str(r['tonbag_no'] or ''):
                tag = 'sample_row'

            values = (idx, r['lot_no'], r['tonbag_no'], r['tonbag_uid'],
                      r['sap_no'], r['bl_no'], r['container_no'], r['product'],
                      r['mxbg_pallet'], r['location'] or '', f"{r['net_weight']:,.0f}",
                      r['salar_invoice_no'], r['ship_date'], r['arrival_date'],
                      r['free_time'], r['warehouse'], r['tonbag_status'],
                      r['customs'], f"{r['weight']:,.0f}",
                      f"{r['initial_w']:,.0f}", f"{r['outbound_w']:,.0f}")

            self.tree_sublot.insert('', 'end', values=values, tags=(tag,))

        # 샘플 행 색상
        self.tree_sublot.tag_configure('sample_row', background='#fff3cd')
```

### 7.2 통계 대시보드 — dashboard_tab.py

```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│📦 총 재고 │ │📋 총 LOT │ │📥 금일입고│ │📤 금일출고│ │● 기존 톤백│
│100,020 kg│ │  20개    │ │  0 kg    │ │  0 kg    │ │  220개   │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘

┌─ 제품별 재고 현황 ────────────────────────────────────────────┐
│ Product           │LOT수│톤백(kg)│톤백수│샘플(kg)│샘플수│총무게  │
│ LITHIUM CARBONATE │ 20  │100,000 │ 200  │  20   │  20 │100,020│
│ 합계              │ 20  │100,000 │ 200  │  20   │  20 │100,020│
└──────────────────────────────────────────────────────────────┘
```

```python
# gui_app_modular/tabs/dashboard_tab.py (핵심 부분)

class DashboardTabMixin:
    def _setup_dashboard_tab(self):
        """대시보드 카드 + 제품별 테이블"""

        # ── 상단: 요약 카드 5개 ──
        card_frame = ttk.Frame(self.tab_dashboard)
        card_frame.pack(fill='x', padx=10, pady=10)

        self._dashboard_cards = {}
        cards = [
            ('total_weight', '📦 총 재고',   '0 kg'),
            ('total_lots',   '📋 총 LOT',   '0개'),
            ('inbound_today','📥 금일 입고', '0 kg'),
            ('outbound_today','📤 금일 출고','0 kg'),
            ('total_tonbags','● 기존 톤백',  '0개'),
        ]

        for key, title, default in cards:
            frame = tk.LabelFrame(card_frame, text=title,
                                  font=('맑은 고딕', 10, 'bold'))
            frame.pack(side='left', expand=True, fill='both', padx=5)

            lbl = tk.Label(frame, text=default,
                           font=('맑은 고딕', 18, 'bold'), fg='#2c3e50')
            lbl.pack(pady=10)
            self._dashboard_cards[key] = lbl

        # ── 하단: 제품별 테이블 ──
        # (생략: inventory_tab과 유사한 Treeview 패턴)

    def _refresh_dashboard(self):
        """대시보드 데이터 갱신"""
        summary = self.engine.db.fetchone("""
            SELECT
                COALESCE(SUM(current_weight), 0) as total_weight,
                COUNT(*) as total_lots
            FROM inventory WHERE status='AVAILABLE'
        """)

        self._dashboard_cards['total_weight'].config(
            text=f"{summary['total_weight']:,.0f} kg")
        self._dashboard_cards['total_lots'].config(
            text=f"{summary['total_lots']}개")

        # ★ 제품별 톤백/샘플 통계 (합계가 중복되지 않도록!)
        # total = tonbag_kg + sample_kg (SQL raw값 직접 사용 X)
```

---

## 8. 개발 Phase 5 — PDF 입고 시스템 (7~10일)

### 8.1 PDF 파싱이란?

PDF 문서에서 텍스트를 추출하고, 정규식(Regex)으로 필요한 데이터를 뽑아내는 것입니다. **이 단계가 가장 어렵습니다.**

### 8.2 문서 유형 자동 감지

```python
# parsers/document_parser_modular/base.py

import fitz  # PyMuPDF
import re

class DocumentParserBase:
    def parse(self, pdf_path: str) -> dict:
        """PDF를 읽어서 데이터 딕셔너리로 반환"""
        # 1. PDF에서 텍스트 추출
        doc = fitz.open(pdf_path)
        total_text = ""
        for page in doc:
            total_text += page.get_text()
        doc.close()

        # 2. 문서 유형 자동 감지
        doc_type = self._detect_document_type(total_text)

        # 3. 유형별 파싱
        if doc_type == 'PACKING_LIST':
            return self._parse_packing_list(total_text)
        elif doc_type == 'INVOICE':
            return self._parse_invoice(total_text)
        elif doc_type == 'BL':
            return self._parse_bl(total_text)
        elif doc_type == 'DO':
            return self._parse_do(total_text)

    def _detect_document_type(self, text: str) -> str:
        """텍스트 내용으로 문서 유형 판별"""
        text_lower = text.lower()
        scores = {
            'INVOICE': sum(1 for kw in ['invoice', 'total amount', 'unit price']
                          if kw in text_lower),
            'PACKING_LIST': sum(1 for kw in ['packing', 'maxibag', 'net weight']
                               if kw in text_lower),
            'BL': sum(1 for kw in ['bill of lading', 'b/l', 'shipper']
                     if kw in text_lower),
            'DO': sum(1 for kw in ['delivery order', 'd/o', 'free time']
                     if kw in text_lower),
        }
        return max(scores, key=scores.get)
```

### 8.3 Packing List 파싱 (★ 가장 중요)

```python
# parsers/document_parser_modular/packing_mixin.py

class PackingListMixin:
    def _parse_packing_list(self, text: str) -> dict:
        """
        ★★★ 패킹리스트에서 LOT별 정보를 추출 ★★★

        패킹리스트 구조 예:
        LOT NO: 1125081447
        NET WEIGHT: 5,001 KG
        MAXIBAG: 10
        CONTAINER: MRSU6643467
        """
        lots = []

        # 정규식으로 LOT 블록 추출
        # ★ 정규식(Regex)은 텍스트에서 패턴을 찾는 도구
        lot_pattern = re.compile(
            r'LOT\s*(?:NO\.?|#)?\s*[:\-]?\s*(\d{10})',  # LOT 번호 (10자리)
            re.IGNORECASE
        )

        net_pattern = re.compile(
            r'NET\s*WEIGHT\s*[:\-]?\s*([\d,]+\.?\d*)\s*KG',
            re.IGNORECASE
        )

        bag_pattern = re.compile(
            r'(?:MAXIBAG|MXBG|BAG)\s*[:\-]?\s*(\d+)',
            re.IGNORECASE
        )

        container_pattern = re.compile(
            r'([A-Z]{4}\d{7})',  # 컨테이너: 영문4 + 숫자7
        )

        # 매칭
        lot_numbers = lot_pattern.findall(text)
        net_weights = net_pattern.findall(text)
        bag_counts = bag_pattern.findall(text)
        containers = container_pattern.findall(text)

        for i, lot_no in enumerate(lot_numbers):
            net_w = float(net_weights[i].replace(',', '')) if i < len(net_weights) else 0
            bags = int(bag_counts[i]) if i < len(bag_counts) else 10
            container = containers[i] if i < len(containers) else ''

            lots.append({
                'lot_no': lot_no,
                'net_weight': net_w,
                'mxbg_pallet': bags,
                'container_no': container,
                'product': 'LITHIUM CARBONATE',
            })

        return {'document_type': 'PACKING_LIST', 'lots': lots}
```

### 8.4 Gemini AI OCR (정규식으로 안 될 때)

```python
# 정규식이 실패할 때 Gemini AI에게 PDF를 보여주고 데이터를 추출
from google import genai

client = genai.Client(api_key=GEMINI_API_KEY)
response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents=[
        "이 패킹리스트에서 LOT번호, NET WEIGHT, MAXIBAG 수를 JSON으로 추출해줘",
        # PDF 이미지를 base64로 전달
    ]
)
```

---

## 9. 개발 Phase 6 — 출고 시스템 (5~7일)

### 9.1 출고 로직

```python
# engine_modules/inventory_modular/outbound_mixin.py

class OutboundMixin:
    def process_outbound(self, tonbag_ids: list, customer: str, outbound_date: str):
        """
        ★ 출고 처리 — All-or-Nothing 트랜잭션

        원칙: 전체 성공 또는 전체 취소 (부분 출고 없음)
        """
        try:
            # ★ 트랜잭션 시작
            self.db.conn.execute("BEGIN IMMEDIATE")

            total_weight = 0

            for tonbag_id in tonbag_ids:
                # 1. 톤백 상태 확인
                tb = self.db.fetchone(
                    "SELECT * FROM inventory_tonbag WHERE id=? AND status='AVAILABLE'",
                    [tonbag_id]
                )
                if not tb:
                    raise ValueError(f"톤백 {tonbag_id}는 출고 불가 (이미 출고됨)")

                # 2. 톤백 상태 변경: AVAILABLE → PICKED
                self.db.conn.execute("""
                    UPDATE inventory_tonbag
                    SET status='PICKED', picked_date=?, picked_to=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                """, [outbound_date, customer, tonbag_id])

                total_weight += tb['weight']

                # 3. LOT의 current_weight 차감
                self.db.conn.execute("""
                    UPDATE inventory
                    SET current_weight = current_weight - ?,
                        picked_weight = picked_weight + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE lot_no = ?
                """, [tb['weight'], tb['weight'], tb['lot_no']])

            # 4. LOT 상태 확인 (모든 톤백이 출고되면 DEPLETED)
            for lot_no in set(tb['lot_no'] for tb in
                             [self.db.fetchone("SELECT lot_no FROM inventory_tonbag WHERE id=?", [tid])
                              for tid in tonbag_ids]):
                available = self.db.fetchone("""
                    SELECT COUNT(*) as cnt FROM inventory_tonbag
                    WHERE lot_no=? AND status='AVAILABLE'
                """, [lot_no])
                if available['cnt'] == 0:
                    self.db.conn.execute(
                        "UPDATE inventory SET status='DEPLETED' WHERE lot_no=?", [lot_no])

            # ★ 트랜잭션 성공 → 커밋
            self.db.conn.commit()
            return {'success': True, 'total_weight': total_weight}

        except Exception as e:
            # ★ 오류 시 전체 롤백
            self.db.conn.rollback()
            return {'success': False, 'error': str(e)}
```

---

## 10. 개발 Phase 7 — Excel 내보내기 (3~4일)

```python
# engine_modules/inventory_modular/export_mixin.py

class ExportMixin:
    def export_inventory_excel(self, output_path: str):
        """재고 리스트 → Excel (18컬럼 포맷)"""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        inventory = self.get_inventory()
        wb = Workbook()
        ws = wb.active
        ws.title = 'Ruby'

        # ★ 헤더 스타일
        headers = ['No.','LOT NO','SAP NO','BL NO','CONTAINER','PRODUCT',
                    'MXBG','NET(Kg)','INVOICE NO','SHIP DATE','ARRIVAL',
                    'FREE TIME','WH','STATUS','CUSTOMS',
                    'Balance(Kg)','Inbound(Kg)','Outbound(Kg)']

        hfill = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
        hfont = Font(name='맑은 고딕', size=11, bold=True, color='FFFFFF')

        for c, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=c, value=h)
            cell.font = hfont
            cell.fill = hfill
            cell.alignment = Alignment(horizontal='center')

        # ★ 데이터 행
        keys = ['lot_no','sap_no','bl_no','container_no','product',
                'mxbg_pallet','net_weight','salar_invoice_no','ship_date',
                'arrival_date','free_time','warehouse','status','customs',
                'current_weight','initial_weight','picked_weight']

        for r, item in enumerate(inventory, 2):
            ws.cell(row=r, column=1, value=r-1)
            for c, k in enumerate(keys, 2):
                ws.cell(row=r, column=c, value=item.get(k, ''))

        wb.save(output_path)
```

---

## 11. 개발 Phase 8 — 테마, 설정, 마무리 (3~5일)

### 11.1 테마 시스템

```python
# gui_app_modular/utils/ui_constants.py

class ThemeColors:
    """Light/Dark 테마 색상 팔레트"""

    PALETTES = {
        'LIGHT': {
            'bg_main': '#f5f6fa',
            'bg_card': '#ffffff',
            'text_primary': '#1a1a2e',     # ★ 반드시 어두운 색!
            'tree_select_bg': '#3498db',
            'tree_select_fg': '#ffffff',
        },
        'DARK': {
            'bg_main': '#1a1a2e',
            'bg_card': '#16213e',
            'text_primary': '#e8e8e8',
            'tree_select_bg': '#2980b9',
            'tree_select_fg': '#ffffff',
        }
    }

    @classmethod
    def apply(cls, style, theme_name: str):
        """Treeview 등에 테마 색상 적용"""
        is_dark = theme_name in ('darkly','cyborg','superhero','solar','vapor')
        p = cls.PALETTES['DARK'] if is_dark else cls.PALETTES['LIGHT']

        # ★ Treeview 글씨색 명시 (안 하면 화이트 테마에서 글씨 안 보임!)
        style.configure('Treeview',
            background=p['bg_card'],
            foreground=p['text_primary'],
            fieldbackground=p['bg_card'],
            rowheight=28,
        )
```

### 11.2 config.py — Gemini API 설정

```python
# config.py에 추가
import configparser

SETTINGS_FILE = BASE_DIR / 'settings.ini'

def load_settings():
    config = configparser.ConfigParser()
    if SETTINGS_FILE.exists():
        config.read(SETTINGS_FILE, encoding='utf-8')
    return config

# Gemini API 키 로드 (환경변수 우선 → ini 파일)
import os
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if not GEMINI_API_KEY:
    cfg = load_settings()
    GEMINI_API_KEY = cfg.get('API', 'gemini_api_key', fallback='')
```

---

## 12. 테스트 전략

### 12.1 단계별 테스트

| Phase | 테스트 항목 | 확인 방법 |
|-------|-----------|----------|
| 1 | 창이 뜨는가 | `python run_app.py` 실행 |
| 2 | DB에 쓰고 읽는가 | Python 콘솔에서 CRUD 테스트 |
| 3 | 테이블에 데이터가 보이는가 | 화면 확인 |
| 4 | 필터가 작동하는가 | 드롭다운 선택 후 행 수 변화 확인 |
| 5 | PDF 입고가 되는가 | 실제 PDF 업로드 후 DB 확인 |
| 6 | 출고 후 잔량이 맞는가 | 출고 전후 Balance 비교 |
| 7 | Excel이 정상 생성되는가 | 파일 열어서 확인 |

### 12.2 정합성 검사 핵심 공식

```python
# ★ 이 3가지가 항상 성립해야 합니다
assert lot.initial_weight == lot.current_weight + lot.picked_weight
assert lot.current_weight == sum(tb.weight for tb in tonbags if tb.status=='AVAILABLE')
assert lot.picked_weight == sum(tb.weight for tb in tonbags if tb.status=='PICKED')
```

---

## 13. 핵심 주의사항 (★★★)

### 13.1 All-or-Nothing 트랜잭션

입고/출고는 반드시 **전체 성공 또는 전체 취소**여야 합니다. 절대 "톤백 3개는 출고 성공, 2개는 실패" 상태가 되면 안 됩니다.

### 13.2 무게 계산 공식

```
LOT NET WEIGHT = 톤백 무게 합 + 샘플 무게
톤백 개별 무게 = (NET WEIGHT - 1) / 톤백수
샘플 무게 = 1kg (항상 고정)
```

### 13.3 `__pycache__` 주의

Python은 `.py` 파일을 컴파일한 `.pyc` 캐시를 `__pycache__` 폴더에 저장합니다. 코드를 수정해도 캐시가 남아있으면 이전 코드가 실행됩니다! 배포 시 반드시 삭제:

```bash
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### 13.4 Mixin 주의사항

Mixin 안의 `self.xxx`는 **모든 Mixin이 합체된 최종 클래스의 속성**입니다. `InventoryTabMixin`에서 `self.engine`을 쓸 수 있는 이유는, 최종 클래스(`SQMInventoryAppFull`)에 `engine` 속성이 있기 때문입니다.

---

## 14. 개발 일정 요약

| Phase | 기간 | 내용 | 산출물 |
|-------|------|------|--------|
| 1 | 1~2일 | 뼈대 (빈 창) | run_app.py, main_app.py |
| 2 | 3~4일 | DB + 엔진 | database.py, crud_mixin.py |
| 3 | 5~7일 | 재고 리스트 UI | inventory_tab.py (18컬럼) |
| 4 | 4~5일 | 톤백 + 대시보드 | tonbag_tab.py, dashboard_tab.py |
| 5 | 7~10일 | PDF 입고 | packing_mixin.py + 3종 |
| 6 | 5~7일 | 출고 | outbound_mixin.py |
| 7 | 3~4일 | Excel + 설정 | export_mixin.py, config.py |
| 8 | 3~5일 | 테마 + 마무리 | ui_constants.py, 테스트 |
| **합계** | **약 30~45일** | | **v1.0 완성** |

---

> **🏌️ Ruby 의견**: 이 계획서대로 Phase 1부터 순서대로 진행하면 됩니다. 가장 중요한 원칙은 **"각 Phase를 완전히 테스트한 후 다음으로"** 입니다. Phase 3의 Treeview가 정상 동작하는 걸 확인하지 않고 Phase 5(PDF)로 넘어가면 나중에 버그 원인을 찾기 매우 어렵습니다.

