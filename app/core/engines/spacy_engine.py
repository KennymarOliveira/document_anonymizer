from typing import List, Dict, Any
import spacy
from app.core.engines.base import BaseEngine

class SpacyNerEngine(BaseEngine):
    def __init__(self) -> None:
        self.nlp = spacy.load("pt_core_news_lg")

    def anonymize(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        doc = self.nlp(text)
        entities = []
        
        # Ordena as entidades de trás para frente para evitar deslocamento de índices ao substituir
        ents = sorted(doc.ents, key=lambda e: e.start_char, reverse=True)
        anonymized_text = text

        for ent in ents:
            if ent.label_ in ["PER", "LOC", "ORG"]:
                entities.append({"text": ent.text, "label": ent.label_, "engine": "Spacy"})
                anonymized_text = (
                    anonymized_text[:ent.start_char] + 
                    f"[{ent.label_}_ANONIMIZADO]" + 
                    anonymized_text[ent.end_char:]
                )

        return anonymized_text, list(reversed(entities))