from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")

    database_url: str
    secret_key: str
    admin_email: str = "admin@uhrbv.nl"
    admin_password: str = ""
    cookie_secure: bool = True
    cookie_name: str = "uhr_session"
    preview_cookie_name: str = "uhr_preview"
    uhrbv_url: str = "https://uhrbv.nl"
    ukrwerkspot_url: str = "https://ukrwerkspot.nl"
    cors_origins: str = "https://uhrbv.nl,https://ukrwerkspot.nl"
    upload_dir: str = "uploads"
    # Not served by any route: applicant documents are downloaded only through the admin API
    private_upload_dir: str = "private_uploads"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_ssl: bool = False
    craftsman_approved_url: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @staticmethod
    def _resolve(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else ROOT / path

    @property
    def uploads_path(self) -> Path:
        return self._resolve(self.upload_dir)

    @property
    def private_uploads_path(self) -> Path:
        return self._resolve(self.private_upload_dir)

    def site_url(self, site: str) -> str:
        urls = {
            "uhrbv": self.uhrbv_url,
            "ukrwerkspot": self.ukrwerkspot_url,
        }
        return urls[site].rstrip("/")


settings = Settings()
