from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseEngine(ABC):
    def detect(self, text: str) -> List[Dict[str, Any]]:
        """Retorna a lista de entidades detectadas no texto sem modificá-lo.
        Cada item deve conter: start, end, text, label, engine.
        """
        return []

    @abstractmethod
    def anonymize(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        """Retorna a tupla (texto_anonimizado, lista_de_entidades)."""
        pass