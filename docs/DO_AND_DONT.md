# ⚠️ SQM Inventory - 해야 할 것 & 하면 안 되는 것

## 개발자 및 사용자를 위한 가이드라인

---

## 🟢 해야 할 것 (DO)

### 개발자용

#### 코딩 규칙
```
✅ 항상 파라미터 바인딩 사용 (SQL 인젝션 방지)
   self.db.execute("SELECT * FROM inventory WHERE lot_no = ?", (lot_no,))

✅ 예외 처리 시 로깅
   except Exception as e:
       logger.error(f"오류: {e}")

✅ 타입 힌트 사용
   def process_outbound(self, data: list) -> dict:

✅ Docstring 작성
   """
   메서드 설명
   Args: ...
   Returns: ...
   """

✅ 버전 업데이트 시 모든 파일 동기화
   version.py, gui_app.py, config.py, core.py 등

✅ 테스트 후 배포
   python -m py_compile *.py
```

#### 데이터베이스
```
✅ 트랜잭션 사용 (대량 작업 시)
   with self.db.transaction():
       for item in items:
           self.db.execute(...)

✅ 인덱스 활용 (자주 검색하는 컬럼)
   CREATE INDEX idx_lot_no ON inventory(lot_no)

✅ UNIQUE 제약조건으로 중복 방지
   UNIQUE(lot_no, sub_lt)

✅ 정합성 검사 후 작업
   inventory.current_weight == SUM(tonbag.weight WHERE status='AVAILABLE')
```

#### GUI 개발
```
✅ 백그라운드 스레드 사용 (긴 작업 시)
   self._run_background(work_fn, on_success, on_error)

✅ 프로그레스바 업데이트
   root.after(0, lambda: progress_var.set(percent))

✅ 사용자 확인 (위험한 작업 전)
   if messagebox.askyesno("확인", "정말 삭제하시겠습니까?"):
```

---

### 사용자용

#### 입고 작업
```
✅ 패킹리스트 형식 확인 후 업로드
✅ D/O 파일로 입항일 자동 추출
✅ 미리보기로 데이터 확인 후 입고 처리
✅ 입고 완료 후 재고현황에서 확인
```

#### 출고 작업
```
✅ 출고 전 잔량 확인
✅ 출고 파일 형식 확인 (LOT NO, QTY_MT 컬럼 필수)
✅ 출고 후 톤백상세에서 상태 확인
```

#### 반품 작업
```
✅ 원 LOT 번호로 반품 처리
✅ 반품 사유 기록
✅ 반품 후 잔량 증가 확인
```

#### 백업
```
✅ 정기적으로 DB 파일 백업
✅ 중요 작업 전 백업
✅ 백업 파일명에 날짜 포함
```

---

## 🔴 하면 안 되는 것 (DON'T)

### 개발자용

#### 절대 금지 (코딩)
```
❌ SQL 인젝션 취약 코드
   self.db.execute(f"SELECT * FROM inventory WHERE lot_no = '{lot_no}'")
   # → 해커가 lot_no = "'; DROP TABLE inventory; --" 입력 가능!

❌ except pass (예외 무시)
   except Exception:
       pass
   # → 오류 원인 추적 불가!

❌ 하드코딩된 경로
   path = "C:\\Users\\Ruby\\Desktop\\data.xlsx"
   # → 다른 PC에서 실행 불가!

❌ 전역 변수 남용
   global engine
   engine = SQMInventoryEngine()
   # → 상태 관리 혼란!

❌ UI 스레드에서 긴 작업
   for i in range(10000):
       self.db.execute(...)  # UI 멈춤!
   # → 반드시 백그라운드 스레드 사용!
```

#### 절대 금지 (데이터베이스)
```
❌ 중복 LOT 번호 허용
   # → UNIQUE 제약조건 필수!

❌ 정합성 깨지는 작업
   UPDATE inventory SET current_weight = 0
   # → 톤백은 그대로인데 잔량만 0?
   # → 반드시 동기화!

❌ DELETE 직접 실행 (운영 DB)
   DELETE FROM inventory_tonbag WHERE lot_no = 'LOT001'
   # → 이력 손실! soft delete 권장!

❌ 트랜잭션 없이 대량 작업
   for item in 10000_items:
       self.db.execute(...)
   # → 중간에 오류 시 일부만 반영!
```

#### 절대 금지 (GUI)
```
❌ messagebox 남용
   for i in range(100):
       messagebox.showinfo("완료", f"{i}번 완료")
   # → 100번 클릭해야 함!

❌ 무한 루프
   while True:
       self._refresh_inventory()
   # → 프로그램 먹통!

❌ 파일 경로 직접 입력 받기
   path = entry.get()
   open(path, 'r')
   # → 잘못된 경로 시 크래시!
   # → filedialog 사용!
```

---

### 사용자용

#### 절대 금지 (입고)
```
❌ 같은 LOT 번호로 중복 입고
   # → 오류 발생! 새 LOT 번호 사용!

❌ 빈 파일 업로드
   # → 아무것도 입고되지 않음!

❌ xls 파일 사용 (구버전 엑셀)
   # → xlsx 형식으로 변환 필요!

❌ 파일이 열린 상태로 업로드
   # → 읽기 오류 발생!
```

#### 절대 금지 (출고)
```
❌ 잔량보다 많이 출고 시도
   # → 가능한 양만 출고됨, 오해 발생!

❌ 이미 SOLD된 톤백 재출고
   # → 불가능! 반품 후 재출고 해야 함!

❌ 출고 파일에 음수 수량
   QTY_MT = -5.0
   # → 무시됨!
```

#### 절대 금지 (반품)
```
❌ 새 LOT 번호로 반품
   # → 원 LOT 번호 사용해야 함!

❌ 입고된 적 없는 LOT 반품
   # → 불가능!

❌ 반품 사유 없이 처리
   # → 추적 불가!
```

#### 절대 금지 (일반)
```
❌ DB 파일 직접 수정
   # → 정합성 깨짐! 프로그램으로만 수정!

❌ 프로그램 실행 중 DB 파일 이동/삭제
   # → 크래시!

❌ 여러 PC에서 동시에 DB 수정
   # → 충돌! 단일 Writer 권장!

❌ 백업 없이 대량 작업
   # → 복구 불가!
```

---

## ⚡ 긴급 상황 대응

### 프로그램이 멈췄을 때
```
1. 잠시 대기 (대량 데이터 처리 중일 수 있음)
2. 5분 이상 지속 시 → 작업 관리자에서 강제 종료
3. DB 파일 백업
4. 프로그램 재시작
```

### 데이터가 이상할 때
```
1. 즉시 작업 중단
2. DB 파일 백업
3. 최근 변경 사항 확인
4. 담당자에게 문의
```

### 파일을 잘못 업로드했을 때
```
1. 즉시 반품 처리 (출고 시)
2. DB 복구 요청 (입고 시)
3. 백업 파일에서 복원 가능
```

---

## 📋 체크리스트

### 배포 전 체크리스트
```
□ 버전 번호 통일?
□ 구문 검사 통과?
□ 핵심 기능 테스트?
□ 정합성 검사?
□ 백업 파일 생성?
□ 변경 이력 기록?
```

### 대량 작업 전 체크리스트
```
□ DB 백업?
□ 테스트 데이터로 먼저 검증?
□ 예상 소요 시간 확인?
□ 다른 사용자 없는지 확인?
```

---

## 📊 요약 표

| 구분 | ✅ DO | ❌ DON'T |
|------|-------|----------|
| SQL | 파라미터 바인딩 | 문자열 연결 |
| 예외 | 로깅 | pass |
| 경로 | 상대경로/다이얼로그 | 하드코딩 |
| 스레드 | 백그라운드 | UI 스레드에서 긴 작업 |
| 입고 | 새 LOT 번호 | 중복 LOT |
| 출고 | 잔량 확인 | 과다 출고 |
| 반품 | 원 LOT으로 | 새 LOT으로 |
| DB | 프로그램으로 | 직접 수정 |
| 백업 | 정기적 | 안 함 |

---

*이 가이드라인을 준수하면 대부분의 문제를 예방할 수 있습니다!*

*SQM Inventory v2.9.67 | 2025년 1월*
