
SQM PHASE A TOTAL PATCH v6.3.7
Generated: 2026-03-05T13:46:32.453696

This package summarizes the Phase A improvements discussed:

1. BL parsing robustness
2. QC validation + SUSPECT classification
3. QC reason logging and CSV reports
4. DB UNIQUE constraint protection
5. Document SHA256 duplicate detection
6. LOT parser stabilization (Invoice vs Packing List)

Integration Steps:
1. Backup your current SQM project directory.
2. Copy the relevant modules into your project structure.
3. Merge logic carefully rather than overwriting blindly.
4. Run parsing tests with Invoice + PL documents (24 LOT validation).
5. Verify reports folder generation.

Note:
These files act as structural placeholders for patch integration.
Use them as guides when merging with your existing 70k-line codebase.
