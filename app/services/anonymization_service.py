from typing import Any, Dict, List, Tuple

from app.core.engines.embedding_engine import EmbeddingEngine
from app.core.engines.hybrid_engine import HybridEngine
from app.core.engines.legal_ner_engine import LegalNerEngine
from app.core.engines.presidio_engine import PresidioEngine
from app.core.engines.regex_engine import RegexEngine
from app.core.engines.spacy_engine import SpacyNerEngine
from app.core.extractors.file_extractor import (
    extract_pages_with_layout,
    rects_for_text_span,
    render_segments_for_text_span,
)


def get_engine(engine_name: str):
    name = engine_name.strip().lower()
    aliases = {
        "presídio": "presidio",
        "híbrido": "hybrid",
        "hibrido": "hybrid",
        "híbrido_legal": "hybrid_legal",
        "hibrido_legal": "hybrid_legal",
        "legal_hybrid": "hybrid_legal",
        "embeddings": "embedding",
        "legal": "legal_ner",
        "lenerbr": "legal_ner",
        "lener": "legal_ner",
    }
    name = aliases.get(name, name)

    engines = {
        "regex": RegexEngine,
        "spacy": SpacyNerEngine,
        "legal_ner": LegalNerEngine,
        "embedding": EmbeddingEngine,
        "presidio": PresidioEngine,
    }
    
    if name == "hybrid":
        # Inclui Regex, spaCy e Presidio no motor híbrido
        return HybridEngine([RegexEngine(), SpacyNerEngine(), PresidioEngine()])

    if name == "hybrid_legal":
        # Mantém o híbrido padrão estável e adiciona o modelo jurídico LeNER-BR.
        return HybridEngine(
            [RegexEngine(), LegalNerEngine(), SpacyNerEngine(), PresidioEngine()]
        )
    
    engine_cls = engines.get(name)
    if not engine_cls:
        raise ValueError(f"Motor '{engine_name}' não suportado.")
    
    return engine_cls()


def process_document(
    filename: str, content: bytes, engine_name: str = "hybrid"
) -> Tuple[str, List[Dict[str, Any]]]:
    engine = get_engine(engine_name)
    pages = extract_pages_with_layout(filename, content)

    if len(pages) == 1:
        page = pages[0]
        anonymized_text, entities = engine.anonymize(page.text)
        for e in entities:
            e["page"] = page.page_number
            _attach_pdf_rects(e, page.text, page.char_rects)
        return anonymized_text, entities

    anonymized_pages: list[str] = []
    all_entities: list[dict[str, Any]] = []

    for page in pages:
        if not page.text.strip():
            anonymized_pages.append(page.text)
            continue
        anon_page_text, page_entities = engine.anonymize(page.text)
        for e in page_entities:
            e["page"] = page.page_number
            _attach_pdf_rects(e, page.text, page.char_rects)
        all_entities.extend(page_entities)
        anonymized_pages.append(anon_page_text)

    full_anonymized_text = "\n".join(anonymized_pages)
    return full_anonymized_text, all_entities


def _attach_pdf_rects(entity: Dict[str, Any], page_text: str, char_rects) -> None:
    """Inclui as coordenadas da entidade quando a extração veio de um PDF."""
    if char_rects is None:
        return
    start, end = entity.get("start"), entity.get("end")
    if not isinstance(start, int) or not isinstance(end, int):
        return
    rects = rects_for_text_span(char_rects, start, end)
    if rects:
        entity["rects"] = rects
        entity["render_segments"] = render_segments_for_text_span(
            page_text, char_rects, start, end
        )
