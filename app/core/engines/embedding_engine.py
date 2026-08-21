import torch
from sentence_transformers import SentenceTransformer, util
from typing import List, Dict, Any

from app.core.engines.base import BaseEngine

class EmbeddingEngine(BaseEngine):
    def __init__(self, threshold: float = 0.8) -> None:
        self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self.threshold = threshold
        self.sensitive_terms = ["senha", "conta", "cartão", "confidencial"]
        self.sensitive_embeddings = self.model.encode(self.sensitive_terms, convert_to_tensor=True)

    def anonymize(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        words = text.split()
        entities = []
        anonymized_words = []

        # A separação por palavras aqui é simplificada. Em produção, 
        # pode ser necessário o uso de n-grams ou tokenização mais robusta.
        for word in words:
            word_emb = self.model.encode(word, convert_to_tensor=True)
            cos_scores = util.cos_sim(word_emb, self.sensitive_embeddings)[0]
            
            if torch.max(cos_scores).item() > self.threshold:
                entities.append({"text": word, "label": "SEMANTIC_SENSITIVE", "engine": "Embedding"})
                anonymized_words.append("[SENSIVEL_ANONIMIZADO]")
            else:
                anonymized_words.append(word)

        return " ".join(anonymized_words), entities