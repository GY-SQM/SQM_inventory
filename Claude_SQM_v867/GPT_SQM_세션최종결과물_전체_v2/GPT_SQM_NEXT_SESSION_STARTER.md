# GPT_SQM_NEXT_SESSION_STARTER.md
Generated: 2026-04-04 18:10 (Asia/Seoul)

[Purpose]
A one-page execution guide to start immediately in the next session.

---

# 1. Execution Order

1. Run P0
2. Validate P0
3. Run P2 + Patch2
4. Test
5. Run P3 + Patch3
6. Test
7. Run P4 + Patch4
8. Test
9. Run P5 + Patch5
10. Final decision (GO / CONDITIONAL / NO-GO)

---

# 2. Command

cd 09_SCRIPTS
./run_all_p0.ps1

---

# 3. Rules

- NEVER proceed on FAIL
- ALWAYS check logs
- ALWAYS test before next step

---

# 4. Failure Handling

1. Stop immediately
2. Check logs
3. Fix issue
4. Re-run stage

---

# 5. Final Decision

GO = production ready  
CONDITIONAL = limited use  
NO-GO = fix required  

---

# 6. Ruby Note

Follow the sequence. Do not skip steps.
