import logging
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.core.builders.file_builder import build_anonymized_file
from app.schemas.anonymizer import AnonymizationResponse, AnonymizedEntity
from app.services.anonymization_service import process_document

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=AnonymizationResponse | None)
async def anonymize_file(
    file: UploadFile = File(...),
    engine: str = Form("hybrid"),
    return_format: Literal["json", "file"] = Form("json")
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="O arquivo enviado não possui nome.")

    content = await file.read()

    try:
        anonymized_text, entities = process_document(file.filename, content, engine)

        if return_format == "file":
            file_stream, media_type = build_anonymized_file(file.filename, content, entities)
        else:
            file_stream = media_type = None

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("Falha ao anonimizar o arquivo %s", file.filename)
        raise HTTPException(
            status_code=500, detail="Erro interno ao processar o documento."
        )

    if return_format == "file":
        new_filename = f"anonimizado_{file.filename}"
        return StreamingResponse(
            file_stream,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={new_filename}"}
        )

    return AnonymizationResponse(
        original_filename=file.filename,
        anonymized_text=anonymized_text,
        entities_found=[AnonymizedEntity(**e) for e in entities]
    )