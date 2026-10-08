"""Definição de exceções de domínio e handlers de segurança/erros da aplicação."""
from typing import Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Exceção base para erros da aplicação com código HTTP e mensagem explicativa."""

    def __init__(
        self,
        detail: str,
        status_code: int = 400,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.headers = headers


class InvalidFileError(AppException):
    """Disparada quando o arquivo enviado é inválido ou não possui nome."""

    def __init__(self, detail: str = "O arquivo enviado não possui nome."):
        super().__init__(detail=detail, status_code=400)


class UnsupportedEngineError(AppException):
    """Disparada quando o motor de anonimização solicitado não existe."""

    def __init__(self, engine_name: str):
        super().__init__(
            detail=f"Motor '{engine_name}' não suportado.",
            status_code=400,
        )


class ExternalIntegrationError(AppException):
    """Disparada quando ocorre falha de integração externa (ex: Google Drive)."""

    def __init__(self, detail: str, status_code: int = 502):
        super().__init__(detail=detail, status_code=status_code)


class DocumentNotFoundError(AppException):
    """Disparada quando um documento não é encontrado no armazenamento externo."""

    def __init__(self, detail: str = "Documento não encontrado."):
        super().__init__(detail=detail, status_code=404)


class DocumentProcessingError(AppException):
    """Disparada para falhas internas durante extração ou anonimização."""

    def __init__(self, detail: str = "Erro interno ao processar o documento."):
        super().__init__(detail=detail, status_code=500)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handler global para capturar AppException e retornar resposta padronizada."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )

