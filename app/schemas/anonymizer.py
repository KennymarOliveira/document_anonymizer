from pydantic import BaseModel

class AnonymizedEntity(BaseModel):
    text: str
    label: str
    engine: str
    page: int | None = None

class AnonymizationResponse(BaseModel):
    original_filename: str
    anonymized_text: str
    entities_found: list[AnonymizedEntity]