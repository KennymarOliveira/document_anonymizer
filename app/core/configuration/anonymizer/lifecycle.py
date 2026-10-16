import logging
import threading
from typing import Callable, Optional
from contract import Config
from app.core.configuration.anonymizer.domain import AppConfig


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Classe principal responsável por gerenciar o cache em memória,
    locks de concorrência, checagem de versão e recarregamento
    """
    def __init__(
        self,
        repository: Config,
        scope: str,
        poll_interval_seconds: int = 30,
        default_config: Optional[AppConfig] = None,
    ) -> None:
        self._repo = repository
        self._scope = scope
        self._poll_interval = poll_interval_seconds

        self._lock = threading.RLock()
        self._current_config: AppConfig = default_config or AppConfig()
        self._current_version: int = -1

        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        self._listeners: list[Callable[[AppConfig], None]] = []

    def start(self, enable_background_polling: bool = True) -> None:
        """
        Carrega a configuração inicial no boot e inicia o watcher em background.
        Se o banco falhar no boot, mantém o Fallback seguro sem derrubar o app.
        """
        logger.info(f"Inicializando ConfigManager para o escopo '{self._scope}'...")
        self.reload(force=True)

        if enable_background_polling and self._worker_thread is None:
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._polling_loop,
                name=f"ConfigPoller-{self._scope}",
                daemon=True,
            )
            self._worker_thread.start()

    def stop(self) -> None:
        """
        Encerra a thread de monitoramento.
        """
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        logger.info("ConfigManager encerrado.")

    def get(self) -> AppConfig:
        """
        Retorna a referência imutável da configuração em memória.
        """
        with self._lock:
            return self._current_config

    def reload(self, force: bool = False) -> bool:
        """
        Verifica se há nova versão no storage e atualiza a memória.
        Pode ser chamado pelo loop de Polling (Pull) ou por um Webhook/PubSub (Push).
        """
        try:
            if not force:
                remote_version = self._repo.fetch_version(self._scope)
                if remote_version is None or remote_version <= self._current_version:
                    return False

            record = self._repo.fetch_raw_config(self._scope)
            if not record:
                logger.warning("Configuração não encontrada no banco. Mantendo estado atual.")
                return False

            new_version, raw_dict = record
            new_config = AppConfig.from_dict(raw_dict)

            with self._lock:
                self._current_config = new_config
                self._current_version = new_version

            logger.info(f"Configuração atualizada com sucesso para a versão v{new_version}.")
            self._notify_listeners(new_config)
            return True

        except Exception as exc:
            logger.error(
                f"Falha ao atualizar configuração (mantendo versão v{self._current_version}): {exc}"
            )
            return False

    def subscribe(self, callback: Callable[[AppConfig], None]) -> None:
        """
        Registra funções que precisam ser avisadas quando a config mudar.
        """
        self._listeners.append(callback)

    def _notify_listeners(self, config: AppConfig) -> None:
        for listener in self._listeners:
            try:
                listener(config)
            except Exception as exc:
                logger.error(f"Erro ao executar listener de configuração: {exc}")

    def _polling_loop(self) -> None:
        while not self._stop_event.wait(self._poll_interval):
            self.reload(force=False)
