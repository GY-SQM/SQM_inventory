# SQM_v568_FULL Project Structure

```text
SQM_v568_FULL/
├── AGENTS.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── DEPLOYMENT_CHECKLIST.md
├── PATCH
│   ├── README_ULTIMATE_PATCH.md
│   └── SQM_v561_Ultimate.patch
├── PROJECT_STRUCTURE.md
├── QUICK_START.md
├── README.md
├── SQM_#Uac1c#Ubc1c#Uacc4#Ud68d#Uc11c_v5.4.6.md
├── SQM_#Uc2e4#Ud589.bat
├── SQM_#Uc77c#Uad04#Ucd9c#Uace0_#Uc591#Uc2dd_#Uc911#Ub7c9.xlsx
├── SQM_#Uc77c#Uad04#Ucd9c#Uace0_#Uc591#Uc2dd_#Ud1a4#Ubc31.xlsx
├── SQM_#Uc785#Uace0_#Uc591#Uc2dd.xlsx
├── SQM_v568_FULL_summary.md
├── SQM_실행.bat
├── VERSION.txt
├── __init__.py
├── backup
│   └── sqm_inventory_20260215_233629.db
├── build
├── build_exe.bat
├── config.json
├── config.py
├── config_sql.py
├── data
│   ├── #Ucd9c#Uace0_Allocation_Table_#Uac00#Uc0c1.xlsx
│   ├── analytics
│   │   └── usage_20260204.json
│   ├── db
│   │   ├── backups
│   │   ├── sqm_inventory.db
│   │   ├── sqm_inventory.db-shm
│   │   └── sqm_inventory.db-wal
│   └── dialog_config.json
├── db
│   └── schema_v5.3.2.sql
├── docs
│   ├── #Ub514#Ubc84#Uae45_#Uc804_#Ubc31#Uc5c5_#Uc548#Ub0b4.md
│   ├── API_DOCUMENTATION.md
│   ├── API_REFERENCE.md
│   ├── API_REFERENCE_V3.md
│   ├── API_REFERENCE_V368.md
│   ├── CHANGELOG_v3.6.3.md
│   ├── CHANGELOG_v3.6.4.md
│   ├── CHANGELOG_v3.6.5.md
│   ├── CODE_QUALITY_AND_IMPROVEMENTS.md
│   ├── CODING_STYLE.md
│   ├── DB_SCHEMA.md
│   ├── DEBUGGING_RISK_OVERVIEW.md
│   ├── DEBUG_REPORT_v3.3.2.md
│   ├── DEBUG_REPORT_v3.6.2.md
│   ├── DEVELOPER_GUIDE.md
│   ├── DO_AND_DONT.md
│   ├── ENTRY_POINT_AND_LIBRARY_REVIEW.md
│   ├── Makefile
│   ├── POSTGRESQL_SETUP_GUIDE.md
│   ├── QUICK_START_v3_KR.md
│   ├── REFACTORING_MASTER_PLAN.md
│   ├── RELEASE_NOTES_v563_tonbag.md
│   ├── RELEASE_NOTES_v569.md
│   ├── RELEASE_NOTES_v573.md
│   ├── RELEASE_NOTES_v575.md
│   ├── RELEASE_NOTES_v577.md
│   ├── RELEASE_NOTES_v578.md
│   ├── RELEASE_NOTES_v579.md
│   ├── RELEASE_NOTES_v580.md
│   ├── REVIEW_DUPLICATES_AND_OUTBOUND_ENTRY.md
│   ├── SQM_#Ucf54#Ub4dc#Uac80#Ud1a0_#Ubcf4#Uace0#Uc11c_v5.4.6.md
│   ├── TTKBOOTSTRAP_MIGRATION_ANALYSIS.md
│   ├── UI_#Ud1b5#Uc77c_#Uaddc#Uce59_#Uc7ac#Uace0_#Ud1a4#Ubc31.md
│   ├── UI_CONSISTENCY_GUIDE.md
│   ├── UI_IMPROVEMENT_v3.5.4.md
│   ├── UI_UX_ANALYSIS.md
│   ├── UI_UX_ANALYSIS_V2.md
│   ├── USER_MANUAL.md
│   ├── USER_MANUAL_KR.md
│   ├── USER_MANUAL_V3_KR.md
│   ├── USER_MANUAL_v3.md
│   ├── api_reference_v384.md
│   ├── archive
│   │   ├── BUG_FIXES.md
│   │   ├── CHANGELOG_v3.3.1.md
│   │   ├── CHANGELOG_v3.5.0.md
│   │   ├── CHANGELOG_v3.6.6.md
│   │   ├── CHANGELOG_v3.6.7.md
│   │   ├── CHANGELOG_v5.2.0_PATCH.md
│   │   ├── CHANGES_v4191.md
│   │   ├── COLUMN_TOGGLE_COMPLETE.md
│   │   ├── DEBUG_REPORT_v3.3_SUPERCOMPUTER.md
│   │   ├── DIAGNOSIS_REPORT_v394.md
│   │   ├── FIX_GUIDE.md
│   │   ├── HOTFIX_v501.md
│   │   ├── HOTFIX_v504.md
│   │   ├── NAMING_CONVENTIONS.md
│   │   ├── PATCH_README.txt
│   │   ├── PHASE1_COMPLETE.md
│   │   ├── PHASE1_COMPLETE_FINAL.md
│   │   ├── PHASE1_FINAL.md
│   │   ├── PHASE2_COMPLETE.md
│   │   ├── PHASE3_COMPLETE.md
│   │   ├── QUICK_START_v500.md
│   │   ├── README_APPLY_ULTIMATE_PATCH.md
│   │   ├── README_v563_PATCH.md
│   │   ├── RELEASE_NOTES_v4191.md
│   │   ├── RELEASE_NOTES_v500.md
│   │   ├── RELEASE_NOTES_v502.md
│   │   ├── RELEASE_NOTES_v502_FINAL.md
│   │   ├── RELEASE_NOTES_v503.md
│   │   ├── RELEASE_NOTES_v505.md
│   │   ├── RELEASE_NOTES_v506.md
│   │   ├── RELEASE_NOTES_v507.md
│   │   ├── RELEASE_NOTES_v508.md
│   │   ├── SQM_v388_3#Ub2e8#Uacc4#Uc6d0#Uce59_#Ubd84#Uc11d.md
│   │   ├── SQM_v388_3#Ub2e8#Uacc4_#Uad6c#Uc870#Ubd84#Uc11d.md
│   │   ├── TONBAG_FILTER_ADDED.md
│   │   └── TONBAG_FILTER_PLAN.md
│   ├── benchmark_v384.md
│   └── source
│       ├── api
│       │   ├── engine.rst
│       │   ├── index.rst
│       │   └── utils.rst
│       ├── changelog.rst
│       ├── conf.py
│       ├── getting_started.rst
│       ├── index.rst
│       └── modules
│           └── index.rst
├── docs_v531
│   └── V5.3.1_CHANGE_SUMMARY.md
├── engine_modules
│   ├── __init__.py
│   ├── constants.py
│   ├── database.py
│   ├── database_interface.py
│   ├── db_migration_mixin.py
│   ├── inventory.py
│   ├── inventory_modular
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── crud_mixin.py
│   │   ├── engine.py
│   │   ├── export_mixin.py
│   │   ├── import_mixin.py
│   │   ├── inbound_mixin.py
│   │   ├── integrity_mixin.py
│   │   ├── outbound_mixin.py
│   │   ├── preflight_mixin.py
│   │   ├── query_mixin.py
│   │   ├── return_mixin.py
│   │   ├── shipment_mixin.py
│   │   ├── tonbag_mixin.py
│   │   └── utils.py
│   ├── performance.py
│   ├── preflight.py
│   ├── query_cache.py
│   ├── tonbag_compat.py
│   └── validators.py
├── features
│   ├── __init__.py
│   └── ai
│       ├── __init__.py
│       ├── gemini_chat_gui.py
│       ├── gemini_chat_query.py
│       ├── gemini_parser.py
│       ├── gemini_utils.py
│       ├── ocr_auto_tuner.py
│       └── openai_parser.py
├── fixes
│   ├── __init__.py
│   ├── auto_style_applier.py
│   └── global_tree_style.py
├── generators
│   └── excel
├── gui_app_modular
│   ├── __init__.py
│   ├── __main__.py
│   ├── dialogs
│   │   ├── __init__.py
│   │   ├── allocation_preview.py
│   │   ├── auto_backup.py
│   │   ├── column_mapper_dialog.py
│   │   ├── custom_messagebox.py
│   │   ├── do_update_dialog.py
│   │   ├── help_dialogs.py
│   │   ├── inbound_dialog_base.py
│   │   ├── info_dialogs.py
│   │   ├── location_upload_preview.py
│   │   ├── lot_detail_dialog.py
│   │   ├── onestop_inbound.py
│   │   ├── outbound_preview_dialog.py
│   │   ├── settings_dialog.py
│   │   └── tonbag_location_upload.py
│   ├── handlers
│   │   ├── __init__.py
│   │   ├── backup_handlers.py
│   │   ├── export_handlers.py
│   │   ├── import_handlers.py
│   │   ├── inbound_processor.py
│   │   ├── inbound_update_mixin.py
│   │   ├── outbound_handlers.py
│   │   ├── outbound_template_mixin.py
│   │   ├── pdf_handlers.py
│   │   ├── pdf_report_handler.py
│   │   ├── product_handlers.py
│   │   ├── simple_excel_outbound.py
│   │   ├── simple_outbound_handler.py
│   │   └── status_import_handlers.py
│   ├── main_app.py
│   ├── mixins
│   │   ├── __init__.py
│   │   ├── advanced_dialogs_mixin.py
│   │   ├── advanced_features_mixin.py
│   │   ├── bulk_import_mixin.py
│   │   ├── context_menu_mixin.py
│   │   ├── custom_menubar.py
│   │   ├── database_mixin.py
│   │   ├── diagnostics_mixin.py
│   │   ├── drag_drop_mixin.py
│   │   ├── features_v2_mixin.py
│   │   ├── keybindings_mixin.py
│   │   ├── menu_mixin.py
│   │   ├── refresh_mixin.py
│   │   ├── statusbar_mixin.py
│   │   ├── theme_mixin.py
│   │   ├── toolbar_mixin.py
│   │   ├── validation_mixin.py
│   │   └── window_mixin.py
│   ├── tabs
│   │   ├── __init__.py
│   │   ├── dashboard_data_mixin.py
│   │   ├── dashboard_tab.py
│   │   ├── inventory_tab.py
│   │   ├── log_tab.py
│   │   ├── summary_tab.py
│   │   └── tonbag_tab.py
│   ├── utils
│   │   ├── __init__.py
│   │   ├── column_toggle.py
│   │   ├── constants.py
│   │   ├── custom_messagebox.py
│   │   ├── formatters.py
│   │   ├── gui_bootstrap.py
│   │   ├── helpers.py
│   │   ├── pdf_report_gen.py
│   │   ├── report_footer.py
│   │   ├── safe_utils.py
│   │   ├── table_styler.py
│   │   ├── tonbag_location_uploader.py
│   │   ├── tree_enhancements.py
│   │   ├── ui_constants.py
│   │   ├── ui_ops_helper.py
│   │   ├── upload_error_dialog.py
│   │   └── upload_error_template.py
│   └── window_config.json
├── gui_config.json
├── gui_processors
│   └── __init__.py
├── logs
│   └── sqm_inventory.log
├── output
├── parsers
│   ├── __init__.py
│   ├── allocation_parser.py
│   ├── base.py
│   ├── document_detector.py
│   ├── document_models.py
│   ├── document_parser_modular
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── bl_mixin.py
│   │   ├── do_mixin.py
│   │   ├── invoice_mixin.py
│   │   ├── packing_mixin.py
│   │   └── parser.py
│   ├── document_parser_v2.py
│   └── pdf_parser.py
├── py.typed
├── query_history.json
├── requirements.txt
├── run.py
├── scripts
│   ├── __init__.py
│   └── migrate_v563_tonbag_weight.py
├── security
│   ├── __init__.py
│   ├── allowed_macs.json
│   ├── allowed_pcs.json
│   └── mac_guard.py
├── sqm_inventory.spec
├── temp
├── tests
│   ├── __init__.py
│   └── test_core.py
├── theme_preference.json
├── tonbag_location_sample.xlsx
├── ui
│   ├── frames
│   └── widgets
├── updates
│   └── latest.json
├── utils
│   ├── backup.py
│   ├── backup_validator.py
│   ├── common.py
│   ├── integrity_check.py
│   ├── logs
│   │   └── error_202602.log
│   ├── path_utils.py
│   ├── pdf_converter.py
│   └── ui_debug.py
├── version.py
└── window_config.json
```

---

# Code Analysis Summary

**사용된 API:** Gemini

이곳에 API를 통한 8만 줄 분석 결과가 작성됩니다...