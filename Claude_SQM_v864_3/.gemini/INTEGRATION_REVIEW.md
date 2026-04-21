# SQM INTEGRATION REVIEW
# Time: 2026-04-19 14:30 (Asia/Seoul)

## Mission
Review Team A~D outputs before merge.
No unsafe merge is allowed.

## Review Order
1. Team A result
2. Team B result
3. Team C result
4. Team D result
5. Cross-team dependency review
6. Regression gate review
7. Merge decision

## 1. Team Result Summary
| Team | Scope | Main Files | Gate Status | Merge Risk |
|---|---|---|---|---|
| Team A | Runtime | run.py etc. | PASS/FAIL | Low/Med/High |
| Team B | UI | MenuBar.jsx etc. | PASS/FAIL | Low/Med/High |
| Team C | API | routes/services/etc. | PASS/FAIL | Low/Med/High |
| Team D | Engine | outbound_mixin.py etc. | PASS/FAIL | Low/Med/High |

## 2. Cross-Team Dependency Check
Check the following:
- Team A startup changes affecting API or frontend boot
- Team B UI expectations conflicting with Team C response contracts
- Team C contract changes affecting Team B parse logic
- Team D engine output changes affecting Team C response mapping
- shared file edit conflicts
- duplicated patch intent

## 3. Required Gates Before Merge
- compile check on changed Python files
- smoke test
- pytest -q
- core scenario verification

## 4. Core Scenario Verification
Verify at minimum:
- app boot
- menu navigation
- key API call
- major engine flow
- export/report trigger if applicable
- relaunch stability

## 5. Merge Block Conditions
Block merge if:
- any team failed gate
- response contract mismatch remains
- startup instability remains
- duplicate mutation risk remains
- no rollback path is described
- same file modified incompatibly by multiple teams

## 6. Merge Decision Format
[Integration Summary]
[Team Gate Status]
[Cross-Team Conflicts]
[Regression Result]
[Merge Decision]
[Blocked Items]
[Next Action]

## 7. Final Decision
Choose exactly one:
- APPROVED FOR MERGE
- APPROVED WITH CONDITIONS
- BLOCKED UNTIL FIXED
