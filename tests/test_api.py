import io
import zipfile

import pytest
from fastapi.testclient import TestClient

import app.api.endpoints.v1.anonymize as endpoint
from tests.utils import build_docx, build_pdf
from app.core.extractors.file_extractor import extract_text
from app.main import app

client = TestClient(app)

URL = "/api/v1/anonymize/"


def enviar(filename: str, content: bytes, **form):
    dados = {"engine": "regex", "return_format": "json"}
    dados.update(form)
    return client.post(
        URL, files={"file": (filename, content, "application/octet-stream")}, data=dados
    )


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_anonymize_endpoint_txt():
    files = {"file": ("teste.txt", b"Meu CPF 123.456.789-00", "text/plain")}
    data = {"engine": "regex"}
    response = client.post(URL, files=files, data=data)

    assert response.status_code == 200
    json_resp = response.json()
    assert "[CPF_ANONIMIZADO]" in json_resp["anonymized_text"]
    assert len(json_resp["entities_found"]) == 1


def test_anonymize_retorna_filename_e_entidades():
    response = enviar("peticao.txt", b"CPF 123.456.789-00 e email a@b.com")

    assert response.status_code == 200
    corpo = response.json()
    assert corpo["original_filename"] == "peticao.txt"
    assert [e["label"] for e in corpo["entities_found"]] == ["CPF", "EMAIL"]
    assert all(e["engine"] == "Regex" for e in corpo["entities_found"])


def test_anonymize_ocorrencias_repetidas():
    response = enviar("doc.txt", b"CPF 111.222.333-44 e 111.222.333-44")

    assert response.status_code == 200
    corpo = response.json()
    assert corpo["anonymized_text"].count("[CPF_ANONIMIZADO]") == 2
    assert len(corpo["entities_found"]) == 2


# --- Erros de requisição: 400 ---------------------------------------------


def test_anonymize_extensao_nao_suportada_retorna_400():
    response = enviar("planilha.csv", b"1,2,3")

    assert response.status_code == 400
    assert "Extensão não suportada" in response.json()["detail"]


def test_anonymize_motor_invalido_retorna_400():
    response = enviar("doc.txt", b"texto", engine="inexistente")

    assert response.status_code == 400
    assert "não suportado" in response.json()["detail"]


def test_anonymize_txt_nao_utf8_retorna_400():
    response = enviar("doc.txt", bytes([0xFF, 0xFE, 0x00]))

    assert response.status_code == 400
    assert "UTF-8" in response.json()["detail"]


def test_anonymize_pdf_corrompido_retorna_400():
    response = enviar("doc.pdf", b"isto nao e um pdf")

    assert response.status_code == 400
    assert "PDF inválido" in response.json()["detail"]


def test_anonymize_docx_corrompido_retorna_400():
    response = enviar("doc.docx", b"isto nao e um docx")

    assert response.status_code == 400
    assert "DOCX inválido" in response.json()["detail"]


def test_anonymize_docx_zip_sem_partes_opc_retorna_400():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as arquivo:
        arquivo.writestr("qualquer.txt", "conteúdo")

    response = enviar("doc.docx", buffer.getvalue())

    assert response.status_code == 400
    assert "DOCX inválido" in response.json()["detail"]


def test_anonymize_filename_vazio_retorna_400():
    """Multipart cru: o httpx omite o parâmetro filename quando recebe "",
    então é preciso montar o corpo à mão para exercitar a guarda."""
    fronteira = "FRONTEIRA"
    corpo = (
        f'--{fronteira}\r\n'
        'Content-Disposition: form-data; name="file"; filename=""\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
        "texto\r\n"
        f'--{fronteira}\r\n'
        'Content-Disposition: form-data; name="engine"\r\n\r\n'
        "regex\r\n"
        f"--{fronteira}--\r\n"
    ).encode()

    response = client.post(
        URL,
        content=corpo,
        headers={"Content-Type": f"multipart/form-data; boundary={fronteira}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "O arquivo enviado não possui nome."


def test_anonymize_campo_sem_arquivo_retorna_422():
    """Sem o parâmetro filename no header, o campo deixa de ser um upload e o
    FastAPI barra na validação, antes do endpoint."""
    response = client.post(URL, files={"file": ("", b"texto")}, data={"engine": "regex"})

    assert response.status_code == 422


# --- Erro interno: 500 ----------------------------------------------------


def test_anonymize_erro_interno_retorna_500_sem_vazar_detalhe(monkeypatch):
    """Falha inesperada não deve ser reportada como erro do cliente, e a
    mensagem interna não deve aparecer na resposta."""

    def explode(*_args, **_kwargs):
        raise RuntimeError("detalhe interno sensivel")

    monkeypatch.setattr(endpoint, "process_document", explode)

    response = enviar("doc.txt", b"texto")

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno ao processar o documento."}
    assert "sensivel" not in response.text


def test_anonymize_falha_na_geracao_do_arquivo_retorna_500(monkeypatch):
    def explode(*_args, **_kwargs):
        raise RuntimeError("falha ao montar o arquivo")

    monkeypatch.setattr(endpoint, "build_anonymized_file", explode)

    response = enviar("doc.txt", b"CPF 123.456.789-00", return_format="file")

    assert response.status_code == 500
    assert response.json()["detail"] == "Erro interno ao processar o documento."


# --- return_format = file -------------------------------------------------


@pytest.mark.parametrize(
    "filename, media_type",
    [
        ("doc.txt", "text/plain"),
        ("doc.docx", "application/vnd.openxmlformats-officedocument."
                     "wordprocessingml.document"),
        ("doc.pdf", "application/pdf"),
    ],
)
def test_anonymize_return_format_file(filename, media_type):
    texto = "Cliente José - CPF 111.222.333-44\nEmail j@ex.com.br"
    amostras = {
        "doc.txt": texto.encode("utf-8"),
        "doc.docx": build_docx(texto).getvalue(),
        "doc.pdf": build_pdf(texto).getvalue(),
    }

    response = enviar(filename, amostras[filename], return_format="file")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(media_type)
    assert (
        response.headers["content-disposition"]
        == f"attachment; filename=anonimizado_{filename}"
    )

    devolvido = extract_text(filename, response.content)
    assert "111.222.333-44" not in devolvido
    assert "j@ex.com.br" not in devolvido
    assert "José" in devolvido
    assert "?" not in devolvido


def test_anonymize_return_format_invalido_retorna_422():
    response = enviar("doc.txt", b"texto", return_format="xml")

    assert response.status_code == 422
