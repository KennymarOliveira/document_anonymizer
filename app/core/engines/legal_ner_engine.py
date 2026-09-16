import re
from typing import Any, Dict, List, Optional, Tuple
import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline
from app.core.engines.base import BaseEngine

LEGAL_DENYLIST = {
    "vossa excelência", "vossa senhoria", "douto parquet", "parquet", "douto",
    "meritíssimo", "mm", "apelante", "apelantes", "apelado", "apelados",
    "impetrante", "paciente", "relator", "revisor", "egrégio", "colenda câmara",
    "tribunal de justiça", "ministério público", "breve síntese", "justiça gratuita",
    "latrocinio", "latrocínio", "recorrer", "recurso", "habeas corpus", "hc", "cpp", "cp",
    "espinola", "espínola", "filho", "sobrinho", "netto", "naves", "comarca", "vara",
    "vara criminal", "cartório", "juizado", "foro", "desembargador", "juiz", "promotor",
}

_MODEL_PIPELINE = None


def get_lenerbr_pipeline(model_id: str = "pierreguillou/ner-bert-base-cased-pt-lenerbr"):
    global _MODEL_PIPELINE
    if _MODEL_PIPELINE is None:
        device = 0 if torch.cuda.is_available() else -1
        tokenizer = AutoTokenizer.from_pretrained(model_id, model_max_length=512)
        model = AutoModelForTokenClassification.from_pretrained(model_id)
        _MODEL_PIPELINE = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy="first",
            device=device,
        )
    return _MODEL_PIPELINE


def chunk_text_safely(text: str, max_chars: int = 1200) -> List[Tuple[int, int, str]]:
    """Divide o texto em blocos contíguos respeitando quebras de linha ou espaços,
    garantindo que nenhum bloco exceda o limite de tokens do BERT."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            split_idx = text.rfind("\n", start, end)
            if split_idx == -1 or split_idx <= start:
                split_idx = text.rfind(" ", start, end)
            if split_idx > start:
                end = split_idx
        chunks.append((start, end, text[start:end]))
        start = end
        while start < len(text) and text[start] in " \t\r\n":
            start += 1
    return chunks


class LegalNerEngine(BaseEngine):
    def __init__(
        self,
        model_id: str = "pierreguillou/ner-bert-base-cased-pt-lenerbr",
        threshold: float = 0.70,
        allowed_labels: Optional[List[str]] = None,
    ) -> None:
        self.model_id = model_id
        self.threshold = threshold
        self.allowed_labels = set(allowed_labels or ["PESSOA", "LOCAL", "ORGANIZACAO"])
        self.pipe = get_lenerbr_pipeline(model_id)

    def detect(self, text: str) -> List[Dict[str, Any]]:
        if not text or not text.strip():
            return []

        chunks = chunk_text_safely(text)
        raw_entities = []

        for c_start, c_end, chunk in chunks:
            if not chunk.strip():
                continue
            res = self.pipe(chunk)
            for r in res:
                word = r["word"].strip(" \t\r\n.,;:-\"'/()[]{}*#")
                lbl = r["entity_group"]
                score = float(r["score"])

                if score < self.threshold:
                    continue
                if lbl not in self.allowed_labels:
                    continue
                if len(word) <= 1 or word.lower() in LEGAL_DENYLIST:
                    continue

                rel_start = r["start"]
                rel_end = r["end"]
                sub_text = chunk[rel_start:rel_end]
                sub_clean = sub_text.strip(" \t\r\n.,;:-\"'/()[]{}*#")
                if not sub_clean or len(sub_clean) <= 1:
                    continue

                offset_inside = sub_text.find(sub_clean)
                if offset_inside == -1:
                    continue

                final_start = c_start + rel_start + offset_inside
                final_end = final_start + len(sub_clean)

                raw_entities.append({
                    "start": final_start,
                    "end": final_end,
                    "text": sub_clean,
                    "label": lbl,
                    "score": score,
                    "engine": "LegalNER",
                })

        # Ordenar e resolver sobreposições internas do modelo
        raw_entities.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
        selected: List[Dict[str, Any]] = []
        last_end = -1
        for ent in raw_entities:
            if ent["start"] < last_end:
                continue
            selected.append(ent)
            last_end = ent["end"]

        return selected

    def anonymize(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        entities = self.detect(text)
        entities_sorted = sorted(entities, key=lambda e: e["start"], reverse=True)
        anonymized_text = text

        for ent in entities_sorted:
            anonymized_text = (
                anonymized_text[:ent["start"]]
                + f"[{ent['label'].upper()}_ANONIMIZADO]"
                + anonymized_text[ent["end"]:]
            )

        clean_entities = [
            {"text": e["text"], "label": e["label"], "engine": e["engine"]}
            for e in reversed(entities_sorted)
        ]
        return anonymized_text, clean_entities

