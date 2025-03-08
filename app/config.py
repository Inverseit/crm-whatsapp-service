import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """
    Application settings that can be loaded from environment variables.
    """
    # Database settings
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_db: str = Field(default="salon_booking")
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    initialize_db: bool = Field(default=False, description="Whether to initialize the database schema on startup")
    
    # OpenAI API settings
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o")
    
    # WhatsApp API settings
    whatsapp_api_url: str = Field(default="https://graph.facebook.com/v22.0")
    whatsapp_api_key: str = Field(default="")
    whatsapp_phone_number_id: str = Field(default="")
    whatsapp_verify_token: str = Field(default="your_verification_token")
    whatsapp_greeting_template: str = Field(default="greeting")
    whatsapp_template_language_code: str = Field(default="en_US")
    
    
    # App settings
    debug: bool = Field(default=False)
    
    @property
    def database_url(self) -> str:
        """
        Constructs a PostgreSQL connection string from the individual settings.
        """
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    class Config:
        env_file = ".env"
        case_sensitive = False

# Create the settings instance
settings = Settings()