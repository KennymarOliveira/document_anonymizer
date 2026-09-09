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
