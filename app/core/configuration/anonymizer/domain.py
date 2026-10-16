from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class RateLimitConfig:
    default_per_minute: int = 60
    burst_per_minute: int = 100


@dataclass(frozen=True)
class AppConfig:
    """
    Objeto imutável que representa a configuração em memória.
    Garante thread-safety durante leituras concorrentes.
    """
    maintenance_mode: bool = False
    timeout_seconds: float = 5.0
    feature_flags: Dict[str, bool] = field(default_factory=lambda: {"new_flow": False})
    rate_limits: RateLimitConfig = field(default_factory=RateLimitConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """
        Validação simples do objeto que pode ser substituída por Pydantic BaseModel.
        """
        rate_data = data.get("rate_limits", {})
        return cls(
            maintenance_mode=bool(data.get("maintenance_mode", False)),
            timeout_seconds=float(data.get("timeout_seconds", 5.0)),
            feature_flags=dict(data.get("feature_flags", {"new_flow": False})),
            rate_limits=RateLimitConfig(
                default_per_minute=int(rate_data.get("default_per_minute", 60)),
                burst_per_minute=int(rate_data.get("burst_per_minute", 100)),
            ),
        )
