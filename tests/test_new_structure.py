"""Testes unitários para validar a nova estrutura modular da aplicação."""
import pytest
from fastapi.testclient import TestClient

from app.core.configuration.settings import settings
from app.core.security.exceptions import InvalidFileError
from app.core.security.logger import get_logger, setup_logging
from app.models.document import AnonymizationResult, DocumentMetadata, EntityMatch
from app.services.utils import (
    create_download_headers,
    get_anonymized_filename,
    validate_uploaded_file,
)
from routes import app

client = TestClient(app)


def test_settings_initialization():
    """Valida se as configurações são carregadas com valores esperados."""
    assert settings.PROJECT_NAME == "Document Anonymizer"
    assert settings.API_V1_PREFIX == "/api/v1/anonymize"
    assert isinstance(settings.USE_GOOGLE_DRIVE_MOCK, bool)


def test_logger_setup():
    """Valida a criação e recuperação de logger padronizado."""
    setup_logging()
    log = get_logger("test_module")
    assert log.name == "test_module"


def test_domain_models():
    """Valida a instanciação dos modelos de domínio."""
    entity = EntityMatch(text="123.456.789-00", label="CPF", engine="regex", page=1)
    metadata = DocumentMetadata(filename="peticao.pdf", size_bytes=1024, total_pages=2)
    result = AnonymizationResult(
        original_filename="peticao.pdf",
        anonymized_text="[CPF_ANONIMIZADO]",
        entities=[entity],
    )
    assert metadata.total_pages == 2
    assert result.entities[0].label == "CPF"


def test_services_utils():
    """Valida as funções utilitárias da camada de serviços."""
    with pytest.raises(InvalidFileError):
        validate_uploaded_file("")
    with pytest.raises(InvalidFileError):
        validate_uploaded_file(None)
    validate_uploaded_file("arquivo.txt")

    assert get_anonymized_filename("doc.docx") == "anonimizado_doc.docx"
    assert create_download_headers("x.pdf") == {
        "Content-Disposition": "attachment; filename=x.pdf"
    }


def test_routes_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_motor_invalido_passa_pelo_handler_de_excecoes():
    """ValueError do serviço vira AppException(400) e é serializado pelo
    handler global registrado em routes.py."""
    response = client.post(
        "/api/v1/anonymize/",
        files={"file": ("a.txt", b"texto", "text/plain")},
        data={"engine": "inexistente"},
    )
    assert response.status_code == 400
    assert "não suportado" in response.json()["detail"]


def test_google_drive_nao_encontrado_retorna_404_via_handler():
    response = client.post(
        "/api/v1/anonymize/google-doc",
        json={"file_id": "nao-existe", "engine": "regex"},
    )
    assert response.status_code == 404
