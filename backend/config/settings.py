import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    RATE_MODE: str = os.getenv("RATE_MODE", "test").strip().lower()
    if RATE_MODE not in ("test", "live"):
        RATE_MODE = "test"

    # FedEx (Real Sandbox)
    FEDEX_CLIENT_ID: str = os.getenv("FEDEX_CLIENT_ID", "")
    FEDEX_CLIENT_SECRET: str = os.getenv("FEDEX_CLIENT_SECRET", "")
    FEDEX_ACCOUNT_NUMBER: str = os.getenv("FEDEX_ACCOUNT_NUMBER", "")
    FEDEX_BASE_URL: str = os.getenv(
        "FEDEX_BASE_URL",
        "https://apis.fedex.com" if RATE_MODE == "live" else "https://apis-sandbox.fedex.com",
    )

    # Shippo (used for UPS + USPS live rating)
    SHIPPO_API_KEY: str = os.getenv("SHIPPO_API_KEY", "")

    # LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # App
    APP_ENV: str = os.getenv("APP_ENV", "development")
    _origins_env: str = os.getenv("ALLOWED_ORIGINS", "").strip()
    if _origins_env:
        ALLOWED_ORIGINS: list = [o.strip() for o in _origins_env.split(",") if o.strip()]
    else:
        ALLOWED_ORIGINS: list = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
        ]

settings = Settings()
