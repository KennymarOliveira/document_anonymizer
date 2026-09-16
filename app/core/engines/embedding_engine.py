import re
from typing import Any, Dict, List, Tuple
import torch
from sentence_transformers import SentenceTransformer, util
from app.core.engines.base import BaseEngine


class EmbeddingEngine(BaseEngine):
    def __init__(self, threshold: float = 0.80) -> None:
        self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self.threshold = threshold
        self.sensitive_prototypes = [
            "dados bancários com número de conta corrente, agência e senha de cartão",
            "diagnóstico médico sigiloso, tratamento de saúde e comorbidade de paciente",
            "qualificação protegida de testemunha sob sigilo ou vítima menor de idade",
            "informação pessoal estritamente confidencial ou segredo de justiça",
        ]
        self.prototype_embeddings = self.model.encode(self.sensitive_prototypes, convert_to_tensor=True)
        self._cache: Dict[str, bool] = {}

    def detect(self, text: str) -> List[Dict[str, Any]]:
        if not text or not text.strip():
            return []

        # Extrai sentenças/cláusulas contextuais com seus respectivos offsets
        sentence_matches = []
        for m in re.finditer(r"[^.!?;\n]+(?:[.!?;\n]+|$)", text):
            raw = m.group()
            cleaned = raw.strip()
            # Avalia sentenças ou orações substantivas com mais de 20 caracteres
            if len(cleaned) >= 20:
                rel_start = m.start() + raw.find(cleaned)
                rel_end = rel_start + len(cleaned)
                sentence_matches.append((rel_start, rel_end, cleaned))

        if not sentence_matches:
            return []

        sentences_to_encode = []
        indices_to_encode = []
        for i, (_, _, s_text) in enumerate(sentence_matches):
            if s_text not in self._cache:
                sentences_to_encode.append(s_text)
                indices_to_encode.append(i)

        if sentences_to_encode:
            s_embeddings = self.model.encode(sentences_to_encode, batch_size=32, convert_to_tensor=True)
            cos_scores = util.cos_sim(s_embeddings, self.prototype_embeddings)
            max_scores, _ = torch.max(cos_scores, dim=1)
            for j, score in enumerate(max_scores):
                sent_text = sentences_to_encode[j]
                self._cache[sent_text] = bool(score.item() > self.threshold)

        entities = []
        for s_start, s_end, s_text in sentence_matches:
            if self._cache.get(s_text, False):
                entities.append({
                    "start": s_start,
                    "end": s_end,
                    "text": s_text,
                    "label": "SEMANTIC_SENSITIVE",
                    "engine": "Embedding",
                })
        return entities

    def anonymize(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
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