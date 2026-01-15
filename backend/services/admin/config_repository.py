"""
Config Repository

Dieses Modul ist für die Persistenz der Admin-Konfiguration zuständig.
Es kapselt ausschließlich das Laden und Speichern der Konfiguration
(z. B. als JSON-Datei) und enthält KEINE Business-Logik.

Single Responsibility:
- Lesen einer Konfiguration von Disk
- Schreiben einer Konfiguration auf Disk
"""

from typing import Optional

from backend.services.io.file_manager import FileManager
from .schemas import AdminConfig


class ConfigRepository:
    """
    Repository-Klasse für die Admin-Konfiguration.

    Diese Klasse abstrahiert den Speicherort (z. B. JSON-Datei)
    und stellt eine saubere Schnittstelle für das Laden und Speichern
    der Konfiguration bereit.
    """

    def __init__(
        self,
        file_manager: FileManager,
        config_path: str = "data/config/admin_config.json",
    ):
        """
        Initialisiert das Repository.

        Args:
            file_manager: FileManager-Instanz für Dateioperationen
            config_path: relativer Pfad zur Konfigurationsdatei
        """
        self.file_manager = file_manager
        self.config_path = config_path

    def exists(self) -> bool:
        """
        Prüft, ob eine Konfigurationsdatei existiert.

        Returns:
            bool: True, wenn Konfiguration existiert
        """
        return self.file_manager.exists(self.config_path)

    def load(self) -> Optional[AdminConfig]:
        """
        Lädt die Admin-Konfiguration von Disk.

        Returns:
            AdminConfig | None:
            - AdminConfig, wenn Datei existiert und gültig ist
            - None, wenn keine Konfiguration existiert
        """
        if not self.exists():
            return None

        data = self.file_manager.read_json(self.config_path)

        # Wandelt JSON-Daten in ein Pydantic-Modell um
        return AdminConfig.model_validate(data)

    def save(self, config: AdminConfig) -> None:
        """
        Speichert die Admin-Konfiguration auf Disk.

        Args:
            config: AdminConfig-Objekt
        """
        self.file_manager.create_json(
            self.config_path,
            config.model_dump(),
            overwrite=True,
        )
