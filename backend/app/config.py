import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin_password@localhost:5432/hoopsquant"
)

# Supabase (will be used in future)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# APIs
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

# Environment
ENV = os.getenv("ENV", "development")
DEBUG = ENV == "development"
