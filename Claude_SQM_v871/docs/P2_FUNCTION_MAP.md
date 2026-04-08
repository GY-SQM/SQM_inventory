# P2 Function Map — onestop_inbound.py (4196줄)

## 클래스 구조
- `OneStopInboundDialog(InboundUploadMixin, InboundDialogBase)` — 메인 클래스 (line 122)
- `InboundUploadMixin` — DB 업로드 + Excel 내보내기 (inbound_upload_mixin.py)
- `InboundDialogBase` — 공통 베이스 (inbound_dialog_base.py)

## 메서드 분류

### 🔵 UI/Dialog — onestop_inbound.py에 유지
| 메서드 | 라인 | 역할 |
|--------|------|------|
| `__init__` | 132 | 초기화 |
| `show` | 184 | 팝업 표시 |
| `_attach_doc_tooltip` | 216 | 툴팁 |
| `_build_inbound_doc_frame` | 242 | 문서 프레임 (위임) |
| `_build_inbound_progress_frame` | 246 | 진행 프레임 (위임) |
| `_build_inbound_preview_frame` | 250 | 미리보기 프레임 (위임) |
| `_build_inbound_button_frame` | 254 | 버튼 프레임 (위임) |
| `_cd_setup_window` | 273 | 윈도우 생성 |
| `_cd_build_step_indicator` | 309 | 단계 표시 UI |
| `_create_dialog` | 375 | 다이얼로그 생성 메인 |
| `_cd_build_doc_file_section` | 395 | 파일 선택 UI |
| `_cd_build_parse_action_buttons` | 536 | 파싱 버튼 UI |
| `_cd_build_carrier_and_progress` | 612 | 선사/프로그레스 UI |
| `_cd_build_preview_table` | 737 | 미리보기 테이블 UI |
| `_build_inbound_action_buttons` | 814 | 액션 버튼 UI |
| `_update_parse_hint` | 902 | 파싱 힌트 갱신 |
| `_activate_step` | 951 | 단계 활성화 UI |
| `_select_folder` | 1001 | 폴더 선택 |
| `_select_file` | 1109 | 파일 선택 |
| `_show_progress_inline` | 1872 | 인라인 진행률 |
| `_hide_progress_inline` | 1893 | 인라인 진행률 숨김 |
| `_show_progress_popup` | 1902 | 팝업 진행률 |
| `_progress_elapsed_tick` | 1905 | 경과 시간 |
| `_start_progress_elapsed_tick` | 1927 | 경과 시간 시작 |
| `_stop_progress_elapsed_tick` | 1933 | 경과 시간 중지 |
| `_progress_busy_tick` | 1943 | 진행 애니메이션 |
| `_start_progress_busy_animation` | 1953 | 애니메이션 시작 |
| `_stop_progress_busy_animation` | 1958 | 애니메이션 중지 |
| `_hide_progress_popup` | 1967 | 팝업 숨김 |
| `_update_progress` | 1983 | 진행률 갱신 |
| `_push_preview_to_main` | 3200 | 메인창 미리보기 전달 |
| `_clear_preview_from_main` | 3211 | 메인창 미리보기 제거 |
| `_show_preview_table` | 3290 | 미리보기 표시 |
| `_hide_preview_table` | 3302 | 미리보기 숨김 |
| `_display_preview` | 3886 | 미리보기 표시 |
| `_update_summary` | 3914 | 합계행 갱신 |
| `_show_success_and_close` | 3948 | 성공 후 닫기 |
| `_build_upload_summary_message` | 4023 | 업로드 요약 |
| `_reset_after_upload_success` | 4045 | 업로드 후 리셋 |
| `_enable_buttons` | 4064 | 버튼 활성화 |
| `_enable_parse_btn` | 4176 | 파싱 버튼 활성화 |
| `_on_cancel` | 4183 | 취소 |
| `_log_safe` | 4188 | 안전 로그 |
| `_update_carrier_badge` | 4147 | 선사 뱃지 UI |
| `_on_add_do_later` | 4128 | D/O 나중에 추가 |
| `_reparse_after_carrier_change` | 4081 | 선사 변경 재파싱 |

### 🔵 Preview Edit UI — onestop_inbound.py에 유지
| 메서드 | 라인 | 역할 |
|--------|------|------|
| `_format_container_display` | 3220 | 컨테이너 표시 |
| `_on_toggle_container_suffix` | 3233 | 접미사 토글 |
| `_row_display_values` | 3240 | 행 표시값 |
| `_capture_original_preview_state` | 3261 | 원본 상태 저장 |
| `_reset_preview_to_original` | 3265 | 원본 복원 |
| `_update_sort_headings` | 3314 | 정렬 헤더 |
| `_toggle_preview_sort` | 3327 | 정렬 토글 |
| `_on_change_preview_filter` | 3336 | 필터 변경 |
| `_update_filter_values_from_preview` | 3339 | 필터값 갱신 |
| `_item_to_source_index` | 3346 | 아이템→소스 인덱스 |
| `_matches_preview_filters` | 3356 | 필터 매칭 |
| `_preview_sort_key` | 3367 | 정렬 키 |
| `_build_view_indices` | 3382 | 뷰 인덱스 |
| `_get_upload_rows_for_db` | 3392 | DB 업로드 행 |
| `_sync_tree_edit_to_preview_data` | 3408 | 트리 편집 동기화 |
| `_setup_preview_edit_bindings` | 3434 | 편집 바인딩 |
| `_snapshot_preview_state` | 3460 | 스냅샷 |
| `_push_undo_snapshot` | 3466 | 언두 스냅샷 |
| `_restore_preview_state` | 3473 | 상태 복원 |
| `_update_undo_redo_buttons` | 3481 | 언두/리두 버튼 |
| `_undo_preview_edit` | 3490 | 언두 |
| `_redo_preview_edit` | 3500 | 리두 |
| `_on_preview_cell_edit` | 3580 | 셀 편집 |
| `_coerce_preview_value` | 3624 | 값 강제변환 |
| `_update_preview_cell` | 3649 | 셀 갱신 |
| `_finish_preview_editing` | 3658 | 편집 완료 |
| `_copy_preview_selection` | 3692 | 복사 |
| `_selected_preview_cells` | 3712 | 선택 셀 |
| `_clear_preview_selection` | 3739 | 선택 해제 |
| `_cut_preview_selection` | 3752 | 잘라내기 |
| `_paste_preview_from_clipboard` | 3773 | 붙여넣기 |
| `_refresh_preview_tree_only` | 3814 | 트리 새로고침 |

### 🟢 Parsing — InboundParser로 분리 대상
| 메서드 | 라인 | 역할 |
|--------|------|------|
| `_pt_init_parser` | 2087 | 파서 초기화 (API키 확인) |
| `_pt_extract_template_hints` | 2104 | 템플릿 힌트 추출 |
| `_pt_parse_documents` | 2159 | 서류별 파싱 루프 |
| `_pt_parse_bl` | 2247 | BL 파싱 |
| `_pt_handle_bl_carrier_detection` | 2295 | BL 선사 감지 |
| `_merge_results` | 2641 | 4종 결과 병합 |
| `_empty_row` | 2752 | 빈 행 생성 |
| `_date_str` | 2757 | 날짜 문자열 변환 |
| `_format_bl` | 2766 | BL번호 포맷 |
| `_fill_do` | 2774 | D/O 데이터 보완 |
| `_lot_order_key` | 3251 | LOT 정렬 키 |

### 🟡 Validation — InboundValidator로 분리 대상
| 메서드 | 라인 | 역할 |
|--------|------|------|
| `_preflight_validate_preview_data` | mixin:24 | 미리보기 데이터 검증 |
| `_has_required_docs` | 3907 | 필수 서류 확인 |
| `_amd_validate_date` | 2845 | 날짜 형식 검증 |
| `_amd_calc_dates` | 2861 | 날짜 상호 계산 |

### 🟠 Repository (DB) — InboundRepository로 분리 대상
| 메서드 | 라인 | 역할 |
|--------|------|------|
| `_save_to_db` | mixin:265 | DB 저장 (LOT별) |
| `_on_upload` | mixin:69 | 업로드 시작 (검증+저장) |
| `_upload_thread` | mixin:197 | 업로드 스레드 |

### 🔴 Template — onestop_inbound.py에 유지 (UI 의존)
| 메서드 | 라인 | 역할 |
|--------|------|------|
| `_load_template_combo` | 1191 | 콤보박스 로드 |
| `_on_template_selected` | 1222 | 템플릿 선택 |
| `_normalize_carrier_for_combo` | 1239 | 선사 정규화 |
| `_carrier_id_matches_filter` | 1254 | 선사 필터 |
| `_auto_match_template_by_carrier` | 1262 | 자동 매칭 |
| `_on_carrier_combo_selected` | 1303 | 선사 콤보 선택 |
| `_show_template_table_picker` / etc | 1316+ | 템플릿 피커 UI |
| `_start_parsing` | 1695 | 파싱 시작 |
| `_show_preparse_select_dialog` | 1712 | 파싱 전 확인창 |
| `_do_start_parsing_after_template` | 1813 | 템플릿 후 파싱 진행 |
| `_parse_thread` | 2024 | 파싱 스레드 (오케스트레이션) |
| `_ask_missing_dates` | 2898 | 날짜 입력 팝업 |

### 🔵 Service 조합 대상 (Parser + Validator + Repository)
- `InboundService.run(files, template, engine)` → parse → merge → validate → save

## 분리 전략
1. **InboundParser**: 순수 파싱 로직 (API 호출, 결과 병합, 데이터 변환)
2. **InboundValidator**: 순수 검증 로직 (데이터 유효성, 날짜 계산)
3. **InboundRepository**: DB 저장 로직 (engine.process_inbound 호출)
4. **InboundService**: Parser → Validator → Repository 파이프라인
5. **onestop_inbound.py**: UI만 유지, Service를 통해 비즈니스 로직 위임
