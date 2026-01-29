from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict

# 1. IMPORTS (Angepasst an deine Ordner-Struktur)
from services.data.karlsruhe_loader import KarlsruheLoader
# WICHTIG: Dein Optimizer liegt im Unterordner simulation!
from services.nsga3_optimizer import NSGA3Optimizer 
from services.mapping_services import MappingService 
from schemas.optimization import OptimizationRequest, OptimizationSettings

# Initialize FastAPI app
app = FastAPI()

# CORS configuration (für Frontend-Zugriff)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                #Every origin allowed 
    allow_credentials=True,             #Allow credentials
    allow_methods=["*"],                #Allow all methods
    allow_headers=["*"],                #Allow all headers
)

# We keep the state of our services here
state = {
    "loader": None,
    "optimizer": NSGA3Optimizer(),
    "mapper": None,
    "last_response": None
}

print("⏳ Initialisiere System...")
state["loader"] = KarlsruheLoader()
state["mapper"] = MappingService(state["loader"])
print("✅ System bereit.")

# Define Data Models for Requests
class WeightRequest(BaseModel):
    weights: Dict[str, int]

# Endpoints
@app.post("/api/run-optimization")                              # Start optimization process
def run_optimization(settings: OptimizationSettings):
    print("🔄 Starte Optimierung...")
    zones = state["loader"].load_zones(limit=500)
    req = OptimizationRequest(zones=zones, settings=settings)
    
    response = state["optimizer"].optimize(req)
    state["last_response"] = response                               # Store last response for further queries
    
    return {"status": "finished", "scenarios_found": len(response.scenarios)}

@app.post("/api/update-view")                                  # Update view with new weights
def update_view(req: WeightRequest):
    if not state["last_response"]:
        raise HTTPException(status_code=400, detail="Erst Optimierung starten!")

# Integrate weightening functionality
    best_scenario = state["optimizer"].select_best_solution_by_weights(
        state["last_response"], 
        req.weights
    )

    if not best_scenario:
        raise HTTPException(status_code=404, detail="Kein Szenario gefunden")

    map_html_string = state["mapper"].generate_map_html(best_scenario.zones)

    return {
        "kpi": {
            "revenue": best_scenario.score_revenue,
            "occupancy_gap": best_scenario.score_occupancy_gap,
            "demand_drop": best_scenario.score_demand_drop,
            "fairness": best_scenario.score_user_balance
        },
        "map_html": map_html_string 
    }