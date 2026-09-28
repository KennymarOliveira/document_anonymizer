from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_google_drive_mock_endpoint_json():
    response = client.post(
        "/api/v1/anonymize/google-doc",
        json={
            "file_id": "doc-corporativo-123",
            "engine": "regex",
            "return_format": "json",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["original_filename"] == "Contrato_Prestacao_Servicos.docx"
    assert "anonymized_text" in data
    assert isinstance(data["entities_found"], list)


def test_google_drive_mock_endpoint_file():
    response = client.post(
        "/api/v1/anonymize/google-doc",
        json={
            "file_id": "doc-corporativo-123",
            "engine": "regex",
            "return_format": "file",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(response.content) > 0


def test_google_drive_mock_not_found():
    response = client.post(
        "/api/v1/anonymize/google-doc",
        json={
            "file_id": "arquivo-inexistente-999",
            "engine": "regex",
            "return_format": "json",
        },
    )
    assert response.status_code == 404


from unittest.mock import MagicMock, patch
import pytest
from googleapiclient.errors import HttpError

from app.core.integrations.google_drive import (
    DOCX_MIMETYPE,
    GOOGLE_DOCS_MIMETYPE,
    GoogleDriveClient,
)


def _fake_media_download(dummy_bytes: bytes):
    def _downloader(stream, request):
        stream.write(dummy_bytes)
        mock_obj = MagicMock()
        mock_obj.next_chunk.return_value = (None, True)
        return mock_obj

    return _downloader


def test_real_client_fetch_google_doc():
    client = GoogleDriveClient(credentials_path="dummy.json")
    mock_service = MagicMock()
    mock_service.files().get().execute.return_value = {
        "name": "Contrato_Prestacao",
        "mimeType": GOOGLE_DOCS_MIMETYPE,
    }

    with patch.object(client, "_get_service", return_value=mock_service):
        with patch(
            "googleapiclient.http.MediaIoBaseDownload",
            side_effect=_fake_media_download(b"fake-docx-content"),
        ):
            filename, content = client.fetch_file("fake-google-doc-id")

    assert filename == "Contrato_Prestacao.docx"
    assert content == b"fake-docx-content"
    mock_service.files().export_media.assert_called_once_with(
        fileId="fake-google-doc-id", mimeType=DOCX_MIMETYPE
    )


def test_real_client_fetch_binary_pdf():
    client = GoogleDriveClient(credentials_path="dummy.json")
    mock_service = MagicMock()
    mock_service.files().get().execute.return_value = {
        "name": "Certidao.pdf",
        "mimeType": "application/pdf",
    }

    with patch.object(client, "_get_service", return_value=mock_service):
        with patch(
            "googleapiclient.http.MediaIoBaseDownload",
            side_effect=_fake_media_download(b"%PDF-1.4-fake"),
        ):
            filename, content = client.fetch_file("fake-pdf-id")

    assert filename == "Certidao.pdf"
    assert content == b"%PDF-1.4-fake"
    mock_service.files().get_media.assert_called_once_with(fileId="fake-pdf-id")


def test_real_client_fetch_http_404():
    client = GoogleDriveClient(credentials_path="dummy.json")
    mock_service = MagicMock()

    fake_resp = MagicMock()
    fake_resp.status = 404
    mock_service.files().get().execute.side_effect = HttpError(
        resp=fake_resp, content=b"File not found"
    )

    with patch.object(client, "_get_service", return_value=mock_service):
        with pytest.raises(FileNotFoundError) as exc_info:
            client.fetch_file("id-inexistente")

    assert "não encontrado no Google Drive" in str(exc_info.value)
