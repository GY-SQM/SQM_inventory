# 🚀 외출 후 작업 재개 가이드

## 1️⃣ Claude Code 재시작 명령

**가장 빠른 방법** — 권한 팝업 없이 완전 자율 모드:

```bash
claude -c --dangerously-skip-permissions
```

옵션 설명:
- `-c` (또는 `--continue`): 가장 최근 세션 그대로 이어받기
- `--dangerously-skip-permissions`: 모든 도구 사용 자동 허용 (외출 중 중단 없이 진행)

---

## 2️⃣ 만약 새 세션이 필요하면

```bash
claude --dangerously-skip-permissions
```

새 세션 시작 후 첫 메시지로:

```
@D:/program/SQM_inventory/Claude_SQM_v864_3/AUTONOMOUS_WORK_INSTRUCTIONS.md 읽고 그대로 진행해줘
```

---

## 3️⃣ 권한 영구 설정 (선택)

이미 `D:/program/SQM_inventory/Claude_SQM_v864_4/.claude/settings.local.json` 에는 다음 설정이 있어 자율 모드:

```json
{ "defaultMode": "bypassPermissions" }
```

v864-3 에 동일하게 적용하려면 `.claude/settings.local.json` 의 permissions 옆에 위 라인 추가.

---

## 4️⃣ 작업 시작 위치

- **현재 폴더**: `D:/program/SQM_inventory/Claude_SQM_v864_3`
- **브랜치**: `claude/v864-3-sprint0`
- **HEAD**: `17448f9` (모두 push 됨)

---

## 5️⃣ 자율 모드로 진행할 다음 작업

[AUTONOMOUS_WORK_INSTRUCTIONS.md](AUTONOMOUS_WORK_INSTRUCTIONS.md) 참고.
