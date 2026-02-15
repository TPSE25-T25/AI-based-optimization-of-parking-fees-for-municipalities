
from typing import Dict, List, Optional
from pydantic import BaseModel

class SaveResultRequest(BaseModel):
    parameters: Dict
    map_config: Optional[Dict] = None
    map_snapshot: Optional[List[Dict]] = None
    map_path: Optional[str] = None
    csv_path: Optional[str] = None
    best_scenario: Optional[Dict] = None
