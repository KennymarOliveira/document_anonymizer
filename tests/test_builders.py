import io
import pytest
from app.core.builders.file_builder import (
    anonymize_docx_in_place,
    anonymize_pdf_in_place,
    build_anonymized_file,
)
from tests.utils import build_docx, build_pdf
from app.core.extractors.file_extractor import extract_text

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

def test_build_anonymized_file_txt():
    content = b"Nome: Joao da Silva, CPF: 123.456.789-00"
    entities = [{"text": "Joao da Silva"}, {"text": "123.456.789-00"}]
    
    stream, media_type = build_anonymized_file("teste.txt", content, entities)
    
    assert media_type == "text/plain"
    text = stream.getvalue().decode("utf-8")
    assert "Joao da Silva" not in text
    assert "123.456.789-00" not in text
    assert "Nome: █████████████, CPF: ██████████████" in text

def test_anonymize_docx_in_place():
    texto = "O autor Joao da Silva requereu..."
    original_docx = build_docx(texto).getvalue()
    entities = [{"text": "Joao da Silva"}]
    
    anonymized_stream = anonymize_docx_in_place(original_docx, entities)
    
    # Extrair texto para verificar se foi substituido
    extracted = extract_text("teste.docx", anonymized_stream.getvalue())
    assert "Joao da Silva" not in extracted
    assert "█████████████" in extracted

def test_anonymize_pdf_in_place():
    texto = "O autor Joao da Silva requereu..."
    original_pdf = build_pdf(texto).getvalue()
    entities = [{"text": "Joao da Silva"}]
    
    anonymized_stream = anonymize_pdf_in_place(original_pdf, entities)
    
    extracted = extract_text("teste.pdf", anonymized_stream.getvalue())
    assert "Joao da Silva" not in extracted

def test_build_anonymized_file_routing():
    texto = "Conteudo do arquivo com Maria"
    entities = [{"text": "Maria"}]
    
    # TXT
    s, m = build_anonymized_file("doc.txt", texto.encode("utf-8"), entities)
    assert m == "text/plain"
    
    # DOCX
    s, m = build_anonymized_file("doc.docx", build_docx(texto).getvalue(), entities)
    assert m == DOCX_MEDIA_TYPE
    
    # DOC
    s, m = build_anonymized_file("doc.doc", build_docx(texto).getvalue(), entities)
    assert m == DOCX_MEDIA_TYPE
    
    # PDF
    s, m = build_anonymized_file("doc.pdf", build_pdf(texto).getvalue(), entities)
    assert m == "application/pdf"

def test_build_anonymized_file_unsupported_extension():
    with pytest.raises(ValueError, match="Extensão não suportada"):
        build_anonymized_file("doc.csv", b"1,2,3", [])


def test_anonymize_pdf_in_place_with_page_targeting():
    import pymupdf
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 50), "Pagina 1: Joao da Silva e CPF 111.222.333-44")
    doc.new_page().insert_text((50, 50), "Pagina 2: Joao da Silva permanece aqui")
    pdf_bytes = doc.tobytes()

    # Tag apenas para página 1
    entities = [{"text": "Joao da Silva", "page": 1}, {"text": "111.222.333-44", "page": 1}]
    anonymized = anonymize_pdf_in_place(pdf_bytes, entities)

    res = pymupdf.open(stream=anonymized.getvalue(), filetype="pdf")
    p1 = res[0].get_text()
    p2 = res[1].get_text()

    assert "Joao da Silva" not in p1
    assert "111.222.333-44" not in p1
    assert "Joao da Silva" in p2


def test_anonymize_pdf_in_place_multipage_concurrency():
    import pymupdf
    doc = pymupdf.open()
    for i in range(6):
        doc.new_page().insert_text((50, 50), f"Pagina {i+1}: Segredo-{i+1}")
    pdf_bytes = doc.tobytes()

    entities = [{"text": f"Segredo-{i+1}", "page": i + 1} for i in range(6)]
    anonymized = anonymize_pdf_in_place(pdf_bytes, entities)

    res = pymupdf.open(stream=anonymized.getvalue(), filetype="pdf")
    assert len(res) == 6
    for i in range(6):
        assert f"Segredo-{i+1}" not in res[i].get_text()

