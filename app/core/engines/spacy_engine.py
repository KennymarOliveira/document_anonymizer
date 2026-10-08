from typing import List, Dict, Any
import spacy
from app.core.engines.base import BaseEngine

LEGAL_DENYLIST = {
    "vossa excelência", "vossa senhoria", "douto parquet", "parquet", "douto",
    "meritíssimo", "mm", "apelante", "apelantes", "apelado", "apelados",
    "impetrante", "paciente", "relator", "revisor", "egrégio", "colenda câmara",
    "tribunal de justiça", "ministério público", "breve síntese", "justiça gratuita",
    "latrocinio", "latrocínio", "recorrer", "recurso", "habeas corpus", "hc", "cpp", "cp",
    "estado", "precedentes", "rel", "min", "constituição", "constituição federal",
}

class SpacyNerEngine(BaseEngine):
    def __init__(self) -> None:
        self.nlp = spacy.load(
            "pt_core_news_lg",
            disable=["parser", "lemmatizer", "morphologizer", "attribute_ruler"]
        )

    def detect(self, text: str) -> List[Dict[str, Any]]:
        doc = self.nlp(text)
        entities = []
        for ent in doc.ents:
            if ent.label_ in ["PER", "LOC", "ORG"]:
                ent_text = ent.text.strip(" \t\r\n.,;:-\"'/()[]{}*#")
                # Remove sufixos processuais comuns grudados por quebra de linha
                for suffix in ["\nApelado", "\nApelante", "\nAdvogado", "\nAutor", "\nRéu"]:
                    if suffix.lower() in ent_text.lower():
                        idx = ent_text.lower().find(suffix.lower())
                        ent_text = ent_text[:idx].strip()

                if len(ent_text) <= 1 or ent_text.lower() in LEGAL_DENYLIST:
                    continue

                # Recalcula offset exato após strip
                rel_offset = ent.text.find(ent_text)
                if rel_offset == -1:
                    continue
                final_start = ent.start_char + rel_offset
                final_end = final_start + len(ent_text)

                entities.append({
                    "start": final_start,
                    "end": final_end,
                    "text": ent_text,
                    "label": ent.label_,
                    "engine": "Spacy"
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
