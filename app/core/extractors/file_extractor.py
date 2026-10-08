import io
from zipfile import BadZipFile

import docx
import pymupdf
from docx.opc.exceptions import PackageNotFoundError


def extract_text_from_txt(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Arquivo TXT não está codificado em UTF-8.") from exc


def extract_text_from_pdf(content: bytes) -> str:
    try:
        with pymupdf.open(stream=content, filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc if page.get_text())
    except Exception as exc:
        raise ValueError(f"PDF inválido ou corrompido: {exc}") from exc


def extract_text_from_docx(content: bytes) -> str:
    # python-docx propaga BadZipFile para bytes que não são um zip e KeyError
    # para um zip válido sem as partes de um OPC (ex.: .zip renomeado).
    try:
        doc = docx.Document(io.BytesIO(content))
    except (PackageNotFoundError, BadZipFile, KeyError) as exc:
        raise ValueError("DOCX inválido ou corrompido.") from exc

    return "\n".join(paragraph.text for paragraph in doc.paragraphs)


def extract_text_by_pages(filename: str, content: bytes) -> list[tuple[int, str]]:
    """Extrai o texto estruturado por página no formato [(page_num, text), ...], 1-indexed."""
    ext = filename.split(".")[-1].lower()

    if ext == "txt":
        return [(1, extract_text_from_txt(content))]
    if ext in ["doc", "docx"]:
        return [(1, extract_text_from_docx(content))]
    if ext == "pdf":
        try:
            with pymupdf.open(stream=content, filetype="pdf") as doc:
                return [(i + 1, page.get_text()) for i, page in enumerate(doc)]
        except Exception as exc:
            raise ValueError(f"PDF inválido ou corrompido: {exc}") from exc

    raise ValueError(f"Extensão não suportada: {ext}")


def extract_text(filename: str, content: bytes) -> str:
    ext = filename.split(".")[-1].lower()

    if ext == "txt":
        return extract_text_from_txt(content)
    if ext == "pdf":
        return extract_text_from_pdf(content)
    if ext in ["doc", "docx"]:
        return extract_text_from_docx(content)

    raise ValueError(f"Extensão não suportada: {ext}")