import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin_password@localhost:5432/hoopsquant" # Default for local dev if not set
)
# IMPORTANT: For Railway deployment with Supabase, use the pgbouncer connection string (port 6543).
# If 'Network is unreachable' errors persist, try adding '?options=-c client_encoding=UTF8&hostaddr=X.X.X.X'
# to force IPv4 connection, where X.X.X.X is the Supabase database's IPv4 address if available.

# Supabase (will be used in future)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# APIs
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

# Environment
ENV = os.getenv("ENV", "development")
DEBUG = ENV == "development"
