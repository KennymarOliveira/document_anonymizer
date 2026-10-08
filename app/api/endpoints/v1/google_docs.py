import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.builders.file_builder import build_anonymized_file
from app.core.integrations.google_drive import (
    GoogleDriveClientInterface,
    get_google_drive_client,
)
from app.schemas.anonymizer import AnonymizationResponse, AnonymizedEntity
from app.schemas.google_drive import GoogleDocAnonymizeRequest
from app.services.anonymization_service import process_document

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/google-doc", response_model=AnonymizationResponse | None)
async def anonymize_google_doc(
    request: GoogleDocAnonymizeRequest,
    drive_client: GoogleDriveClientInterface = Depends(get_google_drive_client),
):
    try:
        filename, content = drive_client.fetch_file(request.file_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Falha ao recuperar arquivo do Google Drive: %s", request.file_id)
        raise HTTPException(
            status_code=502, detail=f"Erro de comunicação com o Google Drive: {exc}"
        ) from exc

    try:
        anonymized_text, entities = process_document(filename, content, request.engine)

        if request.return_format == "file":
            file_stream, media_type = build_anonymized_file(
                filename, content, entities, redaction_mode=request.redaction_mode
            )
        else:
            file_stream = media_type = None

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("Falha ao anonimizar o arquivo %s", filename)
        raise HTTPException(
            status_code=500, detail="Erro interno ao processar o documento."
        )

    if request.return_format == "file":
        new_filename = f"anonimizado_{filename}"
        return StreamingResponse(
            file_stream,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={new_filename}"},
        )

    return AnonymizationResponse(
        original_filename=filename,
        anonymized_text=anonymized_text,
        entities_found=[AnonymizedEntity(**e) for e in entities],
    )
