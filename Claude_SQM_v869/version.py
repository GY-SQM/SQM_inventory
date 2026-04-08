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
    "  [FIX] client.js fetchJson export 추가 - 흰 화면 버그 해결\n"
    "  [FIX] App.jsx useContext 순환 참조 제거\n"
    "  [FIX] react_api/main.py os import + uvicorn 엔트리포인트 추가\n"
    "  [FIX] responsive.css 모바일 반응형 제거 - 사이드바 항상 좌측 고정\n"
    "  [NEW] run_react_network.bat 포트 자동 정리 + .env 동적 포트 지원\n"
    "  [NEW] MenuBar 누락 메뉴 추가 - PDF변환/로그정리/감사로그/자동갱신\n"
    "  [NEW] Sidebar Tonbag 탭 추가\n"
)
