"""
Config Service

Der Service koordiniert:
- Laden/Speichern der Admin-Konfiguration (Repository)
- Fachliche Validierung (validation.py)

Damit bleibt api.py schlank und enthält nur HTTP-Logik.
"""

from typing import Optional

from .schemas import AdminConfig
from .config_repository import ConfigRepository
from .validation import validate_admin_config


class ConfigService:
    def __init__(self, repo: ConfigRepository):
        self.repo = repo

    def get_active_config(self) -> Optional[AdminConfig]:
        """
        Lädt die aktuell aktive Konfiguration.

        Returns:
            AdminConfig oder None, falls keine existiert
        """
        return self.repo.load()

    def set_active_config(self, cfg: AdminConfig) -> AdminConfig:
        """
        Validiert und speichert eine neue Konfiguration.

        Args:
            cfg: AdminConfig

        Returns:
            AdminConfig (gespeichert)
        """
        validate_admin_config(cfg)
        self.repo.save(cfg)
        return cfg
