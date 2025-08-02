"""Configuration management for Email Agent."""

from pathlib import Path
from typing import Optional

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4", env="OPENAI_MODEL")
    
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field("claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")
    
    # Google Gmail API
    google_client_id: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(None, env="GOOGLE_CLIENT_SECRET")
    
    # Microsoft Graph API
    microsoft_client_id: Optional[str] = Field(None, env="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: Optional[str] = Field(None, env="MICROSOFT_CLIENT_SECRET")
    microsoft_tenant_id: Optional[str] = Field(None, env="MICROSOFT_TENANT_ID")
    
    # Database
    database_url: str = Field("sqlite:///~/.email_agent/data.db", env="DATABASE_URL")
    database_encryption_key: Optional[str] = Field(None, env="DATABASE_ENCRYPTION_KEY")
    
    # Agent Configuration
    max_emails_per_sync: int = Field(1000, env="MAX_EMAILS_PER_SYNC")
    brief_generation_enabled: bool = Field(True, env="BRIEF_GENERATION_ENABLED")
    brief_output_dir: str = Field("~/Briefs", env="BRIEF_OUTPUT_DIR")
    categorization_batch_size: int = Field(100, env="CATEGORIZATION_BATCH_SIZE")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("~/.email_agent/logs/agent.log", env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def data_dir(self) -> Path:
        """Get the data directory path."""
        return Path.home() / ".email_agent"
    
    @property
    def briefs_dir(self) -> Path:
        """Get the briefs directory path."""
        return Path(self.brief_output_dir).expanduser()
    
    @property
    def logs_dir(self) -> Path:
        """Get the logs directory path."""
        return Path(self.log_file).expanduser().parent


# Global settings instance
settings = Settings()