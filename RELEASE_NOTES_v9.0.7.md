## SQM v9.0.7 — PC Guard 모듈 (GY_PC_Manager 통합 1회차)

릴리즈일: 2026-07-22
대상: v9.0.6 → v9.0.7
대분류: minor (보안 모델 변경 준비)

### 배경

SQM_inventory는 v8.7.2부터 **"로컬 전용(PyWebView) 의도된 미인증"** 정책이었음
(localhost 바인딩으로 외부 노출만 차단). PC 식별 없이 그 PC에서 누구나 실행 가능.

v9.0.7에서 GY_PC_Manager의 `allowed_pcs.json`을 registry로 사용하는
**PC Guard 시스템 1회차 (스켈레톤)** 도입. **main_webview.py 통합은 v9.0.8**.

### 신규 모듈 (core/pc_guard.py)

#### 1. collect_fingerprint() — PC 핑거프린트 수집
- `hostname` (socket.gethostname)
- `user` (os.getlogin / USERNAME env)
- `machine_guid` (Windows registry `HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid`)
- `macs` (getmac /FO CSV /NH → 모든 NIC MAC, dedup, uppercase, ':' 구분자)

#### 2. inspect() — 인스펙터 리포트
```json
{
  "관리정보": {"리포트제목", "수집시각", "호스트명", "사용자"},
  "하드웨어식별": {"MachineGuid", "전체MAC"},
  "보안판정": {"호스트명", "매칭PC"?, "MAC일치", "GUID일치", "판정", "판정코드", "상세"?}
}
```

#### 3. _judge() — 6가지 판정 코드

| 코드 | 조건 | 동작 |
|---|---|---|
| `FULL_AUTH` | hostname + mac + guid 모두 일치 | ✅ 허용 |
| `PARTIAL_AUTH` | mac 일치, guid 미등록 | ❌ 거부 (--register 권장) |
| `NOT_REGISTERED` | 미등록 PC | ❌ 거부 |
| `DISABLED` | registry 미설정 | ✅ 허용 (backward compat) |
| `REGISTRY_MISSING` | registry 파일 없음 | ❌ 거부 |
| `REGISTRY_PARSE_ERROR` | registry JSON 깨짐 | ❌ 거부 |

#### 4. is_allowed() — 메인 가드 진입점
```python
allowed, reason = pc_guard.is_allowed()
if not allowed:
    # SQM_inventory 시작 차단
    print(f"❌ 차단: {reason}", file=sys.stderr)
    sys.exit(1)
```

#### 5. register() — 현재 PC GUID 등록
- hostname 매칭 항목의 `machine_guid` 필드 채움
- 백업 자동 (`allowed_pcs.json.bak.YYYYMMDD_HHMMSS`)
- 결과: `{"ok": bool, "registered"?, "guid"?, "old_guid"?, "backup"?, "error"?}`

### CLI (tools/inspect_pc.py)

```powershell
# 인스펙터 실행 (env PC_GUARD_REGISTRY 자동)
python tools/inspect_pc.py

# registry 명시
python tools/inspect_pc.py --registry "D:\program-kdn\Network\allowed_pcs.json"

# 현재 PC GUID 등록
python tools/inspect_pc.py --register
```

Windows cp949 회피: stdout utf-8 reconfigure.

Exit code:
- `0` — FULL_AUTH 또는 DISABLED
- `1` — PARTIAL_AUTH, NOT_REGISTERED, REGISTRY_MISSING, PARSE_ERROR

### 비활성 기본 (backward compat)

`PC_GUARD_REGISTRY` 환경변수 미설정 시 `is_allowed() → True`.
main_webview.py 통합은 **v9.0.8 작업**.

### 운영 효과 (v9.0.8 이후)

- 허용된 PC에서만 SQM_inventory 동작
- 등록되지 않은 PC에서 실행 시 차단 UI
- GY_PC_Manager의 allowed_pcs.json을 단일 registry로 사용

### immediate fix (v9.0.7 외)

남대표님 PC (대흥남기동2025)의 MachineGuid `62a420c7-...`를
`D:\program-kdn\Network\allowed_pcs.json`에 등록:
- 다음 인스펙터 실행 시 PARTIAL_AUTH → FULL_AUTH
- 백업: `allowed_pcs.json.bak.20260722_144233`

### 테스트
- `tests/test_pc_guard.py` (26 tests, 누적)
  - `test_pc01~03` — collect_fingerprint (필수 키, list 형식, 대문자+':' 구분자)
  - `test_pc10~11` — get_registry_path (env unset/set)
  - `test_pc20~26` — _judge 6가지 판정 + MAC 대소문자 무시
  - `test_pc30~33` — register (hostname 매칭/미매칭/registry 없음)
  - `test_pc40~43` — is_allowed (DISABLED/FULL_AUTH/PARTIAL/NOT_REGISTERED)
  - `test_pc50~52` — inspect 3섹션 + 시나리오
  - `test_pc60~62` — CLI 실행 (env unset/registry missing/--register mismatch)

### 회귀
- 685 passed (v9.0.6 659 + 신규 26)

### 다음 (v9.0.8+)
- main_webview.py 시작 가드 통합 (PyWebView 에러 화면 → "등록되지 않은 PC" 메시지)
- GY_PC_Manager UI에서 PC 등록/해제 버튼
- 네트워크 공유 경로 자동 동기화
- Phase 3 (새 시즌) 후보
