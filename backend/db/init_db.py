from .database import Base, engine
from .models import SimulationResult


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
