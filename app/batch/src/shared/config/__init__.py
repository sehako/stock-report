import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BatchConfig:
    database_url: str
    log_level: str = "INFO"


def load_batch_config() -> BatchConfig:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL 환경 변수가 필요합니다.")
    return BatchConfig(
        database_url=database_url,
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
