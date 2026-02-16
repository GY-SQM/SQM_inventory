# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 패키지 진입점
====================================

사용법:
    python -m gui_app_modular          # GUI 실행
    python -m gui_app_modular --db DB경로  # DB 지정 실행

v3.8.8: 유일한 진입점으로 통일
"""

from .main_app import main

if __name__ == '__main__':
    main()
