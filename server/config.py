from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MICHAL_")

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480  # 8 hours

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-6"

    # RAG
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    faiss_index_path: str = "./data/faiss_index"
    chunk_size: int = 500
    chunk_overlap: int = 50
    retrieval_top_k: int = 5

    # Quota
    default_query_quota: int = 50

    # Database
    database_url: str = "sqlite:///./data/michal.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    allowed_origins: list[str] = [
        "http://localhost:8000",
        "http://localhost:3000",
    ]
