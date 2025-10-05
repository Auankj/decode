"""
Production Configuration Management
Environment-based configuration with secrets management and validation
"""
import os
import secrets
from functools import lru_cache
from typing import Optional, List, Any
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Production application settings with environment-based configuration
    All settings are validated and type-safe
    """
    
    # Application Settings
    APP_NAME: str = Field(default="Cookie-Licking Detector", env="APP_NAME")
    APP_VERSION: str = Field(default="1.0.0", env="APP_VERSION")
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")
    
    # Security Settings
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32), env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, env="REFRESH_TOKEN_EXPIRE_DAYS")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    
    # Database Settings
    DATABASE_URL: str = Field(default="postgresql://user:pass@localhost:5432/cookie_detector", env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=10, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    DATABASE_POOL_TIMEOUT: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    DATABASE_POOL_RECYCLE: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")
    DB_ECHO: bool = Field(default=False, env="DB_ECHO")
    
    # Redis Settings
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_MAX_CONNECTIONS: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    REDIS_SOCKET_TIMEOUT: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(default=5, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    
    # Celery Settings
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    CELERY_TASK_SERIALIZER: str = Field(default="json", env="CELERY_TASK_SERIALIZER")
    CELERY_RESULT_SERIALIZER: str = Field(default="json", env="CELERY_RESULT_SERIALIZER")
    CELERY_ACCEPT_CONTENT: List[str] = Field(default=["json"], env="CELERY_ACCEPT_CONTENT")
    CELERY_TIMEZONE: str = Field(default="UTC", env="CELERY_TIMEZONE")
    CELERY_ENABLE_UTC: bool = Field(default=True, env="CELERY_ENABLE_UTC")
    
    # GitHub Integration
    GITHUB_TOKEN: Optional[str] = Field(default=None, env="GITHUB_TOKEN")
    GITHUB_APP_ID: Optional[str] = Field(default=None, env="GITHUB_APP_ID")
    GITHUB_APP_PRIVATE_KEY_PATH: Optional[str] = Field(default=None, env="GITHUB_APP_PRIVATE_KEY_PATH")
    GITHUB_WEBHOOK_SECRET: Optional[str] = Field(default=None, env="GITHUB_WEBHOOK_SECRET")
    
    # Ecosyste.ms API Settings
    ECOSYSTE_MS_BASE_URL: str = Field(
        default="https://issues.ecosyste.ms/api/v1", 
        env="ECOSYSTE_MS_BASE_URL"
    )
    ECOSYSTE_MS_EMAIL: Optional[str] = Field(default=None, env="ECOSYSTE_MS_EMAIL")
    ECOSYSTE_MS_RATE_LIMIT: int = Field(default=60, env="ECOSYSTE_MS_RATE_LIMIT")  # per minute
    
    # Notification Settings
    SENDGRID_API_KEY: Optional[str] = Field(default=None, env="SENDGRID_API_KEY")
    FROM_EMAIL: str = Field(default="noreply@cookie-detector.com", env="FROM_EMAIL")
    
    # System Configuration
    DEFAULT_GRACE_PERIOD_DAYS: int = Field(default=7, env="DEFAULT_GRACE_PERIOD_DAYS")
    DEFAULT_NUDGE_COUNT: int = Field(default=2, env="DEFAULT_NUDGE_COUNT")
    CLAIM_DETECTION_THRESHOLD: int = Field(default=75, env="CLAIM_DETECTION_THRESHOLD")
    
    # API Settings
    API_V1_STR: str = Field(default="/api/v1", env="API_V1_STR")
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    API_WORKERS: int = Field(default=1, env="API_WORKERS")
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:8080"], 
        env="ALLOWED_ORIGINS"
    )
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:8080"], 
        env="CORS_ORIGINS"
    )
    ALLOWED_METHODS: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"], env="ALLOWED_METHODS")
    ALLOWED_HEADERS: List[str] = Field(default=["*"], env="ALLOWED_HEADERS")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_BURST: int = Field(default=200, env="RATE_LIMIT_BURST")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")  # json or text
    LOG_FILE: Optional[str] = Field(default=None, env="LOG_FILE")
    LOG_MAX_SIZE: int = Field(default=100, env="LOG_MAX_SIZE")  # MB
    LOG_BACKUP_COUNT: int = Field(default=5, env="LOG_BACKUP_COUNT")
    STRUCTURED_LOGGING: bool = Field(default=True, env="STRUCTURED_LOGGING")
    
    # Monitoring and Health Checks
    HEALTH_CHECK_TIMEOUT: int = Field(default=30, env="HEALTH_CHECK_TIMEOUT")  # seconds
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")  # Alias for backwards compatibility
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    
    # Performance Settings
    REQUEST_TIMEOUT: int = Field(default=30, env="REQUEST_TIMEOUT")  # seconds
    MAX_REQUEST_SIZE: int = Field(default=16, env="MAX_REQUEST_SIZE")  # MB
    BACKGROUND_TASK_TIMEOUT: int = Field(default=300, env="BACKGROUND_TASK_TIMEOUT")  # seconds
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format"""
        if not v.startswith(("postgresql://", "postgresql+psycopg2://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL")
        return v
    
    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format"""
        if not v.startswith(("redis://", "rediss://")):
            raise ValueError("REDIS_URL must be a valid Redis URL")
        return v
    
    @field_validator("CLAIM_DETECTION_THRESHOLD")
    @classmethod
    def validate_threshold(cls, v: int) -> int:
        """Validate claim detection threshold is between 0 and 100"""
        if not 0 <= v <= 100:
            raise ValueError("CLAIM_DETECTION_THRESHOLD must be between 0 and 100")
        return v
    
    @field_validator("DEFAULT_GRACE_PERIOD_DAYS")
    @classmethod
    def validate_grace_period(cls, v: int) -> int:
        """Validate grace period is positive"""
        if v <= 0:
            raise ValueError("DEFAULT_GRACE_PERIOD_DAYS must be positive")
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {valid_levels}")
        return v.upper()
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment"""
        valid_envs = ["development", "staging", "production", "test"]
        if v.lower() not in valid_envs:
            raise ValueError(f"ENVIRONMENT must be one of: {valid_envs}")
        return v.lower()
    
    
    def get_database_url(self) -> str:
        """Get database URL with connection pooling parameters"""
        return self.DATABASE_URL
    
    def get_redis_url(self) -> str:
        """Get Redis URL"""
        return self.REDIS_URL
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT == "development"
    
    def is_testing(self) -> bool:
        """Check if running in test environment"""
        return self.ENVIRONMENT == "test"
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS allowed origins"""
        if self.is_development():
            # Allow common development and admin tools in development
            return [
                "http://localhost:8080",  # pgAdmin
                "http://127.0.0.1:8080"
            ]
        return self.ALLOWED_ORIGINS
    
    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "validate_assignment": True
    }


class DevelopmentSettings(Settings):
    """Development-specific settings"""
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"
    DATABASE_POOL_SIZE: int = 5
    ALLOWED_ORIGINS: List[str] = ["*"]


class ProductionSettings(Settings):
    """Production-specific settings"""
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    
    # Require GitHub token in production
    @field_validator("GITHUB_TOKEN")
    @classmethod
    def github_token_required(cls, v: Optional[str]) -> str:
        if v is None:
            raise ValueError("GITHUB_TOKEN is required in production")
        return v
    
    # Require SendGrid API key in production
    @field_validator("SENDGRID_API_KEY")
    @classmethod
    def sendgrid_key_required(cls, v: Optional[str]) -> str:
        if v is None:
            raise ValueError("SENDGRID_API_KEY is required in production")
        return v


class TestSettings(Settings):
    """Test-specific settings"""
    DEBUG: bool = True
    ENVIRONMENT: str = "test"
    LOG_LEVEL: str = "DEBUG"
    DATABASE_URL: str = "postgresql://test:test@localhost:5432/cookie_detector_test"
    REDIS_URL: str = "redis://localhost:6379/1"  # Use different Redis DB for tests


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings based on environment
    Uses LRU cache to avoid re-reading environment variables
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionSettings()
    elif environment == "test":
        return TestSettings()
    else:
        return DevelopmentSettings()


# Global settings instance
settings = get_settings()


def get_database_engine_config() -> dict:
    """Get database engine configuration"""
    return {
        "pool_size": settings.DATABASE_POOL_SIZE,
        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
        "pool_recycle": settings.DATABASE_POOL_RECYCLE,
        "pool_pre_ping": True,  # Validate connections before use
        "echo": settings.DEBUG,  # Log SQL queries in debug mode
    }


def get_redis_connection_config() -> dict:
    """Get Redis connection configuration"""
    return {
        "max_connections": settings.REDIS_MAX_CONNECTIONS,
        "socket_timeout": settings.REDIS_SOCKET_TIMEOUT,
        "socket_connect_timeout": settings.REDIS_SOCKET_CONNECT_TIMEOUT,
        "retry_on_timeout": True,
        "decode_responses": True,
    }


def get_celery_config() -> dict:
    """Get Celery configuration"""
    return {
        "broker_url": settings.CELERY_BROKER_URL,
        "result_backend": settings.CELERY_RESULT_BACKEND,
        "task_serializer": settings.CELERY_TASK_SERIALIZER,
        "result_serializer": settings.CELERY_RESULT_SERIALIZER,
        "accept_content": settings.CELERY_ACCEPT_CONTENT,
        "timezone": settings.CELERY_TIMEZONE,
        "enable_utc": settings.CELERY_ENABLE_UTC,
        "task_routes": {
            "app.workers.comment_analysis.*": {"queue": "comment_analysis"},
            "app.workers.nudge_check.*": {"queue": "nudge_check"},
            "app.workers.progress_check.*": {"queue": "progress_check"},
            "app.workers.auto_release.*": {"queue": "auto_release_check"},
        },
        "task_default_retry_delay": 60,
        "task_max_retries": 3,
        "task_retry_backoff": True,
        "task_retry_backoff_max": 600,
        "worker_prefetch_multiplier": 1,
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
    }