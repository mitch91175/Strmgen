
import requests
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional
from config import config
from log import setup_logger
logger = setup_logger(__name__)

TMDB_SESSION = requests.Session()
DOWNLOAD_EXECUTOR = ThreadPoolExecutor(max_workers=8)

_tmdb_show_cache = {}
_tmdb_season_cache = {}
_tmdb_episode_cache = {}
_tmdb_movie_cache = {}

def tmdb_get(endpoint: str, params: dict) -> dict:
    params.update({"api_key": config.tmdb_api_key, "language": config.tmdb_language})
    r = TMDB_SESSION.get(f"https://api.themoviedb.org/3{endpoint}", params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def search_any_tmdb(title: str) -> Optional[dict]:
    if not config.tmdb_api_key:
        return None
    try:
        data = tmdb_get("/search/multi", {"query": title})
        results = data.get("results") or []
        for r in results:
            name = r.get("title") or r.get("name")
            if name and name.strip().lower() == title.strip().lower():
                return r
        return results[0] if results else None
    except requests.RequestException as e:
        logger.error("[TMDB] ❌ TMDb multi-search failed for '%s': %s", title, e)
        return None

def get_movie(title: str, year: int) -> Optional[dict]:
    key = (title, year)
    if key in _tmdb_movie_cache:
        return _tmdb_movie_cache[key]
    params = {"query": title}
    if year:
        params["year"] = year
    try:
        data = tmdb_get("/search/movie", params)
        results = data.get("results") or []
        result = results[0] if results else None
        _tmdb_movie_cache[key] = result
        return result
    except requests.RequestException as e:
        logger.error("[TMDB] ❌ get_movie failed for '%s' (year=%s): %s", title, year, e)
        return None

def _download_image(path: str, dest: Path):
    if config.write_nfo_only_if_not_exists and dest.exists():
        logger.info("[TMDB] ⚠️ Skipped image (exists): %s", dest)
        return
    url = f"https://image.tmdb.org/t/p/{config.tmdb_image_size}{path}"
    try:
        r = TMDB_SESSION.get(url, stream=True, timeout=10)
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
        logger.info("[TMDB] 🖼️ Downloaded image: %s", dest)
    except requests.RequestException as e:
        logger.error("[TMDB] ❌ Failed to download %s: %s", url, e)

def download_image(path: str, dest: Path) -> bool:
    DOWNLOAD_EXECUTOR.submit(_download_image, path, dest)

def tmdb_lookup_tv_show(show: str) -> Optional[dict]:
    if show in _tmdb_show_cache:
        return _tmdb_show_cache[show]

    data = tmdb_get("/search/multi", {"query": show})
    results = data.get("results", []) or []
    mshow = next((r for r in results if r.get("media_type") == "tv"), None) or (results[0] if results else None)
    _tmdb_show_cache[show] = mshow
    return mshow