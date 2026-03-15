from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Connection string: dialect+driver://user:password@host:port/dbname
# These values match what we defined in docker-compose.yaml
DATABASE_URL = "postgresql://admin:admin_password@localhost:5432/hoopsquant"

# The engine is the actual connection to the PostgreSQL database.
# echo=True prints every SQL query SQLAlchemy runs — useful for learning!
engine = create_engine(DATABASE_URL, echo=True)

# SessionLocal is a factory that creates individual database sessions.
# autocommit=False: changes are NOT saved automatically — we call session.commit() manually
# autoflush=False: pending changes are NOT sent to DB until explicitly needed
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base is the parent class all our models will inherit from.
# SQLAlchemy uses it to track which tables to create.
class Base(DeclarativeBase):
    pass
