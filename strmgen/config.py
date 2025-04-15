import json
import sys
from pathlib import Path
from typing import List, Optional, Any

from pydantic import BaseModel, Field, ValidationError, field_validator
from log import setup_logger
logger = setup_logger(__name__)

# ─── Config Schema ──────────────────────────────────────────────────────────
class Config(BaseModel):
    access: Optional[str] = None
    refresh: Optional[str] = None

    api_base: str
    stream_base_url: str
    skip_stream_check: bool = False
    remove_strings: List[str] = Field(default_factory=list)

    opensubtitles_download: bool = False
    opensubtitles_app_name: str = "strmgen v1.0.0"
    opensubtitles_api_key: Optional[str] = None
    opensubtitles_username: Optional[str] = None
    opensubtitles_password: Optional[str] = None

    tmdb_api_key: Optional[str] = None
    tmdb_language: str = "en-US"
    tmdb_image_size: str = "original"
    tmdb_create_not_found: bool = False
    minimum_tmdb_rating: float = 0.0
    minimum_tmdb_votes: int = 0
    minimum_tmdb_popularity: float = 0.0

    write_nfo: bool = True
    write_nfo_only_if_not_exists: bool = False

    output_root: str = "/output"
    token_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

    channel_groups: List[str] = Field(default_factory=lambda: ["*"])

    @field_validator("remove_strings", mode="before")
    @classmethod
    def parse_remove_strings(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [s.strip() for s in v.split(',') if s.strip()]
        if isinstance(v, list):
            return v
        raise TypeError('remove_strings must be a list or comma-separated string')

    @property
    def normalized_api_base(self) -> str:
        return self.api_base.rstrip("/")

    @property
    def normalized_stream_ep(self) -> str:
        return self.stream_base_url.lstrip("/")

    @property
    def use_ratings(self) -> bool:
        return bool(self.tmdb_api_key)

    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {', '.join(valid_levels)}")
        return v.upper()


# ─── Load Config ────────────────────────────────────────────────────────────
CONFIG_PATH = Path("./config.json")
SKIP_CACHE_PATH = Path("./skip_cache.json")

def load_config(path: Path) -> Config:
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return Config.model_validate(data)
    except FileNotFoundError:
        logger.error("Config file not found: %s", path)
        sys.exit(1)
    except ValidationError as e:
        logger.error("Invalid configuration:\n%s", e)
        sys.exit(1)

config = load_config(CONFIG_PATH)

# ─── Skip Caches ─────────────────────────────────────────────────────────────
_tmdb_show_cache: dict[str, dict] = {}
_tmdb_season_cache: dict[str, dict] = {}
_tmdb_episode_cache: dict[str, dict] = {}
_tmdb_movie_cache: dict[str, dict] = {}
_skipped_shows: set[str] = set()
_skipped_movies: set[str] = set()
_skipped_247: set[str] = set()

def load_skip_cache() -> None:
    if SKIP_CACHE_PATH.exists():
        try:
            data = json.loads(SKIP_CACHE_PATH.read_text(encoding="utf-8"))
            _skipped_shows.update(data.get("shows", []))
            _skipped_movies.update(data.get("movies", []))
            _skipped_247.update(data.get("247", []))
            logger.info(
                "ℹ️ Loaded skip cache. Shows=%d, Movies=%d, 24/7=%d",
                len(_skipped_shows), len(_skipped_movies), len(_skipped_247)
            )
        except Exception as e:
            logger.warning("⚠️ Failed to load skip cache: %s", e)

def save_skip_cache() -> None:
    data = {
        "shows": list(_skipped_shows),
        "movies": list(_skipped_movies),
        "247": list(_skipped_247)
    }
    try:
        SKIP_CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(
            "ℹ️ Saved skip cache. Shows=%d, Movies=%d, 24/7=%d",
            len(_skipped_shows), len(_skipped_movies), len(_skipped_247)
        )
    except Exception as e:
        logger.warning("⚠️ Failed to save skip cache: %s", e)