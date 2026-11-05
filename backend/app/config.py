from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    llm_provider: str = "ollama"  # ollama (local, default) | gemini
    llm_api_key: str = ""
    llm_model: str = "qwen2.5:7b"
    llm_base_url: str = ""
    llm_translate_model: str = ""  # optional: a different local model for uz/ru translation

    ocr_engine: str = "paddle"
    ocr_device: str = "auto"  # auto | cpu | gpu:0

    blur_threshold: float = 60.0
    max_image_side: int = 2400


def get_settings() -> Settings:
    return Settings()
