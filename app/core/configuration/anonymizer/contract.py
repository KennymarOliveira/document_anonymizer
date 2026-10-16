from typing import Protocol, Optional, Tuple, Dict, Any


class Config(Protocol):
    """
    Interface agnóstica ao banco de dados.
    - No PostgreSQL: 'version' pode ser uma coluna BIGINT ou hash/updated_at.
    - No Elasticsearch: 'version' pode ser '_seq_no' ou '_version'.
    """

    def fetch_version(self, scope: str) -> Optional[int]:
        """
        Consulta de metadados para informações de mudança no banco.
        Ex: SELECT version FROM settings WHERE key = :scope
        Ex: GET /settings/_doc/:scope?_source=false
        """
        

    def fetch_raw_config(self, scope: str) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        Busca o JSON completo e sua versão atual.
        Retorna: (version, payload_dict) ou None se não existir.
        """
        