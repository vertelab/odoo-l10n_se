#!/usr/bin/env python3
"""
Generate a vendor invoice PDF for AI invoice processing.

Purchase order and goods receipt are Odoo-native documents —
they should be created in Odoo, not as PDFs. This script only
generates the external vendor invoice PDF that feed into
account_invoice_ai.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle)
from reportlab.platypus.frames import Frame

OUTPUT_DIR = "/home/waland/fakturor"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Colours ──────────────────────────────────────────────────────────────────
DARK_BLUE  = HexColor("#1a3a5c")
LIGHT_BLUE = HexColor("#e8f0fa")
MED_BLUE   = HexColor("#2c5f8a")
ACCENT     = HexColor("#3a7bd5")
BORDER     = HexColor("#cccccc")
LIGHT_GREY = HexColor("#f5f5f5")
DARK_GREY  = HexColor("#333333")

# ── Styles ───────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

styles.add(ParagraphStyle("DocTitle", fontSize=18, textColor=DARK_BLUE,
                          spaceAfter=4, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("DocSubtitle", fontSize=10, textColor=grey,
                          spaceAfter=2, fontName="Helvetica"))
styles.add(ParagraphStyle("SectionHead", fontSize=11, textColor=DARK_BLUE,
                          spaceAfter=6, spaceBefore=10, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("Label", fontSize=8, textColor=grey,
                          fontName="Helvetica", leading=10))
styles.add(ParagraphStyle("Value", fontSize=9, textColor=DARK_GREY,
                          fontName="Helvetica-Bold", leading=11))
styles.add(ParagraphStyle("TableHeader", fontSize=8, textColor=white,
                          fontName="Helvetica-Bold", alignment=TA_CENTER))
styles.add(ParagraphStyle("TableCell", fontSize=8.5, textColor=DARK_GREY,
                          fontName="Helvetica", leading=11))
styles.add(ParagraphStyle("TableCellRight", fontSize=8.5, textColor=DARK_GREY,
                          fontName="Helvetica", alignment=TA_RIGHT, leading=11))
styles.add(ParagraphStyle("TableCellBold", fontSize=8.5, textColor=DARK_GREY,
                          fontName="Helvetica-Bold", leading=11))
styles.add(ParagraphStyle("Total", fontSize=10, textColor=DARK_BLUE,
                          fontName="Helvetica-Bold", alignment=TA_RIGHT))
styles.add(ParagraphStyle("Footer", fontSize=7, textColor=grey,
                          fontName="Helvetica", alignment=TA_CENTER))
styles.add(ParagraphStyle("Watermark", fontSize=40, textColor=HexColor("#f0f0f0"),
                          fontName="Helvetica-Bold", alignment=TA_CENTER))

# ── Shared data ──────────────────────────────────────────────────────────────
COMPANY = {
    "name": "Nordic Supplies AB",
    "org_nr": "559123-4561",
    "address": "Industrivägen 42",
    "zip_city": "111 22 Stockholm",
    "phone": "08-555 123 00",
    "email": "info@nordicsupplies.se",
    "iban": "SE35 5000 0000 0543 2100 0003",
    "bic": "ESSESESS",
    "bank": "SEB",
}

VENDOR = {
    "name": "TechComponents Europe AB",
    "org_nr": "551234-5686",
    "address": "Storgatan 15",
    "zip_city": "602 34 Norrköping",
    "country": "Sverige",
    "contact": "Maria Lindström",
    "email": "maria.lindstrom@techcomp.se",
    "phone": "011-123 45 00",
    "bank": "Swedbank",
    "iban": "SE80 8000 0843 1234 5678 9012",
    "bic": "SWEDSESS",
}

LINE_ITEMS = [
    {"art_nr": "CPU-I7-13700",  "desc": "Intel Core i7-13700K Processor",
     "qty_ordered": 10, "qty_received": 10, "unit": "st",
     "price": 3895.00, "total": 38950.00},
    {"art_nr": "MB-Z790-PRO",   "desc": "ASUS Z790-PRO WiFi Moderkort",
     "qty_ordered": 10, "qty_received": 10, "unit": "st",
     "price": 3295.00, "total": 32950.00},
    {"art_nr": "RAM-DDR5-32GB", "desc": "Corsair Vengeance DDR5 32GB (2x16GB)",
     "qty_ordered": 20, "qty_received": 18, "unit": "st",
     "price": 1295.00, "total": 25900.00},
    {"art_nr": "SSD-2TB-NVME",  "desc": "Samsung 990 Pro 2TB NVMe M.2 SSD",
     "qty_ordered": 15, "qty_received": 15, "unit": "st",
     "price": 1895.00, "total": 28425.00},
    {"art_nr": "PSU-850W-GLD",  "desc": "Corsair RM850x 850W Gold PSU",
     "qty_ordered": 10, "qty_received": 10, "unit": "st",
     "price": 1495.00, "total": 14950.00},
]

SUB_TOTAL = sum(item["total"] for item in LINE_ITEMS)
VAT_RATE  = 0.25
VAT_AMOUNT = round(SUB_TOTAL * VAT_RATE, 2)
TOTAL      = SUB_TOTAL + VAT_AMOUNT

PO_NUMBER = "PO-2024-0042"
INV_NUMBER = "INV-2024-0187"  # vendor's own invoice number

DELIVERY_DATE = "2024-06-18"  # referenced on the invoice
PO_DATE = "2024-06-10"        # purchase order date (Odoo-native PO, not a PDF)
INVOICE_DATE = "2024-06-20"
DUE_DATE = "2024-07-20"


# ── Number formatting ────────────────────────────────────────────────────────
def fmt_price(amount):
    """Format price with space as thousands separator and dot as decimal,
    without 'kr' suffix embedded in the value line.
    The 'kr' is added separately so AI extracts clean '3895.00'."""
    return f"{amount:,.2f}".replace(",", " ")

def fmt_price_with_kr(amount):
    """Space-separated thousands, dot decimal, appended ' kr'."""
    return f"{fmt_price(amount)} kr"


def header_footer(canvas, doc):
    """Shared header/footer for all pages."""
    canvas.saveState()
    width, height = A4

    # Header bar
    canvas.setFillColor(DARK_BLUE)
    canvas.rect(0, height - 28*mm, width, 28*mm, fill=1, stroke=0)

    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(15*mm, height - 17*mm, COMPANY["name"])

    canvas.setFont("Helvetica", 7)
    canvas.drawString(15*mm, height - 22*mm,
                      f"{COMPANY['address']}, {COMPANY['zip_city']} | "
                      f"Org.nr: {COMPANY['org_nr']} | "
                      f"{COMPANY['phone']} | {COMPANY['email']}")

    # Footer
    canvas.setFillColor(BORDER)
    canvas.rect(0, 18*mm, width, 0.5, fill=1, stroke=0)

    canvas.setFillColor(grey)
    canvas.setFont("Helvetica", 6.5)
    canvas.drawString(15*mm, 12*mm,
                      f"{COMPANY['name']} | {COMPANY['address']}, {COMPANY['zip_city']} | "
                      f"Org.nr: {COMPANY['org_nr']} | "
                      f"Bank: {COMPANY['bank']} | "
                      f"IBAN: {COMPANY['iban']} | BIC: {COMPANY['bic']}")
    canvas.drawRightString(width - 15*mm, 12*mm, f"Sida {canvas.getPageNumber()}")

    canvas.restoreState()


def build_doc_header(doc_title, doc_number, doc_date, extra_info=None):
    """Build the document title block."""
    elements = []
    elements.append(Paragraph(doc_title, styles["DocTitle"]))
    elements.append(Paragraph(f"Nr: {doc_number}", styles["DocSubtitle"]))
    elements.append(Paragraph(f"Datum: {doc_date}", styles["Value"]))
    if extra_info:
        for k, v in extra_info.items():
            elements.append(Paragraph(f"{k}: {v}", styles["Value"]))
    elements.append(Spacer(1, 6*mm))
    return elements


def build_party_block(label, data):
    """A left-aligned block of labelled values."""
    rows = []
    rows.append(Paragraph(label, styles["SectionHead"]))
    rows.append(Paragraph(f"<b>{data['name']}</b>", styles["Value"]))
    if "org_nr" in data:
        rows.append(Paragraph(f"Org.nr: {data['org_nr']}", styles["Value"]))
    if "address" in data:
        rows.append(Paragraph(data["address"], styles["Value"]))
    if "zip_city" in data:
        rows.append(Paragraph(data["zip_city"], styles["Value"]))
    if "country" in data:
        rows.append(Paragraph(data["country"], styles["Value"]))
    if "contact" in data:
        rows.append(Paragraph(f"Kontakt: {data['contact']}", styles["Value"]))
    if "email" in data:
        rows.append(Paragraph(data["email"], styles["Value"]))
    return rows


def build_party_table(left_label, left_data, right_label, right_data):
    """Two-column party block."""
    left_rows = build_party_block(left_label, left_data)
    right_rows = build_party_block(right_label, right_data)

    # Pad
    max_rows = max(len(left_rows), len(right_rows))
    left_rows += [Paragraph("", styles["Value"])] * (max_rows - len(left_rows))
    right_rows += [Paragraph("", styles["Value"])] * (max_rows - len(right_rows))

    table_data = []
    for l, r in zip(left_rows, right_rows):
        table_data.append([l, r])

    t = Table(table_data, colWidths=[85*mm, 85*mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def build_line_table(items, show_cols, received=False, totals_override=None):
    """Build line-item table. show_cols determines which columns to include.
    totals_override: optional dict with 'sub', 'vat', 'total' for invoice-specific totals.
    
    NOTE: prices use space-as-thousands + dot-as-decimal format (e.g. '3 895.00')
    to produce clean AI-extractable numbers like '3895.00'."""
    elements = []
    elements.append(Paragraph("Artiklar / Tjänster", styles["SectionHead"]))

    # Use overrides or globals
    sub = totals_override["sub"] if totals_override else SUB_TOTAL
    vat = totals_override["vat"] if totals_override else VAT_AMOUNT
    tot = totals_override["total"] if totals_override else TOTAL

    # Determine headers
    headers = []
    widths = []
    if "art_nr" in show_cols:
        headers.append("Art.nr")
        widths.append(22*mm)
    headers.append("Beskrivning")
    if "art_nr" in show_cols:
        widths.append(52*mm)
    else:
        widths.append(74*mm)
    if "ordered" in show_cols:
        headers.append("Beställt")
        widths.append(16*mm)
    if "received" in show_cols:
        headers.append("Levererat")
        widths.append(16*mm)
    if "backorder" in show_cols:
        headers.append("Rest")
        widths.append(14*mm)
    if "unit" in show_cols:
        headers.append("Enhet")
        widths.append(12*mm)
    if "price" in show_cols:
        headers.append("á-pris")
        widths.append(20*mm)
    if "total" in show_cols:
        headers.append("Belopp")
        widths.append(24*mm)

    # Build table data
    header_row = [Paragraph(h, styles["TableHeader"]) for h in headers]
    table_data = [header_row]

    for item in items:
        row = []
        if "art_nr" in show_cols:
            row.append(Paragraph(item["art_nr"], styles["TableCell"]))
        row.append(Paragraph(item["desc"], styles["TableCell"]))
        if "ordered" in show_cols:
            row.append(Paragraph(str(item["qty_ordered"]), styles["TableCellRight"]))
        if "received" in show_cols:
            row.append(Paragraph(str(item["qty_received"]), styles["TableCellRight"]))
        if "backorder" in show_cols:
            back = item["qty_ordered"] - item["qty_received"]
            txt = str(back) if back > 0 else "\u2014"
            row.append(Paragraph(txt, styles["TableCellRight"]))
        if "unit" in show_cols:
            row.append(Paragraph(item["unit"], styles["TableCell"]))
        if "price" in show_cols:
            row.append(Paragraph(fmt_price_with_kr(item["price"]), styles["TableCellRight"]))
        if "total" in show_cols:
            row.append(Paragraph(fmt_price_with_kr(item["total"]), styles["TableCellRight"]))
        table_data.append(row)

    # Summary rows
    if "total" in show_cols:
        # Empty spacer row
        empty = [Paragraph("", styles["TableCell"]) for _ in headers[:-1]]
        table_data.append(empty + [Paragraph("", styles["TableCellRight"])])

        # Subtotal
        sub_row = [Paragraph("", styles["TableCell"]) for _ in headers[:-2]]
        sub_row.append(Paragraph("Delsumma:", styles["TableCellBold"]))
        sub_row.append(Paragraph(fmt_price_with_kr(sub), styles["TableCellBold"]))
        table_data.append(sub_row)

        # VAT
        vat_row = [Paragraph("", styles["TableCell"]) for _ in headers[:-2]]
        vat_row.append(Paragraph(f"Moms ({VAT_RATE*100:.0f}%):", styles["TableCell"]))
        vat_row.append(Paragraph(fmt_price_with_kr(vat), styles["TableCell"]))
        table_data.append(vat_row)

        # Total
        total_row = [Paragraph("", styles["TableCell"]) for _ in headers[:-2]]
        total_row.append(Paragraph("ATT BETALA:", styles["TableCellBold"]))
        total_row.append(Paragraph(fmt_price_with_kr(tot), styles["Total"]))
        table_data.append(total_row)

    t = Table(table_data, colWidths=widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_GREY]),
    ]

    # Highlight backorder rows
    if "backorder" in show_cols:
        for i, item in enumerate(items):
            if item["qty_ordered"] > item["qty_received"]:
                style_cmds.append(("BACKGROUND", (0, i+1), (-1, i+1), HexColor("#fff3cd")))

    # Highlight total row
    if "total" in show_cols:
        total_idx = len(table_data) - 1
        style_cmds.append(("BACKGROUND", (0, total_idx), (-1, total_idx), LIGHT_BLUE))
        style_cmds.append(("LINEABOVE", (0, total_idx-1), (-1, total_idx-1), 1, DARK_BLUE))

    t.setStyle(TableStyle(style_cmds))
    return t


def build_vendor_invoice():
    """Leverantörsfaktura (Vendor Bill) — the external PDF that account_invoice_ai processes."""
    path = os.path.join(OUTPUT_DIR, "03_Leverantorsfaktura_INV-2024-0187.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=32*mm, bottomMargin=22*mm)
    story = []

    # Title
    story.extend(build_doc_header("LEVERANTÖRSFAKTURA", INV_NUMBER, INVOICE_DATE, {
        "Förfallodatum": DUE_DATE,
        "Er order": PO_NUMBER,
        "Er referens": "Anders Lindström",
    }))

    # Parties
    story.append(build_party_table("Faktura från", VENDOR, "Faktura till", COMPANY))
    story.append(Spacer(1, 8*mm))

    # Line items (invoice perspective: what was delivered)
    invoice_items = [
        {"art_nr": i["art_nr"], "desc": i["desc"],
         "qty_ordered": i["qty_received"],  # Invoice for received qty
         "qty_received": i["qty_received"],
         "unit": i["unit"], "price": i["price"],
         "total": i["qty_received"] * i["price"]}
        for i in LINE_ITEMS
    ]
    # Recalculate totals based on received quantities
    inv_sub = sum(i["total"] for i in invoice_items)
    inv_vat = round(inv_sub * VAT_RATE, 2)
    inv_total = inv_sub + inv_vat

    inv_totals = {"sub": inv_sub, "vat": inv_vat, "total": inv_total}
    story.append(build_line_table(invoice_items,
        show_cols=["art_nr", "received", "unit", "price", "total"],
        totals_override=inv_totals))

    story.append(Spacer(1, 8*mm))

    # Payment info
    story.append(Paragraph("Betalningsinformation", styles["SectionHead"]))
    pay_data = [
        [Paragraph("Bank:", styles["TableCellBold"]),
         Paragraph(VENDOR["bank"], styles["TableCell"])],
        [Paragraph("IBAN:", styles["TableCellBold"]),
         Paragraph(VENDOR["iban"], styles["TableCell"])],
        [Paragraph("BIC:", styles["TableCellBold"]),
         Paragraph(VENDOR["bic"], styles["TableCell"])],
        [Paragraph("Förfallodatum:", styles["TableCellBold"]),
         Paragraph(DUE_DATE, styles["TableCell"])],
        [Paragraph("OCR/Referens:", styles["TableCellBold"]),
         Paragraph(INV_NUMBER, styles["TableCell"])],
    ]
    pay_table = Table(pay_data, colWidths=[35*mm, 80*mm])
    pay_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREY),
    ]))
    story.append(pay_table)

    # Notes
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(
        f"<i>Tack för er order! Vid frågor, kontakta {VENDOR['contact']}: "
        f"{VENDOR['email']}, {VENDOR['phone']}</i>",
        styles["TableCell"]))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"✓ {path}")
    return path


# ── Build all ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Genererar leverantörsfaktura för AI-behandling\n")
    print("Obs: Inköpsorder och Inleverans hanteras som Odoo-dokument, ej PDF.\n")
    build_vendor_invoice()
    print(f"\n✅ Klart! Fakturan finns i {OUTPUT_DIR}")
