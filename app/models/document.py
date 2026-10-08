"""Modelos de domínio para documentos e entidades de anonimização."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EntityMatch:
    """Representa uma entidade identificada no texto pelo motor de NLP/Regex."""

    text: str
    label: str
    engine: str
    page: Optional[int] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None


@dataclass
class DocumentMetadata:
    """Metadados do documento em processamento."""

    filename: str
    size_bytes: int = 0
    content_type: Optional[str] = None
    total_pages: int = 1


@dataclass
class AnonymizationResult:
    """Resultado da execução do pipeline de anonimização sobre um documento."""

    original_filename: str
    anonymized_text: str
    entities: List[EntityMatch] = field(default_factory=list)

