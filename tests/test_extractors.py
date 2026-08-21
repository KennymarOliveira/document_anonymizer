import pytest
from app.core.extractors.file_extractor import extract_text

def test_extract_text_txt():
    content = b"Texto de teste"
    result = extract_text("documento.txt", content)
    assert result == "Texto de teste"

def test_extract_text_unsupported_extension():
    with pytest.raises(ValueError):
        extract_text("documento.csv", b"1,2,3")