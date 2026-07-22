## SQM v8.8.6 — Hotfix: AUDIT-8 잔여 1건

릴리즈일: 2026-07-22
대상: v8.8.5 → v8.8.6 (1 커밋)

### Hotfix
- main_webview.py:274 — except Exception: pass → except Exception as e: log.debug("socket close 실패 (무시): {e}") (AUDIT-8 잔여, v8.7.0.2에서 7건 처리 시 1건 누락)

### 회귀
- 557 passed, 1 deselected (베이스라인 552 + 알파 5)