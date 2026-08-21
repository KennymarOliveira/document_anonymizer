from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseEngine(ABC):
    @abstractmethod
    def anonymize(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        pass