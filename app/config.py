from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Video Interview POC"
    app_base_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./video_interview.db"

    admin_username: str = "admin"
    admin_password: str = "admin123"
    session_secret: str = "change-this-for-production"

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_deployment: str = ""
    azure_openai_realtime_deployment: str = ""

    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_agent_name: str = "technical-interviewer"
    livekit_inference_stt_model: str = "deepgram/flux-general-en"
    livekit_inference_stt_language: str = "en"
    livekit_inference_llm_model: str = "openai/gpt-oss-120b"
    livekit_inference_tts_model: str = "cartesia/sonic-3"
    livekit_inference_tts_voice: str = "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"


@lru_cache
def get_settings() -> Settings:
    return Settings()
