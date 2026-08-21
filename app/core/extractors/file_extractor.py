import io

import docx
import pypdf


def extract_text_from_txt(content: bytes) -> str:
    return content.decode("utf-8")


def extract_text_from_pdf(content: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())


def extract_text_from_docx(content: bytes) -> str:
    doc = docx.Document(io.BytesIO(content))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)


def extract_text(filename: str, content: bytes) -> str:
    ext = filename.split(".")[-1].lower()
    
    if ext == "txt":
        return extract_text_from_txt(content)
    if ext == "pdf":
        return extract_text_from_pdf(content)
    if ext in ["doc", "docx"]:
        return extract_text_from_docx(content)
        
    raise ValueError(f"Extensão não suportada: {ext}")