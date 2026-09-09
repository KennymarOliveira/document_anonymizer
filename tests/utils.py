import io
import docx
from fpdf import FPDF

def build_docx(texto: str) -> io.BytesIO:
    doc = docx.Document()
    doc.add_paragraph(texto)
    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out

def build_pdf(texto: str) -> io.BytesIO:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)
    # Just a simple pdf generator for testing
    pdf.multi_cell(0, 10, text=texto)
    out = io.BytesIO(pdf.output())
    return out
