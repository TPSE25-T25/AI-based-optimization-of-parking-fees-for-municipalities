from typing import List
from pydantic import BaseModel, Field

from backend.services.optimizer.schemas.optimization_schema import PricingScenario


class WeightSelectionRequest(BaseModel):
    """
    Request for selecting the best solution from optimization results based on user preferences.
    """
    scenarios: List[PricingScenario]
    weights: dict = Field(..., description="Weights for each objective (revenue, occupancy, drop, fairness)")

class WeightSelectionResponse(BaseModel):
    """
    Response with the selected best solution based on user preferences.
    """
    scenario: PricingScenario
