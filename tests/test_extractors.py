import io
import zipfile

import pytest

from tests.utils import build_docx, build_pdf
from app.core.extractors.file_extractor import (
    extract_pages_with_layout,
    extract_text,
    extract_text_by_pages,
    rects_for_text_span,
    render_segments_for_text_span,
)


@pytest.fixture
def zip_sem_partes_opc() -> bytes:
    """Um .zip válido renomeado para .docx — não é um pacote OPC."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as arquivo:
        arquivo.writestr("qualquer.txt", "conteúdo")
    return buffer.getvalue()


def test_extract_text_txt():
    content = b"Texto de teste"
    result = extract_text("documento.txt", content)
    assert result == "Texto de teste"


def test_extract_text_txt_com_acentos():
    result = extract_text("documento.txt", "ação e coração".encode("utf-8"))
    assert result == "ação e coração"


def test_extract_text_pdf():
    conteudo = build_pdf("Primeira linha\nSegunda linha").getvalue()
    result = extract_text("documento.pdf", conteudo)

    assert "Primeira linha" in result
    assert "Segunda linha" in result


def test_extract_text_docx():
    conteudo = build_docx("Primeira linha\nSegunda linha").getvalue()
    result = extract_text("documento.docx", conteudo)

    assert result == "Primeira linha\nSegunda linha"


def test_extract_text_doc_usa_o_leitor_de_docx():
    conteudo = build_docx("Conteúdo").getvalue()
    assert extract_text("documento.doc", conteudo) == "Conteúdo"


def test_extract_text_extensao_maiuscula():
    assert extract_text("DOCUMENTO.TXT", b"ok") == "ok"


def test_extract_text_unsupported_extension():
    with pytest.raises(ValueError, match="Extensão não suportada"):
        extract_text("documento.csv", b"1,2,3")


def test_extract_text_txt_nao_utf8_levanta_value_error():
    with pytest.raises(ValueError, match="UTF-8"):
        extract_text("documento.txt", bytes([0xFF, 0xFE, 0x00]))


def test_extract_text_pdf_corrompido_levanta_value_error():
    with pytest.raises(ValueError, match="PDF inválido"):
        extract_text("documento.pdf", b"isto nao e um pdf")


def test_extract_text_docx_nao_zip_levanta_value_error():
    with pytest.raises(ValueError, match="DOCX inválido"):
        extract_text("documento.docx", b"isto nao e um docx")


def test_extract_text_docx_zip_sem_partes_opc_levanta_value_error(zip_sem_partes_opc):
    with pytest.raises(ValueError, match="DOCX inválido"):
        extract_text("documento.docx", zip_sem_partes_opc)


def test_extract_text_by_pages_txt():
    pages = extract_text_by_pages("doc.txt", b"Texto simples")
    assert pages == [(1, "Texto simples")]


def test_extract_text_by_pages_docx():
    conteudo = build_docx("Linha 1\nLinha 2").getvalue()
    pages = extract_text_by_pages("doc.docx", conteudo)
    assert pages == [(1, "Linha 1\nLinha 2")]


def test_extract_text_by_pages_pdf():
    import pymupdf
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 50), "Texto da Pagina 1")
    doc.new_page().insert_text((50, 50), "Texto da Pagina 2")
    pdf_bytes = doc.tobytes()

    pages = extract_text_by_pages("doc.pdf", pdf_bytes)
    assert len(pages) == 2
    assert pages[0][0] == 1
    assert "Texto da Pagina 1" in pages[0][1]
    assert pages[1][0] == 2
    assert "Texto da Pagina 2" in pages[1][1]


def test_extract_pages_with_layout_mapeia_span_de_pdf_para_retangulo():
    texto = "O cliente Carlos Eduardo assinou o contrato."
    content = build_pdf(texto).getvalue()

    page = extract_pages_with_layout("doc.pdf", content)[0]
    start = page.text.index("Carlos Eduardo")
    rects = rects_for_text_span(page.char_rects, start, start + len("Carlos Eduardo"))

    assert page.page_number == 1
    assert rects
    assert rects[0][2] > rects[0][0]
    assert rects[0][3] > rects[0][1]


def test_render_segments_separa_texto_quebrado_em_linhas():
    texto = "Lucas Andrade\nRamos"
    char_rects = [
        (0, 0, 1, 1) if char != "\n" else None
        for char in texto
    ]
    for index, char in enumerate(texto):
        if char == "R":
            char_rects[index] = (0, 2, 1, 3)
        elif index > texto.index("R"):
            char_rects[index] = (index, 2, index + 1, 3)

    segments = render_segments_for_text_span(texto, char_rects, 0, len(texto))

    assert [segment["text"] for segment in segments] == ["Lucas Andrade", "Ramos"]


def test_extract_text_by_pages_unsupported_extension():
    with pytest.raises(ValueError, match="Extensão não suportada"):
        extract_text_by_pages("doc.xlsx", b"")


def test_extract_text_by_pages_pdf_corrompido():
    with pytest.raises(ValueError, match="PDF inválido"):
        extract_text_by_pages("doc.pdf", b"nao pdf")

