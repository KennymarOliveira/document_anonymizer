import re
import torch
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer, util
from app.core.engines.base import BaseEngine

class EmbeddingEngine(BaseEngine):
    def __init__(self, threshold: float = 0.8) -> None:
        self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self.threshold = threshold
        self.sensitive_terms = [
            "senha", "conta", "cartão", "confidencial",
            "testemunha", "vítima", "menor", "filho", 
            "veículo", "placa", "paciente", "impetrante", 
            "presídio", "penitenciária", "CDP", "filiação", "genitora", 
            "doença", "comorbidade", "tratamento"
        ]
        self.sensitive_embeddings = self.model.encode(self.sensitive_terms, convert_to_tensor=True)

    def detect(self, text: str) -> List[Dict[str, Any]]:
        matches = list(re.finditer(r"\b\w+\b", text))
        if not matches:
            return []

        # Extrai palavras únicas e calcula embeddings em batch
        unique_words = list({m.group() for m in matches})
        word_embeddings = self.model.encode(unique_words, convert_to_tensor=True)
        cos_scores = util.cos_sim(word_embeddings, self.sensitive_embeddings)
        max_scores, _ = torch.max(cos_scores, dim=1)

        sensitive_word_set = {
            unique_words[i]
            for i, score in enumerate(max_scores)
            if score.item() > self.threshold
        }

        entities = []
        for m in matches:
            word = m.group()
            if word in sensitive_word_set:
                entities.append({
                    "start": m.start(),
                    "end": m.end(),
                    "text": word,
                    "label": "SEMANTIC_SENSITIVE",
                    "engine": "Embedding",
                })
        return entities

    def anonymize(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        entities = self.detect(text)
        entities_sorted = sorted(entities, key=lambda e: e["start"], reverse=True)

        anonymized_text = text
        for ent in entities_sorted:
            anonymized_text = (
                anonymized_text[:ent["start"]]
                + "[SENSIVEL_ANONIMIZADO]"
                + anonymized_text[ent["end"]:]
            )

        clean_entities = [
            {"text": e["text"], "label": e["label"], "engine": e["engine"]}
            for e in reversed(entities_sorted)
        ]
        return anonymized_text, clean_entities