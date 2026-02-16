시작하기
========

설치
----

요구사항
^^^^^^^^

* Python 3.8 이상
* Windows 10/11 (GUI 기능)

필수 패키지 설치
^^^^^^^^^^^^^^^^

.. code-block:: bash

    pip install -r requirements.txt

주요 의존성:

* ``pandas`` - 데이터 처리
* ``openpyxl`` - Excel 처리
* ``pdfplumber`` - PDF 파싱
* ``ttkbootstrap`` - GUI 테마 (선택)

설정
----

데이터베이스 경로
^^^^^^^^^^^^^^^^^

기본 데이터베이스 경로는 ``data/sqm_inventory.db`` 입니다.
환경 변수로 변경 가능:

.. code-block:: bash

    export SQM_DB_PATH=/path/to/database.db

실행
----

GUI 모드
^^^^^^^^

.. code-block:: bash

    python main.py

또는

.. code-block:: bash

    python -m gui_modular

CLI 모드
^^^^^^^^

.. code-block:: python

    from engine import SQMEngine
    
    engine = SQMEngine()
    
    # 재고 조회
    inventory = engine.get_inventory(status='AVAILABLE')
    
    # 출고 처리
    result = engine.process_outbound(lot_no='1120000001', qty_mt=5.0)

기본 사용법
-----------

입고 처리
^^^^^^^^^

1. PDF 파일 준비 (D/O, B/L, Packing List)
2. GUI에서 "입고" 탭 선택
3. 파일 드래그 앤 드롭 또는 선택
4. "미리보기"로 검증
5. "입고 처리" 실행

출고 처리
^^^^^^^^^

1. "출고" 탭 선택
2. LOT 번호 입력 또는 검색
3. 출고 수량 입력
4. "출고 처리" 실행

리포트 생성
^^^^^^^^^^^

1. "리포트" 메뉴 선택
2. 원하는 리포트 유형 선택
3. 저장 위치 지정
4. Excel/PDF로 저장
