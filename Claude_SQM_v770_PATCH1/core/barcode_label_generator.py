"""
SQM v6.12 Stage7 — 바코드 라벨 PDF 생성기
작성자: Ruby
"""
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

def generate_barcode_labels(tonbags: list, output_dir: str = 'output/labels',
                             filename: str = 'batch_labels.pdf') -> str:
    """톤백 목록 → A6 바코드 라벨 PDF 생성"""
    try:
        from reportlab.lib.pagesizes import A6
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except ImportError:
        raise ImportError("reportlab 필요: pip install reportlab")
    try:
        import barcode
        from barcode.writer import ImageWriter
    except ImportError:
        raise ImportError("python-barcode 필요: pip install python-barcode")
    try:
        import qrcode
    except ImportError:
        qrcode = None

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    pdf_path = os.path.join(output_dir, filename)
    c = canvas.Canvas(pdf_path, pagesize=A6)
    page_w, page_h = A6
    temp_dir = os.path.join(output_dir, '_temp')
    Path(temp_dir).mkdir(exist_ok=True)

    for idx, tb in enumerate(tonbags):
        tonbag_no = str(tb.get('tonbag_no') or '').strip().upper()
        if not tonbag_no:
            raw_sub_lt = tb.get('sub_lt', 0)
            tonbag_no = 'S00' if int(raw_sub_lt or 0) == 0 else f"{int(raw_sub_lt):03d}"
        elif tonbag_no in {'S0', 'S00'}:
            tonbag_no = 'S00'
        elif tonbag_no.isdigit():
            tonbag_no = tonbag_no.zfill(3)
        uid = tb.get('tonbag_uid') or f"{tb.get('lot_no','?')}-{tonbag_no}"
        lot_no = tb.get('lot_no', '')
        tb.get('sub_lt', 0)
        weight = tb.get('weight', 0)
        margin = 8 * mm
        y = page_h - margin

        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(page_w/2, y, "SQM TONBAG LABEL")
        y -= 18*mm
        c.setFont("Helvetica", 10)
        c.drawString(margin, y, f"LOT: {lot_no}")
        y -= 6*mm
        c.drawString(margin, y, f"Tonbag: #{tonbag_no}  |  {weight:.0f} kg")
        y -= 8*mm
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(page_w/2, y, f"UID: {uid}")
        y -= 10*mm

        try:
            code128 = barcode.get('code128', uid, writer=ImageWriter())
            bc_path = os.path.join(temp_dir, f"bc_{idx}")
            bc_file = code128.save(bc_path, options={'module_width':0.3, 'module_height':12, 'quiet_zone':2, 'text_distance':3, 'font_size':8})
            c.drawImage(bc_file, margin, y-20*mm, width=page_w-2*margin, height=18*mm, preserveAspectRatio=True)
            y -= 25*mm
        except Exception as e:
            c.drawString(margin, y-5*mm, f"[바코드 실패: {e}]")
            y -= 10*mm

        if qrcode:
            try:
                qr = qrcode.QRCode(box_size=3, border=2)
                qr.add_data(f"LOT:{lot_no}|TB:{tonbag_no}|UID:{uid}|W:{weight}")
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white")
                qr_path = os.path.join(temp_dir, f"qr_{idx}.png")
                qr_img.save(qr_path)
                qr_sz = 25*mm
                c.drawImage(qr_path, page_w-margin-qr_sz, y-qr_sz, width=qr_sz, height=qr_sz)
            except Exception as e:
                logger.debug(f"QR code generation skipped: {e}")

        c.setFont("Helvetica", 7)
        c.drawString(margin, margin, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        if idx < len(tonbags)-1:
            c.showPage()

    c.save()
    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        logger.debug(f"Temporary barcode directory cleanup skipped: {e}")
    logger.info(f"바코드 라벨 PDF: {pdf_path} ({len(tonbags)}건)")
    return pdf_path
