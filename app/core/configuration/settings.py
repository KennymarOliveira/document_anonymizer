"""Configurações centrais da aplicação.

Carrega configurações de variáveis de ambiente (.env), aplicando valores padrão
e integrando com sobrescritas de local_settings.py caso definidas.
"""
import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

try:
    from app.core.configuration.local_settings import LOCAL_SETTINGS
except ImportError:
    LOCAL_SETTINGS = {}


@dataclass
class Settings:
    PROJECT_NAME: str = "Document Anonymizer"
    DESCRIPTION: str = "API para anonimização de documentos jurídicos."
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1/anonymize"

    LOG_LEVEL: str = field(
        default_factory=lambda: os.getenv(
            "LOG_LEVEL", str(LOCAL_SETTINGS.get("LOG_LEVEL", "INFO"))
        ).upper()
    )

    USE_GOOGLE_DRIVE_MOCK: bool = field(
        default_factory=lambda: (
            os.getenv(
                "USE_GOOGLE_DRIVE_MOCK",
                str(LOCAL_SETTINGS.get("USE_GOOGLE_DRIVE_MOCK", "true")),
            ).lower()
            in ("true", "1", "yes")
        )
    )
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = field(
        default_factory=lambda: os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS",
            LOCAL_SETTINGS.get("GOOGLE_APPLICATION_CREDENTIALS", None),
        )
    )


settings = Settings()
