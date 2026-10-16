from typing import Optional, Tuple, Dict, Any


class InMemoryDB:
    """
    Simula um banco de dados para desenvolvimento local e testes.
    A implementação dos métodos dependerá do banco (PostgreSQL ou ElasticSearch)
    """

    def __init__(self) -> None:
        self._store: Dict[str, Tuple[int, Dict[str, Any]]] = {
            "core-service": (
                1,
                {
                    "maintenance_mode": False,
                    "timeout_seconds": 3.5,
                    "feature_flags": {"new_flow": True},
                    "rate_limits": {"default_per_minute": 120, "burst_per_minute": 200},
                },
            )
        }

    def fetch_version(self, scope: str) -> Optional[int]:
        record = self._store.get(scope)
        return record[0] if record else None

    def fetch_raw_config(self, scope: str) -> Optional[Tuple[int, Dict[str, Any]]]:
        return self._store.get(scope)

    def simulate_external_db_update(self, scope: str, new_payload: Dict[str, Any]) -> None:
        current_version = self.fetch_version(scope) or 0
        self._store[scope] = (current_version + 1, new_payload)
