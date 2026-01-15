"""
Schemas für Admin-Konfiguration (Pydantic)

Dieses Modul definiert die Datenstruktur der Admin-Konfiguration.
FastAPI nutzt diese Modelle automatisch für:
- Request Validation (PUT/POST JSON)
- Response Serialization

Wichtig:
- Pydantic prüft Typen & Pflichtfelder
- Fachliche Regeln (z.B. min<=max) liegen in validation.py
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PriceRule(BaseModel):
    """
    Preisregel für eine Parkzone.

    Beispiel:
    {
      "zone_id": "A",
      "min_price_eur_per_hour": 1.0,
      "max_price_eur_per_hour": 4.0
    }
    """
    zone_id: str = Field(..., min_length=1)
    min_price_eur_per_hour: float = Field(..., ge=0)
    max_price_eur_per_hour: float = Field(..., gt=0)


class DiscountRule(BaseModel):
    """
    Rabattregel für eine Nutzergruppe.

    Beispiel:
    {
      "user_group": "resident",
      "percent": 20
    }
    """
    user_group: str = Field(..., min_length=1)
    percent: float = Field(..., ge=0, le=100)


class AdminConfig(BaseModel):
    """
    Zentrale Admin-Konfiguration.

    Diese Konfiguration steuert:
    - Objective-Gewichte (Pareto / Multi-Objective Optimierung)
    - Preisregeln pro Zone
    - Rabattregeln pro Nutzergruppe
    - Optional: Auswahl echter Datenquellen
    """

    # Meta
    version: str = Field("1.0.0", min_length=1)
    city: str = Field(..., min_length=1)

    # Multi-Objective Gewichte (werden in validation.py zusätzlich geprüft)
    objective_weights: Dict[str, float] = Field(
        default_factory=lambda: {"revenue": 1.0, "utilization": 1.0, "fairness": 1.0},
        description="Weights for multi-objective optimization (e.g. revenue, utilization, fairness)"
    )

    # Regeln / Constraints
    price_rules: List[PriceRule] = Field(default_factory=list)
    discounts: List[DiscountRule] = Field(default_factory=list)

    # Datenquelle / Betrieb
    allow_real_data: bool = Field(
        default=False,
        description="If false, only synthetic data is allowed"
    )
    active_dataset_id: Optional[str] = Field(
        default=None,
        description="Identifier for active real dataset (only valid if allow_real_data=True)"
    )
