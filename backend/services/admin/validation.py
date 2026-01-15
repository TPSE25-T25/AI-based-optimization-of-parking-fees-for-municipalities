"""
Validation für Admin-Konfiguration

Dieses Modul enthält Business- und Regelvalidierungen für AdminConfig.
Pydantic (schemas.py) prüft bereits Datentypen und Pflichtfelder.
Hier werden zusätzliche fachliche und rechtliche Regeln geprüft.

Beispiele:
- objective_weights dürfen nicht negativ sein
- min_price darf nicht größer als max_price sein
- maximale Parkgebühr darf nicht über einem legalen Limit liegen
- Rabattregeln müssen sinnvoll sein
"""

from typing import Iterable, Set

from .schemas import AdminConfig


class ConfigValidationError(ValueError):
    """Wird geworfen, wenn die Konfiguration fachlich/regeltechnisch ungültig ist."""
    pass


def _require(condition: bool, message: str) -> None:
    """Kleine Helper-Funktion für lesbare Validierungschecks."""
    if not condition:
        raise ConfigValidationError(message)


def validate_admin_config(cfg: AdminConfig) -> None:
    """
    Validiert eine AdminConfig nach fachlichen und rechtlichen Regeln.

    Args:
        cfg: AdminConfig

    Raises:
        ConfigValidationError: falls eine Regel verletzt ist
    """

    # -------------------------------------------------------
    # 1) Objective Weights (Mehrkriterielle Optimierung)
    # -------------------------------------------------------
    # Beispiel: {"revenue": 1.0, "utilization": 1.0, "fairness": 1.0}
    weights = cfg.objective_weights or {}
    _require(len(weights) > 0, "objective_weights must not be empty")

    _require(
        all(v is not None for v in weights.values()),
        "objective_weights must not contain null values"
    )

    _require(
        all(v >= 0 for v in weights.values()),
        "objective_weights must be >= 0"
    )

    _require(
        sum(weights.values()) > 0,
        "Sum of objective_weights must be > 0"
    )

    # Optional: verpflichtende Ziele
    # Falls du willst, dass diese Keys immer vorhanden sind:
    required_keys = {"revenue", "utilization", "fairness"}
    missing = required_keys - set(weights.keys())
    _require(
        not missing,
        f"objective_weights missing required keys: {sorted(missing)}"
    )

    # -------------------------------------------------------
    # 2) Preisregeln (rechtliche / logische Constraints)
    # -------------------------------------------------------
    # Hier definierst du municipal/legal Limits.
    # Du kannst diese Konstanten später in eine eigene Legal-Policy-Datei auslagern.
    LEGAL_MAX_PRICE_EUR_PER_HOUR = 10.0  # Beispiel: Maximal 10 €/h
    LEGAL_MIN_PRICE_EUR_PER_HOUR = 0.0   # Min. 0 €/h

    seen_zone_ids: Set[str] = set()

    for rule in cfg.price_rules:
        _require(rule.zone_id not in seen_zone_ids, f"Duplicate zone_id in price_rules: {rule.zone_id}")
        seen_zone_ids.add(rule.zone_id)

        _require(
            rule.min_price_eur_per_hour >= LEGAL_MIN_PRICE_EUR_PER_HOUR,
            f"min_price_eur_per_hour must be >= {LEGAL_MIN_PRICE_EUR_PER_HOUR} for zone_id={rule.zone_id}"
        )

        _require(
            rule.max_price_eur_per_hour <= LEGAL_MAX_PRICE_EUR_PER_HOUR,
            f"max_price_eur_per_hour must be <= {LEGAL_MAX_PRICE_EUR_PER_HOUR} for zone_id={rule.zone_id}"
        )

        _require(
            rule.min_price_eur_per_hour <= rule.max_price_eur_per_hour,
            f"min_price_eur_per_hour must be <= max_price_eur_per_hour for zone_id={rule.zone_id}"
        )

    # -------------------------------------------------------
    # 3) Rabattregeln (Fairness / Nutzergruppen)
    # -------------------------------------------------------
    # percent wird in schemas.py bereits auf 0..100 begrenzt,
    # trotzdem prüfen wir:
    # - keine Doppeldefinition derselben user_group
    # - keine unrealistischen Summen
    seen_user_groups: Set[str] = set()

    for disc in cfg.discounts:
        _require(
            disc.user_group not in seen_user_groups,
            f"Duplicate user_group in discounts: {disc.user_group}"
        )
        seen_user_groups.add(disc.user_group)

    # Optional: "sanity check" - Summenrabatt nicht absurd hoch
    total_discount = sum(d.percent for d in cfg.discounts)
    _require(
        total_discount <= 200,
        "Total discount sum seems unrealistic (>200). Check discount rules."
    )

    # -------------------------------------------------------
    # 4) Real-Daten Toggle / Dataset Auswahl
    # -------------------------------------------------------
    # Falls real data nicht erlaubt ist, darf kein dataset_id gesetzt sein
    if not cfg.allow_real_data:
        _require(
            cfg.active_dataset_id is None,
            "active_dataset_id must be None when allow_real_data is False"
        )
