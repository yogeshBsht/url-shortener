from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import validator
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server Configuration
    app_name: str = "URL Shortener"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS Configuration
    cors_origins: str = "http://localhost:3000"
    cors_allow_credentials: bool = True
    
    # Database Configuration
    database_host: str
    database_port: int = 5432
    database_name: str
    database_user: str
    database_password: str
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis Configuration
    redis_host: str
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_cache_ttl: int = 86400  # 24 hours
    
    # URL Configuration
    base_url: str = "http://localhost:8000"
    short_code_length: int = 6
    custom_alias_max_length: int = 50
    
    # Feature Flags
    enable_qr_code: bool = True
    enable_analytics: bool = True
    enable_custom_alias: bool = True
    enable_rate_limiting: bool = False
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def database_url(self) -> str:
        """PostgreSQL connection URL."""
        return (
            f"postgresql://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )
    
    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # @property
    # def cors_origins_list(self) -> list:
    #     """Parse CORS origins from comma-separated string."""
    #     allowed_origins = [origin.strip() for origin in self.cors_origins.split(",")]
    #     print(allowed_origins)
    #     return allowed_origins

    # Parsed list — populated by the validator below
    cors_origins_list: List[str] = []

    @validator("cors_origins_list", always=True, pre=True)
    def parse_cors_origins(cls, v, values):
        raw = values.get("cors_origins", "http://localhost:3000")
        parsed = [origin.strip() for origin in raw.split(",")]
        print("CORS origins:", parsed)
        return parsed


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()