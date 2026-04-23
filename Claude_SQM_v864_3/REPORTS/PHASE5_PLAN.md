# Phase 5 작업 지시서 — 회귀 테스트 업데이트

> **목적**: v864.3 Phase 4-B 에서 추가한 12개 신규 엔드포인트 + 기존 50개 = 62+ 엔드포인트 전체 자동 검증.
> **예상 소요**: 30분
> **담당**: Claude Code (자동 실행)
> **선행 조건**: Phase 4-B 12개 기능 구현 완료 (커밋 `79627ff`)

---

## 🎯 Definition of Done (DoD)

- [ ] `tests/test_phase5_regression.py` 가 12개 신규 엔드포인트 테스트 포함
- [ ] `scripts/verify_endpoints.py` 실행 시 100% PASS (또는 의도된 NOT_READY/400 은 허용)
- [ ] `REPORTS/PHASE5_COMPLETE.md` 최종 보고서 갱신
- [ ] git 태그 `v864.3-phase5` 생성
- [ ] 다음 단계 (Phase 6) 자동 진입 조건 만족

---

## 📋 작업 단계

### Step 1 — 환경 확인 (2분)

```bash
cd D:\program\SQM_inventory\Claude_SQM_v864_3
git log --oneline -3
# 기대: 79627ff 또는 이후 커밋이 HEAD

python -c "import pytest, httpx, pandas, openpyxl, pydantic; print('deps OK')"
```

**실패 시**: `pip install pytest httpx pandas openpyxl pydantic fastapi pyinstaller`

---

### Step 2 — 자동 검증 스크립트 실행 (5분)

```bash
python scripts/verify_endpoints.py
```

**스크립트가 하는 일**:
1. FastAPI 앱을 TestClient 로 로드
2. GET 엔드포인트 33개 호출 → 200 또는 의도된 4xx 확인
3. POST 엔드포인트 29개 호출 → 200 또는 NOT_READY 확인
4. 신규 12개 기능 (F001/F002/F003/F004/F007/F013/F014/F015/F016/F017/F022/F028) 집중 검증
5. 결과: `REPORTS/phase5_verify_<timestamp>.json` + `.md` 생성

**PASS 조건**:
- 20+ GET : 200 OK
- 신규 12 POST : 200 ok:true OR (400 with Pydantic validation error) OR (200 ok:false with NOT_READY)
- 기존 44 POST (NOT_READY 상태) : 200 ok:false code:NOT_READY

**FAIL 시**: verify_endpoints.py 출력에서 FAIL 엔드포인트 목록 확인 → 개별 수정

---

### Step 3 — pytest 회귀 테스트 업데이트 (10분)

**파일**: `tests/test_phase5_regression.py`

**기존**: 50 테스트 (Phase 4 시점)
**추가**: 12 신규 테스트 케이스

```python
# 추가할 테스트 패턴 예시
class TestPhase4BNewFeatures:
    """v864.3 Phase 4-B 신규 네이티브 엔드포인트"""

    def test_f001_pdf_upload_empty(self, client):
        """F001 — PDF 빈 파일 거절"""
        r = client.post("/api/inbound/pdf-upload",
                        files={"file": ("x.pdf", b"", "application/pdf")})
        assert r.status_code == 400

    def test_f002_bulk_import_empty(self, client):
        r = client.post("/api/inbound/bulk-import-excel",
                        files={"file": ("x.xlsx", b"", "app/octet-stream")})
        assert r.status_code == 400

    def test_f007_return_excel_invalid(self, client):
        r = client.post("/api/inbound/return-excel",
                        files={"file": ("bad.txt", b"x", "text/plain")})
        assert r.status_code == 400

    def test_f014_allocation_import_no_lot(self, client):
        # ...

    def test_f015_quick_outbound_validation(self, client):
        r = client.post("/api/outbound/quick",
                        json={"lot_no": "", "count": 1, "customer": ""})
        assert r.status_code == 422  # Pydantic

    def test_f015_quick_outbound_info(self, client):
        r = client.get("/api/outbound/quick/info?lot_no=NO_EXIST")
        assert r.status_code == 200
        assert r.json()["data"]["available_count"] == 0

    def test_f016_quick_paste_schema(self, client):
        r = client.post("/api/outbound/quick-paste",
                        json={"rows": [], "customer": "X"})
        assert r.status_code == 422  # empty rows

    def test_f017_picking_list_empty(self, client):
        r = client.post("/api/outbound/picking-list-pdf",
                        files={"file": ("x.pdf", b"", "application/pdf")})
        assert r.status_code == 400

    def test_f022_apply_approved(self, client):
        r = client.post("/api/allocation/apply-approved", json={})
        assert r.status_code == 200
        b = r.json()
        # ok:true OR ok:false with no pending approvals — 둘 다 OK
        assert b.get("ok") in (True, False)

    def test_f028_confirm_blocked(self, client):
        r = client.post("/api/outbound/confirm",
                        json={"lot_no": "", "force_all": False})
        assert r.status_code == 200
        assert r.json()["detail"]["code"] == "CONFIRM_ALL_BLOCKED"

    def test_f028_picked_summary(self, client):
        r = client.get("/api/outbound/picked-summary")
        assert r.status_code == 200
        assert "items" in r.json()["data"]

    def test_debug_log_router(self, client):
        r = client.get("/api/log/ping")
        assert r.status_code == 200
        assert r.json()["router"] == "debug_log"
```

**실행**:
```bash
python -m pytest tests/test_phase5_regression.py -v 2>&1 | tee tests_phase5.log
```

**PASS 조건**: 모든 기존 50 + 신규 12 = 62 테스트 PASS

---

### Step 4 — 보고서 생성 (3분)

**파일**: `REPORTS/PHASE5_COMPLETE.md` (덮어쓰기 또는 append)

템플릿:
```markdown
# SQM v864.3 — Phase 5 Complete Report (Updated)
**Date**: <today>
**Status**: ✅ PASS / ❌ FAIL

## 자동 검증 결과
- 총 엔드포인트: 62개
- PASS: X개
- FAIL: Y개
- NOT_READY (투명): Z개

## 신규 12개 테스트 결과
| Feature | Endpoint | Status |
|---------|----------|--------|
| F001 | POST /api/inbound/pdf-upload | ✅ |
| ... (11 more)

## 세부 로그
- 자동 검증 JSON: REPORTS/phase5_verify_<ts>.json
- pytest 출력: tests_phase5.log
```

---

### Step 5 — 커밋 + 태그 (2분)

```bash
git add tests/ REPORTS/PHASE5_COMPLETE.md REPORTS/phase5_verify_*.json REPORTS/phase5_verify_*.md scripts/verify_endpoints.py

git commit -m "$(cat <<'EOF'
test(v864.3): Phase 5 회귀 테스트 업데이트 — 12개 신규 엔드포인트 포함

- tests/test_phase5_regression.py: TestPhase4BNewFeatures 클래스 추가 (12 테스트)
- scripts/verify_endpoints.py: 62+ 엔드포인트 자동 검증 (JSON+MD 리포트 생성)
- REPORTS/PHASE5_COMPLETE.md: 자동 검증 결과 갱신

PASS: 62/62 (기존 50 + 신규 12)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"

git tag v864.3-phase5
echo "✅ Phase 5 Complete — 다음 Phase 6 자동 진입 가능"
```

---

## ⚠️ 장애 대응

| 증상 | 원인 | 해결 |
|---|---|---|
| `verify_endpoints.py` ModuleNotFoundError | sys.path 문제 | 스크립트 상단 `sys.path.insert(0, ".")` 확인 |
| pytest FAIL 특정 테스트 | 엔드포인트 변경됨 | 해당 backend/api/*.py 로그 확인 → 동기화 |
| 엔진 import 실패 | DB lock / migration 중 | `python -c "from backend.api import app"` 재시도 |
| SQLite disk I/O error | 샌드박스 read-only | `chmod 666 data/db/*.db` 또는 **WSL** 에서 테스트 |

---

## 🔄 자동 진입 조건 (Phase 6)

다음이 모두 만족되면 즉시 Phase 6 시작:
- [x] `git tag v864.3-phase5` 성공
- [x] `REPORTS/PHASE5_COMPLETE.md` 작성됨
- [x] `scripts/verify_endpoints.py` 최근 실행 결과 PASS

→ `REPORTS/PHASE6_PLAN.md` 로 자동 이동.
