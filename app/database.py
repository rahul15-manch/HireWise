from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////tmp/hirewise.db")

# If using PostgreSQL with a 'postgres://' URL (common on some platforms), 
# fix it to 'postgresql://' for SQLAlchemy compatibility.
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Re-encode specifically for PostgreSQL or add SSL if needed
if "postgresql" in SQLALCHEMY_DATABASE_URL:
    # 1. Supabase specific fix: Use Transaction Pooler (port 6543) for serverless
    if "supabase.co" in SQLALCHEMY_DATABASE_URL and ":5432" in SQLALCHEMY_DATABASE_URL:
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(":5432", ":6543")
    
    # 2. Add SSL require
    if "sslmode" not in SQLALCHEMY_DATABASE_URL:
        if "?" in SQLALCHEMY_DATABASE_URL:
            SQLALCHEMY_DATABASE_URL += "&sslmode=require"
        else:
            SQLALCHEMY_DATABASE_URL += "?sslmode=require"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    # Only use check_same_thread for SQLite
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {},
    # Good for serverless reconnections
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
