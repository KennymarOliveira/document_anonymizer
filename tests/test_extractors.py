import io
import zipfile

import pytest

from tests.utils import build_docx, build_pdf
from app.core.extractors.file_extractor import extract_text


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
