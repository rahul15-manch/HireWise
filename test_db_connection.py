import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("❌ DATABASE_URL not found in .env")
    exit(1)

print(f"Connecting to: {db_url.split('@')[-1]}...") # Safe display

try:
    engine = create_engine(db_url)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print(f"✅ Successfully connected!")
        print(f"Database version: {version}")
except Exception as e:
    print(f"❌ Connection failed!")
    print(f"Error: {e}")
