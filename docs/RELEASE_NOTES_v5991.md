# SQM v5.9.9.1 Release Notes

**Release Date:** 2026-02-18  
**Phase:** 로케이션 형식 확장

---

## 변경 요약

### 로케이션 4파트 지원 — 약식 A-01-01-10

- **파일:** `gui_app_modular/utils/tonbag_location_uploader.py`
- **내용:** 위치(로케이션) 코드를 **3파트**뿐 아니라 **4파트**까지 허용
  - **3파트:** `A-01-01` (구역-열-층) — 기존
  - **4파트:** `A-01-01-10` (구역-열-층-칸) — **로케이션 약식** 기본 형식
- **수정:**
  - `validate_location_format()`: `len(parts) in (3, 4)` 허용, 4번째 파트는 숫자만 허용
  - 모듈·함수 docstring에 "약식 A-01-01-10" 명시
  - 5파트 이상·4번째 자리 문자 입력 시 차단 유지
- **하위 호환:** 기존 3파트(`A-01-01`) 형식 그대로 사용 가능

---

## 변경된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `version.py` | 5.9.9.1, VERSION_HISTORY 추가 |
| `VERSION.txt` | v5.9.9.1 |
| `updates/latest.json` | version 5.9.9.1 |
| `gui_app_modular/utils/tonbag_location_uploader.py` | 로케이션 3/4파트 검증, docstring 정리 |
| `docs/RELEASE_NOTES_v5991.md` | **신규** |

---

**(주) 지와이로지스 2026년 2월 18일**
