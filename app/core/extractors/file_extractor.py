import io
from zipfile import BadZipFile

import docx
import pypdf
from docx.opc.exceptions import PackageNotFoundError
from pypdf.errors import PyPdfError


def extract_text_from_txt(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Arquivo TXT não está codificado em UTF-8.") from exc


def extract_text_from_pdf(content: bytes) -> str:
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    except PyPdfError as exc:
        raise ValueError(f"PDF inválido ou corrompido: {exc}") from exc


def extract_text_from_docx(content: bytes) -> str:
    # python-docx propaga BadZipFile para bytes que não são um zip e KeyError
    # para um zip válido sem as partes de um OPC (ex.: .zip renomeado).
    try:
        doc = docx.Document(io.BytesIO(content))
    except (PackageNotFoundError, BadZipFile, KeyError) as exc:
        raise ValueError("DOCX inválido ou corrompido.") from exc

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