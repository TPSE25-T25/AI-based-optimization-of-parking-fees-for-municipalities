from typing import Any, Dict, List, Union
from pydantic import BaseModel

from backend.services.models.city import City
from backend.services.optimizer.schemas.optimization_schema import PricingScenario
from backend.services.settings.optimizations_settings import OptimizationSettings, AgentBasedSettings

class OptimizationRequest(BaseModel):
    """
    The complete payload sent to the API for optimization.
    It acts as a container building the "what" (zones) and the "how" (settings).
    """
    city: City                     # The city model containing parking zones and their data
    optimizer_settings: Union[OptimizationSettings, AgentBasedSettings]              # the NSGA-III algorithm settings

class OptimizationResponse(BaseModel):
    """
    The API response: A list of optimal scenarios (Pareto Front).
    """
    scenarios: List[PricingScenario]
    

class OptimizationSettingsResponse(BaseModel):
    """
    The optimization settings schema for frontend configuration panel.
    """
    settings: Dict[str, Dict[str, Any]]
    
    def __init__(self, **data):
        if not data:
            # Generate settings from OptimizationSettings model
            fields = getattr(OptimizationSettings, "model_fields", None)

            def serialize_field(field):
                info = getattr(field, "field_info", None)
                return {
                    "default": getattr(info, "default", None) if info else getattr(field, "default", None),
                    "min": getattr(info, "ge", None),
                    "max": getattr(info, "le", None),
                    "description": getattr(info, "description", None),
                }

            settings_dict = {name: serialize_field(field) for name, field in fields.items()}
            super().__init__(settings=settings_dict)
        else:
            super().__init__(**data)