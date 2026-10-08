"""Módulo de configuração centralizada de logs."""
import logging
import sys

from app.core.configuration.settings import settings


def setup_logging():
    """Configura o logger raiz da aplicação com formato padronizado."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Retorna uma instância de logger configurada para o módulo."""
    return logging.getLogger(name)

