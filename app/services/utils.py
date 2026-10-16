"""Utilitários de apoio para a camada de serviços e views."""
from pathlib import Path
from typing import Dict, Optional

from app.core.security.exceptions import InvalidFileError


def validate_uploaded_file(filename: Optional[str]) -> None:
    """Valida se o arquivo enviado possui nome."""
    if not filename or not filename.strip():
        raise InvalidFileError("O arquivo enviado não possui nome.")


def get_anonymized_filename(original_filename: str, prefix: str = "anonimizado_") -> str:
    """Gera o nome do arquivo anonimizado com prefixo."""
    return f"{prefix}{Path(original_filename).name}"


def create_download_headers(filename: str) -> Dict[str, str]:
    """Cria cabeçalhos HTTP para download de arquivos via streaming."""
    return {"Content-Disposition": f"attachment; filename={filename}"}
