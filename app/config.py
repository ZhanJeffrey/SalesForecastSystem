from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "销量分析与预测系统"
    secret_key: str = "sales-forecast-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    database_url: str = "sqlite:///./data/sales.db"
    upload_dir: str = "./data/uploads"

    class Config:
        env_file = ".env"


settings = Settings()
