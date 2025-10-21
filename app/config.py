# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DB_HOST: str = os.getenv("DB_HOST")
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_DATABASE: str = os.getenv("DB_DATABASE")
    DB_PORT: str = os.getenv("DB_PORT", "1433")
    PORT: str = os.getenv("PORT", "3000")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "secret")

settings = Settings()
