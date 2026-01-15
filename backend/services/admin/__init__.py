"""
Admin Services Package

Dieses Paket stellt alle administrativen Backend-Funktionen bereit:
- Konfigurationsmanagement
- Validierung rechtlicher und logischer Regeln
- Persistenz der Admin-Konfiguration
- REST-API für Admin-Zugriff
"""

from .api import router

from .schemas import (
    AdminConfig,
    PriceRule,
    DiscountRule,
)

from .config_repository import ConfigRepository
from .config_service import ConfigService
from .validation import ConfigValidationError, validate_admin_config

__all__ = [
    "router",
    "AdminConfig",
    "PriceRule",
    "DiscountRule",
    "ConfigRepository",
    "ConfigService",
    "ConfigValidationError",
    "validate_admin_config",
]
