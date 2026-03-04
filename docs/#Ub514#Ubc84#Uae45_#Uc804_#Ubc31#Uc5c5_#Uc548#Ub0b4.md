# 디버깅 전 백업 안내 (v5.5.2)

**다음 번 디버깅 전에 아래 순서를 권장합니다.**

## 1. 프로젝트 폴더 백업

- 현재 폴더 전체를 복사해 두세요.  
  예: `SQM_v5.5.1` → `SQM_v5.5.1_백업_YYYYMMDD`
- 버전 업 후에는 `version.py`의 `__version__`이 5.5.2로 통일되어 있습니다.

## 2. 버전 통일

- **단일 소스**: `version.py`의 `__version__`만 수정하면 됩니다.
- `run_app.py`, `config.py`, `gui_app_modular/utils/constants.py`,  
  메인 창 타이틀, 메뉴 "버전 정보"는 모두 이 값을 참조합니다.

## 3. PL 파싱 디버깅 시 확인 순서 (10분 내 원인 확정)

1. **Gemini 원문 저장**  
   설정에서 "디버그: Gemini 원문 저장"을 ON → `logs/raw_pl_response.txt` 등으로 저장되어 있는지 확인.
2. **JSON 추출**  
   코드블럭(````json`) 제거, 첫 `{` ~ 마지막 `}` 구간 추출 후 `json.loads` 동작 확인.
3. **LOT 검증 로그**  
   `parsed_keys`, `type(lots)`, `len(lots)`, `lots[0]` 키 목록이 로그에 찍히는지 확인.
4. **프롬프트**  
   "오직 JSON만 출력", "lots 배열 필수" 등 강제 스키마가 반영되어 있는지 확인.

## 4. 설정 옵션 (v5.5.2)

**settings.ini** 예시:

```ini
[Debug]
# 디버깅 시에만 켜기. Gemini 원문을 logs/raw_pl_response.txt 에 저장
save_raw_gemini_response = false

[Parser]
# true 로 두면 OpenAI 폴백 비활성 (Gemini만 사용, 429 시 장애 원인 제거)
disable_openai_fallback = false
```

환경변수: `SQM_SAVE_RAW_GEMINI_RESPONSE=1` 이면 원문 저장 ON.

---

이 문서는 v5.5.2 기준입니다.
