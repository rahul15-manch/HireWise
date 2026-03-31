import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

def robust_fix_url(url):
    if not url or url.startswith("sqlite"):
        return url
    
    # Fix 'postgres://' which SQLAlchemy 1.4+ doesn't like
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    # Handle special characters in password (like #, !, %)
    # Standard urlparse can fail if the password contains '#'
    try:
        from urllib.parse import quote_plus
        if "://" in url and "@" in url:
            scheme, rest = url.split("://", 1)
            # Split from the right to handle '@' in passwords if any (though rare)
            # and to correctly identify the start of the host
            auth, host_path = rest.rsplit("@", 1)
            if ":" in auth:
                user, password = auth.split(":", 1)
                # Reconstruct with encoded password
                url = f"{scheme}://{user}:{quote_plus(password)}@{host_path}"
    except Exception as e:
        print(f"URL encoding warning: {e}")
    
    # Supabase specific: use port 6543 for transaction mode if it's a supabase host
    # This helps avoid 'Max Clients' errors in serverless environments
    if "supabase.co" in url and ":5432" in url:
        url = url.replace(":5432", ":6543")
    
    # Ensure SSL mode is present for Supabase
    if "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url += f"{separator}sslmode=require"
    
    return url

# Get database URL from environment or fallback to SQLite
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Use absolute path for SQLite to avoid issues on Vercel
    DATABASE_URL = "sqlite:////tmp/hirewise.db"

engine_url = robust_fix_url(DATABASE_URL)

# For PostgreSQL, we don't need check_same_thread
connect_args = {}
if engine_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(engine_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
