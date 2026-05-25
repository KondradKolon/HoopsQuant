import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin_password@localhost:5432/hoopsquant" # Default for local dev if not set
)


# Supabase (will be used in future)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# APIs
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

# Bookmakers (comma-separated; account allows up to 2 active at once on odds-api.io)
BOOKMAKERS: list[str] = []
for part in os.getenv("BOOKMAKERS", "Superbet,Stake").split(","):
    name = part.strip()
    if name:
        BOOKMAKERS.append(name)

# CORS — comma-separated origins, default for local dev + production
_DEFAULT_ORIGINS = "http://localhost:3000,http://localhost:3001,https://hoops-quant.vercel.app,https://hoopsquant.vercel.app"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",")

# Environment
ENV = os.getenv("ENV", "development")
DEBUG = ENV == "development"
