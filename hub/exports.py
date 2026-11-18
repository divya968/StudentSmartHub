"""Excel (.xlsx) and PDF export helpers."""
from io import BytesIO
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def build_xlsx(title, headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = title[:30]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="6D28D9")
        cell.alignment = Alignment(horizontal="center")
    for r in rows:
        ws.append(["" if v is None else v for v in r])
    for col in ws.columns:
        width = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 10), 60)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _para(text, style):
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def build_table_pdf(title, headers, rows):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm, title=title)
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=8.5, leading=11)
    head = ParagraphStyle("head", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    data = [[_para(h, head) for h in headers]] + [[_para(v if v is not None else "", cell) for v in r] for r in rows]
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6D28D9")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F3FF")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDD6FE")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    doc.build([Paragraph(escape(title), styles["Title"]), Spacer(1, 8), table])
    return buf.getvalue()


def build_note_pdf(note):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title=note.title)
    styles = getSampleStyleSheet()
    meta = ParagraphStyle("meta", parent=styles["Normal"], textColor=colors.HexColor("#6B7280"))
    story = [Paragraph(escape(note.title), styles["Title"]),
             Paragraph(escape(f"{note.subject}  |  {note.updated_at:%d %b %Y}"
                              + (f"  |  Tags: {note.tags}" if note.tags else "")), meta),
             Spacer(1, 14)]
    for block in note.content.replace("\r", "").split("\n"):
        line = block.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
        if line.startswith("#"):
            story.append(Paragraph(escape(line.lstrip("# ")), styles["Heading2"]))
        elif line[:2] in ("- ", "* "):
            story.append(Paragraph("• " + escape(line[2:]), styles["BodyText"]))
        else:
            story.append(Paragraph(escape(line).replace("**", ""), styles["BodyText"]))
    doc.build(story)
    return buf.getvalue()
