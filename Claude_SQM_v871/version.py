# -*- coding: utf-8 -*-
"""SQM 재고관리 시스템 버전 정보"""

__version__ = "8.7.0"
VERSION = "8.7.0"
VERSION_TUPLE = (8, 7, 0)
RELEASE_DATE = "2026-04-06"
APP_NAME = "SQM 재고관리 시스템"
APP_NAME_EN = "SQM Inventory Management System"
BUILD_DATE = "2026-04-06"
BUILD_NOTE = (
    "v8.7.0 (2026-04-06)\n"
    "  [FIX] client.js fetchJson export - white screen bug fixed\n"
    "  [FIX] App.jsx useContext circular ref removed\n"
    "  [FIX] react_api/main.py os import + uvicorn entrypoint\n"
    "  [FIX] responsive.css mobile removed - sidebar always left\n"
    "  [FIX] MenuBar.jsx div closing tag fixed\n"
    "  [NEW] run_react_network.bat auto port cleanup + .env support\n"
    "  [NEW] MenuBar added: PDF convert/log cleanup/audit log/auto refresh\n"
    "  [NEW] Sidebar Tonbag tab added\n"
)
