
import re
from pathlib import Path
from typing import Optional

from config import config, _tmdb_show_cache, _tmdb_season_cache, _tmdb_episode_cache
from subtitles import download_movie_subtitles, download_episode_subtitles
from streams import write_strm_file
from tmdb_helpers import get_movie, search_any_tmdb, tmdb_lookup_tv_show
from utils import clean_name, target_folder, write_if, write_movie_nfo, write_tvshow_nfo
from log import setup_logger
logger = setup_logger(__name__)

RE_MOVIE_TITLE = re.compile(r"^(.*?)\s*\((\d{4})\)")
RE_EPISODE_TAG = re.compile(r"(.*?)[\s\-]+[Ss](\d{1,2})[Ee](\d{1,2})")
RE_24_7_CLEAN  = re.compile(r"(?i)\b24[/-]7\b[\s\-:]*")

_skipped_shows = set()
_skipped_movies = set()
_skipped_247 = set()

def meets_thresholds(meta: dict) -> bool:
    lang = config.tmdb_language.split("-")[0].casefold()
    return (
        meta.get("original_language", "").casefold() == lang and
        meta.get("vote_average", 0) >= config.minimum_tmdb_rating and
        meta.get("vote_count", 0) >= config.minimum_tmdb_votes and
        meta.get("popularity", 0) >= config.minimum_tmdb_popularity
    )

def filter_by_threshold(cache_set: set, name: str, meta: Optional[dict]) -> bool:
    if meta and not meets_thresholds(meta):
        cache_set.add(clean_name(name))
        return False
    return True

def is_anime_group(group: str) -> bool:
    return any(part.strip().lower() == "anime" for part in re.split(r"[-_/\\]", group))

def resolve_anime_fallback(title: str, year: Optional[int]) -> Optional[dict]:
    tv_result = tmdb_lookup_tv_show(title)
    if tv_result:
        tv_result["media_type"] = "tv"
    return tv_result

def process_24_7(name: str, sid: int, root: Path, group: str, headers: dict, url: str):
    title = clean_name(RE_24_7_CLEAN.sub("", name))
    if title in _skipped_247:
        return
    res = search_any_tmdb(title) if config.tmdb_api_key else None
    if not filter_by_threshold(_skipped_247, name, res):
        return
    fld = target_folder(root, "24-7", group, title)
    if not write_strm_file(fld / f"{title}.strm", sid, headers, url):
        return
    if config.write_nfo and res:
        write_if(True, fld / f"{title}.nfo", write_movie_nfo, res)

def process_movie(name: str, sid: int, root: Path, group: str, headers: dict, url: str):
    if name in _skipped_movies:
        return

    m = RE_MOVIE_TITLE.match(name)
    title, yr = (clean_name(m.group(1)), int(m.group(2))) if m else (clean_name(name), None)

    res = get_movie(title, yr) if config.tmdb_api_key else None

    # 🔁 Fallback for anime content
    if not res and is_anime_group(group):
        logger.info(f"[TMDB] 🔁 Attempting fallback TMDB TV search for anime title: {title}")
        res = resolve_anime_fallback(title, yr)

    if not res and not config.tmdb_create_not_found:
        logger.warning(f"[TMDB] ⚠️ No TMDb metadata found for '{title}'")
        return

    if not filter_by_threshold(_skipped_movies, name, res):
        return

    fld = target_folder(root, "Movies", group, f"{title} ({yr or ''})")
    write_strm_file(fld / f"{title}.strm", sid, headers, url)

    if config.write_nfo and res:
        write_if(True, fld / f"{title}.nfo", write_movie_nfo, res)

    if config.opensubtitles_download and res:
        download_movie_subtitles(res, fld, str(res.get("id")))


def process_tv(name: str, sid: int, root: Path, group: str, headers: dict, url: str):
    m = RE_EPISODE_TAG.match(name)
    if not m:
        return
    show, season, ep = clean_name(m.group(1)), int(m.group(2)), int(m.group(3))
    if show in _skipped_shows:
        return

    # Lookup in cache first
    mshow = _tmdb_show_cache.get(show)
    if config.tmdb_api_key and not mshow:
        mshow = tmdb_lookup_tv_show(show) if config.tmdb_api_key else None
        _tmdb_show_cache[show] = mshow

    if not mshow and not config.tmdb_create_not_found:
        logger.warning(f"[TMDB] ⚠️ No TMDb metadata found for '{name}'")
        return   

    # If we found metadata but it doesn't meet thresholds, skip
    if not filter_by_threshold(_skipped_shows, name, mshow):
        return

    season_str = f"{season:02}"
    ep_str = f"{ep:02}"
    base_name = f"{show} - S{season_str}E{ep_str}"

    # Create/show folder
    sf = target_folder(root, "TV Shows", show)
    if config.write_nfo and mshow:
        write_if(True, sf / f"{show}.nfo", write_tvshow_nfo, mshow)

    # Season/Episode folder & .strm
    ef = target_folder(root, "TV Shows", show, f"Season {season_str}", base_name)
    write_strm_file(ef / f"{base_name}.strm", sid, headers, url)

    if config.opensubtitles_download and mshow:
        download_episode_subtitles(show, season, ep, ef, str(mshow.get("id")))
