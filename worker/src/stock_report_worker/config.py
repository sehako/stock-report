"""Worker runtime configuration."""

from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="WORKER_", extra="ignore")

    database_url: str = Field(default="sqlite+pysqlite:///:memory:")
    timezone: str = Field(default="Asia/Seoul")
    stock_timeout_seconds: float = Field(default=30.0)
    retry_interval_seconds: int = Field(default=600)
    max_retries: int = Field(default=3)
    consecutive_timeout_limit: int = Field(default=5)

    @property
    def zoneinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def retry_interval(self) -> timedelta:
        return timedelta(seconds=self.retry_interval_seconds)
