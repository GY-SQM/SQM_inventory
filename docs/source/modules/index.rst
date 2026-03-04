모듈 구조
=========

.. toctree::
   :maxdepth: 2

핵심 모듈
---------

engine.py
^^^^^^^^^
재고 관리의 핵심 비즈니스 로직을 담당합니다.

* ``SQMEngine`` - 메인 엔진 클래스
* 입고/출고 처리
* 재고 조회 및 업데이트

database.py
^^^^^^^^^^^
SQLite 데이터베이스 연결 및 관리를 담당합니다.

* ``Database`` - DB 연결 클래스
* 트랜잭션 관리
* 스키마 마이그레이션

preflight.py
^^^^^^^^^^^^
입출고 전 검증 시스템입니다.

* ``PreflightValidator`` - 검증 클래스
* ``ValidationResult`` - 검증 결과
* All-or-Nothing 처리 보장

batch_query.py
^^^^^^^^^^^^^^
N+1 쿼리 문제 해결을 위한 배치 처리 모듈입니다.

* ``BatchQueryManager`` - 배치 쿼리 관리자
* 캐시 시스템
* 배치 조회 및 업데이트

GUI 모듈
--------

gui_modular/
^^^^^^^^^^^^

모듈화된 GUI 구조:

* ``main_app.py`` - 메인 애플리케이션
* ``tabs/`` - 탭 모듈
   - ``inventory_tab.py`` - 재고 조회
   - ``tonbag_tab.py`` - 톤백 관리
   - ``search_tab.py`` - 검색
   - ``inbound_tab.py`` - 입고
   - ``outbound_tab.py`` - 출고
* ``dialogs/`` - 팝업 다이얼로그
* ``mixins/`` - 기능 믹스인
* ``utils/`` - 유틸리티

파서 모듈
---------

parsers/
^^^^^^^^

문서 파싱 모듈:

* ``do_parser.py`` - D/O 파싱
* ``bl_parser.py`` - B/L 파싱
* ``packing_parser.py`` - Packing List 파싱
* ``invoice_parser.py`` - Invoice 파싱
* ``unified_parser.py`` - 통합 파서

유틸리티
--------

core.py
^^^^^^^
공통 유틸리티 함수 및 설정.

config.py
^^^^^^^^^
시스템 설정 관리.
