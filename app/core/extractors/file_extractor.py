import io
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional
from zipfile import BadZipFile

import docx
import pymupdf
from docx.opc.exceptions import PackageNotFoundError


@dataclass
class ExtractedPage:
    """Texto de uma página e, para PDFs, o mapa caractere → coordenada."""

    page_number: int
    text: str
    char_rects: Optional[list[Optional[tuple[float, float, float, float]]]] = None


def _extract_pdf_char_rects(page: pymupdf.Page, text: str) -> list[Optional[tuple[float, float, float, float]]]:
    """Alinha o texto extraído aos retângulos dos caracteres do PDF.

    O texto usado pelos motores continua sendo ``page.get_text()``, mas cada
    caractere que também aparece no rawdict recebe seu retângulo correspondente.
    Diferenças de codificação ou espaços de layout ficam sem coordenada, em vez
    de deslocar a entidade para outro trecho da página.
    """
    raw_chars: list[tuple[str, tuple[float, float, float, float]]] = []
    for block in page.get_text("rawdict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                for char in span.get("chars", []):
                    raw_chars.append((char["c"], tuple(char["bbox"])))

    char_rects: list[Optional[tuple[float, float, float, float]]] = [None] * len(text)
    text_visible = [(idx, char) for idx, char in enumerate(text) if not char.isspace()]
    raw_visible = [(char, rect) for char, rect in raw_chars if not char.isspace()]

    matcher = SequenceMatcher(
        a="".join(char for _, char in text_visible),
        b="".join(char for char, _ in raw_visible),
        autojunk=False,
    )
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            text_idx = text_visible[block.a + offset][0]
            char_rects[text_idx] = raw_visible[block.b + offset][1]

    return char_rects


def rects_for_text_span(
    char_rects: Optional[list[Optional[tuple[float, float, float, float]]]],
    start: int,
    end: int,
) -> list[tuple[float, float, float, float]]:
    """Converte um intervalo de texto em um ou mais retângulos por linha."""
    if not char_rects or start < 0 or end > len(char_rects) or start >= end:
        return []

    rects: list[pymupdf.Rect] = []
    current: Optional[pymupdf.Rect] = None
    for raw_rect in char_rects[start:end]:
        if raw_rect is None:
            continue
        rect = pymupdf.Rect(raw_rect)
        if current is None:
            current = rect
            continue

        same_line = abs(rect.y0 - current.y0) <= 0.5 and abs(rect.y1 - current.y1) <= 0.5
        if same_line:
            current.include_rect(rect)
        else:
            rects.append(current)
            current = rect

    if current is not None:
        rects.append(current)

    return [(rect.x0, rect.y0, rect.x1, rect.y1) for rect in rects]


def render_segments_for_text_span(
    text: str,
    char_rects: Optional[list[Optional[tuple[float, float, float, float]]]],
    start: int,
    end: int,
) -> list[dict[str, object]]:
    """Retorna um retângulo e o trecho de texto correspondente por linha."""
    if not char_rects or start < 0 or end > len(char_rects) or start >= end:
        return []

    segments: list[dict[str, object]] = []
    current_rect: Optional[pymupdf.Rect] = None
    current_chars: list[str] = []

    def finish_segment() -> None:
        nonlocal current_rect, current_chars
        if current_rect is None:
            return
        segment_text = "".join(current_chars).strip()
        if segment_text:
            segments.append(
                {
                    "rect": (
                        current_rect.x0,
                        current_rect.y0,
                        current_rect.x1,
                        current_rect.y1,
                    ),
                    "text": segment_text,
                }
            )
        current_rect = None
        current_chars = []

    for index in range(start, end):
        raw_rect = char_rects[index]
        char = text[index]
        if raw_rect is None:
            if current_rect is not None:
                current_chars.append(char)
            continue

        rect = pymupdf.Rect(raw_rect)
        if current_rect is not None:
            same_line = (
                abs(rect.y0 - current_rect.y0) <= 0.5
                and abs(rect.y1 - current_rect.y1) <= 0.5
            )
            if not same_line:
                finish_segment()

        if current_rect is None:
            current_rect = rect
        else:
            current_rect.include_rect(rect)
        current_chars.append(char)

    finish_segment()
    return segments


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


def extract_pages_with_layout(filename: str, content: bytes) -> list[ExtractedPage]:
    """Extrai páginas e preserva coordenadas de caracteres quando for PDF."""
    ext = filename.split(".")[-1].lower()

    if ext == "pdf":
        try:
            with pymupdf.open(stream=content, filetype="pdf") as doc:
                pages: list[ExtractedPage] = []
                for index, page in enumerate(doc):
                    text = page.get_text()
                    pages.append(
                        ExtractedPage(
                            page_number=index + 1,
                            text=text,
                            char_rects=_extract_pdf_char_rects(page, text),
                        )
                    )
                return pages
        except Exception as exc:
            raise ValueError(f"PDF inválido ou corrompido: {exc}") from exc

    return [
        ExtractedPage(page_number=page_num, text=text)
        for page_num, text in extract_text_by_pages(filename, content)
    ]


def extract_text(filename: str, content: bytes) -> str:
    ext = filename.split(".")[-1].lower()

    if ext == "txt":
        return extract_text_from_txt(content)
    if ext == "pdf":
        return extract_text_from_pdf(content)
    if ext in ["doc", "docx"]:
        return extract_text_from_docx(content)

    raise ValueError(f"Extensão não suportada: {ext}")
