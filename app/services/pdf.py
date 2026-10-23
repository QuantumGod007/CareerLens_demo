from io import BytesIO
from pathlib import Path
import re
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether

from app.models import SECTION_ORDER
from app.services.content import clean_profile, grouped_entries


class PDFError(ValueError):
    pass


def read_pdf(data, max_pages=15):
    if not data.startswith(b'%PDF-'):
        raise PDFError('The uploaded file is not a PDF.')
    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise PDFError('Password-protected PDFs are not supported. Upload an unlocked copy.')
        if not len(reader.pages) or (max_pages and len(reader.pages) > max_pages):
            raise PDFError('Upload a resume with 1 to 15 pages.')
        text = '\n'.join(p.extract_text() or '' for p in reader.pages)
        return text, {'pages': len(reader.pages)}
    except PDFError:
        raise
    except Exception as exc:
        raise PDFError('This PDF could not be read. Export a new PDF and try again.') from exc


def register_fonts():
    # Bundle fonts so every machine produces the same PDF, including Greek and
    # Cyrillic characters that were missing from ReportLab's Vera font.
    fonts = Path(__file__).resolve().parent.parent / 'assets' / 'fonts'
    if 'ResumeSans' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('ResumeSans', str(fonts / 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('ResumeSans-Bold', str(fonts / 'DejaVuSans-Bold.ttf')))


def create_pdf(profile, path, section_order=None):
    profile = clean_profile(profile)
    register_fonts()
    ink, muted, accent = colors.HexColor('#182433'), colors.HexColor('#536071'), colors.HexColor('#3056A0')
    body = ParagraphStyle('body', fontName='ResumeSans', fontSize=10.2, leading=15.3, textColor=ink,
                          spaceAfter=8, splitLongWords=True)
    heading = ParagraphStyle('heading', fontName='ResumeSans-Bold', fontSize=10, leading=15,
                             textColor=accent, spaceBefore=13, spaceAfter=6, keepWithNext=True)
    name = ParagraphStyle('name', parent=body, fontName='ResumeSans-Bold', fontSize=22, leading=29,
                          alignment=TA_CENTER, spaceAfter=6)
    contact = ParagraphStyle('contact', parent=body, fontSize=9, leading=13, textColor=muted,
                             alignment=TA_CENTER, spaceAfter=4)
    entry_heading = ParagraphStyle('entry', parent=body, fontName='ResumeSans-Bold', spaceBefore=5,
                                   spaceAfter=4, keepWithNext=True)
    bullet = ParagraphStyle('bullet', parent=body, leftIndent=12, bulletIndent=1,
                            bulletFontName='ResumeSans', bulletFontSize=9, spaceAfter=5)
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=47, leftMargin=47, topMargin=40,
                            bottomMargin=43, title=f'{profile.name or "Candidate"} - Resume', author=profile.name)
    safe = lambda text: escape(text).replace('\n', '<br/>')
    flow = []
    if profile.name:
        flow.append(Paragraph(safe(profile.name), name))
    contacts = [v for v in [profile.email, profile.phone, profile.location] if v]
    if contacts:
        flow.append(Paragraph(safe(' | '.join(contacts)), contact))
    for link in profile.links:
        flow.append(Paragraph(safe(link), contact))
    flow += [Spacer(1, 10), HRFlowable(width='100%', thickness=0.7, color=colors.HexColor('#CBD3DE'))]
    order = list(dict.fromkeys((section_order or SECTION_ORDER) + SECTION_ORDER))
    # Skills stay factual; no keyword stuffing from the job description.
    if profile.skills:
        flow += [Paragraph('SKILLS', heading), Paragraph(safe(' | '.join(profile.skills)), body)]
    for section in order:
        facts = [f for f in profile.facts if f.section == section]
        if facts:
            flow.append(Paragraph(section.upper(), heading))
            for entry in grouped_entries(facts):
                if entry['heading']:
                    flow.append(Paragraph(safe(entry['heading']), entry_heading))
                for text in entry['items']:
                    paragraph = Paragraph(safe(text), bullet if entry['heading'] else body,
                                          bulletText='•' if entry['heading'] else None)
                    flow.append(KeepTogether([paragraph]) if entry['heading'] else paragraph)

    def footer(canvas, document):
        canvas.setFont('ResumeSans', 7)
        canvas.setFillColor(muted)
        canvas.drawRightString(A4[0] - 47, 24, f'Page {document.page}')

    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
    text, meta = read_pdf(Path(path).read_bytes(), max_pages=None)
    # Generated page furniture must not interrupt a fact that spans a page break.
    text = re.sub(r'^Page \d+\s*$', '', text, flags=re.MULTILINE)
    return text, meta
