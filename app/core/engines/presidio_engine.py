from typing import Any, Dict, List, Tuple
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from app.core.engines.base import BaseEngine

LEGAL_DENYLIST = {
    "vossa excelência", "vossa senhoria", "douto parquet", "parquet", "douto",
    "meritíssimo", "mm", "apelante", "apelantes", "apelado", "apelados",
    "impetrante", "paciente", "relator", "revisor", "egrégio", "colenda câmara",
    "tribunal de justiça", "ministério público", "breve síntese", "justiça gratuita",
    "latrocinio", "latrocínio", "recorrer", "recurso", "habeas corpus", "hc", "cpp", "cp",
}


class PresidioEngine(BaseEngine):
    def __init__(self, language: str = "pt", score_threshold: float = 0.65) -> None:
        self.language = language
        self.score_threshold = score_threshold

        # Configura o Presidio para usar o modelo pt_core_news_lg do spaCy
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "pt", "model_name": "pt_core_news_lg"}],
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()
        self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["pt"])

    def detect(self, text: str) -> List[Dict[str, Any]]:
        results = self.analyzer.analyze(
            text=text,
            language=self.language,
            score_threshold=self.score_threshold,
        )
        entities = []
        for res in results:
            ent_text = text[res.start:res.end].strip(" \t\r\n.,;:-\"'/()[]{}*#")
            if len(ent_text) <= 1 or ent_text.lower() in LEGAL_DENYLIST:
                continue

            rel_offset = text[res.start:res.end].find(ent_text)
            final_start = res.start + (rel_offset if rel_offset != -1 else 0)
            final_end = final_start + len(ent_text)

            entities.append({
                "start": final_start,
                "end": final_end,
                "text": ent_text,
                "label": res.entity_type,
                "score": res.score,
                "engine": "Presidio",
            })
        return entities

    def anonymize(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
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