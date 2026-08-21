from fastapi import FastAPI

from app.api.endpoints.v1 import anonymize

app = FastAPI(
    title="Document Anonymizer",
    description="API para anonimização de documentos jurídicos.",
    version="0.1.0",
)

app.include_router(anonymize.router, prefix="/api/v1/anonymize", tags=["Anonymization"])


@app.get("/health")
def health_check():
    return {"status": "ok"}