import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "libsql://my-portfolio-db-sushil-99.aws-ap-south-1.turso.io")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@JobDisha2026!")
ADMIN_CONTACT_NAME = os.getenv("ADMIN_CONTACT_NAME", "Sushil (Portal Owner)")
ADMIN_CONTACT_PHONE = os.getenv("ADMIN_CONTACT_PHONE", "")
SECRET_KEY = os.getenv("SECRET_KEY", "jobdisha_fastapi_secure_secret_key_change_in_production_32chars")
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")
GOOGLE_SITE_VERIFICATION = os.getenv("GOOGLE_SITE_VERIFICATION", "").strip()

