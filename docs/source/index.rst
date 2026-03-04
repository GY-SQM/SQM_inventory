.. SQM 재고관리 시스템 documentation master file

=================================
SQM 재고관리 시스템 API 문서
=================================

.. toctree::
   :maxdepth: 2
   :caption: 목차:

   getting_started
   modules/index
   api/index
   changelog

개요
====

SQM 재고관리 시스템은 Python 기반의 재고 관리 애플리케이션입니다.

주요 기능
---------

* **입고 관리**: PDF/Excel 파일을 통한 재고 등록
* **출고 관리**: 수동/일괄 출고 처리
* **재고 조회**: 다양한 조건의 재고 검색
* **리포트 생성**: Excel/PDF 형식의 리포트 출력
* **톤백 관리**: Sub LOT 단위의 상세 재고 관리

시스템 구조
-----------

.. code-block:: text

   sqm_inventory/
   ├── engine.py          # 핵심 비즈니스 로직
   ├── database.py        # 데이터베이스 관리
   ├── preflight.py       # 검증 시스템
   ├── parsers/           # 문서 파서
   ├── gui_modular/       # 모듈화된 GUI
   │   ├── tabs/          # 탭 모듈
   │   ├── dialogs/       # 다이얼로그
   │   ├── mixins/        # 기능 믹스인
   │   └── utils/         # 유틸리티
   └── tests/             # 테스트 코드

빠른 시작
---------

설치::

    pip install -r requirements.txt

실행::

    python run.py

인덱스
======

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
