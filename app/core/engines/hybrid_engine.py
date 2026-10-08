from typing import Any, Dict, List, Tuple
from app.core.engines.base import BaseEngine


def _get_engine_tier(engine: BaseEngine) -> int:
    name = engine.__class__.__name__.lower()
    if "regex" in name:
        return 100
    if "legal" in name or "lener" in name:
        return 60
    if "spacy" in name:
        return 50
    if "presidio" in name:
        return 30
    if "embedding" in name:
        return 10
    return 50


class HybridEngine(BaseEngine):
    def __init__(self, engines: List[BaseEngine]) -> None:
        self.engines = engines

    def detect(self, text: str) -> List[Dict[str, Any]]:
        all_candidates: List[Dict[str, Any]] = []
        for engine in self.engines:
            tier = _get_engine_tier(engine)
            for ent in engine.detect(text):
                ent_copy = dict(ent)
                ent_copy["tier"] = tier
                all_candidates.append(ent_copy)

        # Ordena candidatos por:
        # 1. Maior prioridade de tier (-tier)
        # 2. Maior comprimento de span (-(end - start))
        # 3. Posição inicial (start)
        all_candidates.sort(
            key=lambda c: (-c.get("tier", 50), -(c["end"] - c["start"]), c["start"])
        )

        selected: List[Dict[str, Any]] = []
        for cand in all_candidates:
            c_start, c_end = cand["start"], cand["end"]
            overlap = False
            for sel in selected:
                s_start, s_end = sel["start"], sel["end"]
                if not (c_end <= s_start or c_start >= s_end):
                    overlap = True
                    break
            if not overlap:
                selected.append(cand)

        # Reordena as entidades finais pelo offset inicial
        selected.sort(key=lambda c: c["start"])
        return selected

    def anonymize(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        selected_entities = self.detect(text)

        anonymized_text = text
        for ent in reversed(selected_entities):
            label_tag = f"[{ent['label'].upper()}_ANONIMIZADO]"
            anonymized_text = (
                anonymized_text[:ent["start"]]
                + label_tag
                + anonymized_text[ent["end"]:]
            )

        clean_entities = [
            {"text": e["text"], "label": e["label"], "engine": e["engine"]}
            for e in selected_entities
        ]

        return anonymized_text, clean_entities