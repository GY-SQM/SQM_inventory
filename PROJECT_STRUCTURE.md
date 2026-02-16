# 📁 SQM Inventory v3.1 프로젝트 구조

> 마지막 업데이트: 2026-01-25

## 루트 폴더 (핵심 파일만)

```
sqm_v3.1/
├── run.py               ★ 엔트리포인트 (유일)
├── SQM_실행.bat         Windows 실행 (run.py 호출)
├── core.py              ★ Core Facade  
├── engine.py            ★ 비즈니스 로직
├── config.py            설정
├── version.py           버전 정보
├── entrypoint.py        초기화
│
├── auto_updater.py      자동 업데이터
├── secure_config_manager.py  보안 설정
├── dashboard_provider.py     대시보드 데이터
├── preflight.py         Preflight 검증
├── validators.py        검증기
├── pipeline.py          처리 파이프라인
└── ...
```

## 핵심 모듈 폴더

```
├── gui_app_modular/     ★★★ GUI 모듈 (Mixin 패턴)
│   ├── main_app.py      메인 앱
│   ├── mixins/          기능별 믹스인 (14개)
│   ├── tabs/            탭 UI (8개)
│   ├── handlers/        이벤트 핸들러 (9개)
│   ├── dialogs/         대화상자 (5개)
│   └── utils/           유틸리티 (5개)
│
├── engine_modules/      ★★★ 엔진 모듈
│   ├── inventory.py     재고 엔진
│   ├── database.py      DB 연결
│   └── inventory_modular/  모듈화된 엔진 (15개)
│
├── validation_system/   검증 시스템
│   ├── preflight_validator.py
│   └── inventory_processor.py
│
├── parsers/             문서 파싱
│   ├── pdf_parser.py
│   ├── document_parser_v2.py
│   └── allocation_parser.py
│
├── core_modular/        Core 모듈 (19개)
└── database/            DB 관리 (4개)
```

## 기능 모듈 폴더

```
├── features/            ★ 확장 기능
│   ├── ai/              AI 기능 (5개)
│   │   ├── gemini_parser.py
│   │   ├── ocr_auto_tuner.py
│   │   └── ...
│   │
│   ├── backup/          백업 기능 (2개)
│   │   ├── auto_backup_scheduler.py
│   │   └── comprehensive_backup.py
│   │
│   ├── monitoring/      모니터링 (5개)
│   │   ├── health_check.py
│   │   ├── anomaly_detector.py
│   │   └── ...
│   │
│   ├── integration/     외부 연동 (4개)
│   │   ├── telegram_notifier.py
│   │   ├── email_reporter.py
│   │   └── ...
│   │
│   ├── reporting/       리포팅 (4개)
│   │   ├── visual_reports.py
│   │   ├── pdf_report.py
│   │   └── ...
│   │
│   ├── optimization/    최적화 (4개)
│   │   ├── db_optimizer.py
│   │   ├── batch_query.py
│   │   └── ...
│   │
│   ├── security/        보안 (4개)
│   │   ├── db_protection.py
│   │   ├── upload_guard.py
│   │   └── ...
│   │
│   └── search/          검색 (3개)
│       ├── advanced_search.py
│       ├── smart_search.py
│       └── document_scanner.py
```

## 기타 폴더

```
├── tools/               개발 도구
│   ├── generators/      샘플 생성기 (6개)
│   └── dev/             개발 도구 (7개)
│
├── tests/               테스트 (387개)
│   ├── unit/
│   ├── integration/
│   └── gui/
│
├── docs/                문서
│   ├── DEVELOPER_GUIDE.md
│   ├── USER_MANUAL_V3_KR.md
│   └── ...
│
├── data/                데이터
│   └── db/              SQLite DB
│
├── build/               빌드 설정
│   └── sqm_inventory.spec
│
├── updates/             업데이트 정보
│   └── latest.json
│
└── archive/             ⚠️ 아카이브 (배포 제외)
    ├── debug_reports/   디버그 리포트
    ├── legacy_code/     레거시 코드
    ├── old_patches/     패치 파일
    └── old_modules/     이전 모듈
```

## 파일 통계

| 구분 | 파일 수 | 설명 |
|------|---------|------|
| 루트 | 20개 | 핵심 파일만 |
| gui_app_modular | 44개 | GUI 모듈 |
| engine_modules | 20개 | 엔진 모듈 |
| features | 31개 | 확장 기능 |
| tests | 30+개 | 테스트 |
| tools | 13개 | 개발 도구 |
| **archive** | **84개** | **배포 제외** |

## 정리 전 vs 후

| 항목 | 정리 전 | 정리 후 |
|------|---------|---------|
| 루트 Python 파일 | 67개 | **20개** |
| DEBUG 리포트 | 17개 | **0개** (archive) |
| 중복 모듈 폴더 | 2개 | **1개** |
| 레거시 코드 | 산재 | **archive로 통합** |

---

**구조 정리 완료!**
