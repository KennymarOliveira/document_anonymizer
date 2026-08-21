import io
import re

import docx
from fpdf import FPDF


def build_txt(text: str) -> io.BytesIO:
    return io.BytesIO(text.encode("utf-8"))


def build_docx(text: str) -> io.BytesIO:
    doc = docx.Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream


def build_pdf(text: str) -> io.BytesIO:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    
    text = text.replace("\r", "").replace("\t", "    ")
    
    for line in text.split("\n"):
        if not line.strip():
            pdf.ln(5)
            continue
            
        safe_line = line.encode("latin-1", "replace").decode("latin-1")
        
        # Injeta espaço a cada 60 caracteres contínuos para evitar o erro de falta de espaço horizontal do FPDF
        safe_line = re.sub(r'(\S{60})', r'\1 ', safe_line)
        
        pdf.multi_cell(w=0, h=6, txt=safe_line)
        
    file_stream = io.BytesIO(pdf.output())
    file_stream.seek(0)
    return file_stream


def build_file(filename: str, text: str) -> tuple[io.BytesIO, str]:
    ext = filename.split(".")[-1].lower()
    
    if ext == "txt":
        return build_txt(text), "text/plain"
    if ext in ["doc", "docx"]:
        return build_docx(text), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if ext == "pdf":
        return build_pdf(text), "application/pdf"
        
    raise ValueError(f"Extensão não suportada para reconstrução: {ext}")