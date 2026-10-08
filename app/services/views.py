"""Views / Handlers HTTP para a camada de serviços da aplicação.

Fluxo de cada view:
    1. Recebe e valida a entrada (upload ou JSON via schemas).
    2. Delega o processamento para ``_run_pipeline`` (serviço + builder).
    3. Converte o resultado em resposta HTTP (JSON ou arquivo).

Erros de domínio são lançados como ``AppException`` e convertidos em JSON
pelo handler global registrado em ``routes.py``.
"""
from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.core.builders.file_builder import build_anonymized_file
from app.core.integrations.google_drive import (
    GoogleDriveClientInterface,
    get_google_drive_client,
)
from app.core.security.exceptions import (
    AppException,
    DocumentNotFoundError,
    DocumentProcessingError,
    ExternalIntegrationError,
)
from app.core.security.logger import get_logger
from app.schemas.anonymizer import AnonymizationResponse, AnonymizedEntity
from app.schemas.google_drive import GoogleDocAnonymizeRequest
from app.services.anonymization_service import process_document
from app.services.utils import (
    create_download_headers,
    get_anonymized_filename,
    validate_uploaded_file,
)

logger = get_logger(__name__)

router = APIRouter()

RedactionMode = Literal[
    "blackout", "black_white_text", "tarja_preta", "tarja_texto_branco"
]


def _run_pipeline(
    filename: str,
    content: bytes,
    engine: str,
    return_format: str,
    redaction_mode: str,
):
    """Executa extração -> anonimização -> (opcional) montagem do arquivo.

    Traduz erros técnicos em exceções de domínio (AppException).
    """
    try:
        anonymized_text, entities = process_document(filename, content, engine)

        if return_format == "file":
            file_stream, media_type = build_anonymized_file(
                filename, content, entities, redaction_mode=redaction_mode
            )
            return _file_response(filename, file_stream, media_type)

    except AppException:
        raise
    except ValueError as exc:
        # Erros de entrada (extensão/motor não suportado, arquivo inválido)
        raise AppException(detail=str(exc), status_code=400) from exc
    except Exception as exc:
        logger.exception("Falha ao anonimizar o arquivo %s", filename)
        raise DocumentProcessingError() from exc

    return _json_response(filename, anonymized_text, entities)


def _file_response(filename: str, file_stream, media_type: str) -> StreamingResponse:
    return StreamingResponse(
        file_stream,
        media_type=media_type,
        headers=create_download_headers(get_anonymized_filename(filename)),
    )


def _json_response(
    filename: str, anonymized_text: str, entities: List[Dict[str, Any]]
) -> AnonymizationResponse:
    return AnonymizationResponse(
        original_filename=filename,
        anonymized_text=anonymized_text,
        entities_found=[AnonymizedEntity(**e) for e in entities],
    )


@router.post("/", response_model=AnonymizationResponse | None, tags=["Anonymization"])
async def anonymize_file(
    file: UploadFile = File(...),
    engine: str = Form("hybrid"),
    return_format: Literal["json", "file"] = Form("json"),
    redaction_mode: RedactionMode = Form(
        "blackout",
        description=(
            "Modo de tarja: 'blackout' (tarja preta sólida) ou "
            "'black_white_text' (tarja preta com texto branco)"
        ),
    ),
):
    """Recebe um arquivo via upload e o anonimiza."""
    validate_uploaded_file(file.filename)
    content = await file.read()
    return _run_pipeline(file.filename, content, engine, return_format, redaction_mode)


@router.post(
    "/google-doc",
    response_model=AnonymizationResponse | None,
    tags=["Google Drive"],
)
async def anonymize_google_doc(
    request: GoogleDocAnonymizeRequest,
    drive_client: GoogleDriveClientInterface = Depends(get_google_drive_client),
):
    """Recupera um arquivo do Google Drive e o anonimiza."""
    try:
        filename, content = drive_client.fetch_file(request.file_id)
    except FileNotFoundError as exc:
        raise DocumentNotFoundError(str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "Falha ao recuperar arquivo do Google Drive: %s", request.file_id
        )
        raise ExternalIntegrationError(
            f"Erro de comunicação com o Google Drive: {exc}"
        ) from exc

    return _run_pipeline(
        filename, content, request.engine, request.return_format, request.redaction_mode
    )


async def health_check():
    """Health check da API."""
    return {"status": "ok"}
