"""Configuration from environment variables / .env. Nothing sensitive is hardcoded."""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"          # "production" hides error details
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    mongodb_uri: str = Field(..., description="MongoDB connection string (required)")
    mongodb_database: str = "rocket_forensics"

    max_upload_size_mb: int = 500
    storage_dir: str = ""                 # empty -> <backend>/storage

    # --- auth ---
    jwt_secret: str = "CHANGE_ME"         # MUST be overridden; production start-up refuses the default
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # --- YOLO ---
    yolo_model_path: str = "models/yolo11n.pt"   # relative paths resolve against the backend directory
    yolo_confidence_threshold: float = Field(
        default=0.35, validation_alias=AliasChoices("yolo_confidence", "yolo_confidence_threshold"))
    yolo_device: str = "cpu"              # "cpu", "cuda:0", "mps", ...
    yolo_classes: str = ""                # optional comma list to keep (e.g. "person,car"); empty = all classes
    max_snapshots_per_analysis: int = 200  # annotated frames saved per analysis run
    frame_sample_rate: float = Field(
        default=2.0, validation_alias=AliasChoices("frame_sample_rate", "analysis_frame_rate"))
    motion_threshold: int = 25            # per-pixel intensity difference (0-255)
    min_contour_area: int = 500           # px^2 (at <=640px processing width)
    motion_gap_seconds: float = 2.0       # debounce: gap that ends a motion event

    cors_origins: str = ""                # comma-separated; empty = no cross-origin access
    frontend_origin: str = ""             # single origin convenience (e.g. http://localhost:5173)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origin_list(self) -> List[str]:
        raw = f"{self.cors_origins},{self.frontend_origin}"
        return list(dict.fromkeys(o.strip() for o in raw.split(",") if o.strip()))

    @property
    def yolo_model_file(self) -> Path:
        p = Path(self.yolo_model_path)
        return p if p.is_absolute() else BASE_DIR / p

    @property
    def yolo_class_filter(self) -> List[str]:
        return [c.strip() for c in self.yolo_classes.split(",") if c.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def storage_root(self) -> Path:
        return Path(self.storage_dir) if self.storage_dir else BASE_DIR / "storage"

    @property
    def evidence_dir(self) -> Path:
        return self.storage_root / "evidence"

    @property
    def processed_dir(self) -> Path:
        return self.storage_root / "processed"

    @property
    def snapshots_dir(self) -> Path:
        return self.storage_root / "snapshots"

    @property
    def reports_dir(self) -> Path:
        return self.storage_root / "reports"

    @property
    def forensic_images_dir(self) -> Path:
        return self.storage_root / "forensic_images"


@lru_cache
def get_settings() -> Settings:
    return Settings()
