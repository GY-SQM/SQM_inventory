# P2_BATCH_A — onestop_inbound 구조 분리 자동실행 MASTER
# 작성일: 2026-04-07
# 최종 반영: 2026-04-07 — GPT_P2_BATCH_A_ALL_IN_ONE 통합 (핵심 코드 레퍼런스 추가)
# 목적: onestop_inbound.py(4196줄)를 parser / validator / repository / service로 안전하게 분리
# 총 단계: 6단계 (S1~S6)

================================================================
## 0. 절대 실행 규칙 ★★★ 반드시 읽고 시작할 것 ★★★
================================================================

### 자율 실행 규칙
- 절대 사용자에게 질문하지 말 것
- 모든 선택은 스스로 판단할 것
- 파일 덮어쓰기/삭제 자동 승인
- 테스트 실패 시 자동 수정 후 재시도
- ★ 중단 없이 끝까지 수행 — S1부터 S6까지
- ★ 한 단계 완료 즉시 다음 단계 시작 — 절대 멈추지 말 것
- ★ 사용자 응답 대기(input()) 절대 금지 — 컴퓨터 앞에 아무도 없음
- ★ 작업 완료 보고 후 즉시 다음 단계 진행
- ★ "다음으로 진행할까요?" 같은 확인 요청 절대 금지
- ★ AskUserQuestion 도구 사용 절대 금지

### 절대 규칙
- 기존 기능 변경 금지 — 리팩토링만, 동작 변경 없음
- 단계별 테스트 후 진행
- mock 금지 — 실제 코드로 테스트
- 실패 시 rollback 가능 상태 유지
- onestop_inbound.py 원본은 backup/ 에 보존

### Telegram 사용 규칙
✅ 허용:
  - 단계 완료 알림
  - 오류 발생 즉시 알림
  - 최종 완료 보고
❌ 금지:
  - 열린 질문, 방향 의견 요청

### 단계 완료 기록 규칙
각 단계 완료 시 반드시 두 줄 실행:
  python -c "open('logs/completed_steps.txt','a').write('단계ID_PASS\n')"
  python scripts/telegram_notify.py "완료 메시지"

### 강제 테스트 규칙
Pre-Test → 구현 → Post-Test → 실패시 수정 → Re-Test → 통과 → 다음 단계

### 프로젝트 구조 이해
- 프로젝트 루트: D:\program\Sqm jaego\Claude_SQM_v871
- 대상 파일: gui_app_modular/dialogs/onestop_inbound.py (4196줄)
- 관련 파일: features/parsers/ (기존 파서들)
- 관련 파일: gui_app_modular/handlers/inbound_processor.py
- DB: data/sqm.db (SQLite)
- 기존 핵심 파일 절대 삭제 금지

================================================================

## 1. 작업 단계 정의

================================================================
S1 — 기능 맵 작성 (P2-A-01)
================================================================
목적: onestop_inbound.py 전체 구조 분석 및 기능 맵 작성
작업:
  - onestop_inbound.py 전체 읽기
  - 클래스/메서드 목록 추출
  - 각 메서드의 역할 분류: parsing / validation / DB저장 / UI / 비즈니스로직
  - docs/P2_FUNCTION_MAP.md 에 기능 맵 저장
  - 분리 대상 메서드와 유지 대상 메서드 구분
확인: docs/P2_FUNCTION_MAP.md 파일 존재 및 내용 확인

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S1_PASS\n')"
  python scripts/telegram_notify.py "✅ [S1] 기능 맵 작성 완료 → S2 시작"

================================================================
S2 — Parser 분리 (P2-A-02)
================================================================
목적: onestop_inbound.py에서 파싱 로직을 InboundParser 클래스로 분리
작업:
  - backup/onestop_inbound_backup.py 에 원본 백업
  - features/parsers/inbound_parser.py 생성
  - InboundParser 클래스 구현:
    - parse_bundle(folder) — 폴더 내 파일 파싱
    - 기존 파싱 관련 메서드들 이관
  - onestop_inbound.py에서 InboundParser import 후 기존 파싱 로직 대체
  - 기존 동작과 동일한지 확인
확인: python -c "from features.parsers.inbound_parser import InboundParser; print('OK')"

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S2_PASS\n')"
  python scripts/telegram_notify.py "✅ [S2] Parser 분리 완료 → S3 시작"

================================================================
S3 — Validator 분리 (P2-A-03)
================================================================
목적: 유효성 검사 로직을 InboundValidator 클래스로 분리
작업:
  - features/validators/inbound_validator.py 생성 (디렉토리 없으면 생성)
  - InboundValidator 클래스 구현:
    - validate(data) — 데이터 유효성 검사, 에러 목록 반환
    - 기존 검증 관련 메서드들 이관
  - onestop_inbound.py에서 InboundValidator import 후 기존 검증 로직 대체
확인: python -c "from features.validators.inbound_validator import InboundValidator; print('OK')"

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S3_PASS\n')"
  python scripts/telegram_notify.py "✅ [S3] Validator 분리 완료 → S4 시작"

================================================================
S4 — Repository 분리 (P2-A-04)
================================================================
목적: DB 저장 로직을 InboundRepository 클래스로 분리
작업:
  - features/repositories/inbound_repository.py 생성 (디렉토리 없으면 생성)
  - InboundRepository 클래스 구현:
    - __init__(conn) — DB 연결 주입
    - save(items) — 아이템 저장
    - 기존 DB 관련 메서드들 이관
  - onestop_inbound.py에서 InboundRepository import 후 기존 DB 로직 대체
확인: python -c "from features.repositories.inbound_repository import InboundRepository; print('OK')"

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S4_PASS\n')"
  python scripts/telegram_notify.py "✅ [S4] Repository 분리 완료 → S5 시작"

================================================================
S5 — Service 도입 (P2-A-05)
================================================================
목적: Parser + Validator + Repository를 조합하는 InboundService 클래스 도입
작업:
  - features/services/inbound_service.py 생성 (디렉토리 없으면 생성)
  - InboundService 클래스 구현:
    - __init__(parser, validator, repo) — 의존성 주입
    - run(folder) — 파싱 → 검증 → 저장 파이프라인
  - onestop_inbound.py에서 InboundService를 사용하도록 연결
  - UI 코드는 onestop_inbound.py에 유지, 비즈니스 로직만 Service로 위임
확인: python -c "from features.services.inbound_service import InboundService; print('OK')"

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S5_PASS\n')"
  python scripts/telegram_notify.py "✅ [S5] Service 도입 완료 → S6 시작"

================================================================
S6 — 통합 테스트 (P2-A-06)
================================================================
목적: 분리된 전체 구조가 기존과 동일하게 동작하는지 최종 검증
작업:
  - tests/test_p2_inbound_refactor.py 생성
  - 테스트 케이스:
    1. InboundParser import 및 기본 동작 확인
    2. InboundValidator import 및 기본 동작 확인
    3. InboundRepository import 및 기본 동작 확인
    4. InboundService 파이프라인 동작 확인
    5. onestop_inbound.py가 정상 import 되는지 확인
  - pytest tests/test_p2_inbound_refactor.py 실행
  - 실패 시 수정 후 재테스트
  - 최종 결과를 docs/P2_REFACTOR_REPORT.md 에 기록
확인: pytest 전체 통과

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S6_PASS\n')"
  python scripts/telegram_notify.py "✅ [S6] 통합 테스트 완료"

================================================================

## 2. 핵심 코드 레퍼런스 (GPT_P2_BATCH_A_ALL_IN_ONE 반영)

> 아래 클래스 구조는 각 단계(S2~S5)에서 구현할 뼈대(skeleton)이다.
> 실제 구현 시 onestop_inbound.py 기존 로직을 이관하되, 인터페이스는 이 구조를 따른다.

### Parser (S2에서 구현)
```python
class InboundParser:
    def parse_bundle(self, folder):
        items = []
        for f in os.listdir(folder):
            if f.endswith(".pdf"):
                items.append({"bl_no":"TEST"})
        return {"items": items}
```

### Validator (S3에서 구현)
```python
class InboundValidator:
    def validate(self, data):
        return []
```

### Repository (S4에서 구현)
```python
class InboundRepository:
    def __init__(self, conn):
        self.conn = conn

    def save(self, items):
        pass
```

### Service (S5에서 구현)
```python
class InboundService:
    def __init__(self, parser, validator, repo):
        self.parser = parser
        self.validator = validator
        self.repo = repo

    def run(self, folder):
        data = self.parser.parse_bundle(folder)
        if self.validator.validate(data):
            return False
        self.repo.save(data["items"])
        return True
```

### 테스트 기본형 (S6에서 확장)
```python
def test_inbound():
    assert True
```

### 실행 명령
```bash
python -m py_compile .
pytest
```

================================================================

## 3. 최종 완료 처리

모든 단계 완료 후:
  python scripts/telegram_notify.py "🎯 P2_BATCH_A 전체 완료! onestop_inbound 구조 분리 성공"
  python -c "open('logs/completed_steps.txt','a').write('FINAL_COMPLETE\n')"
