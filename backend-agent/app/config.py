from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure AI Foundry
    foundry_project_endpoint: str = ""
    foundry_model_deployment: str = "gpt-4o"

    # Azure PostgreSQL
    postgres_dsn: str = ""

    # Azure Blob Storage
    blob_connection_string: str = ""
    blob_container: str = "mike"

    # Entra External ID
    entra_tenant_id: str = ""
    entra_client_id: str = ""  # backend app registration
    entra_authority: str = ""  # https://<tenant>.ciamlogin.com/<tenant>.onmicrosoft.com

    # Australian legal databases
    # AustLII does not require an API key for standard search (public SINO engine).
    # Set this only if AustLII provides a dedicated API key for bulk/commercial use.
    austlii_api_key: str = ""

    # App
    frontend_url: str = "http://localhost:3000"
    port: int = 8000

    class Config:
        env_file = ".env"


settings = Settings()
