"""
Parallel computation engine for parking simulation.
Automatically detects and uses CUDA, multi-threading, or CPU based on availability.
"""

import numpy as np
from typing import Tuple, Optional
from enum import Enum
import warnings

# Try importing CUDA support
try:
    from numba import cuda, float32, int32
    CUDA_AVAILABLE = cuda.is_available()
except (ImportError, Exception):
    CUDA_AVAILABLE = False
    cuda = None

# Joblib for CPU parallelization
try:
    from joblib import Parallel, delayed
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False


class ComputeBackend(Enum):
    """Available computation backends."""
    CUDA = "cuda"
    CPU_PARALLEL = "cpu_parallel"
    CPU_SERIAL = "cpu_serial"


class ParallelEngine:
    """
    Manages parallel computation with automatic backend selection.
    Prioritizes: CUDA > Multi-threaded CPU > Serial CPU
    """
    
    def __init__(self, backend: Optional[ComputeBackend] = None, n_jobs: int = -1):
        """
        Initialize parallel engine.
        
        Args:
            backend: Force specific backend (None = auto-detect)
            n_jobs: Number of parallel jobs for CPU (-1 = all cores)
        """
        self.n_jobs = n_jobs
        
        # Auto-detect best available backend
        if backend is None:
            if CUDA_AVAILABLE:
                self.backend = ComputeBackend.CUDA
            elif JOBLIB_AVAILABLE:
                self.backend = ComputeBackend.CPU_PARALLEL
            else:
                self.backend = ComputeBackend.CPU_SERIAL
        else:
            self.backend = backend
            
        # Validate backend availability
        if self.backend == ComputeBackend.CUDA and not CUDA_AVAILABLE:
            warnings.warn("CUDA requested but not available. Falling back to CPU.")
            self.backend = ComputeBackend.CPU_PARALLEL if JOBLIB_AVAILABLE else ComputeBackend.CPU_SERIAL
        
        if self.backend == ComputeBackend.CPU_PARALLEL and not JOBLIB_AVAILABLE:
            warnings.warn("Parallel CPU requested but joblib not available. Using serial.")
            self.backend = ComputeBackend.CPU_SERIAL
    
    def get_backend_info(self) -> dict:
        """Get information about current backend."""
        return {
            "backend": self.backend.value,
            "cuda_available": CUDA_AVAILABLE,
            "joblib_available": JOBLIB_AVAILABLE,
            "n_jobs": self.n_jobs if self.backend == ComputeBackend.CPU_PARALLEL else 1
        }
    
    def compute_driver_lot_scores(
        self,
        driver_positions: np.ndarray,
        driver_destinations: np.ndarray,
        driver_max_fees: np.ndarray,
        lot_positions: np.ndarray,
        lot_fees: np.ndarray,
        lot_occupancy: np.ndarray,
        fee_weight: float,
        distance_to_lot_weight: float,
        walking_distance_weight: float,
        availability_weight: float,
        normalize_fee: float = 10.0,
        normalize_distance: float = 100.0
    ) -> np.ndarray:
        """
        Compute scores for all driver-lot combinations in parallel.
        
        Args:
            driver_positions: (n_drivers, 2) array of driver starting positions
            driver_destinations: (n_drivers, 2) array of driver destinations
            driver_max_fees: (n_drivers,) array of max fees drivers will pay
            lot_positions: (n_lots, 2) array of lot positions
            lot_fees: (n_lots,) array of lot fees
            lot_occupancy: (n_lots,) array of lot occupancy rates
            *_weight: Weight parameters
            normalize_*: Normalization parameters
            
        Returns:
            (n_drivers, n_lots) array of scores (lower is better, inf if unaffordable)
        """
        if self.backend == ComputeBackend.CUDA:
            return self._compute_cuda(
                driver_positions, driver_destinations, driver_max_fees,
                lot_positions, lot_fees, lot_occupancy,
                fee_weight, distance_to_lot_weight, walking_distance_weight,
                availability_weight, normalize_fee, normalize_distance
            )
        elif self.backend == ComputeBackend.CPU_PARALLEL:
            return self._compute_cpu_parallel(
                driver_positions, driver_destinations, driver_max_fees,
                lot_positions, lot_fees, lot_occupancy,
                fee_weight, distance_to_lot_weight, walking_distance_weight,
                availability_weight, normalize_fee, normalize_distance
            )
        else:
            return self._compute_cpu_vectorized(
                driver_positions, driver_destinations, driver_max_fees,
                lot_positions, lot_fees, lot_occupancy,
                fee_weight, distance_to_lot_weight, walking_distance_weight,
                availability_weight, normalize_fee, normalize_distance
            )
    
    def _compute_cpu_vectorized(
        self,
        driver_positions: np.ndarray,
        driver_destinations: np.ndarray,
        driver_max_fees: np.ndarray,
        lot_positions: np.ndarray,
        lot_fees: np.ndarray,
        lot_occupancy: np.ndarray,
        fee_weight: float,
        distance_to_lot_weight: float,
        walking_distance_weight: float,
        availability_weight: float,
        normalize_fee: float,
        normalize_distance: float
    ) -> np.ndarray:
        """
        Vectorized NumPy computation (baseline, fastest for small datasets).
        """
        n_drivers = driver_positions.shape[0]
        n_lots = lot_positions.shape[0]
        
        # Broadcast to compute all combinations
        # Shape: (n_drivers, 1, 2) vs (1, n_lots, 2)
        driver_pos = driver_positions[:, np.newaxis, :]  # (n_drivers, 1, 2)
        driver_dest = driver_destinations[:, np.newaxis, :]  # (n_drivers, 1, 2)
        lot_pos = lot_positions[np.newaxis, :, :]  # (1, n_lots, 2)
        
        # Distance from driver to lot (n_drivers, n_lots)
        dist_to_lot = np.sqrt(np.sum((driver_pos - lot_pos) ** 2, axis=2))
        
        # Walking distance from lot to destination (n_drivers, n_lots)
        walking_dist = np.sqrt(np.sum((lot_pos - driver_dest) ** 2, axis=2))
        
        # Fee score (normalized) - broadcast lot_fees to (n_drivers, n_lots)
        fee_score = lot_fees[np.newaxis, :] / normalize_fee
        
        # Distance scores (normalized)
        dist_to_lot_score = dist_to_lot / normalize_distance
        walking_dist_score = walking_dist / normalize_distance
        
        # Availability penalty - broadcast occupancy
        availability_penalty = lot_occupancy[np.newaxis, :]
        
        # Total score
        scores = (
            fee_weight * fee_score +
            distance_to_lot_weight * dist_to_lot_score +
            walking_distance_weight * walking_dist_score +
            availability_weight * availability_penalty
        )
        
        # Mask unaffordable lots (set score to infinity)
        # driver_max_fees shape: (n_drivers,) -> (n_drivers, 1)
        # lot_fees shape: (n_lots,) -> (1, n_lots)
        unaffordable = driver_max_fees[:, np.newaxis] < lot_fees[np.newaxis, :]
        scores[unaffordable] = np.inf
        
        return scores
    
    def _compute_cpu_parallel(
        self,
        driver_positions: np.ndarray,
        driver_destinations: np.ndarray,
        driver_max_fees: np.ndarray,
        lot_positions: np.ndarray,
        lot_fees: np.ndarray,
        lot_occupancy: np.ndarray,
        fee_weight: float,
        distance_to_lot_weight: float,
        walking_distance_weight: float,
        availability_weight: float,
        normalize_fee: float,
        normalize_distance: float
    ) -> np.ndarray:
        """
        Parallel CPU computation using joblib (for very large datasets).
        Splits drivers into chunks and processes in parallel.
        """
        n_drivers = driver_positions.shape[0]
        
        # For smaller datasets, vectorized is much faster due to overhead
        # Parallelization only helps with 5000+ drivers
        if n_drivers < 5000:
            return self._compute_cpu_vectorized(
                driver_positions, driver_destinations, driver_max_fees,
                lot_positions, lot_fees, lot_occupancy,
                fee_weight, distance_to_lot_weight, walking_distance_weight,
                availability_weight, normalize_fee, normalize_distance
            )
        
        # Chunk size for parallel processing
        chunk_size = max(100, n_drivers // (self.n_jobs * 4)) if self.n_jobs > 0 else 100
        
        def process_chunk(start_idx: int, end_idx: int) -> np.ndarray:
            """Process a chunk of drivers."""
            return self._compute_cpu_vectorized(
                driver_positions[start_idx:end_idx],
                driver_destinations[start_idx:end_idx],
                driver_max_fees[start_idx:end_idx],
                lot_positions, lot_fees, lot_occupancy,
                fee_weight, distance_to_lot_weight, walking_distance_weight,
                availability_weight, normalize_fee, normalize_distance
            )
        
        # Split into chunks and process in parallel
        chunks = [(i, min(i + chunk_size, n_drivers)) 
                  for i in range(0, n_drivers, chunk_size)]
        
        results = Parallel(n_jobs=self.n_jobs, backend='threading')(
            delayed(process_chunk)(start, end) for start, end in chunks
        )
        
        return np.vstack(results)
    
    def _compute_cuda(
        self,
        driver_positions: np.ndarray,
        driver_destinations: np.ndarray,
        driver_max_fees: np.ndarray,
        lot_positions: np.ndarray,
        lot_fees: np.ndarray,
        lot_occupancy: np.ndarray,
        fee_weight: float,
        distance_to_lot_weight: float,
        walking_distance_weight: float,
        availability_weight: float,
        normalize_fee: float,
        normalize_distance: float
    ) -> np.ndarray:
        """
        CUDA GPU computation for massive parallelization.
        Optimal for very large driver/lot counts.
        """
        n_drivers = driver_positions.shape[0]
        n_lots = lot_positions.shape[0]
        
        # Allocate result array
        scores = np.zeros((n_drivers, n_lots), dtype=np.float32)
        
        # Transfer data to GPU
        d_driver_pos = cuda.to_device(driver_positions.astype(np.float32))
        d_driver_dest = cuda.to_device(driver_destinations.astype(np.float32))
        d_driver_max_fees = cuda.to_device(driver_max_fees.astype(np.float32))
        d_lot_pos = cuda.to_device(lot_positions.astype(np.float32))
        d_lot_fees = cuda.to_device(lot_fees.astype(np.float32))
        d_lot_occupancy = cuda.to_device(lot_occupancy.astype(np.float32))
        d_scores = cuda.to_device(scores)
        
        # Define thread/block dimensions
        threads_per_block = (16, 16)  # 256 threads per block
        blocks_x = (n_drivers + threads_per_block[0] - 1) // threads_per_block[0]
        blocks_y = (n_lots + threads_per_block[1] - 1) // threads_per_block[1]
        blocks_per_grid = (blocks_x, blocks_y)
        
        # Launch kernel
        _cuda_compute_scores[blocks_per_grid, threads_per_block](
            d_driver_pos, d_driver_dest, d_driver_max_fees,
            d_lot_pos, d_lot_fees, d_lot_occupancy,
            d_scores, n_drivers, n_lots,
            fee_weight, distance_to_lot_weight, walking_distance_weight,
            availability_weight, normalize_fee, normalize_distance
        )
        
        # Transfer results back to CPU
        d_scores.copy_to_host(scores)
        
        return scores


# CUDA kernel (only compiled if CUDA is available)
if CUDA_AVAILABLE:
    @cuda.jit
    def _cuda_compute_scores(
        driver_pos, driver_dest, driver_max_fees,
        lot_pos, lot_fees, lot_occupancy,
        scores, n_drivers, n_lots,
        fee_weight, dist_to_lot_weight, walking_dist_weight,
        availability_weight, norm_fee, norm_dist
    ):
        """
        CUDA kernel to compute driver-lot scores.
        Each thread computes one driver-lot pair.
        """
        driver_idx = cuda.blockIdx.x * cuda.blockDim.x + cuda.threadIdx.x
        lot_idx = cuda.blockIdx.y * cuda.blockDim.y + cuda.threadIdx.y
        
        if driver_idx < n_drivers and lot_idx < n_lots:
            # Check affordability
            if driver_max_fees[driver_idx] < lot_fees[lot_idx]:
                scores[driver_idx, lot_idx] = float32(np.inf)
                return
            
            # Distance from driver to lot
            dx1 = driver_pos[driver_idx, 0] - lot_pos[lot_idx, 0]
            dy1 = driver_pos[driver_idx, 1] - lot_pos[lot_idx, 1]
            dist_to_lot = float32((dx1 * dx1 + dy1 * dy1) ** 0.5)
            
            # Walking distance from lot to destination
            dx2 = lot_pos[lot_idx, 0] - driver_dest[driver_idx, 0]
            dy2 = lot_pos[lot_idx, 1] - driver_dest[driver_idx, 1]
            walking_dist = float32((dx2 * dx2 + dy2 * dy2) ** 0.5)
            
            # Compute score components
            fee_score = lot_fees[lot_idx] / norm_fee
            dist_to_lot_score = dist_to_lot / norm_dist
            walking_dist_score = walking_dist / norm_dist
            availability_penalty = lot_occupancy[lot_idx]
            
            # Total score
            score = (
                fee_weight * fee_score +
                dist_to_lot_weight * dist_to_lot_score +
                walking_dist_weight * walking_dist_score +
                availability_weight * availability_penalty
            )
            
            scores[driver_idx, lot_idx] = score
