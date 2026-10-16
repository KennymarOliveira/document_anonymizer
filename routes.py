"""Ponto de entrada principal e definição de rotas da aplicação."""
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.configuration.settings import settings
from app.core.security.exceptions import AppException, app_exception_handler
from app.core.security.logger import get_logger, setup_logging
from app.services.views import health_check, router as anonymize_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida da aplicação (startup e shutdown)."""
    setup_logging()
    logger.info("Iniciando %s (v%s)...", settings.PROJECT_NAME, settings.VERSION)
    yield
    logger.info("Encerrando %s...", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
)

# Handlers globais de segurança e exceções
app.add_exception_handler(AppException, app_exception_handler)

# Inclusão dos roteadores da camada de serviços
app.include_router(
    anonymize_router,
    prefix=settings.API_V1_PREFIX,
)

# Rota de health check
app.add_api_route("/health", health_check, methods=["GET"], tags=["Health"])

