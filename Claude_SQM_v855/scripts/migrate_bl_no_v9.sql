-- ============================================================
-- SQM v9.0 BL No 마이그레이션
-- 목적: 기존 DB의 순수숫자 BL No → MAEU+숫자 형식으로 업데이트
-- 실행: SQM 종료 후 DB 백업 후 실행
-- 작성: Ruby (2026-03-18)
-- ============================================================

-- 1. 실행 전 백업 권장
-- sqlite3 sqm_inventory.db ".backup sqm_inventory_before_v9.db"

-- 2. 현재 bl_no 현황 확인
SELECT
    CASE
        WHEN bl_no GLOB '[A-Z][A-Z]*[0-9]*' THEN '영문+숫자 (이미 변환됨)'
        WHEN bl_no GLOB '[0-9][0-9]*'         THEN '순수숫자 (변환 필요)'
        WHEN bl_no IS NULL OR bl_no = ''      THEN '빈값'
        ELSE '기타'
    END AS bl_type,
    COUNT(*) AS cnt
FROM inventory
GROUP BY bl_type;

-- 3. MAERSK BL (9~10자리 순수숫자) → MAEU 접두사 추가
-- 주의: 선사를 vessel 또는 carrier 정보로 판단
-- MAERSK 선사: vessel에 'MAERSK' 포함 또는 carrier = 'MAERSK'
BEGIN TRANSACTION;

UPDATE inventory
SET bl_no = 'MAEU' || bl_no
WHERE
    bl_no IS NOT NULL
    AND bl_no != ''
    AND bl_no GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'  -- 9자리 숫자
    AND (
        UPPER(COALESCE(vessel,'')) LIKE '%MAERSK%'
        OR UPPER(COALESCE(vessel,'')) LIKE '%MAEU%'
        OR LENGTH(bl_no) = 9   -- MAERSK BL은 주로 9자리
    )
    AND bl_no NOT LIKE 'MAEU%';  -- 이미 변환된 것 제외

-- 4. inventory_tonbag도 동일하게 업데이트
UPDATE inventory_tonbag
SET bl_no = 'MAEU' || bl_no
WHERE
    bl_no IS NOT NULL
    AND bl_no != ''
    AND bl_no GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'
    AND bl_no NOT LIKE 'MAEU%'
    AND lot_no IN (
        SELECT lot_no FROM inventory
        WHERE bl_no LIKE 'MAEU%'  -- 이미 변환된 inventory와 매칭
    );

COMMIT;

-- 5. 변환 결과 확인
SELECT
    bl_no,
    COUNT(*) AS lot_cnt,
    vessel
FROM inventory
WHERE bl_no IS NOT NULL AND bl_no != ''
GROUP BY bl_no, vessel
ORDER BY bl_no;

-- 6. 롤백 방법 (문제 발생 시)
-- UPDATE inventory SET bl_no = SUBSTR(bl_no, 5)
-- WHERE bl_no LIKE 'MAEU%' AND LENGTH(bl_no) = 13;
-- UPDATE inventory_tonbag SET bl_no = SUBSTR(bl_no, 5)
-- WHERE bl_no LIKE 'MAEU%' AND LENGTH(bl_no) = 13;

-- ============================================================
-- carrier_bl_rule 테이블 — 선사별 BL 번호 추출 규칙
-- ============================================================
CREATE TABLE IF NOT EXISTS carrier_bl_rule (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    carrier_id    TEXT NOT NULL,
    carrier_name  TEXT,
    doc_type      TEXT NOT NULL DEFAULT 'BL',  -- 문서 타입: BL / DO
    anchor_label  TEXT,
    pattern_desc  TEXT,
    regex_pattern TEXT NOT NULL,
    extraction_method TEXT DEFAULT 'anchor_regex',
    field_name    TEXT DEFAULT 'bl_no',        -- 추출 필드명 (bl_no/do_no/free_time/container...)
    is_active     INTEGER DEFAULT 1,
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now'))
);

-- 기존 DB 업그레이드: doc_type, field_name 컬럼 추가
ALTER TABLE carrier_bl_rule ADD COLUMN doc_type TEXT DEFAULT 'BL';
ALTER TABLE carrier_bl_rule ADD COLUMN field_name TEXT DEFAULT 'bl_no';

-- 초기 데이터: MAERSK (waybill_line 방식 사용, regex는 폴백용)
-- BL 규칙
INSERT OR IGNORE INTO carrier_bl_rule
    (carrier_id, carrier_name, doc_type, anchor_label, pattern_desc, regex_pattern, extraction_method, field_name)
VALUES
    ('MAERSK','Maersk',  'BL','WAYBILL',  'WAYBILL옆영문+아래숫자9', '[0-9]{9,10}',         'waybill_line', 'bl_no'),
    ('MSC',   'MSC',     'BL','B/L No.',  '알파벳4~6+숫자6~10',      '[A-Z]{4,6}[A-Z0-9]{6,10}', 'anchor_regex','bl_no'),
    ('HMM',   'HMM',     'BL','B/L No.',  'HMMU+숫자7',              'HMMU[0-9]{7}',         'anchor_regex', 'bl_no'),
    ('ONE',   'ONE',     'BL','B/L No.',  'ONEU+숫자7',              'ONEU[0-9]{7}',         'anchor_regex', 'bl_no'),
    ('COSCO', 'COSCO',   'BL','B/L No.',  'COSU+숫자7',              'COSU[0-9]{7}',         'anchor_regex', 'bl_no'),
    ('HAPAG', 'Hapag-Lloyd','BL','B/L No.','HLCU+숫자7',             'HLCU[0-9]{7}',         'anchor_regex', 'bl_no');

-- DO 규칙 (MAERSK D/O 발급확인서 예시)
INSERT OR IGNORE INTO carrier_bl_rule
    (carrier_id, carrier_name, doc_type, anchor_label, pattern_desc, regex_pattern, extraction_method, field_name)
VALUES
    ('MAERSK','Maersk',  'DO','D/O No.',       'D/O번호',          '[A-Z0-9]{6,20}',  'anchor_regex', 'do_no'),
    ('MAERSK','Maersk',  'DO','B/L No.',        'BL번호',           '[0-9]{9,10}',     'anchor_regex', 'bl_no'),
    ('MAERSK','Maersk',  'DO','Free_Time',       '날짜YYYY-MM-DD',  '[0-9]{4}-[0-9]{2}-[0-9]{2}', 'anchor_regex','free_time'),
    ('MAERSK','Maersk',  'DO','반납지',           '반납지코드',       '[A-Z]{5}',        'anchor_regex', 'return_yard'),
    ('MSC',   'MSC',     'DO','B/L No.',        'MSC BL번호',       '[A-Z]{4,6}[A-Z0-9]{6,10}', 'anchor_regex','bl_no'),
    ('HMM',   'HMM',     'DO','B/L No.',        'HMMU+숫자7',       'HMMU[0-9]{7}',    'anchor_regex', 'bl_no');

-- 조회 확인
SELECT carrier_id, doc_type, field_name, pattern_desc FROM carrier_bl_rule ORDER BY carrier_id, doc_type;

-- v9.1: carrier_bl_rule 좌표 컬럼 추가
ALTER TABLE carrier_bl_rule ADD COLUMN x_min_pct REAL DEFAULT NULL;
ALTER TABLE carrier_bl_rule ADD COLUMN x_max_pct REAL DEFAULT NULL;
ALTER TABLE carrier_bl_rule ADD COLUMN y_min_pct REAL DEFAULT NULL;
ALTER TABLE carrier_bl_rule ADD COLUMN y_max_pct REAL DEFAULT NULL;
-- extraction_method 값: 'coord' / 'anchor_regex' / 'waybill_line' / 'label_right'

-- MAERSK DO 기본 좌표 규칙 삽입
INSERT OR IGNORE INTO carrier_bl_rule
    (carrier_id, carrier_name, doc_type, anchor_label, pattern_desc,
     regex_pattern, extraction_method, field_name,
     x_min_pct, x_max_pct, y_min_pct, y_max_pct)
VALUES
    ('MAERSK','Maersk','DO','D/O No.',  'DO번호',           '[0-9]{9,10}',  'coord','do_no',   57.0,95.0,3.5,5.0),
    ('MAERSK','Maersk','DO','B/L No.',  'BL번호',           '[A-Z]{4}[0-9]{9,10}','coord','bl_no', 57.0,95.0,6.8,8.0),
    ('MAERSK','Maersk','DO','Free_Time','날짜YYYY-MM-DD',   '[0-9]{4}-[0-9]{2}-[0-9]{2}','coord','free_time',66.0,79.0,56.5,64.5),
    ('MAERSK','Maersk','DO','반납지',   '6자리 반납지코드',  '[A-Z]{6,8}',   'coord','return_yard',78.0,88.0,56.5,64.5),
    ('MAERSK','Maersk','DO','Container','컨테이너번호',      '[A-Z]{4}[0-9]{7}','coord','container',5.0,20.0,37.5,45.5);
