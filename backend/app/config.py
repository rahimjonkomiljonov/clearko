from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    llm_provider: str = "ollama"  # ollama (local, default) | gemini
    llm_api_key: str = ""
    llm_model: str = "qwen2.5:7b"
    llm_base_url: str = ""
    llm_translate_model: str = ""  # optional: a different local model for ru (and uz fallback)
    uz_translator: str = "nllb"  # nllb (needs the 'uz' extra, non-commercial licence) | llm
    nllb_model: str = "facebook/nllb-200-distilled-1.3B"
    nllb_device: str = "auto"  # auto (GPU if >3.5 GB free) | cpu | cuda

    ocr_engine: str = "paddle"
    ocr_device: str = "auto"  # auto | cpu | gpu:0

    blur_threshold: float = 60.0
    max_image_side: int = 2400

    # ---- API ----
    cors_origins: str = "http://localhost:3000"  # comma separated
    trust_proxy: bool = False  # true behind a reverse proxy: use X-Forwarded-For for rate limits
    max_files: int = 10
    max_file_mb: int = 12
    max_total_mb: int = 40
    max_pages: int = 12
    rate_per_hour: int = 10  # analyses per client
    rate_per_day: int = 30
    global_per_day: int = 500  # protects LLM cost whatever the clients do
    job_ttl_s: int = 900  # results are kept in memory this long, then deleted
    max_queue: int = 4  # jobs waiting for the single worker


def get_settings() -> Settings:
    return Settings()
