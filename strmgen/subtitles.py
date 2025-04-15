from typing import Optional
from pathlib import Path

from opensubtitlescom import OpenSubtitles
from config import config
from utils import clean_name, safe_mkdir, ensure_str
from log import setup_logger
logger = setup_logger(__name__)

sub_client: Optional[OpenSubtitles] = None
if (
    config.opensubtitles_download
    and config.opensubtitles_app_name
    and config.opensubtitles_username
    and config.opensubtitles_password
):
    sub_client = OpenSubtitles(config.opensubtitles_app_name, config.opensubtitles_api_key)
    try:
        sub_client.login(config.opensubtitles_username, config.opensubtitles_password)
    except Exception as e:
        logger.warning(f"[SUB] OpenSubtitles login failed: {e}")
        sub_client = None


def _download_and_write(params: dict, filename: str, folder: Path) -> None:
    if not sub_client:
        logger.warning("[SUB] OpenSubtitles client is not initialized.")
        return
    safe_mkdir(folder)
    try:
        logger.info(f"[SUB] Searching for subtitles with: {params}")
        resp = sub_client.search(**params)
        if not getattr(resp, "data", None):
            logger.info(f"[SUB] No subtitle results found for {filename}.")
            return
        srt_data = sub_client.download_and_parse(resp.data[0])
        content = ensure_str(srt_data)
        (folder / filename).write_text(content, encoding="utf-8")
        logger.info(f"[SUB] Subtitle written: {folder / filename}")
    except Exception as e:
        logger.exception(f"Failed to download/write subtitles: {e}")


def download_movie_subtitles(meta: dict, folder: Path, tmdb_id: Optional[str] = None) -> None:
    if not config.opensubtitles_download or not meta:
        return
    filename = f"{clean_name(meta.get('title', ''))}.en.srt"
    filepath = folder / filename
    if filepath.exists():
        logger.info(f"[SUB] Skipping download, subtitle already exists: {filepath}")
        return

    params = {"languages": "en"}
    if tmdb_id:
        params["tmdb_id"] = tmdb_id
    else:
        params.update({
            "query": meta.get("title", ""),
            "year": meta.get("release_date", "")[:4]
        })

    _download_and_write(params, filename, folder)


def download_episode_subtitles(show: str, season: int, ep: int, folder: Path, tmdb_id: Optional[str] = None) -> None:
    if not config.opensubtitles_download or not show:
        return
    filename = f"{clean_name(show)} - S{season:02}E{ep:02}.en.srt"
    filepath = folder / filename
    if filepath.exists():
        logger.info(f"[SUB] Skipping download, subtitle already exists: {filepath}")
        return

    params = {
        "season_number": season,
        "episode_number": ep,
        "languages": "en"
    }
    if tmdb_id:
        params["tmdb_id"] = tmdb_id
    else:
        params["query"] = show

    _download_and_write(params, filename, folder)