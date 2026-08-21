from app.core.engines.embedding_engine import EmbeddingEngine
from app.core.engines.hybrid_engine import HybridEngine
from app.core.engines.regex_engine import RegexEngine
from app.core.engines.spacy_engine import SpacyNerEngine
from app.core.extractors.file_extractor import extract_text


def get_engine(engine_name: str):
    engines = {
        "regex": RegexEngine,
        "spacy": SpacyNerEngine,
        "embedding": EmbeddingEngine,
    }
    
    if engine_name.lower() == "hybrid":
        return HybridEngine([RegexEngine(), SpacyNerEngine()])
    
    engine_cls = engines.get(engine_name.lower())
    if not engine_cls:
        raise ValueError(f"Motor '{engine_name}' não suportado.")
    
    return engine_cls()


def process_document(filename: str, content: bytes, engine_name: str = "hybrid"):
    text = extract_text(filename, content)
    engine = get_engine(engine_name)
    anonymized_text, entities = engine.anonymize(text)
    
    return anonymized_text, entities