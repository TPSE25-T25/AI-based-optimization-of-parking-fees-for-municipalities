"""
Parking simulation service for optimizing parking lot current_fees.
This module simulates driver behavior in a city with multiple parking lots.
"""

from typing import List, Dict, Tuple, Optional
import statistics
from copy import deepcopy
from pydantic import BaseModel, Field

from backend.models.city import City, ParkingZone
from backend.models.driver import Driver


class SimulationMetrics(BaseModel):
    """
    Container for simulation metrics/objectives.
    These metrics are used by optimization algorithms (e.g., NSGA-II).
    """
    
    # Revenue metrics
    total_revenue: float = Field(default=0.0, description="Total revenue from all parking lots")
    average_revenue_per_lot: float = Field(default=0.0, description="Average revenue per parking lot")
    
    # Occupancy metrics
    total_parked: int = Field(default=0, description="Total number of drivers who successfully parked")
    total_rejected: int = Field(default=0, description="Total number of drivers who couldn't find parking")
    overall_occupancy_rate: float = Field(default=0.0, description="Overall city occupancy rate")
    occupancy_variance: float = Field(default=0.0, description="Variance in occupancy across lots (lower is better)")
    occupancy_std_dev: float = Field(default=0.0, description="Standard deviation of occupancy rates")
    
    # Driver satisfaction metrics
    average_driver_cost: float = Field(default=0.0, description="Average total cost per driver")
    average_walking_distance: float = Field(default=0.0, description="Average walking distance to destination")
    average_current_fee_paid: float = Field(default=0.0, description="Average parking current_fee paid")
    
    # Efficiency metrics
    utilization_rate: float = Field(default=0.0, description="Percentage of capacity utilized")
    rejection_rate: float = Field(default=0.0, description="Percentage of drivers rejected")
    
    # Per-lot metrics
    lot_occupancy_rates: Dict[int, float] = Field(default_factory=dict, description="Occupancy rate per lot ID")
    lot_revenues: Dict[int, float] = Field(default_factory=dict, description="Revenue per lot ID")
    
    class Config:
        arbitrary_types_allowed = True


class DriverDecision:
    """
    Encapsulates the decision-making logic for a driver selecting a parking lot.
    """
    
    def __init__(
        self,
        current_fee_weight: float = 1.0,
        distance_to_lot_weight: float = 0.5,
        walking_distance_weight: float = 1.5,
        availability_weight: float = 0.3
    ):
        """
        Initialize driver decision weights.
        
        Args:
            current_fee_weight: Weight for parking current_fee consideration
            distance_to_lot_weight: Weight for driving distance to lot
            walking_distance_weight: Weight for walking from lot to destination
            availability_weight: Weight for lot availability (penalty for fuller lots)
        """
        self.current_fee_weight = current_fee_weight
        self.distance_to_lot_weight = distance_to_lot_weight
        self.walking_distance_weight = walking_distance_weight
        self.availability_weight = availability_weight
    
    def calculate_lot_score(
        self,
        driver: Driver,
        parking_zone: ParkingZone,
        normalize_current_fee: float = 10.0,
        normalize_distance: float = 100.0
    ) -> float:
        """
        Calculate a score for a parking lot from driver's perspective.
        Lower score is better (driver prefers this lot).
        
        Args:
            driver: The driver making the decision
            parking_zone: The parking lot being evaluated
            normalize_current_fee: Normalization factor for current_fee
            normalize_distance: Normalization factor for distances
        
        Returns:
            Score value (lower is better)
        """
        # current_fee component (normalized)
        current_fee_score = float(parking_zone.current_fee) / normalize_current_fee
        
        # Distance from driver's current position to parking lot
        distance_to_lot = self._calculate_distance(driver.starting_position, parking_zone.position)
        distance_to_lot_score = distance_to_lot / normalize_distance
        
        # Walking distance from parking lot to final destination
        walking_distance = parking_zone.distance_to_point(driver.destination)
        walking_distance_score = walking_distance / normalize_distance
        
        # Availability penalty (penalize lots that are almost full)
        availability_penalty = parking_zone.occupancy_rate()
        
        # Weighted sum
        total_score = (
            self.current_fee_weight * current_fee_score +
            self.distance_to_lot_weight * distance_to_lot_score +
            self.walking_distance_weight * walking_distance_score +
            self.availability_weight * availability_penalty
        )
        
        return total_score
    
    def select_parking_zone(
        self,
        driver: Driver,
        available_lots: List[ParkingZone]
    ) -> Optional[ParkingZone]:
        """
        Select the best parking lot for a driver based on multiple factors.
        
        Args:
            driver: The driver making the decision
            available_lots: List of available parking lots (not full)
        
        Returns:
            Selected parking lot or None if no acceptable lot found
        """
        if not available_lots:
            return None
        
        # Filter lots that driver can afford
        affordable_lots = [
            lot for lot in available_lots
            if lot.current_fee <= driver.max_parking_current_fee
        ]
        
        if not affordable_lots:
            return None
        
        # Find lot with minimum score
        best_lot = None
        best_score = float('inf')
        
        for lot in affordable_lots:
            score = self.calculate_lot_score(driver, lot)
            if score < best_score:
                best_score = score
                best_lot = lot
        
        return best_lot
    
    @staticmethod
    def _calculate_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two points."""
        return ((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2) ** 0.5


class ParkingSimulation:
    """
    Main simulation engine for parking lot optimization.
    """
    
    def __init__(
        self,
        decision_maker: Optional[DriverDecision] = None,
        rejection_penalty: float = 100.0
    ):
        """
        Initialize the simulation engine.
        
        Args:
            decision_maker: Decision logic for drivers (uses default if None)
            rejection_penalty: Cost penalty for drivers who can't find parking
        """
        self.decision_maker = decision_maker or DriverDecision()
        self.rejection_penalty = rejection_penalty
    
    def run_simulation(
        self,
        city: City,
        drivers: List[Driver],
        reset_capacity: bool = True
    ) -> SimulationMetrics:
        """
        Run a complete parking simulation.
        
        Args:
            city: City model with parking lots
            drivers: List of drivers seeking parking
            reset_capacity: Whether to reset parking lot capacities before simulation
        
        Returns:
            SimulationMetrics object with all collected metrics
        """
        # Create a deep copy to avoid modifying original city
        city_copy = deepcopy(city)
        
        # Reset parking lot capacities if requested
        if reset_capacity:
            for lot in city_copy.parking_zones:
                lot.current_capacity = 0
        
        # Initialize metrics tracking
        total_revenue = 0.0
        total_driver_cost = 0.0
        total_walking_distance = 0.0
        parked_count = 0
        rejected_count = 0
        lot_revenues: Dict[int, float] = {lot.id: 0.0 for lot in city_copy.parking_zones}
        
        # Simulate each driver
        for driver in drivers:
            # Get available lots
            available_lots = [lot for lot in city_copy.parking_zones if not lot.is_full()]
            
            # Driver selects best lot
            selected_lot = self.decision_maker.select_parking_zone(driver, available_lots)
            
            if selected_lot:
                # Successfully parked
                selected_lot.current_capacity += 1
                
                # Calculate costs
                parking_cost = selected_lot.current_fee * driver.desired_parking_time / 60
                walking_distance = selected_lot.distance_to_point(driver.destination)
                
                # Update metrics
                total_revenue += parking_cost
                lot_revenues[selected_lot.id] += parking_cost
                total_driver_cost += parking_cost
                total_walking_distance += walking_distance
                parked_count += 1
            else:
                # No suitable parking found
                rejected_count += 1
                total_driver_cost += self.rejection_penalty
        
        # Calculate aggregate metrics
        total_drivers = len(drivers)
        
        # Occupancy metrics
        occupancy_rates = [lot.occupancy_rate() for lot in city_copy.parking_zones]
        occupancy_variance = statistics.variance(occupancy_rates) if len(occupancy_rates) > 1 else 0.0
        occupancy_std_dev = statistics.stdev(occupancy_rates) if len(occupancy_rates) > 1 else 0.0
        
        # Build lot-specific metrics
        lot_occupancy_rates = {lot.id: lot.occupancy_rate() for lot in city_copy.parking_zones}
        
        # Construct metrics object
        metrics = SimulationMetrics(
            total_revenue=total_revenue,
            average_revenue_per_lot=total_revenue / len(city_copy.parking_zones) if city_copy.parking_zones else 0.0,
            total_parked=parked_count,
            total_rejected=rejected_count,
            overall_occupancy_rate=city_copy.city_occupancy_rate(),
            occupancy_variance=occupancy_variance,
            occupancy_std_dev=occupancy_std_dev,
            average_driver_cost=total_driver_cost / total_drivers if total_drivers > 0 else 0.0,
            average_walking_distance=total_walking_distance / parked_count if parked_count > 0 else 0.0,
            average_current_fee_paid=total_revenue / parked_count if parked_count > 0 else 0.0,
            utilization_rate=city_copy.city_occupancy_rate(),
            rejection_rate=rejected_count / total_drivers if total_drivers > 0 else 0.0,
            lot_occupancy_rates=lot_occupancy_rates,
            lot_revenues=lot_revenues
        )
        
        return metrics
    
    def evaluate_current_fee_configuration(
        self,
        city: City,
        drivers: List[Driver],
        current_fee_vector: List[float],
        objectives: List[str] = None
    ) -> Dict[str, float]:
        """
        Evaluate a specific current_fee configuration for optimization algorithms.
        This is the interface that NSGA-II or other optimizers would call.
        
        Args:
            city: City model
            drivers: List of drivers
            current_fee_vector: List of current_fees for each parking lot (ordered by lot ID)
            objectives: List of objective names to return (None = all)
        
        Returns:
            Dictionary of objective values
        """
        # Create city copy and apply current_fees
        city_copy = deepcopy(city)
        sorted_lots = sorted(city_copy.parking_zones, key=lambda x: x.id)
        
        if len(current_fee_vector) != len(sorted_lots):
            raise ValueError(f"current_fee vector length {len(current_fee_vector)} doesn't match parking lot count {len(sorted_lots)}")
        
        for lot, current_fee in zip(sorted_lots, current_fee_vector):
            lot.current_fee = current_fee
        
        # Run simulation
        metrics = self.run_simulation(city_copy, drivers, reset_capacity=True)
        
        # Define available objectives
        all_objectives = {
            'revenue': float(metrics.total_revenue),
            'negative_revenue': -float(metrics.total_revenue),  # For minimization
            'occupancy_variance': metrics.occupancy_variance,
            'avg_driver_cost': float(metrics.average_driver_cost),
            'rejection_rate': metrics.rejection_rate,
            'occupancy_std_dev': metrics.occupancy_std_dev,
            'utilization_rate': metrics.utilization_rate,
            'negative_utilization': -metrics.utilization_rate  # For minimization
        }
        
        # Return requested objectives or all
        if objectives:
            return {obj: all_objectives[obj] for obj in objectives if obj in all_objectives}
        return all_objectives


class SimulationBatch:
    """
    Handles multiple simulation runs with different configurations.
    Useful for stochastic simulations or sensitivity analysis.
    """
    
    def __init__(self, simulation: ParkingSimulation):
        """
        Initialize batch simulator.
        
        Args:
            simulation: ParkingSimulation instance to use
        """
        self.simulation = simulation
    
    def run_multiple_simulations(
        self,
        city: City,
        driver_sets: List[List[Driver]],
        current_fee_vector: Optional[List[float]] = None
    ) -> List[SimulationMetrics]:
        """
        Run multiple simulations with different driver sets.
        
        Args:
            city: City model
            driver_sets: List of driver lists (each is one simulation run)
            current_fee_vector: Optional current_fee configuration to apply
        
        Returns:
            List of SimulationMetrics for each run
        """
        results = []
        
        for drivers in driver_sets:
            if current_fee_vector:
                city_copy = deepcopy(city)
                sorted_lots = sorted(city_copy.parking_zones, key=lambda x: x.id)
                for lot, current_fee in zip(sorted_lots, current_fee_vector):
                    lot.current_fee = current_fee
                metrics = self.simulation.run_simulation(city_copy, drivers)
            else:
                metrics = self.simulation.run_simulation(city, drivers)
            
            results.append(metrics)
        
        return results
    
    def average_metrics(self, metrics_list: List[SimulationMetrics]) -> Dict[str, float]:
        """
        Calculate average metrics across multiple simulation runs.
        
        Args:
            metrics_list: List of SimulationMetrics from multiple runs
        
        Returns:
            Dictionary of averaged metric values
        """
        if not metrics_list:
            return {}
        
        n = len(metrics_list)
        
        return {
            'avg_revenue': sum(float(m.total_revenue) for m in metrics_list) / n,
            'avg_occupancy_variance': sum(m.occupancy_variance for m in metrics_list) / n,
            'avg_driver_cost': sum(float(m.average_driver_cost) for m in metrics_list) / n,
            'avg_rejection_rate': sum(m.rejection_rate for m in metrics_list) / n,
            'avg_utilization': sum(m.utilization_rate for m in metrics_list) / n,
            'std_revenue': statistics.stdev([float(m.total_revenue) for m in metrics_list]) if n > 1 else 0.0,
            'std_occupancy_variance': statistics.stdev([m.occupancy_variance for m in metrics_list]) if n > 1 else 0.0
        }
