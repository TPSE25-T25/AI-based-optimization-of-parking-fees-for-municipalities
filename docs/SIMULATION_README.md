# Parking Simulation Module

This module provides a comprehensive simulation framework for optimizing parking lot prices using multi-objective optimization algorithms like NSGA-II.

## Architecture Overview

The simulation acts as the **fitness evaluation function** for optimization algorithms. It simulates driver behavior in a city with multiple parking lots and returns objective metrics.

```
NSGA-II (or other optimizer)
    ↓
Generate price configuration
    ↓
Simulation evaluates configuration
    ↓
Returns multiple objectives
    ↓
Optimizer uses objectives for selection
    ↓
Evolve new generation
```

## Core Components

### 1. **ParkingSimulation** (`simulation.py`)
Main simulation engine that orchestrates driver behavior and metric collection.

**Key Methods:**
- `run_simulation(city, drivers)` - Runs one complete simulation
- `evaluate_price_configuration(city, drivers, price_vector)` - Interface for optimizers

### 2. **DriverDecision** (`simulation.py`)
Encapsulates driver decision-making logic using weighted scoring.

**Decision Factors:**
- Parking price (configurable weight)
- Distance to parking lot
- Walking distance to destination
- Lot availability/occupancy

**Customizable:** Adjust weights to model different driver populations (price-sensitive, convenience-focused, etc.)

### 3. **SimulationMetrics** (`simulation.py`)
Container for all simulation outputs/objectives.

**Metrics Collected:**
- **Revenue metrics:** Total revenue, average per lot
- **Occupancy metrics:** Utilization rate, variance, standard deviation
- **Driver satisfaction:** Average cost, walking distance, rejection rate
- **Per-lot data:** Individual lot performance

### 4. **DriverGenerator** (`driver_generator.py`)
Utilities for creating driver populations.

**Generator Types:**
- `generate_random_drivers()` - Uniform random distribution
- `generate_clustered_drivers()` - Drivers starting from residential clusters
- `generate_rush_hour_drivers()` - Peak traffic to specific destinations
- `generate_price_sensitive_drivers()` - Budget-conscious drivers

### 5. **SimulationBatch** (`simulation.py`)
Handles multiple simulation runs for stochastic analysis.

**Features:**
- Run same configuration multiple times
- Average metrics across runs
- Calculate variance/confidence intervals

## Usage Examples

### Basic Simulation

```python
from backend.models.city import City
from backend.services.simulation import ParkingSimulation
from backend.services.driver_generator import DriverGenerator

# Create city with parking lots
city = create_your_city()

# Generate drivers
generator = DriverGenerator(seed=42)
drivers = generator.generate_random_drivers(count=500, city=city)

# Run simulation
simulation = ParkingSimulation()
metrics = simulation.run_simulation(city, drivers)

print(f"Total Revenue: ${metrics.total_revenue}")
print(f"Occupancy Rate: {metrics.overall_occupancy_rate:.2%}")
print(f"Rejection Rate: {metrics.rejection_rate:.2%}")
```

### NSGA-II Integration

```python
def nsga2_fitness_function(price_vector):
    """
    Fitness function called by NSGA-II for each candidate solution.
    
    Args:
        price_vector: List of prices for parking lots
        
    Returns:
        Tuple of objective values (all for minimization)
    """
    objectives = simulation.evaluate_price_configuration(
        city, drivers, price_vector,
        objectives=['negative_revenue', 'occupancy_variance', 'avg_driver_cost']
    )
    
    return (
        objectives['negative_revenue'],    # Maximize revenue → negate
        objectives['occupancy_variance'],  # Minimize variance
        objectives['avg_driver_cost']      # Minimize driver cost
    )

# NSGA-II would then:
# 1. Generate population of price vectors
# 2. Evaluate each using fitness function
# 3. Rank solutions by dominance
# 4. Select and evolve population
# 5. Repeat until convergence
```

### Custom Driver Behavior

```python
# Model price-sensitive drivers
price_sensitive = DriverDecision(
    price_weight=3.0,        # Very sensitive to price
    walking_distance_weight=0.5
)

simulation = ParkingSimulation(decision_maker=price_sensitive)
metrics = simulation.run_simulation(city, drivers)
```

### Stochastic Simulation

```python
# Generate multiple driver sets
driver_sets = [
    generator.generate_random_drivers(count=500, city=city)
    for _ in range(10)
]

# Run batch simulation
batch = SimulationBatch(simulation)
results = batch.run_multiple_simulations(city, driver_sets)

# Get average metrics
avg_metrics = batch.average_metrics(results)
print(f"Average Revenue: ${avg_metrics['avg_revenue']} ± ${avg_metrics['std_revenue']}")
```

## Simulation Flow

### Single Simulation Run

1. **Initialization**
   - Reset parking lot capacities to 0
   - Create working copy of city (doesn't modify original)

2. **Driver Processing** (for each driver)
   - Filter available lots (not full)
   - Filter affordable lots (within budget)
   - Score each lot using weighted decision function
   - Select lot with best (lowest) score
   - Update lot occupancy
   - Record metrics

3. **Metric Aggregation**
   - Calculate revenue totals and per-lot breakdown
   - Compute occupancy statistics
   - Calculate driver satisfaction metrics
   - Return SimulationMetrics object

### Driver Decision Algorithm

```python
score = (
    price_weight * (lot.price / normalize_price) +
    distance_weight * (distance_to_lot / normalize_distance) +
    walking_weight * (walking_distance / normalize_distance) +
    availability_weight * lot.occupancy_rate()
)

# Driver selects lot with minimum score
```

## Optimization Objectives

Common objectives for NSGA-II:

| Objective | Type | Description |
|-----------|------|-------------|
| `negative_revenue` | Minimize | Maximize revenue (negated) |
| `occupancy_variance` | Minimize | Balance load across lots |
| `avg_driver_cost` | Minimize | Driver satisfaction |
| `rejection_rate` | Minimize | Ensure capacity |
| `occupancy_std_dev` | Minimize | Alternative to variance |

## Configuration Parameters

### Driver Decision Weights

Adjust to model different driver populations:

```python
DriverDecision(
    price_weight=1.0,              # Sensitivity to parking price
    distance_to_lot_weight=0.5,    # Importance of driving distance
    walking_distance_weight=1.5,   # Importance of walking to destination
    availability_weight=0.3        # Preference for emptier lots
)
```

### Simulation Parameters

```python
ParkingSimulation(
    decision_maker=custom_decision,      # Custom driver logic
    rejection_penalty=Decimal('100.0')   # Cost for rejected drivers
)
```

### Driver Generation

```python
generator.generate_random_drivers(
    count=500,                                    # Number of drivers
    city=city,                                    # City model
    price_range=(Decimal('2.0'), Decimal('10.0')),  # Price tolerance range
    parking_duration_range=(30, 240)              # Duration in minutes
)
```

## Running the Demo

See complete examples:

```bash
python examples/simulation_demo.py
```

This demonstrates:
1. Basic simulation
2. Price configuration comparison
3. Rush hour scenarios
4. Batch/stochastic simulation
5. NSGA-II integration pattern
6. Custom driver behavior

## Extension Points

### Adding New Objectives

Modify `evaluate_price_configuration()` in `simulation.py`:

```python
all_objectives = {
    'revenue': float(metrics.total_revenue),
    'your_custom_objective': calculate_custom_metric(metrics),
    # ... other objectives
}
```

### Custom Driver Behavior

Subclass `DriverDecision` and override `select_parking_lot()`:

```python
class MyCustomDecision(DriverDecision):
    def select_parking_lot(self, driver, available_lots):
        # Your custom logic
        return selected_lot
```

### Time-Based Simulation

Current implementation is static (all drivers at once). To add time dynamics:

1. Sort drivers by arrival time
2. Process sequentially
3. Track lot state changes over time
4. Update metrics calculation

## Best Practices

1. **Start Simple:** Use deterministic simulation (fixed seed) for initial testing
2. **Validate:** Run known configurations to verify behavior makes sense
3. **Iterate:** Add complexity gradually (stochastic, time-based, etc.)
4. **Tune Weights:** Adjust driver decision weights based on real-world data
5. **Multiple Runs:** Use batch simulation for stochastic scenarios
6. **Normalize:** Ensure objectives are on comparable scales for NSGA-II

## Performance Considerations

- Simulation complexity: O(n * m) where n = drivers, m = parking lots
- Each NSGA-II generation evaluates ~100-200 solutions
- For 500 drivers, 10 lots: ~5000 evaluations per solution
- Consider parallelizing population evaluation
- Cache city configurations if evaluating same prices multiple times

## Integration with NSGA-II

The simulation is designed to integrate seamlessly with NSGA-II:

```python
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem

class ParkingOptimizationProblem(Problem):
    def __init__(self, city, drivers, simulation):
        n_lots = len(city.parking_lots)
        super().__init__(
            n_var=n_lots,               # One price per lot
            n_obj=3,                     # Three objectives
            xl=1.0,                      # Min price
            xu=10.0                      # Max price
        )
        self.city = city
        self.drivers = drivers
        self.simulation = simulation
    
    def _evaluate(self, x, out, *args, **kwargs):
        # x is population matrix (n_individuals x n_lots)
        objectives = []
        
        for prices in x:
            price_vector = [Decimal(str(p)) for p in prices]
            obj = self.simulation.evaluate_price_configuration(
                self.city, self.drivers, price_vector,
                objectives=['negative_revenue', 'occupancy_variance', 'avg_driver_cost']
            )
            objectives.append([
                obj['negative_revenue'],
                obj['occupancy_variance'],
                obj['avg_driver_cost']
            ])
        
        out["F"] = np.array(objectives)
```

## Files

- `backend/services/simulation.py` - Core simulation engine
- `backend/services/driver_generator.py` - Driver population generation
- `examples/simulation_demo.py` - Complete usage examples

## Dependencies

- `pydantic` - Data validation
- `decimal` - Precise price calculations
- `statistics` - Metric calculations
- Standard library: `copy`, `typing`, `random`
