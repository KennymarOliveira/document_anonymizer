from typing import List, Dict, Any

from app.core.engines.base import BaseEngine

class HybridEngine(BaseEngine):
    def __init__(self, engines: List[BaseEngine]) -> None:
        self.engines = engines

    def anonymize(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        current_text = text
        all_entities = []

        for engine in self.engines:
            current_text, entities = engine.anonymize(current_text)
            all_entities.extend(entities)

        return current_text, all_entities