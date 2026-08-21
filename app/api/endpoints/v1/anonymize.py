from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.core.builders.file_builder import build_file
from app.schemas.anonymizer import AnonymizationResponse, AnonymizedEntity
from app.services.anonymization_service import process_document

router = APIRouter()

@router.post("/", response_model=AnonymizationResponse | None)
async def anonymize_file(
    file: UploadFile = File(...),
    engine: str = Form("hybrid"),
    return_format: Literal["json", "file"] = Form("json")
):
    try:
        content = await file.read()
        anonymized_text, entities = process_document(file.filename, content, engine)
        
        if return_format == "file":
            file_stream, media_type = build_file(file.filename, anonymized_text)
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))