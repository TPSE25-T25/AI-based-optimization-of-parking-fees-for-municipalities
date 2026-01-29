"""
Admin Configuration API (FastAPI)

REST Endpoints:
- GET  /admin/config           -> get active config
- PUT  /admin/config           -> validate + save config
- POST /admin/config/validate  -> validate ONLY (no saving)

Communication: JSON over REST (FastAPI)
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from backend.services.io.file_manager import FileManager
from .schemas import AdminConfig
from .config_repository import ConfigRepository
from .config_service import ConfigService
from .validation import ConfigValidationError

router = APIRouter(prefix="/admin/config", tags=["admin-config"])

# ----------------------------------------
# Deterministic config path
# repo_root/backend/services/admin/api.py -> parents[3] = repo_root
# ----------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "backend" / "data" / "config" / "admin_config.json"

# ----------------------------------------
# Wiring (MVP)
# ----------------------------------------
_file_manager = FileManager()
_repo = ConfigRepository(_file_manager, config_path=str(CONFIG_PATH))
_service = ConfigService(_repo)


@router.get("", response_model=AdminConfig)
def get_active_config() -> AdminConfig:
    cfg = _service.get_active_config()
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active admin config found.",
        )
    return cfg


@router.put("", response_model=AdminConfig)
def set_active_config(cfg: AdminConfig) -> AdminConfig:
    try:
        return _service.set_active_config(cfg)
    except ConfigValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/validate", response_model=dict)
def validate_config(cfg: AdminConfig) -> dict:
    """
    Validate WITHOUT saving. Frontend can call this before PUT.
    """
    try:
        _service.validate_config(cfg)
        return {"valid": True}
    except ConfigValidationError as e:
        return {"valid": False, "error": str(e)}
