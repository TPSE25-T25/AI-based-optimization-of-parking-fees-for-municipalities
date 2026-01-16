# Parking Simulation Implementation Summary

## Overview
Implemented a complete simulation framework for optimizing parking lot prices using multi-objective optimization (NSGA-II). The simulation models driver behavior in a city with multiple parking lots and evaluates different pricing strategies.

## Files Created

### Core Simulation Module
1. **`backend/services/simulation.py`** (Main simulation engine)
   - `SimulationMetrics`: Data class for all simulation outputs
   - `DriverDecision`: Driver decision-making logic with configurable weights
   - `ParkingSimulation`: Main simulation orchestrator
   - `SimulationBatch`: Multiple simulation runs for stochastic analysis

2. **`backend/services/driver_generator.py`** (Driver population generation)
   - `DriverGenerator`: Creates various driver populations
   - Methods: random, clustered, rush-hour, price-sensitive drivers

### Documentation
3. **`docs/SIMULATION_README.md`**
   - Complete usage guide
   - Architecture explanation
   - Integration patterns
   - Best practices

### Examples
4. **`examples/simulation_demo.py`**
   - 6 complete working examples
   - Basic simulation, price comparison, rush hour, batch runs
   - Custom driver behavior demonstrations

5. **`examples/nsga2_integration.py`**
   - NSGA-II integration reference
   - Pymoo library integration example
   - Custom NSGA-II interface
   - Result analysis utilities

### Tests
6. **`tests/backend_tests/services/test_simulation.py`**
   - Unit tests for all major components
   - Driver decision tests
   - Simulation logic tests
   - Generator tests
   - Batch simulation tests

## Architecture

### Simulation Flow
```
1. Initialize city with parking lots
2. Generate driver population
3. For each driver:
   - Filter available & affordable lots
   - Score lots using weighted decision function
   - Select best lot and park
   - Update occupancy and metrics
4. Return aggregated metrics
```

### Driver Decision Model
Drivers select parking lots based on weighted factors:
- **Price**: Hourly parking cost
- **Distance to lot**: Driving distance from current position
- **Walking distance**: From lot to final destination
- **Availability**: Preference for less crowded lots

Formula: `score = w1*price + w2*dist_to_lot + w3*walking + w4*occupancy`

Driver chooses lot with minimum score (if affordable).

### NSGA-II Integration
```python
# For each candidate price configuration:
1. Apply prices to parking lots
2. Run simulation with drivers
3. Collect objectives:
   - Revenue (maximize → negate)
   - Occupancy variance (minimize)
   - Avg driver cost (minimize)
4. Return objectives to NSGA-II
5. NSGA-II ranks solutions and evolves population
```

## Key Classes

### `ParkingSimulation`
Main simulation engine.

**Methods:**
- `run_simulation(city, drivers)`: Execute one simulation
- `evaluate_price_configuration(city, drivers, prices)`: Interface for optimizers

### `DriverDecision`
Encapsulates driver behavior.

**Configurable weights:**
- `price_weight`: Sensitivity to price (default: 1.0)
- `distance_to_lot_weight`: Importance of driving distance (default: 0.5)
- `walking_distance_weight`: Importance of walking (default: 1.5)
- `availability_weight`: Preference for emptier lots (default: 0.3)

### `SimulationMetrics`
Contains all outputs:
- Revenue metrics (total, per-lot, average)
- Occupancy metrics (rate, variance, std dev)
- Driver satisfaction (avg cost, walking distance, rejection rate)
- Per-lot breakdowns

### `DriverGenerator`
Creates driver populations for testing.

**Generator types:**
- `generate_random_drivers()`: Uniform distribution
- `generate_clustered_drivers()`: Start from residential areas
- `generate_rush_hour_drivers()`: Peak traffic patterns
- `generate_price_sensitive_drivers()`: Budget-conscious drivers

## Usage Examples

### Basic Simulation
```python
from backend.services.simulation import ParkingSimulation
from backend.services.driver_generator import DriverGenerator

# Setup
city = create_city_with_parking_lots()
generator = DriverGenerator(seed=42)
drivers = generator.generate_random_drivers(count=500, city=city)

# Run
simulation = ParkingSimulation()
metrics = simulation.run_simulation(city, drivers)

print(f"Revenue: ${metrics.total_revenue}")
print(f"Occupancy: {metrics.overall_occupancy_rate:.2%}")
```

### NSGA-II Integration
```python
# NSGA-II fitness function
def fitness_function(price_vector):
    objectives = simulation.evaluate_price_configuration(
        city, drivers, price_vector,
        objectives=['negative_revenue', 'occupancy_variance', 'avg_driver_cost']
    )
    
    return (
        objectives['negative_revenue'],
        objectives['occupancy_variance'],
        objectives['avg_driver_cost']
    )
```

### Custom Driver Behavior
```python
# Price-sensitive drivers
decision = DriverDecision(
    price_weight=3.0,  # Very price-sensitive
    walking_distance_weight=0.5
)

simulation = ParkingSimulation(decision_maker=decision)
metrics = simulation.run_simulation(city, drivers)
```

## Optimization Objectives

Available objectives for NSGA-II:

| Objective | Type | Description |
|-----------|------|-------------|
| `negative_revenue` | Minimize | Maximize revenue (negated for minimization) |
| `occupancy_variance` | Minimize | Balance load across parking lots |
| `avg_driver_cost` | Minimize | Driver satisfaction (lower is better) |
| `rejection_rate` | Minimize | Minimize drivers who can't find parking |
| `utilization_rate` | Maximize | Use available capacity efficiently |

## Testing

Run unit tests:
```bash
python -m pytest tests/backend_tests/services/test_simulation.py
```

Or using unittest:
```bash
python -m unittest tests.backend_tests.services.test_simulation
```

## Running Examples

```bash
# Complete demonstration with 6 examples
python examples/simulation_demo.py

# NSGA-II integration reference
python examples/nsga2_integration.py
```

## Design Decisions

### 1. **Static vs Dynamic Simulation**
Current: **Static** - all drivers arrive at once
- Simpler to implement and understand
- Deterministic with fixed seed
- Good for initial optimization

Future: Can add time-based dynamics where drivers arrive sequentially

### 2. **Decision Function**
Uses weighted linear combination for simplicity
- Easy to understand and configure
- Sufficient for most scenarios
- Can be extended with more sophisticated models

### 3. **Metric Collection**
Comprehensive metrics collection for flexibility
- Supports multiple optimization objectives
- Per-lot breakdowns for analysis
- Easy to add new metrics

### 4. **Stochastic vs Deterministic**
Supports both:
- Fixed seed → reproducible results
- No seed → stochastic variation
- Batch simulation for averaging

## Performance Characteristics

- **Complexity**: O(n × m) where n=drivers, m=parking_lots
- **Typical simulation**: 500 drivers, 10 lots = ~5000 operations
- **NSGA-II generation**: ~100-200 evaluations
- **Total**: ~500,000 to 1,000,000 operations per generation
- **Runtime**: Milliseconds per simulation on modern hardware

## Extension Points

### 1. Add New Objectives
```python
# In evaluate_price_configuration
all_objectives['your_metric'] = calculate_your_metric(metrics)
```

### 2. Custom Driver Behavior
```python
class CustomDecision(DriverDecision):
    def select_parking_lot(self, driver, lots):
        # Your logic
        return selected_lot
```

### 3. Time-Based Simulation
- Add arrival times to drivers
- Process sequentially
- Track state changes over time

### 4. Dynamic Pricing
- Update prices during simulation
- Model price elasticity
- Implement surge pricing

## Dependencies

Required:
- `pydantic` - Data validation
- `decimal` - Precise calculations
- Standard library: `typing`, `statistics`, `copy`, `random`

Optional (for examples):
- `numpy` - Array operations (NSGA-II)
- `pymoo` - NSGA-II implementation

## Next Steps

1. **Validate Simulation**: Run with known configurations to verify behavior
2. **Tune Parameters**: Adjust driver weights based on real-world data
3. **Implement NSGA-II**: Use pymoo or custom implementation
4. **Run Optimization**: Find Pareto front of pricing strategies
5. **Analyze Results**: Evaluate trade-offs between objectives
6. **Refine Model**: Add complexity as needed (time dynamics, etc.)

## Integration Checklist

- [x] Core simulation engine
- [x] Driver decision model
- [x] Metric collection
- [x] Driver generation utilities
- [x] Batch simulation support
- [x] NSGA-II interface
- [x] Documentation
- [x] Examples
- [x] Unit tests
- [ ] NSGA-II implementation (user's choice of library)
- [ ] Visualization tools (optional)
- [ ] Real-world validation (optional)

## Notes

- All prices use `Decimal` for precision
- City state is never modified (uses deepcopy)
- Drivers processed sequentially (not parallel)
- Lot capacity strictly enforced
- Unaffordable/full lots automatically filtered
- Rejected drivers receive penalty cost

## Questions & Support

See documentation:
- `docs/SIMULATION_README.md` - Full documentation
- `examples/simulation_demo.py` - Working examples
- `examples/nsga2_integration.py` - NSGA-II integration

Model files:
- `backend/models/city.py` - City, Street, POI models
- `backend/models/parkinglot.py` - ParkingLot model
- `backend/models/driver.py` - Driver model
