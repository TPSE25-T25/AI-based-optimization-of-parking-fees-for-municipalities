"""
Parking simulation service for optimizing parking lot current_fees.
This module simulates driver behavior in a city with multiple parking lots.
"""

from typing import List, Dict, Tuple, Optional
import statistics
from copy import deepcopy  # Only used in SimulationBatch for multiple independent runs
from pydantic import BaseModel, Field
import numpy as np

from backend.services.models.city import City, ParkingZone
from backend.services.models.driver import Driver
from backend.services.simulation.parallel_engine import ParallelEngine, ComputeBackend


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

class DriverDecision:
    """
    Encapsulates the decision-making logic for a driver selecting a parking lot.
    Supports both single-driver and batch processing with parallel computation.
    """
    
    def __init__(
        self,
        fee_weight: float = 1.0,
        distance_to_lot_weight: float = 0.5,
        walking_distance_weight: float = 1.5,
        availability_weight: float = 0.3,
        parallel_engine: Optional[ParallelEngine] = None
    ):
        """
        Initialize driver decision weights.
        
        Args:
            current_fee_weight: Weight for parking current_fee consideration
            distance_to_lot_weight: Weight for driving distance to lot
            walking_distance_weight: Weight for walking from lot to destination
            availability_weight: Weight for lot availability (penalty for fuller lots)
            parallel_engine: Optional parallel engine (auto-created if None)
        """
        self.current_fee_weight = fee_weight
        self.distance_to_lot_weight = distance_to_lot_weight
        self.walking_distance_weight = walking_distance_weight
        self.availability_weight = availability_weight
        self.parallel_engine = parallel_engine or ParallelEngine()
    
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
    
    def select_parking_zones_batch(
        self,
        drivers: List[Driver],
        parking_zones: List[ParkingZone],
        normalize_fee: float = 10.0,
        normalize_distance: float = 100.0,
        driver_positions: Optional[np.ndarray] = None,
        driver_destinations: Optional[np.ndarray] = None,
        driver_max_fees: Optional[np.ndarray] = None,
        lot_positions: Optional[np.ndarray] = None
    ) -> List[Optional[int]]:
        """
        Select parking lots for multiple drivers in parallel.
        This is the performance-optimized version using vectorization/CUDA.
        Accepts pre-computed numpy arrays to avoid repeated conversions.
        
        Args:
            drivers: List of drivers making decisions
            parking_zones: List of all parking zones
            normalize_fee: Normalization factor for fees
            normalize_distance: Normalization factor for distances
            driver_positions: Pre-computed positions array (optional, computed if None)
            driver_destinations: Pre-computed destinations array (optional)
            driver_max_fees: Pre-computed max fees array (optional)
            lot_positions: Pre-computed lot positions array (optional)
        
        Returns:
            List of selected lot indices (None if no suitable lot found)
        """
        if not drivers or not parking_zones:
            return [None] * len(drivers)
        
        n_drivers = len(drivers)
        n_lots = len(parking_zones)
        
        # Use pre-computed arrays if provided, otherwise compute them
        if driver_positions is None:
            driver_positions = np.array([d.starting_position for d in drivers], dtype=np.float32)
        if driver_destinations is None:
            driver_destinations = np.array([d.destination for d in drivers], dtype=np.float32)
        if driver_max_fees is None:
            driver_max_fees = np.array([d.max_parking_current_fee for d in drivers], dtype=np.float32)
        if lot_positions is None:
            lot_positions = np.array([z.position for z in parking_zones], dtype=np.float32)
        lot_fees = np.array([z.current_fee for z in parking_zones], dtype=np.float32)
        lot_occupancy = np.array([z.occupancy_rate() for z in parking_zones], dtype=np.float32)
        
        # Compute all driver-lot scores in parallel
        scores = self.parallel_engine.compute_driver_lot_scores(
            driver_positions=driver_positions,
            driver_destinations=driver_destinations,
            driver_max_fees=driver_max_fees,
            lot_positions=lot_positions,
            lot_fees=lot_fees,
            lot_occupancy=lot_occupancy,
            fee_weight=self.current_fee_weight,
            distance_to_lot_weight=self.distance_to_lot_weight,
            walking_distance_weight=self.walking_distance_weight,
            availability_weight=self.availability_weight,
            normalize_fee=normalize_fee,
            normalize_distance=normalize_distance
        )
        
        # Also mask out full lots
        lot_is_full = np.array([z.is_full() for z in parking_zones])
        scores[:, lot_is_full] = np.inf
        
        # Select best lot for each driver (minimum score)
        best_lot_indices = np.argmin(scores, axis=1)
        
        # Convert to list, replacing invalid choices with None
        result = []
        for i, lot_idx in enumerate(best_lot_indices):
            if scores[i, lot_idx] == np.inf:
                result.append(None)
            else:
                result.append(int(lot_idx))
        
        return result
    
    @staticmethod
    def _calculate_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two points."""
        return ((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2) ** 0.5


class ParkingSimulation:
    """
    Main simulation engine for parking lot optimization.
    Supports both sequential and parallel batch processing.
    Optimized to avoid expensive deep copies during optimization.
    """
    
    def __init__(
        self,
        decision_maker: Optional[DriverDecision] = None,
        rejection_penalty: float = 100.0,
        use_batch_processing: bool = True,
        batch_size: int = 500
    ):
        """
        Initialize the simulation engine.
        
        Args:
            decision_maker: Decision logic for drivers (uses default if None)
            rejection_penalty: Cost penalty for drivers who can't find parking
            use_batch_processing: Whether to use parallel batch processing (recommended for >1000 drivers)
            batch_size: Number of drivers to process in each batch
        """
        self.decision_maker = decision_maker or DriverDecision()
        self.rejection_penalty = rejection_penalty
        self.use_batch_processing = use_batch_processing
        self.batch_size = batch_size
    
    def run_simulation(
        self,
        city: City,
        drivers: List[Driver],
        reset_capacity: bool = True
    ) -> SimulationMetrics:
        """
        Run a complete parking simulation.
        Automatically chooses between batch and sequential processing.
        
        Args:
            city: City model with parking lots
            drivers: List of drivers seeking parking
            reset_capacity: Whether to reset parking lot capacities before simulation
        
        Returns:
            SimulationMetrics object with all collected metrics
        """
        # Use batch processing for any dataset size during optimization
        # Batch processing uses vectorized NumPy operations which are much faster
        # than Python loops, even for small datasets
        if self.use_batch_processing:
            return self._run_simulation_batch(city, drivers, reset_capacity)
        else:
            return self._run_simulation_sequential(city, drivers, reset_capacity)
    
    def _run_simulation_sequential(
        self,
        city: City,
        drivers: List[Driver],
        reset_capacity: bool = True
    ) -> SimulationMetrics:
        """
        Optimized sequential simulation without expensive deep copies.
        Uses lightweight capacity tracking instead of copying entire city.
        
        Args:
            city: City model with parking lots
            drivers: List of drivers seeking parking
            reset_capacity: Whether to reset parking lot capacities before simulation
        
        Returns:
            SimulationMetrics object with all collected metrics
        """
        # Use lightweight capacity tracking instead of deep copy
        original_capacities = [lot.current_capacity for lot in city.parking_zones]
        
        # Reset parking lot capacities if requested
        if reset_capacity:
            for lot in city.parking_zones:
                lot.current_capacity = 0
        
        # Initialize metrics tracking
        total_revenue = 0.0
        total_driver_cost = 0.0
        total_walking_distance = 0.0
        parked_count = 0
        rejected_count = 0
        lot_revenues: Dict[int, float] = {lot.id: 0.0 for lot in city.parking_zones}
        
        # Simulate each driver
        for driver in drivers:
            # Get available lots
            available_lots = [lot for lot in city.parking_zones if not lot.is_full()]
            
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
        
        # Build metrics before restoring capacities
        metrics = self._build_metrics(
            city, drivers, total_revenue, total_driver_cost,
            total_walking_distance, parked_count, rejected_count, lot_revenues
        )
        
        # Restore original capacities
        for lot, orig_capacity in zip(city.parking_zones, original_capacities):
            lot.current_capacity = orig_capacity
        
        return metrics
    
    def _run_simulation_batch(
        self,
        city: City,
        drivers: List[Driver],
        reset_capacity: bool = True
    ) -> SimulationMetrics:
        """
        Vectorized batch simulation using NumPy operations.
        Much faster than sequential for ANY dataset size due to vectorization.
        Process all drivers in batches using parallel score computation.
        
        Args:
            city: City model with parking lots
            drivers: List of drivers seeking parking
            reset_capacity: Whether to reset parking lot capacities before simulation
        
        Returns:
            SimulationMetrics object with all collected metrics
        """
        # Use lightweight capacity tracking instead of deep copy
        original_capacities = [lot.current_capacity for lot in city.parking_zones]
        
        # Reset parking lot capacities if requested
        if reset_capacity:
            for lot in city.parking_zones:
                lot.current_capacity = 0
        
        # Initialize metrics tracking
        total_revenue = 0.0
        total_driver_cost = 0.0
        total_walking_distance = 0.0
        parked_count = 0
        rejected_count = 0
        lot_revenues: Dict[int, float] = {lot.id: 0.0 for lot in city.parking_zones}
        
        # Process drivers in batches
        n_drivers = len(drivers)
        for batch_start in range(0, n_drivers, self.batch_size):
            batch_end = min(batch_start + self.batch_size, n_drivers)
            batch_drivers = drivers[batch_start:batch_end]
            
            # Get parking decisions for entire batch in parallel (vectorized)
            selected_lot_indices = self.decision_maker.select_parking_zones_batch(
                drivers=batch_drivers,
                parking_zones=city.parking_zones,
                driver_positions=None,  # Will be computed (or use cache in optimizer)
                driver_destinations=None,
                driver_max_fees=None,
                lot_positions=None
            )
            
            # Apply decisions sequentially (to respect capacity constraints)
            for driver, lot_idx in zip(batch_drivers, selected_lot_indices):
                if lot_idx is not None:
                    selected_lot = city.parking_zones[lot_idx]
                    
                    # Double-check lot is still available (capacity may have changed)
                    if not selected_lot.is_full():
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
                        # Lot became full in this batch
                        rejected_count += 1
                        total_driver_cost += self.rejection_penalty
                else:
                    # No suitable parking found
                    rejected_count += 1
                    total_driver_cost += self.rejection_penalty
        
        # Build metrics before restoring capacities
        metrics = self._build_metrics(
            city, drivers, total_revenue, total_driver_cost,
            total_walking_distance, parked_count, rejected_count, lot_revenues
        )
        
        # Restore original capacities
        for lot, orig_capacity in zip(city.parking_zones, original_capacities):
            lot.current_capacity = orig_capacity
        
        return metrics
    
    def _build_metrics(
        self,
        city: City,
        drivers: List[Driver],
        total_revenue: float,
        total_driver_cost: float,
        total_walking_distance: float,
        parked_count: int,
        rejected_count: int,
        lot_revenues: Dict[int, float]
    ) -> SimulationMetrics:
        """
        Build SimulationMetrics object from collected data.
        Extracted to avoid code duplication (DRY principle).
        """
        total_drivers = len(drivers)
        
        # Occupancy metrics
        occupancy_rates = [lot.occupancy_rate() for lot in city.parking_zones]
        occupancy_variance = statistics.variance(occupancy_rates) if len(occupancy_rates) > 1 else 0.0
        occupancy_std_dev = statistics.stdev(occupancy_rates) if len(occupancy_rates) > 1 else 0.0
        
        # Build lot-specific metrics
        lot_occupancy_rates = {lot.id: lot.occupancy_rate() for lot in city.parking_zones}
        
        # Construct metrics object
        metrics = SimulationMetrics(
            total_revenue=total_revenue,
            average_revenue_per_lot=total_revenue / len(city.parking_zones) if city.parking_zones else 0.0,
            total_parked=parked_count,
            total_rejected=rejected_count,
            overall_occupancy_rate=city.city_occupancy_rate(),
            occupancy_variance=occupancy_variance,
            occupancy_std_dev=occupancy_std_dev,
            average_driver_cost=total_driver_cost / total_drivers if total_drivers > 0 else 0.0,
            average_walking_distance=total_walking_distance / parked_count if parked_count > 0 else 0.0,
            average_current_fee_paid=total_revenue / parked_count if parked_count > 0 else 0.0,
            utilization_rate=city.city_occupancy_rate(),
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
    Supports parallel execution of multiple simulation runs.
    """
    
    def __init__(self, simulation: ParkingSimulation, n_jobs: int = -1):
        """
        Initialize batch simulator.
        
        Args:
            simulation: ParkingSimulation instance to use
            n_jobs: Number of parallel jobs for running multiple simulations (-1 = all cores)
        """
        self.simulation = simulation
        self.n_jobs = n_jobs
        
        # Check if joblib is available for parallel runs
        try:
            from joblib import Parallel, delayed
            self.parallel_available = True
            self._Parallel = Parallel
            self._delayed = delayed
        except ImportError:  # pragma: no cover
            self.parallel_available = False
    
    def run_multiple_simulations(
        self,
        city: City,
        driver_sets: List[List[Driver]],
        current_fee_vector: Optional[List[float]] = None,
        parallel: bool = True
    ) -> List[SimulationMetrics]:
        """
        Run multiple simulations with different driver sets.
        
        Args:
            city: City model
            driver_sets: List of driver lists (each is one simulation run)
            current_fee_vector: Optional current_fee configuration to apply
            parallel: Whether to run simulations in parallel (requires joblib)
        
        Returns:
            List of SimulationMetrics for each run
        """
        if parallel and self.parallel_available and len(driver_sets) > 1:
            return self._run_parallel(city, driver_sets, current_fee_vector)
        else:
            return self._run_sequential(city, driver_sets, current_fee_vector)
    
    def _run_sequential(
        self,
        city: City,
        driver_sets: List[List[Driver]],
        current_fee_vector: Optional[List[float]] = None
    ) -> List[SimulationMetrics]:
        """Run simulations sequentially."""
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
    
    def _run_parallel(
        self,
        city: City,
        driver_sets: List[List[Driver]],
        current_fee_vector: Optional[List[float]] = None
    ) -> List[SimulationMetrics]:
        """Run simulations in parallel using joblib."""
        
        def run_single(drivers: List[Driver]) -> SimulationMetrics:
            """Helper to run single simulation."""
            if current_fee_vector:
                city_copy = deepcopy(city)
                sorted_lots = sorted(city_copy.parking_zones, key=lambda x: x.id)
                for lot, current_fee in zip(sorted_lots, current_fee_vector):
                    lot.current_fee = current_fee
                return self.simulation.run_simulation(city_copy, drivers)
            else:
                return self.simulation.run_simulation(city, drivers)
        
        # Run in parallel
        results = self._Parallel(n_jobs=self.n_jobs, backend='threading')(
            self._delayed(run_single)(drivers) for drivers in driver_sets
        )
        
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
