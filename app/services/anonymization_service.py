from typing import Any, Dict, List, Tuple

from app.core.engines.embedding_engine import EmbeddingEngine
from app.core.engines.hybrid_engine import HybridEngine
from app.core.engines.presidio_engine import PresidioEngine
from app.core.engines.regex_engine import RegexEngine
from app.core.engines.spacy_engine import SpacyNerEngine
from app.core.extractors.file_extractor import extract_text_by_pages


from app.core.engines.legal_ner_engine import LegalNerEngine

def get_engine(engine_name: str):
    name = engine_name.strip().lower()
    aliases = {
        "presídio": "presidio",
        "híbrido": "hybrid",
        "hibrido": "hybrid",
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
        try:
            ner_engine = LegalNerEngine()
        except Exception:
            ner_engine = SpacyNerEngine()
        return HybridEngine([RegexEngine(), ner_engine, PresidioEngine()])
    
    engine_cls = engines.get(name)
    if not engine_cls:
        raise ValueError(f"Motor '{engine_name}' não suportado.")
    
    return engine_cls()


def process_document(
    filename: str, content: bytes, engine_name: str = "hybrid"
) -> Tuple[str, List[Dict[str, Any]]]:
    engine = get_engine(engine_name)
    pages = extract_text_by_pages(filename, content)

    if len(pages) == 1:
        page_num, text = pages[0]
        anonymized_text, entities = engine.anonymize(text)
        for e in entities:
            e["page"] = page_num
        return anonymized_text, entities

    anonymized_pages: list[str] = []
    all_entities: list[dict[str, Any]] = []

    for page_num, page_text in pages:
        if not page_text.strip():
            anonymized_pages.append(page_text)
            continue
        anon_page_text, page_entities = engine.anonymize(page_text)
        for e in page_entities:
            e["page"] = page_num
        all_entities.extend(page_entities)
        anonymized_pages.append(anon_page_text)

    full_anonymized_text = "\n".join(anonymized_pages)
    return full_anonymized_text, all_entities