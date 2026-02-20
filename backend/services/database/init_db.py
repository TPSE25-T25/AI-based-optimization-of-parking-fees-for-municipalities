from backend.services.database.database import Base, engine

def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":  # pragma: no cover
    init_db()
