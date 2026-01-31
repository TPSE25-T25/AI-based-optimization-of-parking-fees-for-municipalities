from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.sql import func

from .database import Base


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # JSON: request settings, user weights, metadata
    parameters = Column(JSON, nullable=False)

    # Link/path to map file on disk (later: Blob URL)
    map_path = Column(String(1024), nullable=True)

    # Optional map configuration (center, zoom, tiles, etc.)
    map_config = Column(JSON, nullable=True)

    # Optional snapshot of map data (zones + optimized values)
    map_snapshot = Column(JSON, nullable=True)

    # Optional link/path to CSV export
    csv_path = Column(String(1024), nullable=True)

    # Optional summary of the winning scenario
    best_scenario = Column(JSON, nullable=True)
