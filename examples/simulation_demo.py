"""
Example simulation demonstrating driver behavior and NSGA-II integration.
This script shows how to:
1. Create a city with parking lots
2. Generate driver populations
3. Run simulations
4. Evaluate different price configurations
"""

from decimal import Decimal
from typing import List

from backend.models.city import City, PointOfInterest, ParkingLot
from backend.services.simulation.simulation import ParkingSimulation, DriverDecision, SimulationBatch
from backend.services.data.driver_generator import DriverGenerator


def create_example_city() -> City:
    """Create a sample city for simulation."""
    
    # Create city with 1000x1000 canvas
    city = City(
        id=1,
        pseudonym="SimulationCity",
        canvas=(1000.0, 1000.0)
    )
    
    # Add points of interest
    pois = [
        PointOfInterest(id=1, pseudonym="Downtown", position=(500.0, 500.0)),
        PointOfInterest(id=2, pseudonym="Mall", position=(300.0, 700.0)),
        PointOfInterest(id=3, pseudonym="University", position=(700.0, 300.0)),
        PointOfInterest(id=4, pseudonym="Hospital", position=(200.0, 200.0)),
    ]
    
    for poi in pois:
        city.add_point_of_interest(poi)
    
    # Add parking lots near POIs
    parking_lots = [
        # Downtown area - higher capacity, varied pricing
        ParkingLot(id=1, pseudonym="Downtown_Central", price=Decimal('5.00'), 
                   position=(480.0, 480.0), maximum_capacity=200, current_capacity=0),
        ParkingLot(id=2, pseudonym="Downtown_East", price=Decimal('4.50'), 
                   position=(520.0, 500.0), maximum_capacity=150, current_capacity=0),
        
        # Mall area - moderate pricing
        ParkingLot(id=3, pseudonym="Mall_Parking", price=Decimal('3.00'), 
                   position=(310.0, 690.0), maximum_capacity=300, current_capacity=0),
        
        # University area - lower pricing
        ParkingLot(id=4, pseudonym="University_Main", price=Decimal('2.00'), 
                   position=(690.0, 290.0), maximum_capacity=250, current_capacity=0),
        ParkingLot(id=5, pseudonym="University_West", price=Decimal('1.50'), 
                   position=(670.0, 310.0), maximum_capacity=180, current_capacity=0),
        
        # Hospital area - premium pricing
        ParkingLot(id=6, pseudonym="Hospital_Parking", price=Decimal('6.00'), 
                   position=(210.0, 190.0), maximum_capacity=120, current_capacity=0),
        
        # Peripheral parking - cheap but far
        ParkingLot(id=7, pseudonym="Peripheral_North", price=Decimal('1.00'), 
                   position=(500.0, 100.0), maximum_capacity=400, current_capacity=0),
        ParkingLot(id=8, pseudonym="Peripheral_South", price=Decimal('1.00'), 
                   position=(500.0, 900.0), maximum_capacity=400, current_capacity=0),
    ]
    
    for lot in parking_lots:
        city.add_parking_lot(lot)
    
    return city


def example_basic_simulation():
    """Example 1: Basic simulation with random drivers."""
    print("=" * 70)
    print("EXAMPLE 1: Basic Simulation")
    print("=" * 70)
    
    # Create city
    city = create_example_city()
    
    # Generate drivers
    generator = DriverGenerator(seed=42)  # Fixed seed for reproducibility
    drivers = generator.generate_random_drivers(count=500, city=city)
    
    # Create simulation
    simulation = ParkingSimulation()
    
    # Run simulation
    metrics = simulation.run_simulation(city, drivers)
    
    # Display results
    print(f"\nSimulation Results:")
    print(f"  Total Revenue: ${metrics.total_revenue:.2f}")
    print(f"  Drivers Parked: {metrics.total_parked}")
    print(f"  Drivers Rejected: {metrics.total_rejected}")
    print(f"  Rejection Rate: {metrics.rejection_rate:.2%}")
    print(f"  Overall Occupancy: {metrics.overall_occupancy_rate:.2%}")
    print(f"  Occupancy Variance: {metrics.occupancy_variance:.4f}")
    print(f"  Average Driver Cost: ${metrics.average_driver_cost:.2f}")
    print(f"  Average Walking Distance: {metrics.average_walking_distance:.2f}")
    
    print("\nPer-Lot Performance:")
    for lot_id, occupancy in metrics.lot_occupancy_rates.items():
        revenue = metrics.lot_revenues[lot_id]
        print(f"  Lot {lot_id}: {occupancy:.1%} occupancy, ${revenue:.2f} revenue")


def example_price_optimization():
    """Example 2: Evaluating different price configurations."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Price Configuration Evaluation")
    print("=" * 70)
    
    city = create_example_city()
    generator = DriverGenerator(seed=42)
    drivers = generator.generate_random_drivers(count=500, city=city)
    
    simulation = ParkingSimulation()
    
    # Test different price configurations
    price_configs = [
        # Config 1: All low prices
        [Decimal('2.00')] * 8,
        
        # Config 2: All high prices
        [Decimal('8.00')] * 8,
        
        # Config 3: Graduated pricing (downtown expensive, periphery cheap)
        [Decimal('7.00'), Decimal('6.50'), Decimal('4.00'), Decimal('3.00'),
         Decimal('2.50'), Decimal('5.00'), Decimal('1.50'), Decimal('1.50')],
        
        # Config 4: Uniform moderate pricing
        [Decimal('4.00')] * 8,
    ]
    
    config_names = ["Low Prices", "High Prices", "Graduated", "Uniform Moderate"]
    
    print("\nComparing Price Configurations:\n")
    
    for name, prices in zip(config_names, price_configs):
        objectives = simulation.evaluate_price_configuration(
            city, drivers, prices,
            objectives=['revenue', 'occupancy_variance', 'avg_driver_cost', 'rejection_rate']
        )
        
        print(f"{name}:")
        print(f"  Revenue: ${objectives['revenue']:.2f}")
        print(f"  Occupancy Variance: {objectives['occupancy_variance']:.4f}")
        print(f"  Avg Driver Cost: ${objectives['avg_driver_cost']:.2f}")
        print(f"  Rejection Rate: {objectives['rejection_rate']:.2%}")
        print()


def example_rush_hour_simulation():
    """Example 3: Rush hour scenario with many drivers to downtown."""
    print("=" * 70)
    print("EXAMPLE 3: Rush Hour Simulation")
    print("=" * 70)
    
    city = create_example_city()
    
    # Get downtown POI
    downtown = next(poi for poi in city.point_of_interests if poi.pseudonym == "Downtown")
    
    # Generate rush hour drivers
    generator = DriverGenerator(seed=42)
    drivers = generator.generate_rush_hour_drivers(
        count=800,
        city=city,
        peak_destination=downtown
    )
    
    simulation = ParkingSimulation()
    metrics = simulation.run_simulation(city, drivers)
    
    print(f"\nRush Hour Results:")
    print(f"  Total Revenue: ${metrics.total_revenue:.2f}")
    print(f"  Drivers Parked: {metrics.total_parked}")
    print(f"  Drivers Rejected: {metrics.total_rejected}")
    print(f"  Rejection Rate: {metrics.rejection_rate:.2%}")
    print(f"  Overall Occupancy: {metrics.overall_occupancy_rate:.2%}")
    
    # Downtown lots should be most stressed
    print("\nDowntown Area Lots:")
    for lot in city.parking_lots:
        if "Downtown" in lot.pseudonym:
            occupancy = metrics.lot_occupancy_rates[lot.id]
            revenue = metrics.lot_revenues[lot.id]
            print(f"  {lot.pseudonym}: {occupancy:.1%} occupancy, ${revenue:.2f} revenue")


def example_batch_simulation():
    """Example 4: Multiple runs for stochastic analysis."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Batch Simulation (Multiple Runs)")
    print("=" * 70)
    
    city = create_example_city()
    generator = DriverGenerator()  # No seed = different each time
    
    # Generate 5 different driver sets
    driver_sets = [
        generator.generate_random_drivers(count=500, city=city)
        for _ in range(5)
    ]
    
    simulation = ParkingSimulation()
    batch = SimulationBatch(simulation)
    
    # Run all simulations
    results = batch.run_multiple_simulations(city, driver_sets)
    
    # Calculate averages
    avg_metrics = batch.average_metrics(results)
    
    print(f"\nAverage Results (5 runs):")
    print(f"  Avg Revenue: ${avg_metrics['avg_revenue']:.2f} (±${avg_metrics['std_revenue']:.2f})")
    print(f"  Avg Occupancy Variance: {avg_metrics['avg_occupancy_variance']:.4f}")
    print(f"  Avg Driver Cost: ${avg_metrics['avg_driver_cost']:.2f}")
    print(f"  Avg Rejection Rate: {avg_metrics['avg_rejection_rate']:.2%}")
    print(f"  Avg Utilization: {avg_metrics['avg_utilization']:.2%}")


def example_nsga2_interface():
    """Example 5: How NSGA-II would use the simulation."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: NSGA-II Integration Interface")
    print("=" * 70)
    
    city = create_example_city()
    generator = DriverGenerator(seed=42)
    drivers = generator.generate_random_drivers(count=500, city=city)
    
    simulation = ParkingSimulation()
    
    print("\nNSGA-II would call evaluate_price_configuration for each candidate:")
    print("\nCandidate Solution Example:")
    
    # Example: NSGA-II generates a candidate solution (price vector)
    candidate_prices = [Decimal('4.50'), Decimal('4.00'), Decimal('3.50'), Decimal('2.50'),
                       Decimal('2.00'), Decimal('5.50'), Decimal('1.50'), Decimal('1.50')]
    
    print(f"  Price Vector: {[float(p) for p in candidate_prices]}")
    
    # NSGA-II evaluates this candidate
    objectives = simulation.evaluate_price_configuration(
        city, drivers, candidate_prices,
        objectives=['negative_revenue', 'occupancy_variance', 'avg_driver_cost']
    )
    
    print(f"\nObjective Values (for minimization):")
    print(f"  -Revenue: {objectives['negative_revenue']:.2f}")
    print(f"  Occupancy Variance: {objectives['occupancy_variance']:.4f}")
    print(f"  Avg Driver Cost: {objectives['avg_driver_cost']:.2f}")
    
    print("\nNSGA-II uses these values to rank solutions and evolve population.")


def example_custom_driver_behavior():
    """Example 6: Custom driver decision weights."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Custom Driver Behavior")
    print("=" * 70)
    
    city = create_example_city()
    generator = DriverGenerator(seed=42)
    drivers = generator.generate_random_drivers(count=500, city=city)
    
    # Scenario 1: Price-sensitive drivers
    print("\nScenario 1: Price-Sensitive Drivers")
    price_sensitive_decision = DriverDecision(
        price_weight=3.0,  # High weight on price
        distance_to_lot_weight=0.3,
        walking_distance_weight=0.5,
        availability_weight=0.2
    )
    sim1 = ParkingSimulation(decision_maker=price_sensitive_decision)
    metrics1 = sim1.run_simulation(city, drivers)
    print(f"  Avg Price Paid: ${metrics1.average_price_paid:.2f}")
    print(f"  Total Revenue: ${metrics1.total_revenue:.2f}")
    
    # Scenario 2: Convenience-focused drivers
    print("\nScenario 2: Convenience-Focused Drivers")
    convenience_decision = DriverDecision(
        price_weight=0.5,  # Low weight on price
        distance_to_lot_weight=1.5,
        walking_distance_weight=3.0,  # High weight on walking distance
        availability_weight=0.5
    )
    sim2 = ParkingSimulation(decision_maker=convenience_decision)
    metrics2 = sim2.run_simulation(city, drivers)
    print(f"  Avg Walking Distance: {metrics2.average_walking_distance:.2f}")
    print(f"  Total Revenue: ${metrics2.total_revenue:.2f}")
    
    # Scenario 3: Balanced drivers
    print("\nScenario 3: Balanced Drivers (Default)")
    sim3 = ParkingSimulation()
    metrics3 = sim3.run_simulation(city, drivers)
    print(f"  Avg Price Paid: ${metrics3.average_price_paid:.2f}")
    print(f"  Avg Walking Distance: {metrics3.average_walking_distance:.2f}")
    print(f"  Total Revenue: ${metrics3.total_revenue:.2f}")


if __name__ == "__main__":
    # Run all examples
    example_basic_simulation()
    example_price_optimization()
    example_rush_hour_simulation()
    example_batch_simulation()
    example_nsga2_interface()
    example_custom_driver_behavior()
    
    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)
