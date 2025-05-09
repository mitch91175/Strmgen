# strmgen/core/utils.py
"""
Utility functions: directory handling, Jinja2-backed NFO templating, TMDb filtering, and threshold checks.
"""
from pathlib import Path
from typing import List, Any, Optional, Dict, Callable, TypeVar, Union
from jinja2 import Environment, select_autoescape

from strmgen.core.logger import setup_logger
from strmgen.core.config import get_settings
from strmgen.core.models.dispatcharr import DispatcharrStream
from strmgen.core.models.tv import TVShow, EpisodeMeta, SeasonMeta
from strmgen.core.models.movie import Movie

logger = setup_logger(__name__)
settings = get_settings()

# Initialize Jinja2 environment for XML escaping
env = Environment(
    autoescape=select_autoescape(["xml"]),
    trim_blocks=True,
    lstrip_blocks=True
)

# ─── Path Helpers ────────────────────────────────────────────────────────────
def target_folder(root: Path, category: str, group: str, name: Optional[str]) -> Path:
    """Construct and create target folder path."""
    folder = root / category / group
    if name:
        folder = folder / name
    safe_mkdir(folder)
    return folder

# ─── Conditional Writer ─────────────────────────────────────────────────────
T = TypeVar("T", Movie, TVShow, EpisodeMeta, SeasonMeta)

def write_if(
    cond: bool,
    stream: DispatcharrStream,
    tmdb: T,
    writer_fn: Callable[[DispatcharrStream, T], None],
) -> None:
    """Call writer_fn if cond is True."""
    if cond:
        writer_fn(stream, tmdb)

# ─── NFO Templates ──────────────────────────────────────────────────────────
TVSHOW_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<tvshow>
  <title>{{ show.name | e }}</title>
  <originaltitle>{{ show.original_name | e }}</originaltitle>
  <plot>{{ show.overview | e }}</plot>
  <tmdbid>{{ show.id }}</tmdbid>
  <year>{{ show.first_air_date[:4] if show.first_air_date else '' }}</year>
  <premiered>{{ show.first_air_date }}</premiered>
  <rating>{{ show.vote_average }}</rating>
  <votes>{{ show.vote_count }}</votes>
  {% for genre in show.genre_ids %}
  <genre>{{ genre.name | e }}</genre>
  {% endfor %}
  <status>{{ show.raw.get('status', '') }}</status>
  <studio>{{ show.raw.get('networks', [])[0]['name'] if show.raw.get('networks') else '' }}</studio>
</tvshow>"""

EPISODE_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<episodedetails>
  <title>{{ episode.name | e }}</title>
  <season>{{ episode.season_number }}</season>
  <episode>{{ episode.episode_number }}</episode>
  <plot>{{ episode.overview | e }}</plot>
  <aired>{{ episode.air_date }}</aired>
  <rating>{{ episode.vote_average }}</rating>
  <votes>{{ episode.vote_count }}</votes>
  <tmdbid>{{ episode.id }}</tmdbid>
</episodedetails>"""

MOVIE_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<movie>
  <title>{{ movie.title | e }}</title>
  <originaltitle>{{ movie.original_title | e }}</originaltitle>
  <sorttitle>{{ movie.title | e }}</sorttitle>
  <year>{{ movie.release_date[:4] if movie.release_date else '' }}</year>
  <releasedate>{{ movie.release_date }}</releasedate>
  <plot>{{ movie.overview | e }}</plot>
  <runtime>{{ movie.raw.get('runtime', '') }}</runtime>
  <rating>{{ movie.vote_average }}</rating>
  <votes>{{ movie.vote_count }}</votes>
  <tmdbid>{{ movie.id }}</tmdbid>
  {% for genre in movie.genre_ids %}
  <genre>{{ genre.name | e }}</genre>
  {% endfor %}
  <studio>{{ movie.raw.get('production_companies', [])[0]['name'] if movie.raw.get('production_companies') else '' }}</studio>
  <country>{{ movie.raw.get('production_countries', [])[0]['name'] if movie.raw.get('production_countries') else '' }}</country>
  <status>{{ movie.raw.get('status', '') }}</status>
</movie>"""

# ─── Templating Functions ───────────────────────────────────────────────────
def write_tvshow_nfo(stream: DispatcharrStream, show: TVShow) -> None:
    path = stream.nfo_path
    try:
        xml = env.from_string(TVSHOW_TEMPLATE).render(stream=stream, show=show)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(xml, encoding="utf-8")
        logger.info("[NFO] ✅ TV-Show NFO: %s", path)
        logger.debug("[NFO] TV-Show NFO content: %s", xml)
    except Exception:
        logger.exception("[NFO] ❌ Failed TV-Show NFO: %s", show.name)
        raise


def write_episode_nfo(stream: DispatcharrStream, episode: EpisodeMeta) -> None:
    path = stream.nfo_path
    try:
        xml = env.from_string(EPISODE_TEMPLATE).render(stream=stream, episode=episode)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(xml, encoding="utf-8")
        logger.info("[NFO] ✅ Episode NFO: %s", path)
        logger.debug("[NFO] Episode NFO content: %s", xml)
    except Exception:
        # Include show/episode identifiers for easier debugging
        logger.exception(
            "[NFO] ❌ Failed Episode NFO: %s S%02dE%02d",
            stream.channel_group_name, stream.season, stream.episode
        )
        raise


def write_movie_nfo(stream: DispatcharrStream, movie: Movie) -> None:
    path = stream.nfo_path
    try:
        xml = env.from_string(MOVIE_TEMPLATE).render(stream=stream, movie=movie)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(xml, encoding="utf-8")
        logger.info("[NFO] ✅ Movie NFO: %s", path)
        logger.debug("[NFO] Movie NFO content: %s", xml)
    except Exception:
        logger.exception("[NFO] ❌ Failed Movie NFO: %s", movie.title)
        raise

# ─── TMDb Missing Fields Validators ───────────────────────────────────────────
def tmdb_missing_nfo_movie_fields(meta: Dict[str, Any]) -> List[str]:
    required = ['title', 'release_date', 'overview', 'vote_average', 'id']
    return [k for k in required if not meta.get(k)]


def tmdb_missing_nfo_tv_fields(meta: Dict[str, Any]) -> List[str]:
    required = ['name', 'season_number', 'episode_number', 'overview', 'id']
    return [k for k in required if not meta.get(k)]

# ─── TMDb Filtering ──────────────────────────────────────────────────────────
MetaType = Union[Movie, TVShow]


def filter_by_threshold(name: str, meta: Optional[MetaType]) -> bool:
    if meta is None:
        return True

    # both Movie and TVShow now expose a .year property
    year = meta.year

    failures: list[str] = []
    for field, value, threshold in (
        ("rating",     meta.vote_average,  settings.minimum_tmdb_rating),
        ("votes",      meta.vote_count,    settings.minimum_tmdb_votes),
        ("popularity", meta.popularity,    settings.minimum_tmdb_popularity),
    ):
        if value < threshold:
            failures.append(f"{field} {value}<{threshold}")

    if year is not None and year < settings.minimum_year:
        failures.append(f"year {year}<{settings.minimum_year}")

    if failures:
        logger.info(f"[TMDB] ❌ {name} filtered: {', '.join(failures)}")
        return False

    return True



# ─── Filesystem Helpers ───────────────────────────────────────────────────────
def safe_mkdir(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception("Failed mkdir: %s", path)
