SQM Phase B (MVP) Patch v6.3.7B1
Generated: 2026-03-05 14:03:18

What’s included
- New dialog: gui_app_modular/dialogs/review_center.py
  * In-app PDF viewer (PyMuPDF) + drag ROI
  * Extract text from ROI (text-layer PDFs)
  * User enters "correct value" and applies to preview_data row field
- Integration into onestop_inbound.py
  * Adds "🧪 검수센터" button next to "📤 DB 업로드"
  * Enables button when upload becomes enabled
  * _open_review_center() applies corrections and refreshes preview tree

Notes
- MVP focuses on text PDFs. OCR / clipboard image capture to text will be added in next patch.
