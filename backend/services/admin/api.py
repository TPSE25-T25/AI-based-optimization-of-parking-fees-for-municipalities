"""
Admin Configuration API (FastAPI)

Dieses Modul stellt REST-Endpunkte bereit, über die ein Admin:
- die aktive Konfiguration abrufen kann
- eine neue Konfiguration setzen kann (mit Validierung)
- eine Konfiguration validieren kann, ohne sie zu speichern (optional, sehr praktisch fürs Frontend)

Kommunikation: JSON über REST (FastAPI)
"""

from fastapi import APIRouter, HTTPException, status

from backend.services.io.file_manager import FileManager
from .schemas import AdminConfig
from .config_repository import ConfigRepository

# Optional (empfohlen):
# Falls du diese Dateien schon hast, nutze sie. Wenn nicht, sag Bescheid.
from .config_service import ConfigService

from .validation import ConfigValidationError

router = APIRouter(prefix="/admin/config", tags=["admin-config"])

# ----------------------------------------
# Wiring (einfacher MVP-Ansatz)
# ----------------------------------------
# Später kannst du Dependency Injection nutzen (Depends),
# aber für den Start ist diese Verdrahtung okay und verständlich.

_file_manager = FileManager()
_repo = ConfigRepository(_file_manager, config_path="data/config/admin_config.json")
_service = ConfigService(_repo)


# ----------------------------------------
# GET: aktive Konfiguration abrufen
# ----------------------------------------
@router.get("", response_model=AdminConfig)
def get_active_config() -> AdminConfig:
    """
    Liefert die aktuell aktive Admin-Konfiguration.

    Returns:
        AdminConfig: aktuelle Konfiguration

    Raises:
        404: wenn keine Konfiguration existiert
    """
    cfg = _service.get_active_config()
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active admin config found."
        )
    return cfg


# ----------------------------------------
# PUT: Konfiguration setzen (speichern)
# ----------------------------------------
@router.put("", response_model=AdminConfig)
def set_active_config(cfg: AdminConfig) -> AdminConfig:
    """
    Setzt eine neue Admin-Konfiguration als aktiv.
    Validiert die Konfiguration und speichert sie anschließend.

    Args:
        cfg: AdminConfig aus Request JSON

    Returns:
        AdminConfig: gespeicherte Konfiguration

    Raises:
        400: Validierungsfehler (Constraints verletzt)
    """
    try:
        return _service.set_active_config(cfg)
    except ConfigValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ----------------------------------------
# POST: Konfiguration nur validieren (ohne Speichern)
# ----------------------------------------
@router.post("/validate", response_model=dict)
def validate_config(cfg: AdminConfig) -> dict:
    """
    Validiert die Konfiguration, ohne sie zu speichern.
    Sehr nützlich für Frontend: "Check" bevor man speichert.

    Returns:
        dict: {"valid": True} oder {"valid": False, "error": "..."}
    """
    try:
        # Nutzt dieselbe Validierung wie beim Speichern
        _service.set_active_config(cfg)  # würde speichern -> deshalb NICHT gut
        return {"valid": True}
    except ConfigValidationError as e:
        return {"valid": False, "error": str(e)}
