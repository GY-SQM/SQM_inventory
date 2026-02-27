# SQM v4.2.3 핫픽스 #1

📅 **릴리즈 날짜**: 2026년 2월 10일  
🎯 **대상 버전**: SQM v4.2.3  
⚠️ **중요도**: **중간** (Bug Fix)

---

## 🐛 수정된 버그

### Bug #1: table_styler.py - logger 미정의

**증상:**
```
재고 탭 체크박스 클릭 시
(특정 조건에서) 프로그램 크래시 가능성
```

**원인:**
```python
# table_styler.py, 라인 165
logger.warning(...)  # ← logger가 import 안 됨!
```

**수정:**
```python
import logging
logger = logging.getLogger(__name__)  # ← 추가!
```

**영향:**
- 재고 탭 컬럼 토글 안정성 향상
- 오류 로깅 정상 작동

---

## 📂 변경 파일

| 파일 | 경로 | 변경 내용 |
|------|------|-----------|
| `table_styler.py` | `gui_app_modular/utils/` | logging import 추가 (2줄) |

---

## 🔧 적용 방법

### ⚠️ 프로그램 종료 필수!

### Step 1: 백업 (선택사항)
```
이미 백업 있으면 스킵 가능
```

### Step 2: 파일 복사
```
hotfix_v423_1\files\gui_app_modular\utils\table_styler.py
→ D:\프로그램\Sqm\sqm_v417\gui_app_modular\utils\

덮어쓰기: 예
```

### Step 3: 프로그램 재시작
```
run.py 실행
→ 정상 작동 확인
```

---

## ✅ 적용 확인

```
☐ 프로그램 정상 실행
☐ 재고 탭 컬럼 토글 정상 작동
☐ 오류 없음
```

---

## 💡 참고사항

### 이 핫픽스는:
```
✅ 안정성 개선
✅ 기능 추가 없음
✅ 기존 기능 유지
✅ 데이터 영향 없음
```

### 적용하지 않아도:
```
- 대부분의 경우 정상 작동
- 특정 엣지 케이스에서만 문제
- 하지만 적용 권장!
```

---

## 🔙 롤백

```
핫픽스 적용 전 table_styler.py로 교체
(백업 파일 사용)
```

---

**Ruby's Note**: 

작은 버그지만 안정성을 위해 수정했습니다.
편한 시간에 적용하세요! 👍
