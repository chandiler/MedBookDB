# app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from config import DB_CONFIG  # import DB configuration from config.py file

# Build the DATABASE_URL connection string from DB_CONFIG
DATABASE_URL = (
    f"postgresql+psycopg://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
)

# Create engine and session
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def init_db():
    Base.metadata.create_all(bind=engine)