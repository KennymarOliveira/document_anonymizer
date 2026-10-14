"""Views / Handlers HTTP para a camada de serviços da aplicação.

Fluxo de cada view:
    1. Recebe e valida a entrada (upload ou JSON via schemas).
    2. Delega o processamento para ``_run_pipeline`` (serviço + builder).
    3. Converte o resultado em resposta HTTP (JSON ou arquivo).

Erros de domínio são lançados como ``AppException`` e convertidos em JSON
pelo handler global registrado em ``routes.py``.
"""
import io
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Literal
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.core.builders.file_builder import (
    build_anonymized_file,
    build_txt_entity_identifiers,
)
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
    include_report: bool = False,
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
            if include_report:
                if Path(filename).suffix.lower() != ".txt":
                    raise ValueError(
                        "O relatório de detecções está disponível somente para arquivos TXT."
                    )
                return _txt_zip_response(filename, file_stream, entities)
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


def _txt_zip_response(
    filename: str,
    anonymized_stream: io.BytesIO,
    entities: List[Dict[str, Any]],
) -> StreamingResponse:
    """Entrega o TXT anonimizado e seu relatório de detecções em um ZIP."""
    original_name = Path(filename).name
    anonymized_name = get_anonymized_filename(original_name)
    zip_name = f"anonimizacao_{Path(original_name).stem}.zip"
    report = _build_txt_detection_report(original_name, entities)

    zip_stream = io.BytesIO()
    with ZipFile(zip_stream, "w", ZIP_DEFLATED) as archive:
        archive.writestr(anonymized_name, anonymized_stream.getvalue())
        archive.writestr("relatorio_deteccoes.txt", report.encode("utf-8"))
    zip_stream.seek(0)

    return StreamingResponse(
        zip_stream,
        media_type="application/zip",
        headers=create_download_headers(zip_name),
    )


def _build_txt_detection_report(
    filename: str, entities: List[Dict[str, Any]]
) -> str:
    """Cria um relatório de teste com o mapeamento entre IDs e valores detectados."""
    identifiers = build_txt_entity_identifiers(entities)
    grouped: Dict[tuple[str, str], Dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "pages": set(), "engines": set()}
    )

    for entity in entities:
        value = entity.get("text")
        if not value:
            continue
        label = str(entity.get("label") or "DADO").upper()
        group = grouped[(label, value)]
        group["count"] += 1
        if entity.get("page") is not None:
            group["pages"].add(entity["page"])
        if entity.get("engine"):
            group["engines"].add(entity["engine"])

    lines = [
        "RELATÓRIO DE DETECÇÕES",
        f"Arquivo de origem: {filename}",
        "Uso exclusivo para testes: este relatório contém dados sensíveis detectados.",
        "",
    ]
    for key, data in grouped.items():
        label, value = key
        pages = ", ".join(str(page) for page in sorted(data["pages"])) or "não informada"
        engines = ", ".join(sorted(data["engines"])) or "não informado"
        lines.extend(
            [
                identifiers[key],
                f"- tipo: {label}",
                f"- valor detectado: {value}",
                f"- ocorrências: {data['count']}",
                f"- página(s): {pages}",
                f"- motor(es): {engines}",
                "",
            ]
        )
    return "\n".join(lines)


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
    include_report: bool = Form(
        False,
        description=(
            "Para TXT, devolve um ZIP com o arquivo anonimizado e um relatório "
            "de detecções sem dados sensíveis"
        ),
    ),
):
    """Recebe um arquivo via upload e o anonimiza."""
    validate_uploaded_file(file.filename)
    content = await file.read()
    return _run_pipeline(
        file.filename,
        content,
        engine,
        return_format,
        redaction_mode,
        include_report,
    )


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
        filename,
        content,
        request.engine,
        request.return_format,
        request.redaction_mode,
        request.include_report,
    )


async def health_check():
    """Health check da API."""
    return {"status": "ok"}
