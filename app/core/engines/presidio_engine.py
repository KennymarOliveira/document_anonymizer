from typing import List, Dict, Any
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from app.core.engines.base import BaseEngine

class PresidioEngine(BaseEngine):
    def __init__(self, language: str = "pt") -> None:
        self.language = language
        
        # Configura o Presidio para usar o modelo pt_core_news_lg do spaCy
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "pt", "model_name": "pt_core_news_lg"}],
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()
        self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["pt"])

    def detect(self, text: str) -> List[Dict[str, Any]]:
        results = self.analyzer.analyze(text=text, language=self.language)
        entities = []
        for res in results:
            entities.append({
                "start": res.start,
                "end": res.end,
                "text": text[res.start:res.end],
                "label": res.entity_type,
                "engine": "Presidio"
            })
        return entities

    def anonymize(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        entities = self.detect(text)
        entities_sorted = sorted(entities, key=lambda e: e["start"], reverse=True)

        anonymized_text = text
        for ent in entities_sorted:
            anonymized_text = (
                anonymized_text[:ent["start"]]
                + f"[{ent['label']}_ANONIMIZADO]"
                + anonymized_text[ent["end"]:]
            )

        clean_entities = [
            {"text": e["text"], "label": e["label"], "engine": e["engine"]}
            for e in reversed(entities_sorted)
        ]
        return anonymized_text, clean_entities