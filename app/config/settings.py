from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Google Gemini Configuration (Primary LLM Provider)
    gemini_api_key: str
    
    # App Configuration  
    debug: bool = False
    port: int = 8000
    host: str = "0.0.0.0"  # ADD THIS
    enable_auth: bool = False
    
    # API Authentication (optional)
    api_key: Optional[str] = "your-secret-api-key"
    
    # File Upload Settings
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: set = {'.jpg', '.jpeg', '.png', '.pdf', '.webp'}
    upload_dir: str = "temp_uploads"
    
    # LLM Settings
    llm_provider: str = "gemini"
    
    # Processing Settings
    max_batch_files: int = 10
    processing_timeout: int = 60  # seconds
    
    # Confidence Settings
    min_confidence_threshold: float = 0.5
    confidence_weights: dict = {
        'text_clarity': 0.4,
        'context_validation': 0.3,
        'position_context': 0.2,
        'format_validation': 0.1
    }
    
    # Alternative LLM Keys (backup options)
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Create upload directory if it doesn't exist
        os.makedirs(self.upload_dir, exist_ok=True)
        
        # Validate Gemini API key
        if not self.gemini_api_key and not self.debug:
            raise ValueError("GEMINI_API_KEY is required")
    
    # Compatibility properties for existing code
    @property
    def MAX_FILE_SIZE(self) -> int:
        return self.max_file_size
    
    @property 
    def ALLOWED_EXTENSIONS(self) -> set:
        return self.allowed_extensions
    
    @property
    def UPLOAD_DIR(self) -> str:
        return self.upload_dir
    
    @property
    def ENABLE_AUTH(self) -> bool:
        return self.enable_auth
    
    @property
    def API_KEY(self) -> Optional[str]:
        return self.api_key
    
    @property
    def GEMINI_API_KEY(self) -> str:
        return self.gemini_api_key
    
    @property
    def LLM_PROVIDER(self) -> str:
        return self.llm_provider
    
    @property
    def DEBUG(self) -> bool:
        return self.debug
    
    @property
    def MIN_CONFIDENCE_THRESHOLD(self) -> float:
        return self.min_confidence_threshold
    
    @property
    def HOST(self) -> str:  # ADD THIS
        return self.host
    
    @property
    def PORT(self) -> int:  # ADD THIS
        return self.port

# Create settings instance
settings = Settings()
