import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
# Locate the root project directory
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the project's .env
load_dotenv(PROJECT_DIR / ".env")

def get_engine():
    """Create and return a PostgreSQL database engine."""
    required_variables = ["DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing_variables = [variable for variable in required_variables if not os.getenv(variable)]

    if missing_variables:
        raise ValueError("Missing database configuration in .env: "+ ", ".join(missing_variables))

    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
    )
    return create_engine(database_url)


def test_connection():
    """Check whether the database connection works."""
    engine = get_engine()

    try:
        with engine.connect() as connection:
            database_name = connection.execute(text("SELECT current_database()")).scalar()
            print(f"Successfully connected to database: {database_name}")
    except Exception as error:
        print(f"Database connection failed: {error}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    test_connection()
