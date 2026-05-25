from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "mysql+pymysql://root:my12345@192.168.39.100:3306/document_agent"

    # LLM (Chinese LLM via OpenAI-compatible API)
    llm_base_url: str = "http://192.168.39.100:11806/v1"
    llm_api_key: str = "empty"
    llm_model_name: str = "qwen3.6:35b"

    # VFS
    vfs_base_dir: str = "/tmp/doc_agent_vfs"

    # Storage
    data_dir: Path = Path("./data")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_prefix": "APP_", "env_file": ".env"}


settings = Settings()
